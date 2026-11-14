# Root Cause — Design Doc (MadHacks 2026)

> **Status:** draft for the team. Build approach **A (all Python on Databricks)** is Claude's recommendation and has **not** been confirmed by the team yet. Items marked **[verify]** must be checked in Hour 0. Items marked **[our call]** are decisions Claude made that you can override.
>
> Companion doc: `madhacks-2026-idea-brief.md` (how we got here, alternatives, sources).

---

## 1. One-line pitch

**When an ambulance is late, everyone blames the ambulance. Root Cause lets you click any late 911 response, dig layer by layer down to the real bottleneck — often a full ER — and test a fix in simulation before trying it for real.**

## 2. Why this, why now

- **Problem:** Ambulance response times and ER crowding are usually treated as separate problems. They aren't. When ERs are full, ambulances wait at the hospital to hand over patients ("offload delay"), and while they wait they can't answer the next 911 call.
- **Evidence:** ER walkouts roughly doubled 2017–2021 (median 1.1% → 2.1%); ER boarding described as a crisis and still rising; each walkout ~$550 (estimate); travel nurses ~$90/h vs ~$56/h staff. Full sources in the idea brief.
- **Gap:** Hospitals and EMS agencies test changes with discrete-event simulation studies run by consultants/engineers (Simio, Arena). We found no evidence of a self-serve tool that connects the 911 side to the hospital side and lets a planner test a fix in seconds. **[verify: Qventus, LeanTaaS, EMS-specific tools]**
- **Theme — "Let's Dig In":** digging *is* the core interaction. Every other team will "dig into data"; we dig from a symptom down to its **root** cause, one layer at a time.

## 3. User

**Primary user [our call]:** an **operations planner** — an EMS deployment/operations manager or a hospital ED operations director — deciding where to spend the next dollar: more ambulances, more ER nurses, or fixing boarding.

- They currently get: response-time reports (what happened), not causes (why) or tests (what if).
- They need: "Which fix actually brings response times down, and by how much?"
- Not the user (for this build): dispatchers in real time, the public, patients.

## 4. Goals, non-goals, anti-goals

**Goals**
1. Click a late call → see a clear, layered explanation of *why* it was late.
2. Rank root causes across a whole night by how many minutes each one costs.
3. Test a fix (sliders) → see before/after response times in seconds.
4. Grounded in **real NYC EMS data**, with simulated parts clearly labeled.

**Non-goals**
- Whole-city, multi-month modeling. We model **one borough, one Friday night, 3 hospitals**.
- Real-time operation or integration with Epic/CAD systems (that's the "what's next" slide).
- Medically detailed patient modeling.

**Anti-goals (fail even if it "works")**
- A dashboard of charts with no dig-down story.
- Presenting simulated numbers as if they were measured.
- Making claims about the performance of **real, named hospitals** → use "Hospital A/B/C" at approximate locations **[our call]**.
- A chatbot as the main feature.

## 5. The end product

Single web app, four views. Streamlit + pydeck map.

### 5.1 View 1 — "Friday Night" map (landing)

```
┌───────────────────────────────────────────────────────────────┐
│ ROOT CAUSE            Brooklyn · Friday 6 PM – 6 AM   [▶ Replay]│
├───────────────────────────────────────────────┬───────────────┤
│                                               │ Tonight       │
│      ● ● ●  (calls, colored by response time)  │ Calls: 412    │
│   ●     🏥A [ED ▓▓▓▓▓▓▓░ 92%]                   │ Median: 9.4m  │
│        🚑 🚑     ●  ●                          │ >15 min: 18%  │
│   🏥B [ED ▓▓▓▓░░ 61%]      ●  🔴 (late call)   │               │
│                 🚑   🏥C [ED ▓▓▓▓▓▓▓▓ 98%]      │ Top cause:    │
│                                               │ Offload at A  │
│  time slider ─────────●───────────── 2:10 AM   │ [Dig in →]    │
└───────────────────────────────────────────────┴───────────────┘
```
- Calls as dots (green → red by response time). Hospitals with ED load gauges. Ambulances moving on replay.
- Click any red dot → View 2.

### 5.2 View 2 — The Dig (core interaction)

```
CALL #2214 · 2:10 AM · Severity 2 · Waited 14.2 min           [REAL]
  ⛏ Dig
LAYER 1 — Availability                                         [SIM]
  No ambulance free within 3 mi. Nearest free unit: 5.8 mi away.
  ⛏ Dig
LAYER 2 — Where were the nearby ambulances?                    [SIM]
  🚑 12  offloading at Hospital A   (waiting 38 min)
  🚑 7   offloading at Hospital A   (waiting 51 min)
  🚑 19  on scene, other call
  ⛏ Dig
LAYER 3 — Why were they stuck at Hospital A?                   [SIM]
  ED at 98% — 11 of 24 beds held by admitted patients (boarding).
  ⛏ Dig
ROOT — Boarding at Hospital A, Friday 10 PM – 4 AM
  Counterfactual: if offload ≤ 20 min, this call's wait → 6.1 min.
  [Test a fix →]
```
- Each layer is revealed one "dig" at a time (animation: layer slides down, map zooms to the relevant units/hospital).
- Every number carries a **REAL** or **SIM** badge.

### 5.3 View 3 — Root cause ranking (the whole night)

```
Minutes of response time attributable to each cause (Friday night)
Offload delay at hospitals   ████████████████████  −4.2 min median
Too few ambulances            █████                −1.1 min
Long travel distances         ███                  −0.7 min
Demand spike 11 PM – 1 AM      ██                   −0.5 min
```
- Computed by **counterfactual simulation** (Section 6.5).

### 5.4 View 4 — Test a fix

```
Levers                                   Result (30 simulated Friday nights)
+ ER nurses at Hospital A   [ 0 ●──── 4 ]   Median response   9.4 → 6.8 min
Reduce boarding by          [ 0% ──●── 50%]  % calls > 15 min   18% → 7%
Offload time target         [ none ●─ 20m]  Est. cost / night  $X
+ Ambulances                [ 0 ●──── 4 ]   [map heat before | after]
                       [Run simulation ▶]   ("Cheapest fix that hits target" — stretch)
```
- Before/after distribution chart + side-by-side map heat.
- The punchline: "+2 ER nurses beats +2 ambulances — at lower cost." (Only say this if the simulation actually shows it. **Never hard-code the conclusion.**)

## 6. Architecture

### 6.1 Overview

```
            ┌───────────────────────── DATABRICKS ─────────────────────────┐
NYC Open    │  01_ingest      02_features        03_forecast     04_calibrate │
Data  ─────▶│  raw EMS  ───▶  arrivals by    ───▶ ML model   ───▶ tune sim     │
(EMS calls) │  (Delta)        zip × hour,         λ(zip,hour)     params to    │
CMS / CDC ─▶│                 severity mix,       (MLflow)        match real   │
            │                 travel & hospital                   response     │
            │                 time distributions                  times        │
            └──────────────────────────┬────────────────────────────────────┘
                                       │ gold tables / parquet
                                       ▼
            ┌────────────── rootcause/ (Python package) ──────────────┐
            │  sim/engine.py   SimPy model: calls, units, hospitals    │
            │  sim/trace.py    per-call event log + state snapshots    │
            │  analysis/dig.py per-call layered explanation            │
            │  analysis/attribution.py  counterfactual cause ranking   │
            └──────────────────────────┬──────────────────────────────┘
                                       ▼
            ┌──────────── app/ (Streamlit + pydeck) ──────────────┐
            │  Map · Dig · Ranking · Test-a-fix                    │
            │  Hosted on Databricks Apps (fallback: local)         │
            └──────────────────────────────────────────────────────┘
```

### 6.2 Data layer (Databricks)

| Source | Use | Notes |
|---|---|---|
| **NYC EMS Incident Dispatch Data** (NYC Open Data, Socrata) | Real call times, severity, borough/zip, dispatch & travel & response seconds | **[verify]** dataset id (believed `76xm-jjuj`) and columns. Believed to include incident time, first assignment, first on scene, **first hospital arrival**, and **incident close**. If hospital-arrival → close exists, it is a **real proxy for time spent at the hospital** (offload + turnaround) — a big credibility win. It likely does **not** say which hospital. |
| **ZIP code centroids** (US Census ZCTA gazetteer) | Place calls on the map | Calls are zip-level, not exact addresses. Jitter dots within the zip for display. |
| **CMS Care Compare – ED measures** | Realistic ED throughput ranges | Per-hospital medians; used only to set plausible parameter ranges. |
| **CDC NHAMCS ED public-use files** | Walk-in arrival patterns, triage mix, ED length of stay | Optional; use published summary values if time is short. |
| **Published research** | Offload delay & boarding parameters | Cite every number used in `docs/parameters.md`. |

**Scope filter [our call]:** Brooklyn, Fridays 6 PM–6 AM, last 12 months available. Pull via Socrata API with a `$where` filter (avoid downloading the full multi-million-row file) **[verify size/limits]**.

**Tables (Delta, gold):**
- `calls` — `call_id, ts, zip, lat, lon, severity, dispatch_s, travel_s, response_s, at_hospital_s?`
- `arrivals_zip_hour` — `zip, dow, hour, mean_calls, severity_mix`
- `distributions` — fitted on-scene time, travel speed, at-hospital time (by severity)
- `forecast_friday` — `zip, hour, lambda`

### 6.3 ML: demand forecast (owner: ML person)

- **Target:** calls per (zip, hour). **Features:** hour, day-of-week, month, holiday flag, lagged counts, zip one-hot / target encoding.
- **Model:** LightGBM (Poisson objective) **[our call]**; baseline = historical mean for that zip × hour × dow.
- **Report:** MAE vs baseline on held-out Fridays. Track in **MLflow** (Databricks-native — good sponsor talking point).
- **Output:** `lambda(zip, hour)` for the demo Friday → drives simulated arrivals.
- **Two arrival modes:** `replay` (real calls from a chosen real Friday — most credible for the Dig view) and `forecast` (Poisson from λ — used for the 30-night Test-a-fix runs).

### 6.4 Simulation engine (SimPy)

**Entities**
- `Call(id, t, zip, severity)`
- `Unit(id, base_zip, state ∈ {available, enroute, on_scene, transporting, offloading, returning})`
- `Hospital(id, loc, ed_beds, ed_nurses, boarders(t))`

**Process per call**
1. Call arrives (replay or Poisson).
2. **Dispatch:** nearest *available* unit by straight-line distance × road factor **[our call]**. If none, the call waits in a queue (priority by severity).
3. **Travel** to scene: distance / speed (speed fitted so simulated travel times match real `travel_s`).
4. **On scene:** sampled from fitted distribution.
5. **Transport** (fraction by severity) to nearest hospital (or nearest with capacity — parameter).
6. **Offload:** unit waits until the ED can accept (free bed + nurse). ED capacity = beds − boarders(t). **This is the coupling between the 911 side and the ER side.**
7. Unit returns toward base, available on the way.

**ED model (simple on purpose)**
- Inflows: ambulance patients + walk-ins (Poisson by hour).
- Bed occupancy time: sampled; a fraction become **boarders** who hold a bed for an extra boarding time.
- Levers map directly to parameters: `+nurses` → treatment rate; `boarding reduction` → boarding time ×(1−r); `offload target` → max offload wait (units released, patient handed to hallway care); `+ambulances` → more units.

**Trace (`sim/trace.py`)**
- For every call, record the timeline and a **state snapshot at dispatch**: every unit within N miles, its state, and (if offloading) which hospital and for how long; plus each hospital's occupancy and boarders.
- This snapshot is what the Dig view reads. No LLM needed to explain — the explanation is computed.

**Performance target:** one Friday night (≈300–500 calls, ~20 units, 3 hospitals) in < 0.5 s; 30 replications in < 15 s. Pre-compute baseline runs; run fixes live with `st.cache_data`.

### 6.5 Analysis

**Dig (per call) — `analysis/dig.py`**
Rule-based layers from the trace:
1. Was response > target (e.g., 10 min)? → Layer 0 (REAL response time in replay mode).
2. Availability: nearest free unit distance vs nearest unit overall.
3. Unit states of the k nearest units → group by reason (offloading at hospital X, on another call, returning).
4. If "offloading" dominates → hospital state at that time (occupancy, boarders).
5. **Per-call counterfactual:** re-run the night with the same random seed and offload capped → this call's new wait.

**Root cause ranking — `analysis/attribution.py`**
- Run baseline and one counterfactual per cause, each with **30 replications** and **common random numbers** (same seeds) so differences are due to the change, not noise:
  - offload delay → capped at 0 / target
  - fleet size → +k units
  - travel → speed +X% (proxy for better station placement)
  - demand spike → flatten peak hours
- Report Δ median response time with a 95% interval. Shapley-style decomposition is a stretch goal; one-at-a-time removal is fine and easier to explain **[our call]**.

**Calibration — `notebooks/04_calibrate`**
- Grid/random search over unknown parameters (fleet size on duty, at-hospital time multiplier, speed) to match the **real** distribution of response times for Brooklyn Friday nights (compare median, p90).
- Show a "simulated vs real" histogram in the app's About panel and in the pitch. This is the answer to "why should we trust your simulation?"

### 6.6 App (Streamlit + pydeck)

- `app/main.py` with four pages (Map, Dig, Ranking, Test a fix) + About (data sources, REAL/SIM legend, calibration chart).
- Map: pydeck `ScatterplotLayer` (calls), `IconLayer` (hospitals, units), `HeatmapLayer` (response time before/after). Time slider replays the night.
- Plain-English text is **template-based** (reliable). An LLM "explain this" button is a stretch goal only.
- **Hosting [verify at 2 PM workshop]:** Databricks Apps (Streamlit supported?) using data from Unity Catalog / exported parquet. **Fallback:** run locally with parquet files in `data/gold/` — demo must work offline.

### 6.7 Interface contract (so two people + two Claude sessions can work in parallel)

Agree on these in Hour 0 and do not change them without telling each other:

```python
# rootcause/sim/engine.py
def run_night(params: SimParams, arrivals: pd.DataFrame, seed: int) -> SimResult: ...
# SimResult: .calls (DataFrame: call_id, t, zip, severity, unit_id, response_s, ...)
#            .events (DataFrame: t, entity, state, hospital_id, ...)
#            .snapshots (dict[call_id] -> Snapshot)

# rootcause/analysis/dig.py
def dig(call_id: str, result: SimResult) -> list[Layer]   # Layer: title, text, badge(REAL|SIM), focus (map ids)

# rootcause/analysis/attribution.py
def rank_causes(params, arrivals, n_reps=30) -> pd.DataFrame  # cause, delta_median_s, ci_low, ci_high

# data contract (parquet in data/gold/)
calls.parquet, arrivals_zip_hour.parquet, distributions.json, forecast_friday.parquet, params_calibrated.json
```
Until the real data is ready, Person 2 builds against a **fake `calls.parquet`** with the same columns.

## 7. Repository structure

```
madhacks-2026/
├── README.md                    # what it is, how to run, demo link
├── madhacks-2026-idea-brief.md
├── root-cause-design.md         # this file
├── docs/
│   ├── parameters.md            # every modeled number + its source
│   └── pitch.md                 # script + slide outline
├── notebooks/                   # Databricks (export as .py or .ipynb)
│   ├── 01_ingest.py
│   ├── 02_features.py
│   ├── 03_forecast.py
│   └── 04_calibrate.py
├── rootcause/
│   ├── __init__.py
│   ├── config.py                # SimParams dataclass, defaults
│   ├── data.py                  # load gold parquet
│   ├── sim/engine.py
│   ├── sim/trace.py
│   ├── analysis/dig.py
│   └── analysis/attribution.py
├── app/
│   ├── main.py
│   ├── views/{map,dig,ranking,fix,about}.py
│   └── app.yaml                 # Databricks Apps config [verify]
├── data/
│   ├── gold/                    # small, committed demo data (parquet)
│   └── raw/                     # gitignored
├── tests/
│   ├── test_engine.py           # conservation, determinism with seed
│   └── test_dig.py
├── requirements.txt             # simpy, pandas, numpy, pyarrow, lightgbm, mlflow, streamlit, pydeck, plotly
└── .gitignore
```

## 8. Build plan (Sat 12:00 PM → Sun 12:00 PM)

Person 1 = **ML/data** · Person 2 = **sim/app**. Each works in their own Claude session on separate folders.

| Time | Person 1 (ML/data) | Person 2 (sim/app) | Checkpoint |
|---|---|---|---|
| **12:00–1:00** | Pull 1 day of NYC EMS data via API; **[verify]** columns, esp. hospital arrival & close times | Repo skeleton, `SimParams`, fake `calls.parquet`, Streamlit hello-world map | Interface contract agreed |
| **1:00–2:00** | Brooklyn Friday-night extract → `calls.parquet` | SimPy engine v0: calls → nearest unit → scene → hospital → return | Tiny end-to-end: fake data → sim → map |
| **2:00–3:00** | **Databricks workshop** (ask: Apps + Streamlit? free tier limits?) | Offload/ED coupling in engine | Know hosting answer |
| **3:00–6:00** | Features + distributions; zip centroids | Trace + snapshots; Dig view v1 (text layers) | Click a call → layers appear |
| **6:00–7:00** | Dinner | Dinner | — |
| **7:00–10:00** | Forecast model (LightGBM + MLflow) vs baseline | Test-a-fix view: sliders → 30 reps → before/after | Full flow on real data |
| **10:00–1:00 AM** | Calibration: sim vs real response histogram | Ranking view (attribution); REAL/SIM badges | **Core done. Freeze features.** |
| **1:00–4:00 AM** | `docs/parameters.md`; deploy to Databricks Apps | Map polish: replay slider, dig animation, heat before/after | Deployed URL works |
| **4:00–7:00 AM** | Pick the demo call (a real late call with a clean dig story); seed fixed | Bug bash; offline fallback | Demo path is deterministic |
| **7:00–9:30 AM** | Slides: problem, evidence, before/after, tech | Record a backup demo video | Backup video saved |
| **9:30–11:00 AM** | Devpost write-up | README, screenshots | Draft submitted |
| **11:00–12:00 PM** | Rehearse ×3, timed | Rehearse ×3, timed | **Submit by 11:30 — don't cut it close** |

**Stretch (only if core is solid by ~1 AM):** "cheapest fix that hits target" optimizer; LLM "explain" button; Shapley attribution.

## 9. Demo script (~2.5 min) [draft]

**0:00 – Hook (15 s)**
"Raise your hand if you've ever waited in an ER." … "When an ambulance shows up late, everyone blames the ambulance. We dug in — and the ambulance usually isn't the problem."

**0:15 – Problem (20 s)**
"ER walkouts roughly doubled in four years. ERs are so full that ambulances get stuck at the door waiting to hand over patients — and while they wait, they can't answer the next 911 call. Hospitals and EMS treat these as two separate problems. They're one."

**0:35 – Live demo (60 s)**
1. Map of Brooklyn, a real Friday night. "Every dot is a real 911 call. Red ones waited over 15 minutes."
2. Click the red call at 2:10 AM. **Dig** → "No ambulance free nearby." **Dig** → "Two of the closest were stuck at Hospital A for 40+ minutes." **Dig** → "Hospital A's ER was 98% full — half its beds held by admitted patients with nowhere to go." **Root.**
3. Ranking: "Across the whole night, offload delay costs 4.2 minutes per call. Too few ambulances: 1.1."
4. Test a fix: "+2 ER nurses at Hospital A" → Run → map turns greener, "median 9.4 → 6.8 minutes." Then "+2 ambulances" → smaller change. "The fix for slow ambulances was inside the hospital."
*(Numbers above are placeholders — use whatever the calibrated sim actually shows.)*

**1:35 – How it works (30 s)**
"Real NYC EMS dispatch data, processed on Databricks. An ML model forecasts calls by neighborhood and hour. A discrete-event simulation of ambulances and ERs, calibrated to match real NYC response times — here's simulated vs real. Root causes come from counterfactual simulation: we re-run the night without each cause and measure the difference. Everything real is tagged REAL; everything modeled is tagged SIM."

**2:05 – Theme (15 s)**
"'Let's Dig In' — most dashboards stop at *what happened*. Root Cause digs to *why*, then lets you test *what if* before spending a dollar."

**2:20 – Close**
"Today, answering 'should we buy ambulances or fix the ER?' takes a consulting study. With Root Cause it takes one click. Next: hospitals plug in their own data."

**Judge interaction:** hand a judge the laptop to click "Dig" and move a slider themselves.

## 10. Risks and fallbacks

| Risk | Likelihood | Fallback |
|---|---|---|
| NYC dataset lacks hospital-time fields | Medium | Model at-hospital time from published offload research; label SIM; say so in pitch. |
| Socrata API slow / rate-limited | Medium | Download one filtered CSV once; commit small gold parquet. |
| Databricks Apps doesn't support our setup / free tier limits | Medium | Run Streamlit locally; keep notebooks + MLflow on Databricks for the sponsor story. |
| Sim doesn't calibrate to real numbers | Medium | Calibrate only median + p90; show the chart honestly; narrow to fewer zips. |
| Counterfactual results noisy | Medium | More reps on precomputed runs; common random numbers; show intervals. |
| Sim shows the "wrong" story (ER isn't the bottleneck) | Low–Med | That's fine — the tool still digs to *a* root cause. Pick a demo call where offload is the cause; never fake results. |
| Live demo breaks | Low | Pre-recorded video + fixed seed + offline data. |
| Judge: "you're not EMS experts" | High | One real quote from a paramedic/ER nurse; parameters doc with sources; humility. |

## 11. Judge Q&A prep

- **"Is this real data?"** Calls and response times: real (NYC Open Data). Hospital internals: simulated from published research, calibrated so overall response times match reality. Badges show which is which.
- **"How do you know the root cause is right?"** We don't claim certainty — we show *how much each cause matters in the model* by removing it and re-running, with confidence intervals. It's a decision aid, not an oracle.
- **"Who would pay?"** EMS agencies and hospital systems; today they buy consulting simulation studies.
- **"Why not just a dashboard?"** Dashboards show *what*. We show *why* and *what if*.
- **"Why Databricks?"** Ingest, features, ML forecast (MLflow), and hosting in one place; scales to full-city, multi-year data.
- **"What's next?"** Hospital-specific data via exports; live mode; optimizer for cheapest fix; other cities with open EMS data.

## 12. Calls made by Claude (please check)

1. Build approach **A** (all Python, Streamlit, Databricks).
2. User = operations planner (EMS or hospital ops), not a dispatcher.
3. Scope = Brooklyn, Friday nights, 3 hospitals, ~20 units.
4. Real hospitals shown as **Hospital A/B/C**, not named.
5. LightGBM (Poisson) for the forecast; one-at-a-time counterfactual attribution (Shapley = stretch).
6. Explanations are template-based; LLM only as a stretch.
7. Name "Root Cause" is a working title.

## 13. Open questions (need the team or Hour-0 checks)

- [verify] NYC EMS dataset id, columns, size; whether hospital arrival → close times exist.
- [verify] Databricks Apps + Streamlit support and free-tier limits (2 PM workshop).
- [verify] Exact sponsor track prompts (TDS, Databricks, Qualcomm / N+1) and Devpost submission requirements.
- [verify] Existing competitors: Qventus, LeanTaaS, EMS deployment tools.
- Team: can either of you get one quote from a paramedic or ER nurse tonight?
