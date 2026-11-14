"""The digital twin: replay one Friday night (6 PM -> 6 AM) of 911 calls, ambulances, and ER doors.

Plain-English model:
  1. Each call arrives at its real time. After a short dispatch delay, the nearest free ambulance goes.
     If none is free, the call waits (urgent calls, severity 1-3, go first).
  2. The crew spends time on scene. If the patient is transported, the crew drives to the call's ER.
  3. At the ER door the crew waits until the ER accepts the patient (limited handoffs at a time).
     That waiting is the "offload delay": the ambulance is stuck and cannot take new 911 calls.
  4. An offload nurse at that ER (during their 2-hour block) takes patients off crews, up to
     `nurse_patients` at once. A crew handing to the nurse is released after `nurse_handoff_min`.
     The nurse keeps the patient until the ER accepts them.
  5. A call is "late" if it is urgent (severity <= 3) and the ambulance took more than 10 minutes.
"""
import math
import random
from collections import deque
from dataclasses import dataclass, field

import simpy

from pipeline.config import HOSPITALS, LATE_MIN

N_BLOCKS = 6
BLOCK_MIN = 120
SAMPLE_EVERY_MIN = 5
HOSP_IDS = [h["id"] for h in HOSPITALS]
HOSP_POS = {h["id"]: (h["lat"], h["lon"]) for h in HOSPITALS}


@dataclass(frozen=True)
class SimParams:
    n_ambulances: int = 35
    speed_kmh: float = 25.0
    dispatch_delay_min: float = 1.5
    scene_min: float = 15.0
    door_capacity: tuple[tuple[int, ...], ...] = ((2,) * 6, (2,) * 6, (2,) * 6)  # [hosp][block]
    handoff_mean_min: float = 25.0
    cleanup_min: float = 10.0
    nurse_handoff_min: float = 20.0
    nurse_patients: int = 4
    urgent_max_severity: int = 3


@dataclass
class NightResult:
    late_ids: list[int]
    response_min: dict[int, float]
    stuck: list[list[float]]           # 3x6 mean ambulances at the ER door
    door_wait_min: list[list[float]]   # 3x6 mean minutes a crew spent at the door, by arrival block
    time_at_hosp_min: list[float] = field(default_factory=list)


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _block(t: float) -> int:
    return min(N_BLOCKS - 1, max(0, int(t // BLOCK_MIN)))


def run_night(calls: list[dict], params: SimParams, slots: frozenset[str] = frozenset(),
              extra_ambulances: int = 0, seed: int = 0) -> NightResult:
    calls = sorted(calls, key=lambda c: (c["t"], c["id"]))
    rng = random.Random(seed)
    # Draw all randomness up front, in a fixed order, so every plan replays the same night
    # (same ambulance starts, same handoff times): only the plan differs between runs.
    picks = [calls[rng.randrange(len(calls))] for _ in range(params.n_ambulances + 50)]
    starts = [(c["lat"], c["lon"]) for c in picks]
    handoff = {c["id"]: rng.expovariate(1 / params.handoff_mean_min) for c in calls}

    env = simpy.Environment()
    n_amb = params.n_ambulances + extra_ambulances
    pos = starts[:n_amb]
    free = set(range(n_amb))
    waiting: list[tuple[int, float, dict]] = []         # (priority, ready time, call)
    door_queue = {h: deque() for h in HOSP_IDS}         # patients waiting for the ER to accept
    in_service = {h: 0 for h in HOSP_IDS}
    nurse_load = {h: 0 for h in HOSP_IDS}
    at_door = {h: 0 for h in HOSP_IDS}                  # crews currently stuck at each door
    response: dict[int, float] = {}
    samples = [[[] for _ in range(N_BLOCKS)] for _ in HOSP_IDS]
    door_waits = [[[] for _ in range(N_BLOCKS)] for _ in HOSP_IDS]
    time_at_hosp: list[float] = []

    def capacity(h: str) -> int:
        return params.door_capacity[HOSP_IDS.index(h)][_block(env.now)]

    def door_try(h: str):
        while door_queue[h] and in_service[h] < capacity(h):
            item = door_queue[h].popleft()
            in_service[h] += 1
            item["started"].succeed()
            env.process(serve(h, item))

    def serve(h: str, item: dict):
        yield env.timeout(handoff[item["id"]])
        in_service[h] -= 1
        item["done"].succeed()
        door_try(h)

    def block_ticks(h: str):
        for b in range(1, N_BLOCKS):
            yield env.timeout(b * BLOCK_MIN - env.now)
            door_try(h)                                   # capacity may have changed

    def nurse_holds(h: str, item: dict):
        yield item["started"]                            # ER accepted the patient from the nurse
        nurse_load[h] -= 1

    def mission(i: int, call: dict):
        dest = (call["lat"], call["lon"])
        yield env.timeout(_km(pos[i], dest) / params.speed_kmh * 60)
        response[call["id"]] = env.now - call["t"]
        yield env.timeout(params.scene_min)
        pos[i] = dest
        if call.get("transport"):
            h = call["hosp"]
            yield env.timeout(_km(dest, HOSP_POS[h]) / params.speed_kmh * 60)
            arrived = env.now
            item = {"id": call["id"], "started": env.event(), "done": env.event()}
            door_queue[h].append(item)
            at_door[h] += 1
            door_try(h)
            if f"{h}-{_block(arrived)}" in slots and nurse_load[h] < params.nurse_patients:
                nurse_load[h] += 1
                env.process(nurse_holds(h, item))
                yield env.any_of([item["done"], env.timeout(params.nurse_handoff_min)])
            else:
                yield item["done"]
            at_door[h] -= 1
            door_waits[HOSP_IDS.index(h)][_block(arrived)].append(env.now - arrived)
            time_at_hosp.append(env.now - arrived + params.cleanup_min)
            yield env.timeout(params.cleanup_min)
            pos[i] = HOSP_POS[h]
        free.add(i)
        dispatch_waiting()

    def nearest_free(dest) -> int:
        return min(free, key=lambda i: _km(pos[i], dest))

    def send(call: dict):
        i = nearest_free((call["lat"], call["lon"]))
        free.discard(i)
        env.process(mission(i, call))

    def dispatch_waiting():
        while free and waiting:
            waiting.sort(key=lambda w: (w[0], w[1]))
            _, _, call = waiting.pop(0)
            send(call)

    def arrival(call: dict):
        yield env.timeout(call["t"] + params.dispatch_delay_min)
        priority = 0 if call["severity"] <= params.urgent_max_severity else 1
        waiting.append((priority, env.now, call))
        dispatch_waiting()

    def sampler():
        while env.now < N_BLOCKS * BLOCK_MIN:
            for k, h in enumerate(HOSP_IDS):
                samples[k][_block(env.now)].append(at_door[h])
            yield env.timeout(SAMPLE_EVERY_MIN)

    for c in calls:
        env.process(arrival(c))
    for h in HOSP_IDS:
        env.process(block_ticks(h))
    env.process(sampler())
    env.run()

    def mean(xs):
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    sev = {c["id"]: c["severity"] for c in calls}
    late = sorted(i for i, r in response.items() if r > LATE_MIN and sev[i] <= params.urgent_max_severity)
    return NightResult(
        late_ids=late,
        response_min=response,
        stuck=[[mean(samples[k][b]) for b in range(N_BLOCKS)] for k in range(len(HOSP_IDS))],
        door_wait_min=[[mean(door_waits[k][b]) for b in range(N_BLOCKS)] for k in range(len(HOSP_IDS))],
        time_at_hosp_min=time_at_hosp,
    )
