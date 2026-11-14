from shared.contract import plan_key, validate_scenarios
from shared.make_fake import make_fake


def test_plan_key_is_order_independent():
    assert plan_key(["B-3", "A-2", "A-3"]) == "A-2,A-3,B-3"
    assert plan_key([]) == ""


def test_fake_is_valid():
    assert validate_scenarios(make_fake()) == []


def test_lookup_covers_all_plans_up_to_4():
    night = make_fake()["nights"]["typical"]
    assert len(night["lookup"]) == 4048
    assert "" in night["lookup"]


def test_validator_catches_missing_night_field():
    d = make_fake()
    del d["nights"]["typical"]["calls"]
    assert any("calls" in e for e in validate_scenarios(d))


def test_validator_catches_late_id_not_in_calls():
    d = make_fake()
    d["nights"]["typical"]["baseline"]["late_ids"].append(10**9)
    assert validate_scenarios(d) != []


def test_validator_requires_city():
    d = make_fake()
    del d["city"]
    assert any("city" in e for e in validate_scenarios(d))
