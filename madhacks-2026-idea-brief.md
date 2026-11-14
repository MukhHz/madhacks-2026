# MadHacks 2026 — Idea Brief

> **For the reader (human or Claude):** This is a summary of a brainstorming session for our MadHacks 2026 project. We are a team of **2**. Please read it and give us your honest opinion — see **"What we want your opinion on"** at the bottom. Nothing has been built yet.

---

## 1. The event

- **MadHacks 2026**, UW–Madison, Morgridge Hall — **Nov 14–15, 2026**
- Hacking: **12:00 PM Sat → 12:00 PM Sun** (~24 h). Judging 1:00–2:30 PM Sun, finalist presentations after.
- **Theme: "Let's Dig In"**
- **Sponsor tracks:** TDS, Databricks, Qualcomm / N+1 Institute (exact track prompts not yet read — need to check Devpost/Discord)
- Useful workshops: **Getting Started with Databricks — 2:00 PM Sat, B2550**; TDS Networking Workshop 4:00 PM.
- Official site: https://www.madhacks.io/

## 2. The team

- 2 people, both CS + Data Science.
- We build mostly by prompting Claude. One of us leans ML/AI.
- Implication: keep the stack in **Python**, **one codebase**, minimal integration work.

## 3. How we're choosing (the framework we're following)

From a "how I won 11 of 15 hackathons" video:

1. **Start from a real problem, not an idea.** Research size, frequency, cost, and existing solutions.
2. **A specific user**, never "everyone."
3. **Remove friction** — build for how that user actually works.
4. **~3 features that nail the core problem** beat 15 half-features.
5. **Sell it in the demo:** problem → evidence → cost → solution → live demo in the user's real flow → before/after numbers → (tech) → team. Be honest about what isn't built.

**What won MadHacks 2025** (13 winners / 114 projects, https://madhacks-fall-2025.devpost.com/project-gallery):
- 1st place **3Docs** — turned PDF repair manuals into interactive 3D guides with voice.
- Accessibility projects did well (Unsilenced, Bird's I drone guide for the visually impaired).
- "Hard thing made easy for beginners" (WireShrimp = simplified Wireshark).
- Fun crowd-pleasers (Electric Chair, GPT Rewind).
- **Sous-Chef** (fridge → recipes → cooking guide) did **not** place.

## 4. Ideas we explored and why we moved on

| Idea | Why we dropped / parked it |
|---|---|
| Cooking timeline (recipe → dependency-aware live schedule) | Sous-Chef was similar and didn't place; our own cooking failures (pancake too big, sauce too sweet) were "rescue" problems, not scheduling. Hard to demo without a stove. |
| Cooking rescue ("too sweet, what now?") | Hard to put a number on; weak answer to "why not ChatGPT?" Best literal theme fit though ("let's dig in!" before eating). |
| Macro tracking for home-cooked / Malaysian food | MacroFactor already does recipe/serving logging and adaptive TDEE. |
| Menu → picks that fit your macros | Can't know what's actually in a restaurant dish. |
| "Point your camera at it" tech help for older adults | Gemini Live / Be My Eyes already do point-and-ask. |
| Sign language coach (hearing parents of deaf kids) | Good on-device AI fit (Qualcomm), but prior art (fingerspelling.xyz, PopSign), no personal tie, weak theme fit. |
| International-student paperwork / FICA refund checker | The international student office (ISS) already covers much of it; felt too niche to us. |
| ER staffing simulator alone | Good, but "dig into data" is a weak theme fit on its own. |
| **Before You Dig** (read 811 utility paint marks, warn before digging) | **Still a live backup** — literal theme fit, TDS (buries fiber) + Qualcomm (on-device vision). ~192k US utility damages in 2021, ~$30B/yr societal cost (CGA DIRT). Risks: paint shows location not depth; AR in iOS browsers is limited; need to check for homeowner-facing competitors (enterprise tools like vGIS / Trimble SiteVision exist). |

## 5. The current pick: **"Root Cause"** — dig from a late ambulance down to the real bottleneck

### One-liner
Click any late 911 response and **dig layer by layer to why it was late** — often not "too few ambulances," but ambulances **stuck at a full ER** — then **test a fix in simulation** before trying it for real.

### The dig-down (core interaction)
```
Surface:   "This 911 call in Brooklyn waited 14 min for an ambulance."
  ↓ dig    "No ambulance was free within 3 miles."
  ↓ dig    "Three nearby ambulances were stuck at the same hospital."
  ↓ dig    "That ER was full — admitted patients boarding in ER beds."
  ↓ ROOT   "Not enough inpatient beds / ER staff on Friday nights."
  ▶ Test a fix: "+1 ER nurse Fri nights" → simulated response times drop X min across the area.
```

### Why we like it
- **Theme is the product:** the main action *is* digging to a root cause (roots).
- **Grand but specific:** lives and money, but one concrete chain (911 → ambulance → ER → beds).
- **Counter-intuitive insight:** the ambulance problem can be a hospital problem.
- **Same pattern as a friend's startup** (test virtually before doing it for real — his got a $50K grant offer).
- **Real public data + Databricks fit.**

### Evidence so far
- Patients leaving ERs without being seen roughly **doubled** (median 1.1% → 2.1%, 2017–2021); worst hospitals ~10%. — Kaufman Hall / HFMA
- ~**18.5%** of those return within 7 days. — Healio (2025 study)
- Each walkout costs a hospital **~$550** (HFMA estimate; source of the figure unclear — use with care).
- ER **boarding** has steadily worsened and is described as a crisis (WestJEM 2025; Health Affairs 2017–2024).
- Travel nurse bill rate **~$90/h** vs ~$56/h employed RN (SIA/NATHO; NSI — vendor data).
- Academic ED discrete-event simulations exist (Simio, Arena, R) but need consultants/engineers — **no evidence yet of a self-serve tool** a manager can use.
- **Still to verify:** what Qventus / LeanTaaS offer; ambulance offload ("wall time") evidence and numbers.

### Data
- **NYC EMS Incident Dispatch Data** (NYC Open Data) — real call times, severity, response times by borough/zip. Probably **no** ER handoff/offload time → that link is **modeled** from research, not measured.
- **CDC NHAMCS** ED public-use files — arrival patterns, triage mix, wait times.
- **CMS Care Compare** — per-hospital ED measures (median ED time, % left without being seen).
- MIMIC-IV-ED needs credentialed access (days/weeks) — not essential.
- **Rule for the demo:** visually label **real data** vs **simulated/modeled** values. Be upfront with judges.

### Where AI/ML is used (meaningfully, not as a buzzword)
1. **Demand forecast** — ML model on Databricks predicting calls by hour × area (incl. surges).
2. **Root-cause attribution by counterfactual simulation** — re-run the sim *without* each suspected cause ("if ambulances weren't stuck at the ER: −4.2 min; if +2 ambulances: −1.1 min → the ER is the bottleneck").
3. *(Stretch)* Auto-find the cheapest fix that hits a target; plain-English "what if" box.

### Scope guardrails
- **One area, 2–3 hospitals, Friday night.** Not a whole city.
- The dig-down + one "test a fix" simulation is enough to win. Cut the auto-scheduler and the chat box first.
- Don't let it become a dashboard of charts — the **dig chain** and **test-a-fix button** are the demo.
- Get **one real quote** from a paramedic or ER nurse if at all possible.

## 6. How to build it — three options (not yet decided)

**A. All Python, on Databricks — current recommendation**
- Databricks notebooks: load/clean NYC EMS data, train the forecast model.
- Simulation in **SimPy** (ambulances, hospitals, ER handoff queue).
- App in **Streamlit** + **pydeck** map, dig-down screens, hosted on **Databricks Apps** (confirm support at the 2 PM workshop).
- ✅ One language, one codebase, plays to DS/ML skills, strongest Databricks story. ❌ Looks more "data app" than polished product.

**B. Python backend (FastAPI + SimPy) + React/Next.js frontend with an animated map**
- ✅ Most polished demo. ❌ Two codebases to connect — risky for 2 people at 4 AM.

**C. Everything in the browser (precomputed data + JS simulation)**
- ✅ Fastest/smoothest demo. ❌ Weak Databricks story; moves work away from Python/ML strengths.

**Proposed split (for A):**
- **Person 1 (ML):** Databricks pipeline, forecast model, calibrate the sim to real NYC response times.
- **Person 2:** SimPy simulation + Streamlit app (map, dig-down, test-a-fix).
- Each uses their own Claude session on **separate files** to avoid overwriting each other.

### Draft pitch outline
1. **Hook:** "When an ambulance is late, everyone blames the ambulance. We dug in."
2. **Problem + evidence:** walkouts doubled, boarding crisis, cost numbers.
3. **Live demo:** click a late call → dig, dig, dig → root cause → test a fix → response times drop.
4. **Before / after:** e.g., "Consultant study: weeks. Root Cause: one click." + minutes saved.
5. **Tech:** real NYC data on Databricks, ML forecast, counterfactual simulation.
6. **Honest limits + what's next** (hospitals plug in their own Epic data; live mode).

## 7. What we want your opinion on

Please be skeptical and specific:

1. **Is "Root Cause" a winning idea** for a 24-hour, 2-person team at MadHacks with the theme "Let's Dig In"? What would a judge's first objection be?
2. **Root Cause vs. Before You Dig** — which would you build, and why?
3. **Is the scope realistic** for 2 people in ~23 hours? What would you cut?
4. **Build approach A, B, or C?**
5. **Data:** is it credible to model the ambulance-stuck-at-ER link when NYC's open data doesn't include it? How would you present that honestly?
6. Anything we're missing — an existing product that already does this, a better dataset, or a sharper user?

## Sources
- MadHacks 2026: https://www.madhacks.io/
- MadHacks 2025 gallery: https://madhacks-fall-2025.devpost.com/project-gallery · 3Docs: https://devpost.com/software/3docs
- HFMA, ED overcrowding: https://www.hfma.org/operations-management/4-strategies-to-reduce-ed-overcrowding/
- Kaufman Hall: https://kaufmanhall.com/insights/article/four-strategies-reduce-emergency-department-overcrowding
- Healio, LWBS returns: https://cm.healio.com/news/primary-care/20250121/many-who-leave-emergency-rooms-without-been-seen-return-within-a-week
- Becker's, LWBS rankings: https://www.beckershospitalreview.com/rankings-and-ratings/22-hospitals-with-highest-left-without-being-seen-rates/
- WestJEM boarding & LWBS: https://escholarship.org/content/qt2nd6d5b2/qt2nd6d5b2.pdf
- GWU, travel nurses/overtime & safety: https://publichealth.gwu.edu/node/25851
- NSI, travel vs core staff: https://www.nsinursingsolutions.com/Documents/Library/Travel_Vs_Core_Staff.pdf
- Winter Simulation Conference 2025 ED study: https://www.informs-sim.org/wsc25papers/con151.pdf
- Simio ED case study: https://www.simio.com/case-studies/evaluating-an-emergency-department-care-redesign-a-simulation-approach
- R-based ED simulation platform: https://bmcmedinformdecismak.biomedcentral.com/track/pdf/10.1186/1472-6947-14-50
- CGA 2021 DIRT report: https://trenchlesstechnology.com/common-ground-alliance-releases-2021-dirt-report/
- ~$30B utility damage cost (2019): https://amerisurv.com/2020/10/15/excavation-related-damages-to-utilities-cost-the-u-s-approximately-30-billion-in-2019/
