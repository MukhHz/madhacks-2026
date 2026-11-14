"""Writes a contract-valid FAKE web/data/scenarios.json (toy model from the mockup).

Lets Person B build the page before the real pipeline exists. Run: python -m shared.make_fake
"""
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from shared.contract import HOSPITAL_IDS, N_BLOCKS, plan_key

BLOCKS = ["6-8P", "8-10P", "10P-12A", "12-2A", "2-4A", "4-6A"]
HOSPITALS = [
    {"id": "A", "lat": 40.655, "lon": -73.945},
    {"id": "B", "lat": 40.600, "lon": -73.960},
    {"id": "C", "lat": 40.690, "lon": -73.915},
]
NIGHT_SPECS = {
    "typical": {"calls": 560, "seed": 11, "label": "Typical Friday (FAKE)",
                "cong": [[1, 2, 4, 5, 4, 2], [0, 1, 2, 3, 2, 1], [0, 0, 1, 1, 1, 0]]},
    "holiday": {"calls": 680, "seed": 23, "label": "Holiday weekend Friday (FAKE)",
                "cong": [[2, 3, 5, 6, 5, 3], [1, 2, 3, 4, 3, 2], [0, 1, 1, 2, 1, 1]]},
    "heat": {"calls": 640, "seed": 37, "label": "Heat wave Friday (FAKE)",
             "cong": [[1, 1, 2, 3, 2, 1], [2, 3, 5, 6, 4, 2], [1, 1, 2, 2, 1, 0]]},
}
ALL_SLOTS = [f"{h}-{b}" for h in HOSPITAL_IDS for b in range(N_BLOCKS)]


def _gen_calls(n: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    weights = np.array([.13, .15, .19, .2, .18, .15])
    calls = []
    for i in range(n):
        lat, lon = 40.58 + rng.random() * 0.15, -74.02 + rng.random() * 0.15
        b = int(rng.choice(6, p=weights))
        t = round(b * 120 + rng.random() * 119.9, 1)
        d = [np.hypot(h["lat"] - lat, h["lon"] - lon) for h in HOSPITALS]
        calls.append({"id": i, "t": t, "lat": round(lat, 5), "lon": round(lon, 5),
                      "hosp": HOSPITALS[int(np.argmin(d))]["id"], "severity": int(rng.integers(1, 9)),
                      "_u": float(rng.random())})
    return calls


def _result(calls, cong, slots: frozenset, amb: bool = False) -> dict:
    stuck = [[0.0] * N_BLOCKS for _ in HOSPITAL_IDS]
    for h, hid in enumerate(HOSPITAL_IDS):
        for b in range(N_BLOCKS):
            red = (2.6 if f"{hid}-{b}" in slots else 0) + (1 if b > 0 and f"{hid}-{b - 1}" in slots else 0)
            stuck[h][b] = round(max(0.0, cong[h][b] - red), 1)
    late = []
    for c in calls:
        s = stuck[HOSPITAL_IDS.index(c["hosp"])][min(5, int(c["t"] // 120))]
        p = 0.06 + 0.11 * s
        if amb:
            p = max(0.04, p - 0.025)
        if c["_u"] < p:
            late.append(c["id"])
    door = [[round(25 + 9 * v, 1) for v in row] for row in stuck]
    return {"late_ids": late, "stuck": stuck, "door_wait_min": door}


def _greedy(calls, cong, budget: int) -> list[str]:
    plan: list[str] = []
    for _ in range(budget):
        best = min((s for s in ALL_SLOTS if s not in plan),
                   key=lambda s: len(_result(calls, cong, frozenset(plan + [s]))["late_ids"]))
        plan.append(best)
    return plan


def make_fake(seed: int = 7) -> dict:
    nights = {}
    for name, spec in NIGHT_SPECS.items():
        calls = _gen_calls(spec["calls"], spec["seed"] + seed)
        cong = spec["cong"]
        lookup = {}
        for k in range(5):
            for combo in combinations(ALL_SLOTS, k):
                lookup[plan_key(combo)] = _result(calls, cong, frozenset(combo))
        greedy = _greedy(calls, cong, 6)
        ai = {str(k): {"slots": greedy[:k], **_result(calls, cong, frozenset(greedy[:k]))} for k in range(1, 7)}
        nights[name] = {
            "label": spec["label"],
            "calls": [{k: v for k, v in c.items() if k != "_u"} for c in calls],
            "real": {"median_response_min": 8.6, "median_time_at_hospital_min": 42.7},
            "baseline": _result(calls, cong, frozenset()),
            "ambulances_plus2": _result(calls, cong, frozenset(), amb=True),
            "ai_plans": ai,
            "lookup": lookup,
        }
    return {
        "generated_at": "FAKE",
        "city": {"name": "New York City", "area": "Brooklyn"},
        "blocks": BLOCKS,
        "hospitals": HOSPITALS,
        "costs": {"nurse_shift_usd": 180, "ambulance_night_usd": 3600},
        "nights": nights,
    }


def main(out: Path = Path("web/data/scenarios.json")) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(make_fake(), separators=(",", ":")))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
