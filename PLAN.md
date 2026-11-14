# Offload Planner — Team Plan (MadHacks 2026)

**Product:** A planner that tells ER managers where and when to put offload nurses, so ambulances stop getting stuck at the door and get back to 911 calls. Built on real NYC 911 data, tested in simulation before anyone changes a shift.

**Pitch line:** "Ambulances aren't slow. They're stuck. Dashboards show you the problem; we tell you the fix."

**Product framing:** a **digital twin** of a city's ambulances and ERs. NYC is city #1 (our test city). Any city with the same 911 records (call time, location, hospital arrival, ambulance free again) can get its own: swap the config + data, re-calibrate, get a schedule. All city-specific values live in `pipeline/config.py` only. We do **not** build multi-city support in 24 h; we just keep it swappable and say so on one slide.

**Implementation plan (task by task):** `docs/superpowers/plans/2026-11-14-offload-planner.md`

Mock of the final screen: `mockup/offload-planner.html` (toy numbers; layout is the target).

---

## Who does what

| | **Person A — Data + Model** (ML/AI lead) | **Person B — Product + Pitch** |
|---|---|---|
| Owns folders | `pipeline/`, `sim/`, `data/` | `web/`, `slides/`, `agent/` (stretch) |
| Builds | Data pull → simulation → calibration → optimizer → exports `scenarios.json` | The real web page, "Send schedule", slides, Devpost, backup video, agent chat box (stretch) |
| Delivers to the other | `web/data/scenarios.json` (real numbers) | Feedback on what the page needs in the JSON |

**Rule:** only edit your own folders. The only shared file is `web/data/scenarios.json`, and only Person A writes it. If you want to change its format, say so first.

---

## The contract: `web/data/scenarios.json`

Agree on this in hour 1. Person B builds with a fake version until Person A's real one lands.

```json
{
  "generated_at": "2026-11-15T03:00:00",
  "city": {"name": "New York City", "area": "Brooklyn"},
  "blocks": ["6-8P", "8-10P", "10P-12A", "12-2A", "2-4A", "4-6A"],
  "hospitals": [{"id": "A", "lat": 40.65, "lon": -73.95}, {"id": "B", "lat": 0, "lon": 0}, {"id": "C", "lat": 0, "lon": 0}],
  "costs": {"nurse_shift_usd": 180, "ambulance_night_usd": 3600},
  "nights": {
    "typical": {
      "label": "Typical Friday (2026-09-12)",
      "calls": [{"id": 0, "t": 12.5, "lat": 40.66, "lon": -73.94, "hosp": "A", "severity": 3}],
      "real": {"median_response_min": 8.6, "median_time_at_hospital_min": 42.7},
      "baseline": {"late_ids": [4, 9], "stuck": [[1,2,4,5,4,2],[0,1,2,3,2,1],[0,0,1,1,1,0]], "door_wait_min": [[...],[...],[...]]},
      "ambulances_plus2": {"late_ids": [], "stuck": [], "door_wait_min": []},
      "ai_plans": {"1": {"slots": ["A-3"], "late_ids": []}, "2": {}, "3": {}, "4": {}, "5": {}, "6": {}},
      "lookup": {"A-2,A-3,B-3": {"late_ids": [], "stuck": [], "door_wait_min": []}}
    },
    "holiday": {},
    "heat": {}
  }
}
```

- `t` = minutes since 6 PM. Slot key = `"<hospital>-<block index>"`, sorted, comma-joined.
- `lookup` holds **every user plan of up to 4 shifts** (~4,000 combos), so the page never computes anything live.
- `stuck[h][b]` = ambulances waiting at the door; `door_wait_min[h][b]` = average minutes at the door.

---

## Timeline (Sat 12 PM → Sun 12 PM)

| When | Person A | Person B |
|---|---|---|
| **Sat 12–2 PM** | Repo setup together. Agree on the JSON. Start the data pull (Brooklyn Fridays 2024–2026). | Turn the mock into `web/` and write a fake `scenarios.json` in the format above. |
| **Sat 2–3 PM** | **Databricks workshop (B2550)** — ask about Apps/free tier | Real Brooklyn map (zip code shapes) + real hospital-ish positions |
| **Sat 3–7 PM** | Clean data: zip → lat/lon, calls per hour, time at hospital per hour. Pick 3 real nights (typical / holiday / hot). | Page reads `scenarios.json`: replay, schedule grid, compare bars, "why" chart |
| **🔁 7 PM sync** | Show real call data for 1 night | Show the page running on fake JSON |
| **Sat 7 PM–12 AM** | SimPy simulation: ambulances, 3 hospitals, door queue. **Calibrate** to real 8.6 min response / 43 min at hospital. Make the sim-vs-real chart. | "Send schedule" (clean printable shift sheet). Start slides: hook, problem, evidence. |
| **🔁 12 AM sync** | First real `scenarios.json` (even if rough) | Plug in real JSON, fix what breaks |
| **Sun 12–4 AM** | Greedy optimizer → AI plans for budgets 1–6. Precompute all ≤4-shift plans for `lookup`. | Devpost draft. Polish page. Stretch: agent chat box UI. |
| **🔁 4 AM sync** | Final JSON | Decide: is the agent in or out? |
| **Sun 4–8 AM** | Stretch: forecast model (LightGBM, Databricks + MLflow) for "this Friday". Sleep 2 h. | Stretch: agent wired to lookups. Record backup demo video. Sleep 2 h. |
| **Sun 8–11 AM** | Rehearse 3× together. Finalize numbers on slides. | Rehearse 3× together. Finalize Devpost. |
| **Sun 11:30 AM** | **Submit on Devpost.** | |

---

## If you're behind

1. Behind at 12 AM → drop the `lookup` table; the page only shows AI plans + do nothing + 2 ambulances.
2. Behind at 4 AM → drop the optimizer; compare 3 hand-picked plans.
3. Drop the agent and forecast model before anything else.
4. **Never drop:** real NYC call data + the door queue + before/after + the schedule output.

## Honesty rules (for the pitch and the page)

- Label **REAL** (NYC 911 data) vs **SIM** (simulation outputs) everywhere.
- Hospitals are A/B/C and calls go to the nearest one — say this is an assumption.
- "Time at hospital" includes cleanup, not just the handoff.
- Only say "AI agent" if the agent chat box is built. The ML part is the forecast; the "AI" deciding is the optimizer.

## Git (each person, own folders only)

```bash
git pull
git add <your folder>
git commit -m "what you did"
git push
```
