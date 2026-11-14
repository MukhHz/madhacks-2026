# Offload Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-page planner that, for a real Brooklyn Friday night, recommends where and when to place offload nurses (3 hospitals × 6 two-hour blocks), lets the user try their own plan, and compares it with "do nothing" and "+2 ambulances", using real NYC 911 data and a calibrated simulation.

**Architecture:** Person A's Python pipeline pulls NYC EMS data, simulates each night with SimPy, calibrates to real response and time-at-hospital numbers, runs a greedy optimizer, and precomputes every result into one file, `web/data/scenarios.json`. Person B's static page (HTML + d3 SVG map) reads only that file, so nothing computes live on stage. A shared contract validator gates the file in both directions.

**Tech Stack:** Python 3.11, simpy 4.1.1, pandas 2.2.3, numpy 2.1.3, requests 2.32.3, matplotlib 3.9.2, pytest 8.3.4 · static HTML/JS, d3 7.9.0 (cdnjs) · stretch: lightgbm 4.5.0 + MLflow on Databricks, FastAPI 0.115.6 + Anthropic SDK.

**Spec:** `PLAN.md` (team plan + JSON contract) and `mockup/offload-planner.html` (target screen). `root-cause-design.md` is outdated; ignore it.

## Global Constraints

- Owners: Person A edits only `pipeline/`, `sim/`, `data/`, `tests/pipeline/`, `tests/sim/`. Person B edits only `web/` (except `web/data/scenarios.json`), `slides/`, `agent/`. Both may edit `shared/` only together.
- Only Person A's export writes `web/data/scenarios.json` once Task A6 lands. Before then, `shared/make_fake.py` writes it.
- Night window: **Friday 18:00 → Saturday 06:00** local time. `t` = minutes since 18:00 (0–720).
- Blocks: `["6-8P","8-10P","10P-12A","12-2A","2-4A","4-6A"]`. Block index = `int(t // 120)`, clamped to 0–5.
- Hospitals: ids `"A","B","C"`, anonymized, fixed coordinates in `pipeline/config.py`. Each call goes to the nearest hospital (an assumption; say so on the page).
- Slot key = `"<hospital>-<block index>"`, e.g. `"A-3"`. Plan key = slot keys sorted ascending and joined with `","`. The empty plan key is `""`.
- "Late" = response time over **10 minutes**.
- Calibration targets (real Brooklyn data): median response **8.6 min**, median time at hospital **42.7 min**. The simulation must land within ±10% of both.
- Costs: nurse shift (2 h) **$180**; +2 ambulances for the night **$3,600**. Both are placeholders until verified, and the page footer says so.
- `lookup` covers every plan of **0–4** shifts (4,048 plans per night). AI plans cover budgets **1–6**.
- Page labels: **REAL** for NYC data values, **SIM** for simulation outputs. Hospitals are never named.
- Never commit or push from an agent session. Print the git commands for the human.
- **Any-city rule (digital twin framing):** every city-specific value (data URL, borough filter, hospital coordinates, costs, centroid file, calibration targets' source) lives only in `pipeline/config.py` as one `CITY` dict. No other file may hard-code "Brooklyn", "NYC", or coordinates. `scenarios.json` carries a top-level `"city": {"name": "New York City", "area": "Brooklyn"}` and the page header reads it.

## Review Focus

1. **Calls after midnight.** A Friday-only date filter drops the 12–6 AM half of the night. The fetch must pull Friday 18:00 → Saturday 06:00 (tested in Task A1).
2. **Calls never transported or missing timestamps.** These have no hospital arrival or close time. They still count as demand but must not count toward time at hospital (tested in Task A2).
3. **Bad time-at-hospital values.** Negative values or values over 10 hours exist in raw data and must be dropped before medians are taken (tested in Task A2).
4. **Tapping slots in any order.** The page must build the same plan key as Python, or the lookup misses (tested in Task 0 contract + Task B3).
5. **More than 4 shifts placed, or budget lowered below placed shifts.** The page must show a clear message and must not crash on a missing lookup key (tested in Task B3).

---

## File Structure

```
shared/contract.py        validate_scenarios(d) -> list[str]; plan_key(slots) -> str
shared/make_fake.py       writes a contract-valid fake web/data/scenarios.json
pipeline/config.py        HOSPITALS, BLOCKS, LATE_MIN, costs, Socrata URL
pipeline/fetch.py         fetch_night_calls(...) -> raw parquet
pipeline/clean.py         clean_calls, attach_locations, pick_nights, real_stats
sim/model.py              SimParams, NightResult, run_night(...)
sim/calibrate.py          calibrate(...) -> SimParams; sim-vs-real chart
sim/optimize.py           greedy_plans(...), all_plan_keys(...)
sim/export.py             build_night(...), build_scenarios(...), main()
web/index.html, web/app.js, web/style.css, web/schedule.html
web/data/scenarios.json   the only data the page reads
web/data/brooklyn_zcta.geojson
agent/server.py           (stretch) chat endpoint over lookups
tests/                    pytest, mirrors folders
```

---

### Task 0 (both, hour 1): Repo skeleton, contract validator, fake data

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `shared/__init__.py`, `shared/contract.py`, `shared/make_fake.py`
- Test: `tests/test_contract.py`

**Interfaces:**
- Produces: `plan_key(slots: Iterable[str]) -> str`; `validate_scenarios(d: dict) -> list[str]` (empty list = valid); `make_fake(seed: int = 7) -> dict`.

- [ ] **Step 1: Write the failing tests**

```python
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
    d = make_fake(); del d["nights"]["typical"]["calls"]
    assert any("calls" in e for e in validate_scenarios(d))

def test_validator_catches_late_id_not_in_calls():
    d = make_fake(); d["nights"]["typical"]["baseline"]["late_ids"].append(10**9)
    assert validate_scenarios(d) != []
```

- [ ] **Step 2: Run** `pytest tests/test_contract.py -v`. Expected: FAIL, module not found.

- [ ] **Step 3: Implement `shared/contract.py`.** Validate exactly the shape in `PLAN.md` § contract: top-level `city` (`name`, `area` strings), `blocks` (6 items), `hospitals` (3, ids A/B/C), `costs`, `nights` with keys `typical`, `holiday`, `heat`. Each night has `label`, `calls` (each `id,t,lat,lon,hosp,severity`; `0 <= t <= 720`), `real`, `baseline`, `ambulances_plus2`, `ai_plans` (keys `"1"`–`"6"`, each with `slots` of that length plus a result), and `lookup`. Every result has `late_ids` (subset of call ids), `stuck` (3×6 numbers ≥ 0), and `door_wait_min` (3×6 numbers ≥ 0).

- [ ] **Step 4: Implement `shared/make_fake.py`** by porting the mock's toy model (`mockup/offload-planner.html`: `genCalls`, `stuck`, `late`) to Python. Iterate plans with `itertools.combinations` over the 18 slots for k = 0..4. Give `main()` a write to `web/data/scenarios.json`.

- [ ] **Step 5: Run** `pytest -v` → PASS. Run `python -m shared.make_fake` and check the file is under 15 MB.

- [ ] **Step 6: Commit (human runs)**

```bash
git add requirements.txt pytest.ini shared tests/test_contract.py web/data/scenarios.json
git commit -m "Add data contract, validator, and fake scenarios"
```

---

### Task A1 (Person A): Fetch real Friday-night calls

**Files:**
- Create: `pipeline/__init__.py`, `pipeline/config.py`, `pipeline/fetch.py`
- Test: `tests/pipeline/test_fetch.py`

**Interfaces:**
- Produces: `night_where(start: date, end: date) -> str` (the SoQL `$where`); `fetch_night_calls(start: date, end: date, out: Path) -> Path` (parquet of raw rows, borough BROOKLYN). Constants in `config.py`: `SOCRATA_URL = "https://data.cityofnewyork.us/resource/76xm-jjuj.json"`, `HOSPITALS = [{"id":"A","lat":..,"lon":..}, ...]`, `BLOCKS`, `LATE_MIN = 10`, `NURSE_SHIFT_USD = 180`, `AMB_NIGHT_USD = 3600`.

- [ ] **Step 1: Write failing tests.** `night_where(date(2026,9,1), date(2026,9,30))` must contain `"BROOKLYN"`, must select both `date_extract_dow(incident_datetime)=5 AND date_extract_hh(incident_datetime)>=18` and `date_extract_dow(incident_datetime)=6 AND date_extract_hh(incident_datetime)<6`, and must not contain a bare `dow=5` filter alone. A test with a mocked `requests.get` (monkeypatch) returning two pages of 2 rows then an empty page must make `fetch_night_calls` write 4 rows and request `$offset=0` then `$offset=50000`.
- [ ] **Step 2: Run** `pytest tests/pipeline/test_fetch.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Page with `$limit=50000` + `$offset` + `$order=incident_id` until an empty page. Select only the columns `clean.py` needs (see Task A2). Pick 3 hospital coordinates spread across central, south, and east Brooklyn.
- [ ] **Step 4: Run tests → PASS.** Then do a live pull: `python -m pipeline.fetch 2024-01-01 2026-09-30 data/raw/fridays.parquet`. Expected: at least 90,000 rows. (`data/raw/` is gitignored.)
- [ ] **Step 5: Commit** `pipeline/ tests/pipeline/`.

---

### Task A2 (Person A): Clean, locate, pick nights, real stats

**Files:**
- Create: `pipeline/clean.py`, `data/zcta_centroids.csv` (Brooklyn rows from the Census 2023 Gazetteer ZCTA file: `zip,lat,lon`)
- Test: `tests/pipeline/test_clean.py`

**Interfaces:**
- Consumes: raw parquet from A1; `HOSPITALS` from config.
- Produces:
  - `clean_calls(raw: pd.DataFrame) -> pd.DataFrame`, with columns `incident_id, night (date of the Friday), t (float min since 18:00), zip, severity (int), transport (bool: first_hosp_arrival_datetime present), response_min (float|NaN), time_at_hosp_min (float|NaN)`
  - `attach_locations(df, centroids: pd.DataFrame, seed: int = 0) -> pd.DataFrame`, which adds `lat, lon, hosp`
  - `pick_nights(df) -> dict[str, date]`, with keys `typical, holiday, heat`
  - `real_stats(df) -> dict`, with keys `median_response_min, median_time_at_hospital_min`

- [ ] **Step 1: Write failing tests.**

```python
def test_after_midnight_belongs_to_friday_night():   # Sat 01:30 -> night = Fri, t = 450
def test_untransported_call_kept_with_nan_time_at_hosp():
def test_time_at_hosp_outliers_dropped():           # -5 and 700 -> NaN; 42 kept
def test_attach_locations_nearest_hospital_and_jitter_is_deterministic():
def test_real_stats_medians():                      # tiny frame with known medians
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.**
  - `time_at_hosp_min = (incident_close_datetime - first_hosp_arrival_datetime)` in minutes. Keep only values in (0, 600].
  - `response_min = incident_response_seconds_qy / 60`. Keep only rows where `valid_incident_rspns_time_indc == "Y"`.
  - Location = zip centroid + uniform jitter of ±0.004° from `np.random.default_rng(seed)`. Drop rows whose zip has no centroid.
  - `pick_nights` picks:
    - `typical`: the night whose call count is closest to the median
    - `holiday`: the highest-count night within ±3 days of a US federal holiday
    - `heat`: the highest-count night in June–August
- [ ] **Step 4: Run → PASS.** Then on the real pull, print `real_stats` for 2024–2026. Expected: about 8.6 and 42.7.
- [ ] **Step 5: Commit** `pipeline/clean.py data/zcta_centroids.csv tests/pipeline/test_clean.py`.

---

### Task A3 (Person A): Simulation engine

**Files:**
- Create: `sim/__init__.py`, `sim/model.py`
- Test: `tests/sim/test_model.py`

**Interfaces:**
- Consumes: a night's rows from `attach_locations` as `list[dict]` with keys `id, t, lat, lon, hosp, severity`, plus `transport: bool` (`True` when the real call reached a hospital).
- Produces:

```python
@dataclass(frozen=True)
class SimParams:
    n_ambulances: int = 35
    speed_kmh: float = 25.0
    dispatch_delay_min: float = 1.5
    door_capacity: tuple[tuple[int, ...], ...] = ((2,)*6, (2,)*6, (2,)*6)  # [hosp][block]
    handoff_mean_min: float = 25.0
    cleanup_min: float = 10.0

@dataclass
class NightResult:
    late_ids: list[int]
    response_min: dict[int, float]
    stuck: list[list[float]]          # 3x6 mean ambulances waiting at door
    door_wait_min: list[list[float]]  # 3x6 mean wait+handoff for arrivals in block
    time_at_hosp_min: list[float]

def run_night(calls: list[dict], params: SimParams, slots: frozenset[str] = frozenset(),
              extra_ambulances: int = 0, seed: int = 0) -> NightResult
```

- [ ] **Step 1: Write failing tests.**
  - `test_same_seed_same_result`
  - `test_nurse_never_increases_late_count`: across seeds 0–4, a plan with `"A-3"` is ≤ baseline, using a toy night where hospital A is jammed
  - `test_extra_ambulances_reduce_response`
  - `test_no_transport_calls_never_reach_door`
  - `test_shapes`: `stuck` and `door_wait_min` are 3×6
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** with this algorithm (the signature does not decide it):
  - Ambulances start at random call locations from the night (seeded).
  - At each call's `t`, wait `dispatch_delay_min`, then assign the nearest free ambulance (haversine km / `speed_kmh`). If none is free, queue the call FIFO with severity 1–3 first. Response = queue wait + delay + travel.
  - Transported calls drive to their `hosp` and request a handoff at the door. The door's effective capacity is `door_capacity[h][block] + (1 if f"{h}-{block}" in slots else 0)`. Implement it as a `simpy.Resource` sized to max capacity, with a holder process that occupies the unused slots for each block.
  - Handoff time ~ exponential(`handoff_mean_min`). Then `cleanup_min`, then the ambulance is free at the hospital.
  - Use `random.Random(seed)` for all randomness so plans compared with the same seed share random numbers.
  - Record `stuck` by sampling the door queue length every 5 sim-minutes.
- [ ] **Step 4: Run → PASS.** Time one real night: `python -c "..."` under 0.3 s.
- [ ] **Step 5: Commit** `sim/model.py tests/sim/test_model.py`.

---

### Task A4 (Person A): Calibrate to real numbers + credibility chart

**Files:**
- Create: `sim/calibrate.py`
- Output: `data/params_calibrated.json`, `web/img/sim_vs_real.png`
- Test: `tests/sim/test_calibrate.py`

**Interfaces:**
- Consumes: `run_night`, `SimParams`, `real_stats`.
- Produces: `calibrate(nights: dict[str, list[dict]], target: dict, seeds: range = range(5)) -> SimParams`; `within_tolerance(sim: dict, target: dict, tol: float = 0.10) -> bool`; `plot_sim_vs_real(df_real, nights, params, out: Path) -> None`.

- [ ] **Step 1: Write failing tests:** `within_tolerance({"median_response_min":9.0,...},{"median_response_min":8.6,...})` is True; 10.0 vs 8.6 is False.
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** a grid search:
  - `n_ambulances` ∈ {25, 30, 35, 40, 45}
  - `handoff_mean_min` ∈ {15, 20, 25, 30, 35}
  - a base door capacity ∈ {1, 2, 3}, where per-block capacity drops by 1 in the hospital/blocks with the highest real time at hospital

  Pick the combination with the smallest summed relative error on the two Global Constraint targets, averaged over seeds. Write it to JSON. The chart shows median response by block, real vs sim, as two lines labelled REAL and SIM.
- [ ] **Step 4: Run → PASS.** Then run `python -m sim.calibrate`. Expected: printed errors within ±10% and the PNG written.
- [ ] **Step 5: Commit** `sim/calibrate.py tests/sim/test_calibrate.py data/params_calibrated.json web/img/sim_vs_real.png`.

---

### Task A5 (Person A): Greedy optimizer + plan enumeration

**Files:**
- Create: `sim/optimize.py`
- Test: `tests/sim/test_optimize.py`

**Interfaces:**
- Consumes: `run_night`, `plan_key`.
- Produces:
  - `all_slots() -> list[str]`, with 18 items
  - `all_plan_keys(max_k: int = 4) -> list[str]`, with 4,048 items
  - `score(calls, params, slots: frozenset[str], seeds) -> float`, the mean late count
  - `greedy_plans(calls, params, max_budget: int = 6, seeds=range(5)) -> dict[int, list[str]]`

- [ ] **Step 1: Write failing tests.**
  - `len(all_plan_keys()) == 4048`
  - `greedy_plans(...)[k]` has length k
  - each budget's plan is a superset of the previous one
  - on the toy jammed-A night, `greedy_plans(...)[1][0].startswith("A-")`
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** Greedy: at each step, add the slot with the lowest `score`, using the same seeds for every candidate.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit.**

---

### Task A6 (Person A): Export real `scenarios.json`

**Files:**
- Create: `sim/export.py`
- Test: `tests/sim/test_export.py`

**Interfaces:**
- Consumes: everything above + `validate_scenarios`.
- Produces: `result_to_json(r: NightResult) -> dict` (keys `late_ids, stuck, door_wait_min`, numbers rounded to 1 dp); `build_night(name, calls, params, real, seed=0) -> dict`; `build_scenarios(...) -> dict`; `main()` writes `web/data/scenarios.json` only when `validate_scenarios` returns `[]` (otherwise prints the errors and exits 1).

- [ ] **Step 1: Write failing tests.** On a 40-call toy night with `max_k=1`:
  - `build_night` has a `lookup` of 19 entries
  - `ai_plans` has keys `"1"`–`"6"`
  - the full `build_scenarios` output on toy nights passes `validate_scenarios`
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.**
  - Run the lookup with `multiprocessing.Pool` over plan keys, one seed (seed 0) for lookup entries.
  - `ambulances_plus2` = `run_night(..., extra_ambulances=2)`.
  - `real` = that night's `real_stats`.
  - `label` = `"<Typical|Holiday weekend|Heat wave> Friday (<YYYY-MM-DD>)"`.
- [ ] **Step 4: Run → PASS.** Then run `python -m sim.export`. Expected: it finishes in under 30 min, `pytest tests/test_contract.py` still passes, and the file is under 15 MB. If it's slow, lower `max_k` to 3 and tell Person B.
- [ ] **Step 5: Commit** `sim/export.py tests/sim/test_export.py web/data/scenarios.json`.

---

### Task B1 (Person B): Page reads `scenarios.json`

**Files:**
- Create: `web/index.html`, `web/app.js`, `web/style.css` (start from `mockup/offload-planner.html`, split into three files)
- Modify: `.claude/launch.json` → serve `web/` on 8765

**Interfaces:**
- Consumes: `web/data/scenarios.json` (contract in `shared/contract.py`).
- Produces (in `app.js`): `loadScenarios(): Promise<object>`, `planKey(slots: Set<string>): string` (must equal Python `plan_key`), `resultFor(night, slots): object|null` (from `lookup`, or `null` if absent).

- [ ] **Step 1:** Replace the mock's toy model (`genCalls`, `stuck`, `late`, `greedy`) with reads from the JSON. Dots are placed from `lat/lon` and colored red when their `id` is in `late_ids`. Door queues come from `stuck[h][block]`.
- [ ] **Step 2: Verify.** Start the preview and load the page with the fake JSON. Check:
  - Play runs 6 PM → 6 AM
  - "Show AI plan" works for budgets 1–6
  - the console has no errors
- [ ] **Step 3:** Add a console self-check that runs on load: `console.assert(planKey(new Set(["B-3","A-2","A-3"])) === "A-2,A-3,B-3")`.
- [ ] **Step 4: Commit** `web/ .claude/launch.json`.

### Task B2 (Person B): Real Brooklyn map

**Files:**
- Create: `web/data/brooklyn_zcta.geojson` (from the NYC Open Data MODZCTA GeoJSON export, filtered to Brooklyn zips; verify the dataset id before downloading)
- Modify: `web/app.js`

- [ ] **Step 1:** Load d3 from `https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js`. Draw the zip polygons with `d3.geoMercator().fitSize([w,h], geojson)`, and project calls and hospitals with the same projection.
- [ ] **Step 2: Verify.**
  - Dots fall inside Brooklyn
  - Hospitals A/B/C show
  - the page works at 375 px width with no horizontal scroll
- [ ] **Step 3: Commit.**

### Task B3 (Person B): Your plan vs AI, compare bars, "why" chart

**Files:** Modify `web/app.js`, `web/index.html`

- [ ] **Step 1:** Wire up the plan controls:
  - Tapping a slot toggles it. Look up `resultFor(night, slots)`.
  - When the user places more than 4 shifts, or budget is above 4 for "your plan", show "We precomputed plans up to 4 shifts. Remove one or press Show AI plan." Never call into a missing key.
  - Lowering the budget below the placed count removes the most recently placed slots.
- [ ] **Step 2:** Compare bars show do nothing / +2 ambulances / your plan / AI plan, each as `baseline.late_ids.length - result.late_ids.length`. Stats show:
  - reached late
  - extra people in time
  - cost (`slots × costs.nurse_shift_usd`)
  - cost per extra person
- [ ] **Step 3:** The "why" chart covers the hospital with the highest summed baseline `stuck`, comparing baseline vs current `door_wait_min`, labelled SIM. Next to it, show `real.median_time_at_hospital_min` labelled REAL.
- [ ] **Step 4: Verify in the browser.**
  - Tapping `A-3` then `A-2` gives the same numbers as tapping `A-2` then `A-3`.
  - Placing a 5th shift shows the message, and the console stays clean.
  - Switching nights resets the plan.
- [ ] **Step 5: Commit.**

### Task B4 (Person B): "Send schedule" shift sheet

**Files:** Create `web/schedule.html` (print stylesheet). Modify `web/app.js`.

- [ ] **Step 1:** A "Send schedule" button opens `schedule.html?night=<name>&plan=<plan key>`. The sheet shows the night label, one row per slot ("Hospital A · 10 PM–12 AM · 1 offload nurse"), the expected extra people reached in time, the cost, and a SIM disclaimer. It has a Print button (`window.print()`).
- [ ] **Step 2: Verify.** Open it with a 3-slot plan. The print preview fits on one page, and an empty plan shows "No shifts placed".
- [ ] **Step 3: Commit.**

### Task B5 (Person B): Pitch, Devpost, backup video

**Files:** Create `slides/` (deck), `slides/devpost.md`

- [ ] Slides follow the order in `PLAN.md` and include the `web/img/sim_vs_real.png` chart, plus one "Any city" slide: "NYC is city #1. Give us a city's 911 records → we build its digital twin → calibrate → schedule." Name the data a new city needs: call time, location, hospital arrival, ambulance free again. Every number on a slide is copied from the final `scenarios.json` or `real_stats`.
- [ ] A 2-minute screen recording of the full demo flow, saved to `slides/backup-demo.mp4`.
- [ ] `slides/devpost.md` states the honesty rules from `PLAN.md` (REAL vs SIM, nearest-hospital assumption, time at hospital includes cleanup).
- [ ] Commit.

---

### Stretch S1 (Person A, only after A6): Forecast "this Friday"

**Files:** `pipeline/forecast.py`, a Databricks notebook `notebooks/forecast.py`, `tests/pipeline/test_forecast.py`

- [ ] Train LightGBM (`objective="poisson"`) on calls per block for Friday nights, with features block, month, and holiday flag. Log it to MLflow.
- [ ] Test: predictions are non-negative and the output has length 6.
- [ ] Use it to add a 4th night, `forecast`, whose call times are resampled from the predicted counts. That night must pass `validate_scenarios` (the contract adds `"forecast"` as an optional night key, agreed with Person B first).

### Stretch S2 (Person B, only if the 4 AM sync says go): Agent chat box

**Files:** `agent/server.py`, `agent/tools.py`, `web/app.js` chat panel, `tests/agent/test_tools.py`

- [ ] **Tools.** The tools are pure functions over `scenarios.json`:
  - `best_plan(night: str, budget: int) -> dict`
  - `evaluate_plan(night: str, slots: list[str]) -> dict` (returns an error dict when there are more than 4 slots)
  - `compare(night: str) -> dict`

  Tests assert `evaluate_plan("typical", ["A-3","A-2"]) == evaluate_plan("typical", ["A-2","A-3"])`.
- [ ] **Server.** FastAPI `POST /chat {message} -> {reply, plan}`. It uses the Anthropic SDK tool-use loop with model `claude-sonnet-5-5`, and its system prompt says every number must come from a tool result. Load the `claude-api` skill before writing this file. The API key comes from `.env` (gitignored).
- [ ] **Verify.** Ask "I can afford 3 nurses on the holiday night, where?" The reply must match `ai_plans["3"]` for `holiday`, and the page must highlight those slots.

---

## Sync checkpoints (from PLAN.md)

| When | Gate |
|---|---|
| 7 PM | A2 done (real stats printed) · B1 done on fake JSON |
| 12 AM | A4 done, first real `scenarios.json` (A6 with `max_k=2` is fine) · B2 + B3 working on it |
| 4 AM | A6 final · B4 done · go/no-go on S2 |
| 8 AM | Freeze code. Only B5 and rehearsal after this. |
