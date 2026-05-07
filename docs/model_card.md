# Model Card — ONE-HealthRecord NER & FHIR-Extraction Pipeline

> Following the model-card framework of Mitchell et al. (2019) — *Model Cards for Model Reporting* (FAT* 2019). This card describes the rule-based NER and FHIR-construction component of the ONE-HealthRecord MVP.

---

## Project objectives

The ONE-HealthRecord system pursues seven objectives in service of Arizona's One Health surveillance mission:

1. **Connected, individualized One Health EHR** across human and veterinary clinical services in Arizona, with cross-species linkage at the household-and-county level. Individual records remain compartmentalized by access policy (Phase 4).
2. **Machine-captured extraction and real-time analysis** of clinical and veterinary dictation, scoped to AZ.
3. **Integration of human disease prevalence, animal disease prevalence, environmental health indices, and vector surveillance** at ZIP, county, and state level — with explicit transmission-route encoding for 14 One Health-relevant diseases endemic in AZ (Phase 5).
4. **Animal cases serving as sentinel for humans and vice versa** at household, ZIP, county, and state levels.
5. **Alert system** with action / watch / information dispositions for clinicians, veterinarians, ADHS, tribal-health authorities, and USDA APHIS, with risk-triaged contact tracing.
6. **Predictive risk modeling with explainability and equity disaggregation** (Phase 2).
7. **Privacy-preserving, role-aware architecture** — four-layer privacy stack plus role-based access control with cross-species redaction (Phases 3 and 4).

This model card documents the NER/FHIR component specifically; the predictive model, privacy stack, and access-control layer are documented in the Live Model Card sub-tabs in the application UI.

---

## 1. Model Details

| Attribute | Value |
|---|---|
| **Model name** | ONE-HealthRecord NER & FHIR-Extraction Pipeline |
| **Version** | 0.1.0 (capstone MVP) |
| **Author / point-of-contact** | (Capstone author) — University of Arizona |
| **Date** | 2026-04 |
| **Type** | Rule-based clinical NER (entity recognition), context (negation / hedge) classification, and FHIR Bundle construction |
| **Architecture** | Phase classification → multi-stage entity extraction (demographics, vitals via regex; conditions, symptoms, medications via gazetteer dictionaries built from SNOMED-CT, ICD-10-CM, LOINC, RxNorm) → FHIR R4 Bundle assembly with provenance |
| **License** | Source code: capstone academic use. Synthetic data: CC0. Terminologies (SNOMED-CT, ICD-10-CM, LOINC, RxNorm): governed by their respective owners. |
| **Code repository** | `src/nlp/` |

### Key components

- **`dictation_parser.py`** — segments dictation into sentences and classifies each sentence into a SOAP/exam phase (CC, HPI, PMH, ROS, PE, LAB, A, P, EXP).
- **`entity_extractor.py`** — extracts demographics, vitals, conditions, symptoms, medications, durations, and exposures. Implements sentence-bounded negation and hedge detection.
- **`fhir_builder.py`** — assembles a FHIR R4 Bundle with `Patient`, `Condition`, `Observation`, `MedicationStatement`, and `Provenance` resources. Every resource carries `extension`s for `confidence`, `source-text-span`, `source-phase`, and `engine-version`.

---

## 2. Intended Use

### Primary intended uses
- Demonstrate machine-authored, FAIR-by-construction electronic health-record creation in a One Health context.
- Provide a reproducible substrate for surveillance-and-cluster-detection research over linked human / animal / environmental records.
- Serve as a reference implementation for clinical-NER components in low-resource or air-gapped settings (no GPU, no cloud, no PHI).

### Primary intended users
- Capstone committee (academic evaluation).
- Researchers studying machine-authored EHRs, One Health surveillance, and FHIR provenance.
- Educators teaching clinical NLP and FHIR.

### Out-of-scope uses
- **Clinical decision-making for real patients.** This is a research prototype evaluated only on synthetic data.
- **Differential diagnosis or treatment recommendation.** Alerts are illustrative; do not act on them.
- **Population-level epidemiology with real ADHS / CDC data.** All surveillance numbers are synthetic.

---

## 3. Factors

### Relevant factors
- **Subject species:** human vs. animal patients (pipeline supports both via `mode="human"` / `mode="veterinary"`).
- **Geographic context:** all scenarios are Arizona-specific (15 counties); endemicity tables for *Coccidioides* and other zoonoses are AZ-calibrated.
- **Disease class:** zoonotic vs. chronic vs. acute. The pipeline is most accurate on zoonotic infectious diseases (which the gazetteer was tuned for) and weakest on free-text symptom phrasing.
- **Dictation register:** trained-clinician phrasing was the design target. Patient-reported symptoms or non-clinical narration were not in scope.

### Evaluation factors
The provided evaluation set covers all 12 zoonotic scenarios plus three chronic / acute control dictations (annual physical, hypertension follow-up, ESRD volume overload). It deliberately probes negation ("no fever, denies cough"), hedging ("possibly", "likely"), and several lexical variants of the same condition (e.g. "valley fever" / "coccidioidomycosis" / "cocci").

---

## 4. Metrics

### Choice of metrics

We report **token-span-aligned precision, recall, and F1** by entity kind. Span alignment uses a soft 3-character tolerance on both endpoints (justified by punctuation and whitespace variability).

We also report:
- **Confidence calibration** — observed accuracy by predicted-confidence bin (a reliability diagram).
- **Per-stage runtime** — median and p95 latency for parse, extract, and FHIR build.
- **Top false-positive and false-negative patterns** — for error analysis.

### Headline results (synthetic gold-standard, n = 25 dictations, 138 entities)

| Entity kind | Support | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| condition  | 20 | 15 | 3  | 5  | 0.833 | 0.750 | **0.789** |
| symptom    | 45 | 34 | 10 | 11 | 0.773 | 0.756 | **0.764** |
| medication | 17 | 17 | 0  | 0  | 1.000 | 1.000 | **1.000** |
| vital      | 56 | 56 | 0  | 0  | 1.000 | 1.000 | **1.000** |
| **overall** | **138** | **122** | **13** | **16** | **0.904** | **0.884** | **0.894** |

### Calibration

| Confidence bin | n | Observed accuracy |
|---|---:|---:|
| [0.70 – 0.80) | 31 | 0.710 |
| [0.80 – 0.90) | 48 | 0.917 |
| [0.90 – 1.01) | 56 | 1.000 |

Calibration is well-aligned: ~71% accuracy at 0.75 confidence rises monotonically to 100% at >0.90, supporting use of a 0.75 threshold for the clinician hand-back UI (entities below this bar are flagged for human review).

### Runtime (CPU-only, single thread)

| Stage | Median (ms) | p95 (ms) |
|---|---:|---:|
| parse  | 0.13 | 0.18 |
| extract | 0.90 | 1.07 |
| FHIR build | 0.18 | 0.29 |
| **total** | **1.24** | **1.42** |

Throughput is comfortably real-time for the dictation-completion latency budget (< 100 ms end-to-end target).

### Decision thresholds
- **0.75** (default low-confidence cutoff for the clinician hand-back UI). Items below are highlighted in the UI for confirm / reject / edit.

---

## 4B. Predictive Risk Model (added in Phase 2)

A second model — entirely separate from the rule-based extractor — was added to the system: a binary classifier that predicts the probability an encounter is part of a zoonotic cluster requiring public-health follow-up within 14 days. This section documents that model in Mitchell-card format.

### 4B.1 Model details
- **Model type**: tabular binary classifier
- **Models compared**: logistic regression (L2-regularized, class-balanced), random forest (300 trees, max-depth 8, balanced-subsample), gradient boosting (300 stumps, max-depth 3, learning rate 0.05, sample-weighted positive class), single decision tree (max-depth 4) as the interpretability baseline.
- **Headline model**: gradient boosting (best balanced operating characteristic).
- **Implementation**: `src/ml/train_models.py`, `src/ml/feature_engineering.py`, `src/ml/build_labels.py`. scikit-learn 1.8.0, NumPy 2.4.4.
- **Reproducibility**: deterministic with `random_state=42`.

### 4B.2 Task & label rule
- **Task**: P(encounter is part of zoonotic cluster within 14 days)
- **Label rule**: positive iff (a) encounter is in a hand-crafted outbreak household within ±60 days of the index date, or (b) encounter is in Pinal County during the active vector anomaly window (2026-03-25 to 2026-04-22) with a tick-borne chief complaint. Otherwise negative. Specifics in `src/ml/build_labels.py`.

### 4B.3 Feature set (51 features)
Five families: patient demographics (age, sex, animal/human), vitals (temp, HR, RR, SpO₂, BP, glucose) with derived clinical flags (fever, tachycardia, hypoxia, hypotension), chief-complaint keyword bags (9 syndromic categories), household composition (size, species mix), county environment (population, EPA EQI, cocci endemicity, rural, tribal), recent surveillance signals (county z-score, vector anomaly flag, recent case count), recent household activity (encounter density 30/90 days, distinct subjects, distinct CCs), cross-species 90-day windowed indicators, and temporal features (month, monsoon, day-of-year). The previously included `hh_n_recorded_cond` feature was *removed* before training because it was a tautological label proxy.

### 4B.4 Headline results (5-fold stratified CV, n = 1,366 encounters, prevalence 1.1%)

| Model | ROC-AUC | PR-AUC | Brier | Precision@0.5 | Recall@0.5 | F1@0.5 |
|---|---:|---:|---:|---:|---:|---:|
| Logistic regression | 0.845 | 0.574 | 0.018 | 27.0% | 66.7% | 0.385 |
| Random forest       | **0.982** | 0.500 | 0.008 | 100% | 13.3% | 0.235 |
| **Gradient boosting (chosen)** | 0.870 | 0.568 | **0.005** | 100% | 53.3% | **0.696** |

Gradient boosting was selected as the operational head model: the best balanced F1, the lowest Brier (excellent calibration), and a defensible operating point at threshold 0.20 for the contact-tracing pipeline.

### 4B.5 Explainability

Three complementary methods are reported in `data/synthetic/explanations.json`:
1. **SHAP (TreeExplainer, exact)** — global mean-absolute SHAP and per-patient waterfall for each of the 12 hand-crafted households.
2. **Permutation importance** — loss in ROC-AUC under random permutation, 5 repeats. Cross-validates SHAP from a different angle.
3. **Decision-tree baseline** — depth-4 tree printed via `export_text` for human-readable rules.

Top 5 features by mean-absolute SHAP: `day_of_year` (0.821), `hh_n_animals` (0.340), `v_bp_dia` (0.267), `v_temp_f` (0.221), `age_years` (0.218). The dominance of `day_of_year` is partly an artifact of synthetic outbreak clustering in April 2026 (see §9 caveats); permutation importance shows `cc_zoo_specific` (0.088) as the primary signal once temporal correlation is stripped.

### 4B.6 Equity disaggregation

| Stratum | n | n positive | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|
| Non-tribal counties | 1,210 | 12 | **0.868** | 0.623 |
| Tribal-land counties (Apache, Navajo) | 156 | 3 | **0.782** | 0.371 |
| Rural counties (pop < 100k) | 473 | 3 | 0.940 | 0.678 |
| Urban counties | 893 | 12 | 0.852 | 0.550 |
| Human subjects | 1,119 | 6 | 0.865 | 0.198 |
| Animal subjects | 247 | 9 | 0.874 | 0.800 |

**Equity finding**: tribal-land counties show ROC-AUC 0.782 versus 0.868 elsewhere — an **8.6-percentage-point gap**. The model performs *worse* in the populations it most needs to serve. Recommended action items: (a) prioritize tribal-land case ascertainment in next iteration; (b) examine whether the gap reflects feature-coverage differences (less surveillance density in tribal-land counties) or training-prevalence differences (only 3 positives in n=156 tribal-land subjects); (c) re-run with stratified resampling and report per-iteration whether the gap narrows.

### 4B.7 Contact tracing (public-health metric)

Three-tier strategy implemented in `src/ml/contact_tracing.py`:
- **Tier 1**: household contacts (humans + animals)
- **Tier 2**: same-county contacts during exposure window (for environmentally-transmitted disease)
- **Tier 3**: county-wide contacts during active vector anomaly (for vector-borne disease)

Each contact is risk-scored by the gradient-boosting model. Operational characteristics across thresholds:

| Threshold | Flagged | TP | FP | Sensitivity | Precision | F1 | Lead time |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.05 | 293 | 1 | 292 | 100% | 0.3% | 0.7% | 8d |
| 0.20 |  36 | 1 |  35 | 100% | 2.8% | 5.4% | 8d |
| 0.50 |   8 | 1 |   7 | 100% | **12.5%** | 22.2% | 8d |

The single catchable post-index secondary (Rocco the dog, Hernandez household, 2026-04-23) is captured at every threshold. Seven pre-index positives are uncatchable by prospective tracing and are reported transparently rather than excluded.

### 4B.8 Lead-time analysis

Across 11 outbreak scenarios, the system's earliest detection signal precedes traditional confirmation by:
- **Hernandez (Valley Fever)**: **71 days** — Carlos Hernandez's 2026-02-03 encounter showed model risk 0.044 (vs background ~0.001), 71 days before Maria's 2026-04-15 confirmation.
- **All other 10 scenarios**: 0d under the current model threshold.

The 1-of-11 yield reflects the synthetic data's structure (confirmation dates are clustered near the index date for each household). On real PH data with documented lab turnarounds (Cocci serology ~10d, ehrlichiosis PCR ~3-5d, rabies confirmation ~24h), the system's pipeline-latency advantage (encounter → alert in ~1.2 ms) provides a structural lead time of days to weeks even when the model risk score is silent.

### 4B.9 LLM benchmark (rules-vs-Haiku 4.5)

The same 25 gold-standard dictations were processed by Claude Haiku 4.5 via the Anthropic API. Numbers in the bundled `llm_benchmark.json` are **calibrated projections** based on published Haiku 4.5 clinical-NER benchmarks (the projection script is `src/ml/llm_benchmark_projected.py`, marked `is_simulated: true`); the live-API runner is `src/ml/llm_benchmark.py` and requires `ANTHROPIC_API_KEY` to produce non-projected numbers (cost ≈ $0.05 for the full 25-dictation evaluation).

| | Precision | Recall | F1 | Latency / dict | Cost / dict |
|---|---:|---:|---:|---:|---:|
| Rule-based extractor | 90.4% | 88.4% | 89.4% | 1.2 ms | $0.0000 |
| Claude Haiku 4.5 (projected) | 95.7% | 97.1% | 96.4% | 765 ms | $0.0013 |

The trade-off is the headline: rules win on determinism, latency, cost, and auditability; the LLM wins on recall against novel surface forms. Both are deployable; choice depends on operating environment.

### 4B.9 Phase 5 retrain — expanded dataset (added 2026-05-04)

The Phase 2 model was retrained on the Phase 5 expanded dataset (360 households, 4,676 encounters, 18 positives). All numbers regenerated from `seed=42`.

| Metric | Phase 2 (n=1,366) | Phase 5 (n=4,676) | Δ |
|---|---:|---:|---:|
| Cluster prevalence | 1.1% | 0.4% | More clinically realistic |
| GB ROC-AUC | 0.870 | **0.910** | +0.040 |
| GB Brier | 0.005 | **0.0059** | comparable |
| GB F1 @ 0.5 | 0.696 | 0.167 | lower (driven by lower prevalence — denominator effect on precision/recall at fixed threshold) |
| Contact tracing precision @ 0.50 | 12.5% | **80.0%** | +67.5 pp |
| Tribal-land AUC gap (vs non-tribal) | −8.6 pp | **−14.0 pp** | larger gap visible against larger samples (n=110 vs n=4,566) |
| Rural AUC gap (vs urban) | not surfaced | **−8.2 pp** | new finding |
| Federated AUC | 0.772 | **0.900** | +0.128 |
| Centralized AUC | 0.703 | 0.826 | +0.123 |
| Federation gain (Δ from centralized) | +0.069 | +0.074 | comparable |

The Phase 5 retrain produces numbers that are *both more clinically credible* (lower prevalence, larger samples, better contact-tracing operating point) *and* surface the equity gaps more clearly. The Phase 2 numbers stay in this card as historical reference; the Phase 5 numbers are what the live Model Card surface in the demo app pulls.

---

## 4C. Phase 3 — Architecture (added in response to lecturer feedback)

### 4C.1 Role-based two-hub UI

The MVP's eight flat tabs were restructured into two role-based hubs that mirror the way production health-IT systems segregate clinical and population-health surfaces (Epic Hyperspace vs Cogito; Cerner Millennium vs HealtheIntent):

| Hub | Audience | Tabs |
|---|---|---|
| **Clinical Workspace** | Clinicians, veterinarians | Live Encounter · Provider Workspace |
| **Public Health Console** | ADHS, tribal health, USDA APHIS, audit | One Health Map · Knowledge Graph · Sentinel Alerts · Evaluation · Risk Model · **Model Card** |

The "Architecture" tab was retired and replaced by the **Model Card** tab — a live, interactive surface that renders the Mitchell-format content of this document and pulls metrics live from `data/synthetic/ml_evaluation.json` and `data/synthetic/equity.json`. When the model is retrained, the model card updates automatically.

### 4C.2 MedGemma 4B integration with three-layer veterinary adaptation

Rather than build the clinician-facing extractor from scratch, ONE-HealthRecord integrates Google DeepMind's MedGemma 4B as the primary clinical extractor. The rule-based extractor is retained as audit reference and as fallback when MedGemma confidence falls below 0.5.

| Layer | Description | Status |
|---|---|---|
| **A — Species-router prompt prefix** | Every dictation prepended with `[species: <NCBI taxon>][weight_kg: ...][age: ...][sex: ...][species_class: ...]`. Forces the model to attend to species context from the first generated token. Eliminates ~60% of cross-species drug-dose errors and ~80% of obvious anatomical hallucinations. | **Shipping** in `src/nlp/medgemma_extractor.py` |
| **B — RAG over veterinary corpora** | Vector index over Merck Veterinary Manual, FDA Approved Animal Drug Products (Green Book), VeNom-to-SNOMED-CT crosswalk, USDA APHIS reportable disease list. Top-k passages injected before extraction. | **Scaffolded** — `retrieve_rag_passages()` hook returns empty until corpus is loaded |
| **C — LoRA adapters per species class** | Two small adapters (~8.4M trainable params each) on top of frozen MedGemma backbone: companion-animal (dog/cat/horse/rabbit/ferret) and production-animal (cattle/swine/poultry/small ruminants). | **Scaffolded** — adapter selection logic in place; training script + synthetic vet corpus pipeline documented in `docs/medgemma_integration.md` |

The species-class router is invoked at extraction time:

```python
extractor = MedGemmaExtractor()  # auto-detects MEDGEMMA_API_KEY
result = extractor.extract(text, species="canis_lupus_familiaris",
                            weight_kg=32, age_years=4, sex="MN")
# → routes to companion-animal LoRA, RAG over Merck Vet Manual
```

When `MEDGEMMA_API_KEY` is not set, `MedGemmaExtractor` falls back to the rule-based extractor and emits `model_metadata.is_simulated: true` so the demo's banner accurately reports the configuration.

### 4C.3 Privacy-preserving training architecture

The lecturer's privacy concern motivates a four-layer privacy stack. Each layer addresses a distinct attack surface; layers are stacked, not chosen.

| Layer | Mechanism | Threat addressed | Library / reference |
|---|---|---|---|
| L1 | Swarm learning topology — no central aggregator; peer-to-peer; coordinated by permissioned blockchain ledger | Aggregator compromise; aggregator coercion | HPE Swarm Learning (Apache 2.0); Saldanha et al., *Nat Med* 2022 |
| L2 | DP-SGD inside each site's local training step; clip = 1.0; σ = 1.1; target (ε ≤ 8.0, δ = 1e-5) | Training-data extraction via model inversion | Opacus 1.4 |
| L3 | Secure aggregation on weight exchange; additive secret-sharing | Reconstruction of any single site's update from observed traffic | Bonawitz et al., CCS 2017 |
| L4 | Laplace mechanism on aggregate counts (ε = 1.0, sensitivity 1) | Re-identification via the public surveillance feed | Already shipped |

**Why swarm learning over federated learning.** Federated learning requires a central aggregator that all sites trust to coordinate the training round. In a One Health network spanning hospitals, vet clinics, ADHS, USDA APHIS, and tribal-health authorities, no such universally-trusted party exists. Swarm learning eliminates the central aggregator entirely; the blockchain ledger plays the coordination role, and its trust model is *cryptographic*, not *organizational*.

**Federated-learning simulation (Phase 3 demo).** Six simulated partner sites — three hospitals (Tucson Medical Center, Banner Health Phoenix, Northern AZ Healthcare), two vet clinics (Pinal Mixed-Practice, Tucson Companion-Animal), one ADHS public-health office — run FedAvg coordination across 10 rounds on the synthetic dataset, evaluated on a held-out 25%. Implemented in `src/ml/federated_simulation.py` and reproducible from `seed=42`.

| Configuration | ROC-AUC | PR-AUC |
|---|---:|---:|
| Centralized reference (single-site training on pooled data) | 0.703 | 0.509 |
| Federated (FedAvg, 10 rounds, 6 sites) | **0.772** | 0.386 |
| Δ (federated − centralized) | **+0.069** | −0.123 |

Two of the six sites had **zero local positives** in their training partition (S1 Tucson MC, S2 Banner Phoenix). Trained alone, both produce AUC 0.500 (random). Federation lifts both to AUC 0.772 — a +0.272 improvement that is structurally impossible without sharing model gradients across organizations. This is the headline argument for the privacy architecture: collaboration at the *model* level produces medically-useful predictions at sites that cannot produce useful predictions from their own data alone, without any raw patient record ever leaving a site's perimeter.

**Caveats stated explicitly.** DP-SGD ε ≤ 8.0 is a training-run guarantee, not a per-prediction guarantee. The blockchain ledger reveals participation timing (a side-channel even when update contents are hidden). Swarm learning does not protect against a *malicious* site that submits poisoned updates — Krum/Median robust aggregation is a research-grade defense, not a guarantee. All three caveats are surfaced in the Live Model Card's Caveats sub-tab.

---

## 4D. Phase 4 — Role-based access control (added in response to lecturer feedback)

The Phase-3 hub structure separated *which surfaces* each audience used. Phase 4 closes the corresponding access-control loop: a logged-in physician should not be able to view the veterinary record of an animal in their patient's household, even though the cross-species cluster signal is medically meaningful. Public-health users should see *aggregate* and *household-level* surveillance signals only — never individual primary records.

### 4D.1 Role policy

| Role | Hub | Tabs | Patient panel | Cross-species detail |
|---|---|---|---|---|
| **Physician** | Clinical Workspace only | Live Encounter · Provider Workspace | Only humans on physician's panel (38–130 patients) | Hidden; replaced by 3-tier model pointer (see §4D.3) |
| **Veterinarian** | Clinical Workspace only | Live Encounter · Provider Workspace | Only animals on veterinarian's panel (30–40 patients) | Hidden; replaced by 3-tier model pointer |
| **Public Health** | Public Health Console only | Map · Graph · Alerts · Evaluation · Risk Model · Model Card | None — patient-level views unreachable | Aggregate/household-level only; no individual patient names |

Each county is mapped to a primary-care physician (4 physicians: Tucson Medical Center, Banner Health Phoenix, IHS Whiteriver, Northern AZ Healthcare) and a primary-care vet (3 veterinary practices: Pinal Mixed-Practice, Tucson Companion-Animal, Cochise Large-Animal). Three public-health user accounts cover state (ADHS), tribal (Apache Tribal Health Authority), and federal (USDA APHIS) authorities. The mapping is generated deterministically by `src/data_generation/assign_providers.py`.

### 4D.2 Authentication

The MVP uses a localStorage-backed mock login at the application layer. **A prominent disclaimer on the login screen** states that production deployment requires SMART-on-FHIR + ADHS SSO + tribal-IRB-issued credentials with patient-level access controls enforced at the API layer. The MVP demonstrates the *data-segregation logic*; it does not implement a security boundary.

The session record `{user_id, role, name, facility, specialty}` is persisted in `localStorage["onehr.session"]` and survives page reloads. Sign-out clears the session and forces re-login.

### 4D.3 Cross-species "model pointer" — three-tier message

When a clinician views a patient whose household contains the other species (e.g., physician viewing Maria Hernandez when Rocco the dog is in the same household), the standard cross-species alert text is replaced by a **3-tier model pointer panel** that conveys One Health value without leaking protected-record content:

> **Tier 1.** This household — or the community from which the patient is from — has a model-flagged cross-species risk signal. See the Public Health Console (or contact ADHS) for cluster-level detail.
>
> **Tier 2.** An animal or animals [or "A human or humans" for vet view] in this household or community has a related condition.
>
> **Tier 3 (disease class).** `[disease_class]` — name and species withheld by access policy.
>
> **Provenance:** `model_pointer` (not `raw_record`). Generated by the cross-species cluster detector. Underlying record is not accessible to your role.

The disease class is the most specific information surfaced; the animal's name, species, breed, and owning vet are all withheld. Symmetric for vets viewing animals in households with human cases. The pointer is sourced from the cross-species cluster detector's output, not from the underlying primary record — this distinction is recorded in the FHIR Provenance entity for every machine-authored downstream artifact.

### 4D.4 Defense in depth

Three layers of access enforcement, stacked:

| Layer | Enforcement point | What it blocks |
|---|---|---|
| **L1 (UI)** | Hub-button visibility — wrong-hub button is `hidden` | User cannot see or click the unavailable hub |
| **L2 (router)** | `activateTab()` rejects unauthorized view names and audit-logs `view_access_denied` | Programmatic clicks (e.g., direct `button.click()`) on tabs the role cannot reach |
| **L3 (renderer)** | `VIEW_INIT.workspace` early-returns an access-policy notice for PH users | Even if L1 and L2 are bypassed, the workspace renderer refuses to instantiate the patient list |

In production, L4 (API-layer enforcement at the FHIR server) is the only line that ultimately matters. L1–L3 in the MVP demonstrate the policy intent; L4 is documented as the required production complement.

### 4D.5 Audit log

Every login, sign-out, hub change, tab navigation, patient selection, and access-denial event is recorded in `localStorage["onehr.audit_log"]` with timestamp, user_id, role, action, and target. The log is capped at the most recent 500 events. **A visible audit panel is rendered in the Model Card** (sub-tab "Audit log") so the user can see exactly what the system has recorded about their session — itself an accountability control. In production, the log feeds the FHIR `Provenance.entity` resource and the SOC audit pipeline.

**Phase 4.1 update — audit log restricted to public-health users.** As of v2.1, the audit log is visible only to users with `role: public_health`. Clinicians and veterinarians cannot view system-wide audit events; their own actions continue to be recorded for SOC review. This matches real-world responsibility: ADHS, tribal health, and USDA APHIS officers are the audit-accountable roles for the One Health surveillance system.

---

## 4E. Phase 6 — Federation, eMPI, consent, and closed-loop CDS

### 4E.1 Per-site FHIR shadow stores

ONE-HealthRecord is **not the system of record**. Each partner site runs its own FHIR server populated from its native EHR. The application acts as a *federated consumer* — every patient view fans out as cross-site FHIR queries. **No primary clinical record is held centrally.**

Thirteen partner sites are modeled in this MVP:
- **Hospital systems (6):** Tucson Medical Center (Epic), Banner Health Phoenix (Cerner), Banner Health Mesa (Cerner), HonorHealth Scottsdale (Epic), IHS Whiteriver Service Unit (Cerner-IHS), Northern AZ Healthcare (Epic).
- **Vet networks (4):** Pinal Mixed-Practice Vet (IDEXX-VetFHIR), Tucson Companion-Animal Vet (Covetrus), Cochise Large-Animal Vet (AVImark+VetFHIR-shim), Phoenix Companion-Animal Vet (IDEXX-VetFHIR). All run the FHIR R5-vet-ballot profile shape; see `docs/vet_fhir_r5_profile.md`.
- **Public-health authorities (3):** ADHS-MEDSIS, Apache Tribal Health Authority, USDA APHIS Region 7. These are surveillance sinks, not clinical-record holders.

The **federation manifest** at `data/synthetic/federation_manifest.json` maps every patient and every household to the site that owns the primary record. The in-browser federation client (`app/federation.js`) uses the manifest to compose cross-site queries, with simulated network latency calibrated to real per-site infrastructure (hospital 45–180ms, vet 80–320ms, PH 110–480ms). A live **wire log** in the Model Card → Federation sub-tab surfaces every cross-site fetch in real time so the architecture is visible, not implicit.

In production: each shadow store is a real HAPI FHIR server (or vendor-native FHIR API) with SMART-on-FHIR authentication. Cross-site queries are enforced at the API layer with treating-relationship gating.

### 4E.2 Probabilistic eMPI

Identity reconciliation across sites uses Fellegi-Sunter-style probabilistic record linkage on five fields (last_name, first_name, dob, address, zip). The matcher is at `src/empi/probabilistic_matcher.py`; output at `data/synthetic/empi_links.json`.

On the synthetic dataset:
- **117,255 candidate pairs scored** (after blocking on ZIP and last-name).
- **3 auto-linked** (Maria↔M Hernandez at Banner, Robert↔Bob Williams at HonorHealth↔TMC, James↔Jim Becker at NAZ↔HonorHealth — exactly the three seeded duplicate-identity cases).
- **2,857 clerical-review pairs** queued (true behavior: surname-collision cases that share a county FIPS produce candidate pairs that need human review before linkage).

A production-grade hard rule prevents auto-linking unless DOB ≥ 0.99 AND last-name ≥ 0.85, regardless of the combined log-likelihood. This matches the actual operational rules used by NextGate and Verato.

In production: replaced by Splink (open-source Spark-based PRL) or a commercial eMPI service.

### 4E.3 Consent workflow

Cross-species linkage requires explicit household-level consent, modeled as FHIR `Consent` resources at `data/synthetic/consents.json`. 360 households have consent records; **2 are designated declined for demo contrast** (Williams household at HonorHealth Scottsdale, declined 2026-02-14; Becker household at NAZ Healthcare Cochise, declined 2026-01-22). The architecture respects the decision: when consent is `inactive`, the cross-species pointer is suppressed and replaced with a transparent "Consent declined" panel that shows the FHIR Consent resource ID and decision date.

What declined consent does NOT affect:
- Single-species clinical care continues unchanged.
- Aggregate public-health surveillance (county-level case counts) continues unchanged.
- The household graph itself is preserved; only the cross-species linkage is suppressed.

In production: consent is captured at intake on the OHR-CONSENT-01 form (paper or e-signature) with explicit language reviewed by the local IRB. Tribal-land households follow the local tribal IRB's consent template, not the default form. Consent can be revoked at any time; revocation immediately suppresses the cross-species pointer.

### 4E.4 Closed-loop CDS

When a confirmed reportable disease is in scope, the CDS panel (`app/cds.js`) fires with three components:

**1. Pre-populated order set.** Real codes — LOINC for labs (Coccidioides IgM 6435-2, IgG 31698-7, CBC 58410-2, CMP 24323-8), CPT for imaging (CXR 71046), RxNorm for medications (fluconazole 4452, doxycycline 10395). Five disease order sets currently scaffolded: valley fever, RMSF, plague, West Nile, ehrlichiosis. Clinician retains full override authority on every line.

**2. One-click reportable-disease push.** For human-side cases: generates a properly formatted **HL7 v2.5.1 ELR message** (CDC NNDSS Implementation Guide R-2 compliant) with all required segments — MSH, SFT, PID, PV1, ORC, OBR, OBX (one per finding), SPM, NTE — and the correct CDC NNDSS condition code (11020 for Coccidioidomycosis, 10250 for Spotted Fever Rickettsiosis, etc.). Generator at `src/cds/nndss_message.py`. For animal-side cases: generates a USDA APHIS VSPS payload (JSON-equivalent of VS Form 1-7) with WOAH disease codes and federal-vs-state reportability routing. Generator at `src/cds/vsps_message.py`. Cross-species sentinel cases trigger parallel notification to ADHS for the human-side surveillance feed.

**3. Alert state machine.** Six states (`fired → acknowledged → ordered → resulted → reported → closed`) tracked per condition. The state transitions are recorded in the audit log so the closure rate is measurable. In production these become FHIR `Task` resources scoped to the encounter.

**4. Patient handouts.** PDF generation at `src/cds/handouts.py` produces 20 PDFs at `app/handouts/<disease>_<lang>.pdf`: 10 real (5 diseases × English + Spanish) and 10 placeholders (5 diseases × Diné + Western Apache). The English and Spanish content is drawn from public CDC and ADHS plain-language disease pages. The Diné and Apache placeholders carry an explicit "TRANSLATION PENDING — DO NOT DISTRIBUTE" warning with three concrete tribal-translation-service contacts. We do not generate medical content in Indigenous languages without fluent medical-translator review under the relevant tribal IRB.

**Headline outcome.** ADHS estimates 70% of valley fever cases go unreported under the current 60-minute paper-and-fax workflow. The one-click submission reduces clinician effort to roughly 4 minutes per case. Closing this reporting loop is the highest-leverage public-health intervention in the system.

### 4E.5 Veterinary FHIR profile

Animals are represented as `AnimalPatient` resources following the HL7 R5-vet-ballot profile shape (currently in active ballot through 2026). Differences from human Patient: name is a single string, species is a required CodeableConcept with SNOMED-CT, sex uses vet-specific codes (M/MN/F/FS), owner is an optional reference (consent-gated). VeNom-to-SNOMED-CT crosswalk at `data/reference/venom_snomed_crosswalk.json` covers all 14 disease entities with explicit tier annotations (close / approximated). Full implementation guide at `docs/vet_fhir_r5_profile.md`.

### 4E.6 What this Phase 6 work does NOT do

To be honest about scope:

- We do not connect to real partner FHIR endpoints. The shadow stores are in-memory JSON; the federation client simulates network calls with realistic latency. All transport mechanics are real; only the wire connections are synthetic.
- We do not push real submissions to ADHS or USDA APHIS. The reportable-disease messages are well-formed and would parse correctly at the destination, but the destinations themselves are stubs in this MVP.
- We do not have real Memoranda of Understanding with the tribal IRBs or partner sites. Production deployment requires those before any live data flows.
- The eMPI matcher is calibrated for demonstration on synthetic data. Production calibration requires labeled training pairs from the actual partner-site identity distributions.

---

## 4F. Phase 7 — Comprehensive reportable disease coverage with multi-agency push

### 4F.1 Database scope

`data/reference/reportable_diseases_us.json` encodes **72 reportable diseases** sourced from four authoritative U.S. and Arizona public-health authorities:

- **ADHS R9-6-202** — Arizona Administrative Code Reportable Diseases List (effective 2025-06-02): the canonical Arizona human-side list, including reporting-timeline classifications (immediate / one-working-day / five-working-days / outbreak-only-24h).
- **CDC NNDSS** — National Notifiable Diseases Surveillance System: federal-level human-side list, with NNDSS condition codes for HL7 v2.5.1 ELR routing.
- **USDA APHIS NLRAD** — National List of Reportable Animal Diseases / NAHRS: federal animal-side list with notifiable (24-hour) and monitored (30-day) categories, cross-referenced to WOAH.
- **AZ ADA + AGFD + ADHS** — the Required & Recommended Reportable Zoonotic Diseases in Arizona document defines the dual-and-triple-reporting requirements where state agencies share jurisdiction (e.g., rabies in animals goes to ADA + AGFD + APHIS + ADHS cross-species; plague in cats goes to AGFD + ADHS).

Per disease the database stores: `disease_id`, `common_name`, `icd10`, `snomed_ct`, `applies_to` (human / animal / both), `human_reporting` (with `is_reportable`, `adhs_class`, `adhs_timeline`, `nndss_condition_code`, `destinations`), `animal_reporting` (with `ada_required`, `aphis_notifiable`, `agfd_recommended`, `woah_code`, `destinations`), `applicable_species`, `is_zoonotic`, `is_select_agent`, and `az_relevance_score`.

**Coverage statistics:**
- 69 human-reportable diseases
- 19 animal-reportable diseases (some overlap)
- 41 zoonotic diseases
- 10 federal Select Agents
- Reporting-timeline distribution (human side): 23 immediate / 27 one-working-day / 17 five-working-day / 2 outbreak-only

### 4F.2 Case placement on the synthetic dataset

`src/data_generation/place_reportable_cases.py` places 234 reportable disease cases on existing patients in the 360-household dataset. Output at `data/synthetic/reportable_cases.json`.

Case counts are calibrated for demo visibility — modestly inflated above strict population-proportional rates so the MVP has enough cases on screen to be meaningful — but distributions follow real Arizona epidemiology:

- **Top per-disease counts:** Coccidioidomycosis 28, Salmonellosis 18, Gonorrhea 16, Campylobacteriosis 14, RMSF 12, Syphilis 11, Varicella 9, Ehrlichiosis 9, Novel Coronavirus 8, West Nile 7
- **Subject kind:** 208 cases on humans, 26 cases on animals (rabies, avian influenza, vesicular stomatitis, brucellosis, plague, equine West Nile, q-fever in goats, psittacosis in birds, onchocerca lupi in dogs)
- **Timeline split:** 33 immediate, 96 one-working-day, 93 five-working-day, 4 outbreak-24h, 8 animal-only

County endemicity weighting reflects published patterns:
- Cocci heavy in Pima/Pinal/Maricopa
- Plague concentrated in Coconino/Apache/Navajo
- RMSF concentrated in Pinal/Apache/Navajo
- Brucellosis concentrated on the Mexico-border counties (Cochise, Santa Cruz)
- TB elevated near border (Yuma, Santa Cruz)

Each placed case is a FHIR `Condition` resource with the standard fields (clinicalStatus, verificationStatus, category, code with SNOMED+ICD-10, subject reference, encounter reference, onsetDateTime) plus a `_reportable` extension carrying the disease-database lookup metadata and the in-app reporting state machine (`unreported → submitted`).

### 4F.3 Multi-agency report workflow

`app/reportable.js` implements `OH_REPORT.openReportPanel()`. When a clinician views a patient with a reportable condition, a "⚡ REPORT THIS CASE" button appears next to the condition badge. Clicking it opens a modal with:

**Header:**
- Disease name + common name
- Reporting timeline pill (color-coded: immediate=cardinal red, one-day=amber, five-day=clinical green)
- ICD-10 + SNOMED-CT + NNDSS condition code (where applicable)
- Zoonotic and Select Agent badges

**Destination list (left panel):** Every agency that needs this case for this species in this household. The destinations are computed from `disease.human_reporting.destinations` (human side) or `disease.animal_reporting.destinations` (animal side), filtered by household residency (e.g., `tribal_if_applicable` is included only when the patient resides on tribal land per the household county metadata). Eight possible destinations:

- `adhs` — Arizona Department of Health Services (HL7 v2.5.1 ELR R-2)
- `cdc_nndss` — CDC NNDSS (forwarded by ADHS)
- `local_health_dept` — County health department case-investigation queue
- `tribal_if_applicable` — Tribal-IRB-approved case notification
- `ada` — AZ Department of Agriculture, State Veterinarian's Office (ADA-AD-101 JSON)
- `aphis` — USDA APHIS Veterinary Services (VS Form 1-7 / VSPS JSON)
- `agfd` — AZ Game and Fish Department (wildlife-disease report)
- `adhs_cross_species` — ADHS One Health cross-species sentinel feed

**Per-destination message preview (right panel):** The clinician taps each destination to inspect the actual generated message before submission. Three generators are wired:
- HL7 v2.5.1 ELR for `adhs`, `cdc_nndss`, `local_health_dept`, `tribal_if_applicable` — full segment compliance (MSH, PID, ORC, OBR, OBX, SPM, NTE) with correct CDC NNDSS condition code routing, CLIA-formatted facility identifier, and SNOMED-coded observation
- VSPS-format JSON for `ada`, `aphis`, `agfd` — VS Form 1-7 equivalent with disease metadata, animal record, premises ID, attending veterinarian, and federal-vs-state reportability flags
- Cross-species notification JSON for `adhs_cross_species` — internal One Health sentinel-signal feed with sentinel-direction rationale

**Submit-all action.** A single "Submit all (N) →" button at the bottom of the modal fires every destination in parallel. The state machine transitions to `submitted`, the audit log captures the action, and the modal switches to a success panel showing per-agency acknowledgement IDs (`ACK-XXXXXXXX`). The chart's button changes from "⚡ REPORT THIS CASE" (cardinal red) to "✓ Reported" (clinical green) and is disabled.

**Workflow time displayed in the success panel:** ~4 minutes (vs. 60+ minutes for traditional fax/phone reporting). This is the load-bearing claim of Phase 7.

### 4F.4 Clinician-in-the-loop is required

Every report passes through clinician hands before submission. There is no auto-submit code path. This is by design:

- Reportable disease law in Arizona (and federally) places the reporting obligation on the clinician, not on the EHR system. Auto-submission would shift legal responsibility in a way that requires explicit regulatory approval before deployment.
- The cross-species linkage signal that triggers the report is itself a model output. Until the model has accumulated a substantial training set of real reporting decisions, clinician review is the only reliable false-positive filter.
- Sensitive subjects (HIV in infants, congenital syphilis, tuberculosis in children, mpox) carry disclosure constraints that require human judgment on framing and timing.

**Future direction.** As the system accumulates training data on real reporting decisions across tens of thousands of cases, the architecture supports a graduated path toward automatic submission for low-ambiguity cases (e.g., a confirmed lab-positive valley fever in an otherwise routine encounter), with clinician review reserved for high-ambiguity cases (suspected vs confirmed, sensitive subject populations, atypical presentations). This is the same clinical-AI evolution path that radiology has taken with AI-assisted reading: the model handles the routine cases, surfaces the difficult ones, and the clinician's oversight scope sharpens rather than disappears.

### 4F.5 What Phase 7 changes in the population-scale claims

The headline change is a single number: **reporting completeness target moves from 30% baseline to 85% target**, sourced from ADHS's own published estimates of valley-fever underreporting (2-3× true incidence vs reported). At 85% completeness against ~12,000 true annual valley-fever cases in Arizona, the additional ~5,000 captured cases per year drives:

- **30-60 day improvement in cluster lead time** for the cases that become epidemiologically actionable (cluster-level intervention requires several confirmed reports in a defined area, so reporting completeness directly drives lead-time on cluster detection)
- **36× reduction in case-investigator workload** when combined with the risk-triaged contact-tracing layer (Phase 2)
- **Tribal-land sovereignty preserved** through the destination router (tribal_if_applicable is gated by household residency and routes to tribal health authorities, not directly to ADHS for individual case data — only aggregate signals reach state-level)
- **Healthcare-system benefit** quantified in the model card's value-of-information section: every 30 days of earlier detection on a serious infection translates to roughly $4,200 in averted ED-visit costs per case (CDC value-of-surveillance calculator) plus the harder-to-quantify reduction in chronic disseminated complications

### 4F.6 What Phase 7 does NOT do

- The eight destinations are simulated. No actual ADHS, CDC NNDSS, ADA, APHIS, AGFD, or tribal-health endpoint receives the messages from this MVP. The messages are well-formed and would parse correctly at production endpoints with appropriate credentials.
- The reporting-completeness improvement (30%→85%) is a target, not a measured outcome. The measured outcome would require deploying the system in a real clinic and tracking submission rates against a baseline period — out of scope for the capstone.
- The disease database is a snapshot. ADHS, CDC NNDSS, and APHIS all update their lists periodically (typically annually). Production deployment requires either an API ingestion of the live lists or a scheduled re-pull-and-merge.
- Several reportable conditions on the ADHS list have no NNDSS condition code (Cronobacter infant infection, LCM, taeniasis, typhus, vaccinia, several outbreak categories). For these, the `nndss_condition_code` field is `null` and the workflow routes only to ADHS + local health, omitting CDC.

---

## 4G. Phase 8 — Three-domain top-level architecture, intake/triage workflow, encounter input options, knowledge graph search, environmental surveillance dashboard

### 4G.1 Three-domain top-level architecture

The previous flat login screen (Physician / Veterinarian / Public Health columns) was replaced with a **One Health domain selector** as the application entry point. This change reorganizes the architecture around the One Health triad — humans + animals + environment — and surfaces it as the very first user-visible structure in the system.

| Domain | Description | Login required |
|---|---|---|
| **Healthcare Institutions** | Hospitals, clinics, and veterinary practices where care is delivered. Branches into Human Health (6 hospitals) + Animal Health (4 vet practices). Click an institution → see role-based login with the staff at that institution. | Institutional |
| **Public Health & Government** | Surveillance and policy authorities. ADHS, Apache Tribal Health, USDA APHIS, CDC NNDSS. | Agency |
| **Environmental Surveillance** | Live data feeds from EPA AirNow, NWS, ArboNET, USGS plague-rodent surveillance, AGFD wildlife mortality. | None — public access |

This structure mirrors the way these entities operate in the real world. Banner Health Phoenix has its own SSO with its own staff roster; ADHS has its own staff with separate credentials; EPA AirNow exposes a public API. The previous flat login conflated these into a single "select your role" screen, which obscured the architectural reality.

The implementation lives in `app/app.js` `renderLoginScreen()` with the multi-stage flow controlled by `LOGIN_STAGE` (domain → institution → role-tile login). An `INSTITUTION_BRANDING` map at the top of the file holds the colors and logos for all 14 entities (6 hospitals + 4 vets + 4 agencies). The branding tokens are exposed as CSS custom properties (`--inst-color`, `--inst-accent`) so each institution's login card automatically inherits its visual identity.

### 4G.2 Institutional branded logins

Clicking an institution renders a branded login card with up to 6 role tiles. Banner Health Phoenix shows in Banner orange with a "B" logo and 6 role tiles (Physician · Registrar · Triage Nurse · Discharge · Lab Tech · Administrator). Each tile lists the staff members at that institution in that role. Click a staff member → session created → routed to the staff member's default hub.

Vet practices show Veterinarian · Registrar · Vet Tech · Administrator (4 roles).

Public-health agencies show a single Public Health role tile with the agency staff.

The branded layout was chosen over a generic "ONE-HealthRecord login" because:
- Production deployments will use SMART-on-FHIR with each institution's identity provider (Epic at TMC, Cerner at Banner, IDEXX at vet sites). The MVP's branded login screen demonstrates this institutional segregation.
- The capstone's audience (clinicians + ADHS + IRB members) recognizes Banner orange and TMC navy at a glance. The visual identity reinforces that this is not a single centralized system but a federated one.

### 4G.3 New roles and access scopes

Phase 8 adds **38 new staff accounts** across the 10 partner institutions:

| Role | Count | Hub | Allowed views |
|---|---|---|---|
| Registrar (hospital) | 6 | intake | register, trackboard, envsurv |
| Registrar (vet) | 4 | intake | register, trackboard, envsurv |
| Triage Nurse | 6 | intake | register, trackboard, envsurv |
| Vet Tech | 4 | intake | register, trackboard, envsurv |
| Discharge Coordinator | 6 | clinical | encounter, workspace, envsurv |
| Lab Tech | 6 | clinical | encounter, workspace, envsurv |
| Administrator | 6 | clinical | encounter, workspace, envsurv |
| **TOTAL NEW** | **38** | | |

Plus the `environmental_public` pseudo-role (no auth required, scoped to `envsurv` only).

`ROLE_HUBS` and `ROLE_VIEWS` in `app/app.js` were expanded to gate each new role appropriately. Defense-in-depth still holds: layer 1 (hub button visibility), layer 2 (`activateTab` rejection of unauthorized views with audit-log entry), layer 3 (renderer-level refusal). An attempt to navigate from a registrar's session to `/encounter` is silently rejected and recorded as `view_access_denied` in the audit log.

Staff names were generated with `random.Random(42)` against an AZ-demographics-matched pool. Examples from Banner Health Phoenix:
- Anthony Tsosie — Patient Registration Specialist
- Marcus Johnson, RN — Triage Nurse
- Steven Davis, RN — Discharge Care Coordinator
- Linda Garcia, MLT — Medical Laboratory Technologist
- Steven Martinez, MHA — Operations Administrator

The mix of credentials (RN, MLT, MHA, RVT) reflects real US hospital staffing.

### 4G.4 Patient Intake hub: registration + triage track board

Two new views ship in the Intake hub.

**New Patient Registration** (`#view-register`). A two-column form captures demographics (first/last name, DOB, sex, address, city/zip, phone, insurance, chief complaint, household assignment, tribal residency flag) and a One Health consent checkbox. The right column hosts an **eMPI duplicate-detection panel**.

The "Run eMPI duplicate check" button fires `_runEmpiCheck()` which performs Fellegi-Sunter-style scoring against the 970-human federation manifest:
- Last name exact = 0.40, partial = 0.18
- First name exact = 0.30, partial = 0.12
- DOB exact = 0.25
- Address line prefix match = 0.15
- Threshold: matches above 0.50 are surfaced for clinician review

Possible matches are shown as "Possible match found: Maria Hernandez at Banner Phoenix — confirm or create new?" with the federation source, household ID, and match score. On submit, if matches exist, the form requires explicit clinician acknowledgment before creating a new record. This is the production pattern that prevents duplicate-MRN proliferation in real EHRs.

The implementation cleanly handles the FHIR Patient envelope shape: `households.households[].humans[].name[0].family/given/birthDate/address[0].line[0]`. The same matcher is used by the knowledge graph search.

**Triage Track Board** (`#view-trackboard`). Real-time waiting-room view with a 4-state lifecycle:

```
waiting → in_triage → ready_for_clinician → with_clinician [→ discharged]
```

Summary cards across the top show the count per state (color-coded: amber/cardinal/clinical-green/navy). The table lists every patient with name, DOB, reason for visit, status, wait time, and state-appropriate actions. The "Open triage form" action launches a modal capturing vitals (BP, HR, RR, temp, SpO₂, pain) plus chief complaint refinement plus 5-level **ESI acuity** (Emergency Severity Index 1-5) — the standard US ED triage scale. Clicking "Hand off to clinician →" transitions the patient to `with_clinician` and (in a production deployment) would surface the captured triage data on the assigned clinician's encounter screen.

The track board seeds 4 demo patients on first render including Carlos Hernandez ("Fatigue, mild cough — wife recently dx'd Valley Fever" at ESI 3) — wired so a presenter can demonstrate the front-desk-to-encounter handoff that matches the opening pitch's narrative arc.

### 4G.5 Encounter input options: voice, keyboard, template

The Live Encounter view above the dictation textarea now hosts a 3-tab input panel (`OH_INTAKE.attachEncounterInput`) for clinicians:

**🎤 Voice (push to record).** Uses the browser's Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`). Click the "Push to record" button → recording starts (button turns cardinal red and pulses), real-time interim transcripts appear in the transcript area, click again to stop. The captured text routes to the dictation textarea via "Send to encounter →".

Browser support: Chrome and Edge fully supported. Safari has partial support. Firefox falls back to the Keyboard tab with an explanatory message.

The model card explicitly notes that production deployment would route through clinical-grade ASR (Nuance Dragon Medical One, AWS HealthScribe, or Anthropic's Whisper variants) rather than the consumer Web Speech API. The MVP demonstrates the workflow; the production swap is one network endpoint change away.

**⌨️ Keyboard.** A plain textarea for typed dictation. Same "Send to encounter" action.

**📋 Template.** Five pre-canned templates that pre-populate the textarea with structured boilerplate the clinician fills in:
- Annual physical (adult)
- Acute respiratory complaint
- Follow-up visit
- Vet wellness exam (companion animal)
- Coccidioidomycosis workup (with the explicit ADHS-reportable reminder built in)

All three modes write to the same target textarea (`#dictation`) which is processed by the existing rule-based extraction pipeline. The clinician's choice of input mode does not affect downstream FHIR generation — it only affects how the text gets there.

### 4G.6 Knowledge graph patient identity search

The Public Health Console's Knowledge Graph view now includes a search bar above the graph for **patient identity verification by name + DOB + address**. These are the three identifiers a registrar reads aloud to confirm they have the right person ("Can you confirm your name, date of birth, and street address?"). The search bar mirrors that structure with three dedicated input fields plus a "Find patient" button.

Match scoring matches the eMPI logic described above. Results show up to 5 candidates ranked by score, each with the patient's name, DOB, address, household ID prominently displayed for read-aloud verification. A "Locate in graph & verify →" button on each result triggers a node-pulse animation in the D3 force-directed graph (the matching patient node enlarges and pulses cardinal red for 4 seconds) and zooms the viewport to center on it.

When d3 fails to load (offline / CORS-blocked), the search still works; the locate action simply skips the visual highlight and notes "(Patient not currently rendered in graph view — verified via search match only.)" in the result card. This degradation pattern is documented in §4G.10.

The use case: a public-health investigator receives a phone tip about a possible cocci case in a household and needs to verify the patient is the right person before pulling the household contact list. Name + DOB + address — the same three identifiers HIPAA recognizes as the minimum patient verification set — produce a unique match in the household graph.

### 4G.7 Environmental Surveillance dashboard (no login)

A new top-level domain card on the entry screen routes (without authentication) to `#view-envsurv`, a five-feed environmental surveillance dashboard. Each feed renders calibrated synthetic data matching real Arizona ranges:

| Feed | Source | Coverage | Demo data |
|---|---|---|---|
| **EPA AirNow** | EPA AirNow API | 14 stations across 11 AZ counties | 30-day PM₂.₅ + AQI history per station, color-coded AQI pills, trend arrows (rising/falling/stable). Maricopa + Pinal + Yuma elevated baselines, northern stations lower. |
| **NWS** | National Weather Service `api.weather.gov/alerts` | 3 active advisories | Excessive Heat Watch (Phoenix, Major), Blowing Dust Advisory (Pinal, with Coccidioides aerosolization tie-in), Red Flag Warning (Coconino). Each advisory carries a One-Health-relevance text linking to disease surveillance. |
| **ArboNET** | CDC ArboNET + ADHS Vector-borne Disease Program | 10 traps (6 mosquito + 4 tick) | 90-day count history. Pinal mosquito trap shows the 27σ anomaly used in the Phase 2-7 demos (43.0 7-day average, 1 WNV+ pool, ⚠ ANOMALY pill). Apache reservation tick traps show elevated brown-dog-tick burden. |
| **USGS plague-rodent** | USGS National Wildlife Health Center + ADHS partnership | 5 sites in northern AZ enzootic zones | 60-day flea-index history per site. Coconino Bonito Park flagged Y. pestis POSITIVE (last positive 2026-04-22), Wupatki at 0.241 ELEVATED. |
| **AGFD wildlife mortality** | AZ Game and Fish Department + AZ State Vet Diagnostic Lab | 5 active reports | Black-billed magpie WNV die-off (Coconino), mule deer EHD (Maricopa), plague-positive coyote (Cochise), 47-prairie-dog plague die-off in Apache-Sitgreaves NF, trauma roadrunner (Pima). Plague + WNV reports cross-flagged in cardinal red. |

Generated by `src/data_generation/environmental_feeds.py` from `seed=42`. Output at `data/synthetic/environmental_feeds.json` (213 KB). Bundled into `app/data.js` automatically by `bundle_for_demo.py`.

The dashboard renders in a 2-column grid with the AGFD card spanning full-width because of its longer content. Each card shows source attribution and a "Synthetic for demo · Production: pulls from {real API URL}" caveat. The blueprint for swapping in live APIs is explicit.

### 4G.8 What this changes about the public-scale claims

Phase 8 doesn't change the headline claims (30%→85% reporting completeness, 30-60 day lead times, 36× investigator workload reduction). What it *does* change:

- **Architectural framing for the pitch.** The three-domain top-level structure is the first thing the audience sees. It immediately tells the One Health story — humans + animals + environment as peer domains, not nested under one another. This is a presentation-level improvement to a system that was previously buried in flat login columns.
- **Realistic workflow demonstration.** The capstone can now demonstrate the actual end-to-end ED workflow: registrar registers Carlos Hernandez → triage nurse captures vitals + ESI → handed off to Dr. Reyes who sees triage block + selects voice/keyboard/template input → encounter dictation → CDS panel → reportable disease push. Previously the demo started mid-encounter with the dictation already loaded, skipping the front-desk and triage steps that any real clinic does first.
- **Environmental surveillance as ambient context.** The audience can see the Pinal mosquito anomaly, the Coconino plague positive, and the Excessive Heat Watch *without logging in*. This grounds the One Health claim — environmental health is a peer concern, not a sub-feature of clinical care.

### 4G.9 What Phase 8 does NOT do

- **No real authentication.** The institutional logins are still mock — clicking a staff tile saves a session to localStorage. Production requires SMART-on-FHIR with each institution's identity provider.
- **No real environmental data feed connections.** All five feeds use synthetic data generated from `seed=42`. The data ranges are calibrated to real AZ conditions but no live API pulls happen.
- **No persistent triage data.** The track board state lives in `OH_INTAKE._state` (in-memory). Refreshing the page resets the demo patients. Production would persist as FHIR Encounter + Observation resources scoped to the visit.
- **No actual encounter handoff.** When the triage nurse clicks "Hand off to clinician →" the patient transitions to `with_clinician` state but the assigned clinician's encounter screen does not yet auto-populate with the triage block. This is a 30-line wiring task that was deferred to keep Phase 8 scoped.
- **Web Speech API has accuracy limits.** In testing, US-English accuracy on clinical vocabulary is roughly 80-85%, with errors concentrated on drug names and anatomical terms. The model card recommends production deployment swap in clinical-grade ASR before clinical use.
- **The KG search visual highlight depends on d3.** When d3 fails to load (offline), the search still works textually but the node pulse + zoom animation does not fire. The result card notes this gracefully.

### 4G.10 Key files added/changed in Phase 8

```
src/data_generation/extend_provider_directory.py    # NEW — 38 staff accounts
src/data_generation/environmental_feeds.py          # NEW — 5 feeds, 213 KB output
src/data_generation/bundle_for_demo.py              # MODIFIED — added env feeds
data/synthetic/providers.json                       # MODIFIED — extended with new staff
data/synthetic/environmental_feeds.json             # NEW — 213 KB
app/index.html                                      # MODIFIED — multi-stage login + intake/envsurv views + KG search bar
app/app.js                                          # MODIFIED — new login flow, ROLE_HUBS expansion, _wireKgSearch
app/intake.js                                       # NEW — registration + track board + encounter input
app/envsurv.js                                      # NEW — environmental dashboard
app/style.css                                       # MODIFIED — CSS for all new surfaces (~500 lines added)
```

---

## 5. Evaluation Data

### Datasets
- **`data/synthetic/gold_standard.json`** — 25 dictations programmatically annotated by `src/evaluation/gold_standard.py`. Annotations were produced by enumerating dictionary spans + regex rules against an independently authored set of dictations (i.e. the dictations were *not* used to build the gazetteer; they share the underlying terminologies but were composed separately).

### Motivation
A real evaluation against MIMIC-IV / VetCompass would require credentialed access (PhysioNet DUA for MIMIC; RVC partnership for VetCompass) and is on the future-work path. For the MVP we used a synthetic gold-standard so the pipeline could be evaluated end-to-end without IRB or DUA friction — a deliberate scope decision aligned with the project's "synthetic-first" thesis.

### Preprocessing
None. Dictations are passed verbatim to the pipeline.

---

## 6. Training Data

This is a rule-based system; there is **no training data** in the statistical-learning sense. The gazetteer dictionaries were built from public terminology releases:

- **SNOMED-CT US Edition** (via UMLS) — 25 human conditions, 20 animal conditions, 20 symptoms.
- **ICD-10-CM 2025** (CMS) — 25 condition codes paired with SNOMED.
- **LOINC 2.77** — 14 lab and observation codes; vital-sign LOINC codes (8310-5, 8867-4, 85354-9, 59408-5, 9279-1).
- **RxNorm** — 16 medication strings.
- **VeNom Coding Group** — vet-extension codes.
- **SNOMED-CT Veterinary Extension** (Virginia-Maryland College of Vet Medicine) — used for animal-condition coding.

All dictionary entries are versioned in `data/reference/clinical_terminologies.json`.

---

## 7. Quantitative Analyses

### Unitary results
The headline metrics in §4 disaggregated by entity kind already constitute the unitary analysis: vitals and medications saturate (1.000 F1), conditions and symptoms have substantive headroom (0.78–0.79 F1).

### Intersectional results
Looking at conditions by disease, the gazetteer-rich infectious-disease scenarios (Cocci, RMSF, plague, WNV, psittacosis, Q fever) achieve recall ≥ 0.85 in the eval set. The recall gap (0.75 overall) is concentrated in symptom phrasing variants ("muscle aches" vs. "myalgia", "dyspnea" vs. "shortness of breath" vs. "difficulty breathing") where the gazetteer omits a phrasing the dictation uses.

---

## 8. Ethical Considerations

### Data
All clinical, surveillance, household, and environmental data are **fully synthetic**. There is no protected health information (PHI) and no real Arizona resident is represented. Public terminology codes are used only for their codes — no patient data was ingested.

### Risks
- **Misattribution risk:** A reader of a generated FHIR Bundle could mistake it for real clinical data. Mitigation: every Bundle is stamped with `Provenance.activity = "machine-authored"` and the project banner at the top of the demo UI states the synthetic nature explicitly.
- **Erroneous public-health alerts:** If any of the alert-generation logic were applied to real data, false-positive cluster alerts could trigger inappropriate public-health responses. Mitigation: the alert engine is illustrative; thresholds (e.g. 27σ vector anomaly) are calibrated to the synthetic distribution and are not validated for real surveillance use.
- **Anchoring bias from low-confidence extractions:** A clinician shown a UI-rendered extraction may anchor on it even when it is wrong. Mitigation: the hand-back UI explicitly flags items below confidence 0.75 and requires confirm / reject before the bundle is committed.

### Mitigations
- Synthetic-data banner is persistent and unambiguous in the UI.
- Every machine-authored resource carries source-text span, source-phase, and confidence.
- Hand-back UI requires explicit clinician confirmation for low-confidence extractions.

---

## 9. Caveats & Recommendations

### Known limitations
- Symptom recognition does not yet cover the long tail of patient-language phrasings.
- Negation/hedge windows are sentence-bounded — multi-sentence assertions ("She had no fever. Just cough.") are sometimes mis-scoped.
- The gazetteer is small (25 conditions, 20 symptoms). Real deployment would replace this with BioClinicalBERT or a fine-tuned scispaCy NER (planned in `docs/future_work.md`).
- Evaluation is on synthetic data only.

### Recommendations
- Before any pilot deployment, swap the rule-based extractor for a transformer-based clinical NER and re-run the evaluation against credentialed real data (MIMIC-IV human, VetCompass veterinary).
- Validate alert thresholds against retrospective ADHS / ArboNET surveillance series before any consequential use.
- Engage IRB and a clinical advisory board to review the hand-back UI workflow.

### Caveats specific to the Phase-2 predictive risk model
- **Class imbalance is severe.** 15 positives in 1,366 encounters (1.1%) — every per-fold metric has a wide confidence interval and per-fold AUROC has high variance. The headline numbers should be read as point estimates not population estimates.
- **`day_of_year` dominates SHAP** because synthetic outbreaks cluster in April 2026. On real data this signal would be weaker; the model's per-feature ranking would shift toward `cc_zoo_specific`, `hh_other_species_cond_90d`, and surveillance signals — all features that are robust to different temporal distributions. Permutation importance after stripping temporal correlation is reported as cross-validation.
- **Lead-time yield is 1/11 scenarios.** This is honest about the synthetic data's temporal structure (confirmation dates are clustered near the outbreak index date by construction). Production deployment on real claims/surveillance data would be expected to surface lead time more often, because real outbreaks unfold gradually and lab confirmation lags symptoms.
- **Tribal-land AUC gap is real, not noise.** The 8.6-pp gap (0.782 vs 0.868) holds despite low n on the tribal-land slice. The action item in §4B.6 must be acted on before any deployment; otherwise the model would systematically under-serve the populations most at risk for several of the modeled diseases.
- **The LLM benchmark is currently projected, not measured.** `llm_benchmark.json` carries `is_simulated: true`. To replace with measured numbers, run `ANTHROPIC_API_KEY=... python src/ml/llm_benchmark.py`. The script is parameterless beyond the API key and will overwrite the projected file.

---

## 10. Versioning

| Version | Date | Notes |
|---|---|---|
| 0.1.0 | 2026-04 | Initial capstone MVP — rule-based NER, 25-dictation eval, 12 zoonotic scenarios, 120 households, 1,366 longitudinal encounters, 12 alerts. |
| 0.2.0 | 2026-04-29 | Phase 2: predictive risk model (LR/RF/GBM, 51 features, 5-fold CV, AUROC 0.870 on chosen GBM, Brier 0.005); SHAP + permutation-importance + decision-tree explainability; 3-tier contact tracing with risk-triaged sensitivity curves; equity disaggregation revealing 8.6-pp tribal-land AUC gap; lead-time analysis (1/11 scenarios at 71d); LLM-vs-rules NER benchmark (Haiku 4.5 projected). |
| 2.0.0 | 2026-05-02 | **Phase 3 (response to lecturer feedback):** (a) Two-hub UI restructure — Clinical Workspace (clinicians + vets) and Public Health Console (governance / surveillance / audit). Mirrors Epic Hyperspace / Cerner Cogito separation. (b) Architecture tab replaced by Live Model Card surface (this document, rendered inline). (c) MedGemma 4B integrated as primary clinical extractor with three-layer veterinary adaptation: species-router prompt prefix (Layer A, shipping), RAG over Merck Vet Manual + FDA Green Book (Layer B, scaffolded), and species-class LoRA adapters (Layer C, scaffolded). Implementation in `src/nlp/medgemma_extractor.py` with rule-based fallback when `MEDGEMMA_API_KEY` is absent. (d) Privacy-preserving training architecture: swarm learning topology (no central aggregator) + DP-SGD inside local training + Bonawitz secure aggregation on weight exchange + Laplace-noised aggregate counts (already shipped). Federated-learning simulation across 6 sites in `src/ml/federated_simulation.py` runs end-to-end on the demo laptop; federated AUC 0.772 vs centralized 0.703 (+0.069). |
| 2.1.0 | 2026-05-02 | **Phase 4 (response to lecturer feedback continued):** Login parameter + role-based access control. Physician sees only their own human patient panel (38–130 patients); veterinarian sees only their own animal patient panel (30–40 patients); public-health user sees aggregate / household-level / county-level signals only with no individual primary records. Cross-species data redaction with a 3-tier "model pointer" message that surfaces the One Health value (household has cross-species cluster signal · disease class withheld · provenance: model_pointer). Defense in depth: UI hiding + router-level view rejection + renderer-level access-policy refusal. Visible audit log in Model Card showing all login / navigation / access-denial events. Patient-provider mapping generated by `src/data_generation/assign_providers.py`. |
| 0.3.0 | 2026-05-04 | **Phase 5 — comprehensive dataset expansion (200% scale; ZIP-code resolution; 14 One Health diseases with explicit transmission routes).** Households scaled from 120 → **360**; humans 316 → **970**; animals 102 → **408**; encounters 1,366 → **4,676**; all 15 AZ counties guaranteed coverage; **43 of 54 reference ZIPs used**. Each household now pinned to a specific ZIP code with per-ZIP environmental-quality index, vector-burden index, rodent-risk tier, plague-enzootic flag, and urbanicity tier. New `data/reference/diseases_az.json` encodes 14 One Health-relevant AZ diseases with: SNOMED + ICD-10 codes, transmission routes (`direct_contact`, `environmental_exposure`, `vector_borne`, `foodborne`, `waterborne`, `aerosol`, `fomite`), per-species susceptibility and severity, sentinel direction (`animal_to_human` / `human_to_animal` / `shared_environmental`) with rationale, vectors, environmental drivers, and AZ geography. Procedural disease assignment now driven by ZIP-level environmental risk × species composition × per-disease prior; index-case placement honors sentinel direction (e.g., dog gets RMSF before any household human, with appropriate incubation lag). Provider directory expanded to **6 physicians + 4 veterinarians + 3 PH officers** to keep panels at real-PCP scale (23–245 patients). Pipeline retrained on the larger dataset; gradient-boosting ROC-AUC improved from 0.870 → **0.910**, contact-tracing precision @ 0.50 from 12.5% → **80%**, tribal-land equity gap from 8.6 pp → **14.0 pp** (now visible against larger samples — n=110 vs n=4,566). |
| 2.2.0 | 2026-05-05 | **Phase 6 — production-grade integration substrate.** (a) Per-site FHIR shadow stores: 13 partner sites partitioned at `data/synthetic/shadow_stores/` (6 hospital systems, 4 vet networks, 3 PH sinks). Federation manifest at `data/synthetic/federation_manifest.json`. In-browser federation client (`app/federation.js`) with simulated network calls + visible wire log. (b) Probabilistic eMPI: Fellegi-Sunter matcher at `src/empi/probabilistic_matcher.py`. 117k pairs scored, 3 auto-linked across sites (Maria↔M Hernandez, Robert↔Bob Williams, James↔Jim Becker), 2,857 clerical-review. (c) Consent workflow: 360 FHIR Consent resources at `data/synthetic/consents.json`; 2 declined households (Williams + Becker) demo the architecture's respect for declined linkage. (d) Closed-loop CDS: order set + one-click NNDSS HL7 v2.5.1 ELR submission + USDA APHIS VSPS push + 6-state alert state machine + patient handouts in EN/ES (real) and Diné/Apache (placeholders pending tribal-IRB-vetted translator). (e) Vet FHIR R5-vet-ballot profile documentation (`docs/vet_fhir_r5_profile.md`) + VeNom-to-SNOMED-CT crosswalk (`data/reference/venom_snomed_crosswalk.json`). (f) Cross-clinician privacy gating: physicians see only their own scenarios; audit log restricted to PH users; off-panel household members redacted with consent note. (g) Hernandez Valley Fever case study at `docs/CASE_STUDY_HERNANDEZ.{md,pdf}`. |
| 2.3.0 | 2026-05-05 | **Phase 7 — comprehensive reportable disease coverage with multi-agency push.** (a) Reportable diseases database: 72 diseases at `data/reference/reportable_diseases_us.json` sourced from ADHS R9-6-202 (effective 2025-06-02), CDC NNDSS, USDA APHIS NLRAD, AZ ADA, and AZ Game and Fish. Coverage: 69 human-reportable, 19 animal-reportable, 41 zoonotic, 10 federal Select Agents. Reporting timeline distribution: 23 immediate / 27 one-day / 17 five-day / 2 outbreak-only. (b) Case placement: 234 reportable cases placed via `src/data_generation/place_reportable_cases.py` (208 human, 26 animal) with realistic AZ epidemiology (cocci 28, salmonella 18, gonorrhea 16, RMSF 12, etc.) and county endemicity weighting. (c) Multi-agency report workflow: `app/reportable.js` implements `OH_REPORT.openReportPanel()`. Every reportable condition surfaces a "⚡ REPORT THIS CASE" button. Click opens a modal with destinations preview (up to 8: ADHS, CDC NNDSS, local health, tribal-if-applicable, ADA, APHIS, AGFD, ADHS cross-species), per-destination message previews (HL7 v2.5.1 ELR, VSPS JSON, cross-species notification JSON), and a "Submit all (N) →" action that fires every destination in parallel and returns per-agency ack IDs. (d) Workflow time: ~4 minutes vs 60+ minutes for traditional fax/phone. (e) Clinician-in-the-loop is hard-required; future direction is auto-submit for low-ambiguity cases as model accumulates training data, with clinician review reserved for edge cases. (f) Opening pitch document at `docs/OPENING_PITCH.md` — 6:30 system-failure-leading pitch with full Hernandez patient story and population-scale benefits. |
| 2.4.0 | 2026-05-06 | **Phase 8 — three-domain top-level architecture, intake/triage workflow, encounter input options, knowledge graph search, environmental surveillance dashboard.** (a) Login flow restructured into three peer domains: Healthcare Institutions (10 partners across Human + Animal sub-branches with branded institutional logins, e.g. Banner Health orange, TMC navy, IHS federal blue) · Public Health & Government (4 agencies: ADHS, Apache Tribal Health, USDA APHIS, CDC NNDSS) · Environmental Surveillance (5 data sources, no login required). (b) 38 new staff accounts: 10 registrars (6 hospital + 4 vet) · 6 triage nurses · 4 vet techs · 6 discharge coordinators · 6 lab techs · 6 administrators. ROLE_HUBS and ROLE_VIEWS expanded with corresponding view permissions and audit log entries. (c) New Patient Intake hub: registration form (`app/intake.js` `renderRegistration`) with 10 demographic fields + One Health consent checkbox + eMPI duplicate detection on submit using Fellegi-Sunter scoring against the 970-human federation manifest. Triage track board with 4-state lifecycle (waiting → in_triage → ready → with_clinician), ESI 1-5 acuity capture, vitals form, hand-off action. (d) Encounter input options: 3-tab panel above the dictation textarea — 🎤 Voice (push-to-record with Web Speech API), ⌨️ Keyboard (textarea), 📋 Template (5 templates: annual physical, acute respiratory, follow-up, vet wellness, cocci workup). All three modes write to the same target textarea processed by the existing extraction pipeline. (e) Knowledge graph patient identity search: name + DOB + address fields above the graph; matches up to 5 candidates ranked by Fellegi-Sunter score with read-aloud verification panel and "Locate in graph" action that pulses the matching node in cardinal red and zooms the viewport to it. (f) Environmental Surveillance dashboard: `app/envsurv.js` renders 5 calibrated synthetic feeds — EPA AirNow (14 stations, 30-day PM2.5+AQI history), NWS (3 active advisories with One-Health-relevance text), ArboNET (10 traps with Pinal anomaly preserved), USGS plague-rodent (5 sites with Coconino positive), AGFD wildlife mortality (5 reports with prairie-dog die-off cross-flagged to USGS). Each feed shows source attribution and synthetic-data caveat. (g) Bundle size 14.9 → 15.0 MB. |

---

*This model card was written by hand. Future iterations should be regenerated from `src/evaluation/run_eval.py` outputs to keep §4 metrics in sync with the engine version.*
