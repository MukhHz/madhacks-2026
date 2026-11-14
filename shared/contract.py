"""The data contract between Person A (pipeline) and Person B (web page).

`web/data/scenarios.json` must pass `validate_scenarios` before anyone ships it.
"""
from typing import Iterable

NIGHTS = ("typical", "holiday", "heat")
HOSPITAL_IDS = ("A", "B", "C")
N_BLOCKS = 6


def plan_key(slots: Iterable[str]) -> str:
    """Canonical key for a set of slots like "A-3": sorted, comma-joined. Empty plan -> ""."""
    return ",".join(sorted(slots))


def _check_grid(name: str, grid, errors: list[str]) -> None:
    if (not isinstance(grid, list) or len(grid) != len(HOSPITAL_IDS)
            or any(not isinstance(r, list) or len(r) != N_BLOCKS for r in grid)):
        errors.append(f"{name}: must be a 3x6 grid")
        return
    if any(not isinstance(v, (int, float)) or v < 0 for r in grid for v in r):
        errors.append(f"{name}: values must be numbers >= 0")


def _check_result(name: str, res, call_ids: set, errors: list[str]) -> None:
    if not isinstance(res, dict):
        errors.append(f"{name}: must be an object")
        return
    for key in ("late_ids", "stuck", "door_wait_min"):
        if key not in res:
            errors.append(f"{name}: missing {key}")
    if "late_ids" in res:
        bad = [i for i in res["late_ids"] if i not in call_ids]
        if bad:
            errors.append(f"{name}: late_ids not in calls: {bad[:5]}")
    for key in ("stuck", "door_wait_min"):
        if key in res:
            _check_grid(f"{name}.{key}", res[key], errors)


def _check_night(name: str, night, errors: list[str]) -> None:
    p = f"nights.{name}"
    if not isinstance(night, dict):
        errors.append(f"{p}: must be an object")
        return
    for key in ("label", "calls", "real", "baseline", "ambulances_plus2", "ai_plans", "lookup"):
        if key not in night:
            errors.append(f"{p}: missing {key}")
    calls = night.get("calls", [])
    call_ids = set()
    for c in calls:
        missing = [k for k in ("id", "t", "lat", "lon", "hosp", "severity") if k not in c]
        if missing:
            errors.append(f"{p}.calls: call missing {missing}")
            break
        if not 0 <= c["t"] <= 720:
            errors.append(f"{p}.calls: t out of range for call {c['id']}")
            break
        if c["hosp"] not in HOSPITAL_IDS:
            errors.append(f"{p}.calls: unknown hospital {c['hosp']}")
            break
        call_ids.add(c["id"])
    for key in ("baseline", "ambulances_plus2"):
        if key in night:
            _check_result(f"{p}.{key}", night[key], call_ids, errors)
    plans = night.get("ai_plans", {})
    for k in range(1, 7):
        plan = plans.get(str(k)) if isinstance(plans, dict) else None
        if plan is None:
            errors.append(f"{p}.ai_plans: missing budget {k}")
            continue
        if len(plan.get("slots", [])) != k:
            errors.append(f"{p}.ai_plans.{k}: slots must have length {k}")
        _check_result(f"{p}.ai_plans.{k}", plan, call_ids, errors)
    lookup = night.get("lookup", {})
    if isinstance(lookup, dict):
        if "" not in lookup and "lookup" in night:
            errors.append(f"{p}.lookup: missing empty plan \"\"")
        for key, res in lookup.items():
            if key and key != plan_key(key.split(",")):
                errors.append(f"{p}.lookup: key not canonical: {key}")
                break
            _check_result(f"{p}.lookup[{key}]", res, call_ids, errors)


def validate_scenarios(d: dict) -> list[str]:
    """Return a list of human-readable problems; empty list means valid."""
    errors: list[str] = []
    city = d.get("city")
    if not isinstance(city, dict) or not isinstance(city.get("name"), str) or not isinstance(city.get("area"), str):
        errors.append("city: must have string name and area")
    if not isinstance(d.get("blocks"), list) or len(d["blocks"]) != N_BLOCKS:
        errors.append("blocks: must list 6 blocks")
    hosps = d.get("hospitals")
    if not isinstance(hosps, list) or [h.get("id") for h in hosps] != list(HOSPITAL_IDS):
        errors.append("hospitals: must be A, B, C in order")
    if not isinstance(d.get("costs"), dict) or not {"nurse_shift_usd", "ambulance_night_usd"} <= set(d["costs"]):
        errors.append("costs: needs nurse_shift_usd and ambulance_night_usd")
    nights = d.get("nights")
    if not isinstance(nights, dict):
        errors.append("nights: missing")
        return errors
    for name in NIGHTS:
        if name not in nights:
            errors.append(f"nights: missing {name}")
        else:
            _check_night(name, nights[name], errors)
    return errors
