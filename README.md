# ONE-HealthRecord

> **Machine-authored, FAIR-by-construction One Health electronic health record for Arizona.** A capstone demonstration of how clinician dictation, veterinary records, and environmental signals can be unified into structured, code-bound, provenance-rich data — and surfaced as real-time cross-species clinical decision support.

[![Status](https://img.shields.io/badge/status-capstone--MVP-blue)]() [![Data](https://img.shields.io/badge/data-100%25%20synthetic-green)]() [![Bundle](https://img.shields.io/badge/bundle-15.0%20MB-lightgrey)]() [![Reproducibility](https://img.shields.io/badge/seed-42-orange)]() [![License](https://img.shields.io/badge/license-All%20Rights%20Reserved-red)](LICENSE)

> ⚠️ **Synthetic data only.** Every patient, household, animal, encounter, and condition in this repository is procedurally generated. See [SYNTHETIC_DATA_NOTICE.md](SYNTHETIC_DATA_NOTICE.md) before reviewing.

---

## For the certification panel — start here

**If you have 5 minutes:**
1. Open [`app/index.html`](app/index.html) in Chrome or Edge. The MVP runs entirely in the browser, no install.
2. Click **Environmental Surveillance** on the opening domain selector — no login required. You'll see five live data feeds (EPA AirNow, NWS, ArboNET, USGS plague-rodent, AGFD wildlife mortality).
3. That's the One Health argument made architectural.

**If you have 30 minutes:**
1. Read [`docs/OPENING_PITCH.md`](docs/OPENING_PITCH.md) (~6:30 read aloud) — the system-failure-leading pitch.
2. Read [`docs/CASE_STUDY_HERNANDEZ.md`](docs/CASE_STUDY_HERNANDEZ.md) — the canonical patient story end-to-end.
3. Open [`docs/ONE-HealthRecord_Capstone.pdf`](docs/ONE-HealthRecord_Capstone.pdf) — 23 slides, ~25 min spoken.
4. Open [`app/index.html`](app/index.html) and walk through the demo flow in [`docs/demo_cheatsheet.md`](docs/demo_cheatsheet.md).

**If you want depth:**
- [`docs/model_card.md`](docs/model_card.md) — Mitchell-format model card, ~70 KB, every metric and limitation.
- [`docs/SPEAKER_SPEECH.docx`](docs/SPEAKER_SPEECH.docx) — full presentation speech for the panel, 48 pages.
- [`data/reference/reportable_diseases_us.json`](data/reference/reportable_diseases_us.json) — the 72-disease reportable database with full source citations.

---

## Project objectives

1. **Connected, individualized One Health EHR** across human and veterinary clinical services in Arizona — FHIR R4 bundles with full provenance, linked at the household-and-county level via a cross-species knowledge graph; *individual records remain compartmentalized by access policy*.

2. **Machine-captured extraction and real-time analysis** of clinical and veterinary dictation at roughly 1.2 milliseconds per encounter, scoped to Arizona's 15 counties and 43 ZIP codes; primary extractor is MedGemma 4B with species-router prompt prefix, with rule-based fallback.

3. **Integration of human disease prevalence, animal disease prevalence, environmental health indices, and vector surveillance** at the **ZIP-code, county, and state** level for Arizona — 14 One Health-relevant sentinel diseases with explicit transmission routes (direct contact · environmental · vector-borne · foodborne · waterborne · aerosol · fomite) and per-disease ZIP-level environmental risk scores, plus a **comprehensive 72-disease reportable disease database** sourced from ADHS R9-6-202 + CDC NNDSS + USDA APHIS NLRAD + AZ Department of Agriculture + AZ Game and Fish, with multi-agency one-click reporting workflow that fans out to up to 8 destinations in parallel.

4. **Animal disease cases serving as sentinel for humans and vice versa** — cross-species cluster detection at household, ZIP, county, and state levels; demonstrated by the 71-day model-based lead time on the Hernandez Valley Fever cluster, plus the canine-RMSF→human-RMSF and prairie-dog-die-off→human-plague sentinel pathways encoded in `data/reference/diseases_az.json`.

5. **Alert system with action / watch / information dispositions** for clinicians, veterinarians, ADHS, tribal-health authorities, and USDA APHIS — with risk-triaged contact tracing (100% sensitivity at threshold 0.20, **80% precision at 0.50** at the new dataset scale) and trace-back analysis during outbreaks.

6. **Predictive risk modeling with explainability and equity disaggregation** — gradient boosting at **AUROC 0.910 / Brier 0.0059** on 4,676 encounters at 0.4% prevalence, SHAP plus permutation plus decision-tree explainability, and a **14-percentage-point tribal-land AUC gap** surfaced as the headline equity finding.

7. **Privacy-preserving, federated, role-aware architecture** — four-layer privacy stack (swarm learning, DP-SGD, secure aggregation, Laplace-noised outputs); 13-site federated FHIR substrate with per-site shadow stores, probabilistic eMPI, household-level FHIR Consent gating, and closed-loop CDS (one-click NNDSS HL7 v2.5.1 ELR + USDA APHIS VSPS push); role-based access control with cross-species redaction via a three-tier model pointer; defense in depth across UI, router, and renderer; visible audit log surfaced to public-health users; live federation wire log surfaced to all roles.

---

## Quick demo

The demo runs **in your browser, with no installation**.

```
open   app/index.html      # macOS
start  app\index.html      # Windows
xdg-open app/index.html    # Linux
```

Or just double-click `app/index.html` in your file explorer. Everything is self-contained — embedded synthetic data, JS-side NLP pipeline, D3 / Leaflet visualisations, no server required.

The interface uses a **login parameter and role-based access control** (Phase 4) wrapped around a **two-hub navigation structure** (Phase 3). Both restructurings respond to lecturer feedback and mirror the way real production EHR systems segregate clinical vs population-health surfaces (Epic Hyperspace vs Cogito; Cerner Millennium vs HealtheIntent):

### Clinical Workspace — for clinicians and veterinarians

| Tab | What it shows |
|---|---|
| **01 · Live Encounter** | Type or paste a clinician or vet dictation; watch the engine extract entities, highlight phases, and emit a FHIR R4 bundle in real time. Twelve hand-crafted scenarios across human and animal patients. **Phase 3:** powered by MedGemma 4B (or rule-based fallback when no API key) with species-router prompt prefix for veterinary cases. |
| **02 · Provider Workspace** | Patient list (filterable by role), longitudinal patient chart with vitals trend and encounter timeline, household context with active alerts and county-level disease trends. |

### Public Health Console — for ADHS, tribal health, USDA APHIS, audit

| Tab | What it shows |
|---|---|
| **01 · One Health Map** | Leaflet map of Arizona with all 360 synthetic households across all 15 counties and 43 ZIP codes. Cross-species clusters pulse in cardinal red. |
| **02 · Knowledge Graph** | D3 force-directed view of the full 694-node One Health graph. Cross-species disease links shown as dashed cardinal-red edges. |
| **03 · Sentinel Alerts** | The 12 active surveillance alerts with severity, confidence, evidence, rationale, and Laplace-noised aggregate counts. |
| **04 · Evaluation** | Live evaluation panel for the rule-based NER: precision, recall, F1, calibration reliability diagram, runtime benchmarks, top false positives and false negatives. |
| **05 · Risk Model** | **(Phase 2.)** Three-model bake-off (LR / RF / GBM) on the zoonotic-cluster prediction task; SHAP global + per-patient explanations; permutation importance; decision-tree baseline; risk-triaged contact tracing; lead-time analysis; equity disaggregation; LLM-vs-rules NER head-to-head. Four sub-tabs: AI metrics · Explainability · Public-health metrics · LLM vs. rules. |
| **06 · Model Card** | **(Phase 3 + 4.)** Live, interactive model card following Mitchell et al. (2019) format. **Seven** sub-tabs: Overview · Components & versions · Metrics · Privacy & security (4-layer stack with federated-simulation results) · Ethical considerations · Caveats · **Audit log** (Phase 4 — visible to the user themselves; records every login/navigation/access-denial event). Replaces the old Architecture tab. |

---

## Headline numbers

### Rule-based NER pipeline (Phase 1) — *expanded in Phase 5*

| Metric | Value |
|---|---|
| Synthetic households | **360** *(was 120 in MVP)* |
| Human patients | **970** *(was 316)* |
| Animal patients | **408** *(was 102)* |
| Longitudinal encounters | **4,676** *(was 1,366)* |
| Zoonotic / One Health diseases modelled | **14** *(was 12)* |
| **Reportable diseases encoded (Phase 7)** | **72** (ADHS + CDC NNDSS + USDA APHIS + AZ ADA + AGFD) |
| **Reportable cases placed in dataset (Phase 7)** | **234** (208 human, 26 animal) |
| **One Health domains (Phase 8)** | **3** — Healthcare Institutions / Public Health & Government / Environmental Surveillance |
| **Partner institutions (Phase 8)** | **10** branded logins (6 hospitals + 4 vet practices) + 4 public-health agencies |
| **New staff accounts (Phase 8)** | **38** — registrars + triage nurses + vet techs + discharge + lab techs + administrators |
| **Environmental data feeds (Phase 8)** | **5** — EPA AirNow (14 stations) + NWS + ArboNET (10 traps) + USGS plague-rodent + AGFD wildlife |
| Arizona counties covered | **15** (all of AZ) |
| Distinct ZIP codes used | **43 of 54 reference ZIPs** |
| Disease transmission routes encoded | **7 routes** (direct contact · environmental · vector-borne · foodborne · waterborne · aerosol · fomite) |
| Cross-species clusters in handcrafted scenarios | **12** |
| End-to-end pipeline F1 (synthetic gold-standard) | **0.894** |
| Median per-encounter runtime (CPU only) | **1.2 ms** |
| Active surveillance alerts | **12** |

### Predictive ML pipeline (Phase 2)

| Metric | Value |
|---|---|
| Predictive task | **P(encounter is part of zoonotic cluster within 14 days)** |
| Cluster prevalence (synthetic) | **0.4 %** (18 / 4,676) |
| Models compared | **Logistic regression · Random forest · Gradient boosting · Decision tree (interpretability baseline)** |
| Engineered features | **51** |
| Headline model | **Gradient boosting** |
| Gradient boosting ROC-AUC (5-fold CV) | **0.910** |
| Gradient boosting PR-AUC | **0.166** |
| Gradient boosting Brier (calibration) | **0.0059** |
| Gradient boosting F1 @ threshold 0.5 | **0.167** |
| Random forest ROC-AUC (best discrimination) | **0.961** |
| Explainability methods | **SHAP (TreeExplainer) · Permutation importance · Decision-tree rules** |
| Equity disaggregation slices | **rural/urban · tribal/non-tribal · human/animal · 3 metro tiers** |
| Tribal-land AUC gap (vs. non-tribal) | **−14.0 percentage points** (n=110 vs n=4,566) |
| Rural AUC gap (vs. urban) | **−8.2 percentage points** (n=210 vs n=4,466) |
| Contact tracing — index cases traced | **8 (top-K)** |
| Contact tracing — sensitivity at threshold 0.20 | **100%** |
| Contact tracing — precision at threshold 0.50 | **80%** (10 contacts flagged, 8 catches) |
| Lead time on catchable secondary | **8 days** (Rocco the dog, Hernandez household) |
| Best model-based lead time | **71 days** (Hernandez household, Carlos's earliest elevated-risk encounter) |
| LLM benchmark | **Claude Haiku 4.5** vs. rule-based, 25 dictations |
| LLM F1 (projected, calibrated) | **0.964** vs. rule-based **0.894** |
| LLM latency / cost per dictation | **765 ms / $0.0013** vs. **1.2 ms / $0.0000** |

### Architecture upgrades (Phase 3 — response to lecturer feedback)

| Metric | Value |
|---|---|
| UX restructure | **Two role-based hubs** — Clinical Workspace · Public Health Console |
| Architecture tab | Replaced by **Live Model Card** (Mitchell et al. format, 6 sections, pulls live metrics from `data/synthetic/ml_evaluation.json`) |
| Primary clinical extractor | **MedGemma 4B** (Google DeepMind) with rule-based fallback when no API key |
| Veterinary adaptation layers | **3** — species-router prompt prefix · RAG over Merck Vet Manual + FDA Green Book · LoRA adapters per species class |
| Privacy stack layers | **4** — Swarm learning · DP-SGD (Opacus) · Secure aggregation (Bonawitz CCS'17) · Laplace-noised outputs |
| Federated-learning simulation | **6 sites** (3 hospitals · 2 vet clinics · 1 ADHS) · 10 FedAvg rounds · held-out 25% eval |
| Federated AUC | **0.772** vs. centralized **0.703** (+0.069) |
| Sites with zero local positives that benefit from federation | **2 of 6** lift from AUC 0.500 → 0.772 (**+0.272**) |
| DP-SGD target privacy budget | **(ε ≤ 8.0, δ = 1e-5)** |
| Laplace mechanism on aggregate counts | **ε = 1.0, sensitivity 1** (already shipped on Sentinel Alerts) |

### Access control (Phase 4 — response to lecturer feedback)

| Metric | Value |
|---|---|
| Authentication | **Login parameter** (localStorage-backed mock; production uses SMART-on-FHIR + ADHS SSO + tribal-IRB credentials) |
| User accounts | **10** — 4 physicians · 3 veterinarians · 3 public-health officers |
| Patient-provider mapping | **418 assignments** generated by `src/data_generation/assign_providers.py` |
| Physician panel sizes | **38 to 130 humans** per physician (real PCP scale) |
| Veterinarian panel sizes | **30 to 40 animals** per vet |
| Cross-species redaction | **3-tier model pointer** — household signal · related condition (no name/species) · disease class only · provenance: `model_pointer` |
| Defense in depth | **3 layers** — UI hiding · router-level `activateTab` rejection · renderer-level access-policy refusal |
| Audit log | **Visible to the user** in Model Card; every login, hub change, tab navigation, patient selection, access denial recorded |
| Audit log retention | **Last 500 events** in localStorage |

---

## What this demonstrates

ONE-HealthRecord is a research instrument for showing that **a unified Person × Animal × Environment health record can be machine-built from existing dictation streams**, and that doing so produces real-time clinical decision support that no single-species EHR can match.

Twelve hand-crafted scenarios are designed to make this case end-to-end:

1. **Hernandez (Pima)** — Maria + dog Rocco, Valley Fever cross-species cluster.
2. **Johnson (Pinal)** — Dog Bella ehrlichiosis, husband Tom RMSF presentation.
3. **Williams (rural Maricopa)** — Hantavirus index case, rodent exposure.
4. **Patel (Yuma)** — Dog Rex leptospirosis from canal water.
5. **Chen (Flagstaff)** — Healthy control household.
6. **Begay (Apache)** — Cat Shadow + Sarah, plague cluster.
7. **Ramirez (Cochise)** — Horse Trigger + Roberto, West Nile encephalitis.
8. **Thompson (Mohave)** — Skunk attack on dog Buddy, child Jake rabies exposure.
9. **Becker (Santa Cruz)** — Goat dairy, James Becker Q fever pneumonia.
10. **Nguyen (Maricopa)** — African Grey parrot Mango → Lan Nguyen psittacosis.
11. **Sanchez (Pinal)** — Carlos Sanchez tularemia from rabbit hunting.
12. **Yazzie (Navajo)** — Bearded dragon Spike → daughter Ellie salmonellosis.

Independent of the family-level scenarios, a planted **27.2σ tick-burden anomaly in Pinal County** demonstrates the public-health-scale `VECTOR_ANOMALY` detector.

The Provider Workspace lets you experience the same household graph **from a clinician's chart and from a vet's chart**, demonstrating that cross-species linkage is the default behavior of the system, not a special integration.

---

## Architecture

```
CAPTURE              EXTRACT                RESOLVE                  COMPOSE
─────────            ─────────              ─────────                ─────────
Clinician            Phase classify         SNOMED                   FHIR R4 Bundle
dictation            NER (gazetteer)        ICD-10                   + Provenance
Vet dictation        Negation               LOINC                    + source-text
Synthetic            Hedge detect           RxNorm                     spans
ADHS feed                                   VeNom                    + confidence
                                                                     + engine version

                                  │
                                  ▼

                       ┌──────────────────────────┐
                       │  Knowledge graph (NetworkX │
                       │  → D3) · 694 nodes · 680   │
                       │  edges · cross-species root │
                       └──────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────┬──────────────────┬──────────────────┐
        │ Patient view     │ Provider         │ Sentinel         │
        │ (live encounter) │ workspace        │ surveillance     │
        │ + hand-back UI   │ (longitudinal)   │ + Laplace-noise  │
        └──────────────────┴──────────────────┴──────────────────┘
```

Every machine-authored resource carries:

- The exact source-text span that produced it
- The phase it came from (CC, HPI, PMH, ROS, PE, LAB, A, P, EXP)
- A confidence score (calibrated against the synthetic gold-standard)
- The engine version that produced it

This is what "FAIR by construction" means.

---

## Repository layout

```
one-healthrecord/
├── app/                          # ← Open app/index.html in any browser
│   ├── index.html                # 8-tab demo UI
│   ├── style.css                 # Neomorphism + clinical styling
│   ├── app.js                    # Tab logic, scenarios, hand-back UI, Risk Model views
│   ├── extractor.js              # JS port of the NLP pipeline
│   └── data.js                   # Embedded ~2.5 MB synthetic bundle (incl. ML outputs)
├── data/
│   ├── reference/                # Counties, terminologies, breed maps
│   └── synthetic/                # Households, encounters, surveillance, eval, ML outputs
├── src/
│   ├── data_generation/          # Generators (households / encounters / surveillance / providers)
│   │   └── assign_providers.py   #   Phase 4: county → physician/vet panel assignment
│   ├── nlp/                      # Phase classifier, NER, FHIR builder, MedGemma integration
│   │   └── medgemma_extractor.py #   Phase 3: MedGemma 4B + species router + rule fallback
│   ├── graph/                    # NetworkX knowledge graph
│   ├── surveillance/             # 5 sentinel detectors
│   ├── evaluation/               # Gold-standard + run_eval.py for the rule-based NER
│   ├── ml/                       # Phase 2: predictive risk model + XAI + PH metrics
│   │   ├── build_labels.py            #   binary cluster-membership labels
│   │   ├── feature_engineering.py     #   51 features across 5 families
│   │   ├── train_models.py            #   LR / RF / GBM + decision tree, 5-fold CV
│   │   ├── explain.py                 #   SHAP + permutation + tree
│   │   ├── equity_disaggregation.py   #   stratified AUCs across 4 dimensions
│   │   ├── contact_tracing.py         #   3-tier strategy + risk-triaged eval
│   │   ├── lead_time.py               #   model-based lead-time analysis
│   │   ├── llm_benchmark.py           #   Anthropic API runner (real)
│   │   ├── llm_benchmark_projected.py #   Calibrated projection fallback
│   │   └── federated_simulation.py    #   Phase 3: 6-site FedAvg simulation
│   └── api/                      # FastAPI scaffold (research export)
├── docs/
│   ├── ONE-HealthRecord_Capstone.pptx   # 17-slide deck
│   ├── slide-NN.jpg                     # Slide thumbnails
│   ├── slide_outline.md
│   ├── presenter_script.md              # 13-min spoken narration
│   ├── demo_cheatsheet.md
│   ├── model_card.md                    # Mitchell et al. format (incl. §4B Phase-2)
│   ├── evaluation_report.md             # NER metrics + ML methodology + equity findings
│   ├── video_walkthrough.md             # Screencast script
│   ├── hosting_guide.md                 # Deployment options
│   └── architecture_diagram.svg
└── README.md
```

---

## Reproducing the data and metrics

Everything is reproducible from `seed=42`:

```bash
# 1. Synthetic data
python src/data_generation/household_generator.py
python src/data_generation/surveillance_generator.py
python src/data_generation/encounter_generator.py

# 2. Knowledge graph + alerts
python src/graph/knowledge_graph.py
python src/surveillance/sentinel.py

# 3. Rule-based NER evaluation
python src/evaluation/gold_standard.py
python src/evaluation/run_eval.py

# 4. Phase 2: predictive ML pipeline
python src/ml/build_labels.py            # → labels.json
python src/ml/feature_engineering.py     # → features.parquet (51 features)
python src/ml/train_models.py            # → models.pkl + ml_evaluation.json
python src/ml/explain.py                 # → explanations.json
python src/ml/equity_disaggregation.py   # → equity.json
python src/ml/contact_tracing.py         # → contact_tracing.json
python src/ml/lead_time.py               # → lead_time.json
python src/ml/llm_benchmark_projected.py # → llm_benchmark.json (calibrated projection)
# To replace the projection with measured numbers:
ANTHROPIC_API_KEY=... python src/ml/llm_benchmark.py

# 5. Phase 3: privacy + MedGemma
python src/ml/federated_simulation.py    # → federated.json (6-site FedAvg simulation)
python src/nlp/medgemma_extractor.py     # → medgemma_smoke.json (smoke test)
# To run with live MedGemma API:
MEDGEMMA_API_KEY=... python src/nlp/medgemma_extractor.py

# 6. Phase 4: role-based access control
python src/data_generation/assign_providers.py  # → providers.json (4 phys + 3 vet + 3 PH; 418 assignments)

# 6b. Phase 6: federation manifest + consent records + eMPI
python src/data_generation/partition_shadow_stores.py
python src/data_generation/generate_consents.py
python src/empi/probabilistic_matcher.py

# 6c. Phase 7: place reportable cases on existing patients
python src/data_generation/place_reportable_cases.py  # → reportable_cases.json (234 cases across 60+ diseases)

# 6d. Phase 8: extend provider directory + generate environmental feeds
python src/data_generation/extend_provider_directory.py  # → +38 staff (registrars + triage + discharge + lab + admin + vet techs)
python src/data_generation/environmental_feeds.py        # → environmental_feeds.json (5 feeds, 213 KB)

# 7. Bundle for the demo (regenerates app/data.js)
python src/data_generation/bundle_for_demo.py
```

The `bundle_for_demo.py` script writes `data/synthetic/demo_bundle.json` and updates `app/data.js`, which is what the browser reads.

To regenerate the slide deck:

```bash
cd docs && node build_pptx.js
```

This requires `pptxgenjs` installed globally (`npm i -g pptxgenjs@4.0.1`).

---

## What's intentionally not here

This is a capstone demonstration. The following are **explicit future work**, documented in the model card and the limitations slide:

- **BioClinicalBERT NER** — the rule-based gazetteer is the MVP; production swaps in a fine-tuned transformer.
- **Whisper ASR** — the demo accepts text dictation; production adds audio.
- **Neo4j + GNN cluster detection** — NetworkX is fine at this scale; production migrates as the graph grows.
- **Calibrated ensemble + per-disease specialist heads** — the three-model bake-off is the MVP risk model; production layers per-disease specialists on top.
- **Counterfactual explainability (DiCE)** — SHAP + permutation + decision-tree is the MVP XAI; counterfactual explanations are a future addition.
- **Geospatial mobility-graph contact propagation** — the 3-tier tracing is the MVP; production traces beyond county granularity.
- **Live LLM A/B prompt-engineering** — the projected benchmark is the MVP; production runs measured A/B on real dictations.
- **Full DP-SGD with formal ε-δ accounting** — the demo applies a Laplace-noise stub; production needs a formal privacy budget.
- **Real-data evaluation** — the harness is built; the corpora (i2b2, n2c2, MIMIC-IV, VetCompass) require credentialed access.

These are component swaps, not architectural rewrites. Every interface, schema, and contract is in place.

---

## Documentation

- **`docs/presenter_script.md`** — 13-minute capstone narration, slide-by-slide, with full Q&A bank.
- **`docs/slide_outline.md`** — 17-slide outline, hero elements, timing.
- **`docs/model_card.md`** — Mitchell et al. format. Intended uses, limitations, ethical considerations. §4B documents the Phase-2 predictive risk model.
- **`docs/evaluation_report.md`** — Rule-based NER P / R / F1, calibration, runtime + Phase-2 ML methodology, results, equity disaggregation, contact tracing, lead time, LLM benchmark.
- **`docs/demo_cheatsheet.md`** — One-page reference for live demo flow.
- **`docs/video_walkthrough.md`** — 8-10 minute screencast script.
- **`docs/hosting_guide.md`** — Deployment to Netlify Drop, GitHub Pages, or Vercel.

---

## License and attribution

Capstone work. University of Arizona, April 2026. All synthetic data; no real Arizona resident is represented.
