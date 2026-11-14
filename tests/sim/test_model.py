from dataclasses import replace

from sim.model import SimParams, run_night
from tests.sim.toy import jammed_a_night

TIGHT = SimParams(n_ambulances=14, door_capacity=((1,) * 6, (2,) * 6, (2,) * 6), handoff_mean_min=30)


def test_same_seed_same_result():
    calls = jammed_a_night()
    a, b = run_night(calls, TIGHT, seed=4), run_night(calls, TIGHT, seed=4)
    assert a.late_ids == b.late_ids and a.stuck == b.stuck


def test_nurse_never_increases_late_count():
    calls = jammed_a_night()
    for seed in range(5):
        base = run_night(calls, TIGHT, seed=seed)
        with_nurse = run_night(calls, TIGHT, frozenset({"A-3"}), seed=seed)
        assert len(with_nurse.late_ids) <= len(base.late_ids)


def test_nurse_shortens_door_queue_in_its_block():
    calls = jammed_a_night()
    base = run_night(calls, TIGHT, seed=0)
    nurse = run_night(calls, TIGHT, frozenset({"A-3"}), seed=0)
    assert nurse.stuck[0][3] < base.stuck[0][3]


def test_extra_ambulances_reduce_response():
    calls = jammed_a_night()
    base = run_night(calls, TIGHT, seed=0)
    more = run_night(calls, TIGHT, extra_ambulances=4, seed=0)
    assert sum(more.response_min.values()) < sum(base.response_min.values())


def test_no_transport_calls_never_reach_door():
    calls = [dict(c, transport=False) for c in jammed_a_night()]
    r = run_night(calls, TIGHT, seed=0)
    assert r.time_at_hosp_min == []
    assert all(v == 0 for row in r.stuck for v in row)


def test_shapes_and_every_call_answered():
    calls = jammed_a_night()
    r = run_night(calls, TIGHT, seed=0)
    assert len(r.stuck) == 3 and all(len(row) == 6 for row in r.stuck)
    assert len(r.door_wait_min) == 3 and all(len(row) == 6 for row in r.door_wait_min)
    assert set(r.response_min) == {c["id"] for c in calls}
    assert set(r.late_ids) == {i for i, v in r.response_min.items() if v > 10}
