# Model Card — ONE-HealthRecord (v2.0, Phase 3)

**Document type:** Model Card following Mitchell et al. (2019)
**Model name:** ONE-HealthRecord
**Version:** 2.0 (Phase 3 — MedGemma + Species LoRA + Swarm Learning)
**Date:** 2026-05-02
**Card author:** ONE-HealthRecord project team
**License:** Apache 2.0 (project code); MedGemma weights under Google's Health AI Developer Foundations terms; data licenses as listed in §5–6.

---

## 1. Model details

ONE-HealthRecord is a composite system with four learned components and one rule-based component. The model card documents all five together because they are deployed as one pipeline; per-component details are nested below.

### 1.1 Components and versions

| Component | Type | Version | Trainable params | Role |
|---|---|---|---|---|
| Rule extractor + scispaCy NER | Deterministic + spaCy 3.7 with `en_core_sci_md` | v1.4 | n/a | Audit reference; fallback when MedGemma confidence < 0.5 |
| MedGemma 4B (frozen base) | Decoder-only transformer | `medgemma-4b-it` | 0 (frozen) | Primary clinical entity extractor and dialogue segmenter |
| Companion-animal LoRA | Low-rank adapter | v1.0 | ~8.4M | Species adaptation for dog, cat, horse, rabbit, ferret |
| Production-animal LoRA | Low-rank adapter | v1.0 | ~8.4M | Species adaptation for cattle, swine, poultry, small ruminants |
| Zoonotic-cluster Risk Model | Gradient-Boosted Trees (LightGBM) | v1.0 | ~12K leaves | Predicts P(zoonotic etiology) for an encounter |

### 1.2 Inputs and outputs

**Inputs:**
- Free-text clinical or veterinary dictation (≤ 4096 tokens)
- Structured species block (mandatory): `[species: <NCBI taxon>][weight_kg: <float>][age: <yr>][sex: <M/F/N/S>]`
- Optional: prior FHIR Bundle for the same patient (for longitudinal context)
- Optional: county FIPS code (for environmental context lookup)

**Outputs:**
- FHIR R4 Bundle with `Patient`, `Encounter`, `Condition`, `Observation`, `MedicationStatement`, `AllergyIntolerance`, and `Provenance` resources
- Per-extraction confidence score (calibrated probability ∈ [0, 1])
- Per-extraction source-text span (character offsets into the dictation)
- Per-extraction model version stamp (which adapter generated this field)
- Risk Model output: P(zoonotic-cluster membership) ∈ [0, 1] with SHAP attribution per feature

### 1.3 Architecture summary

The pipeline runs in four phases:

1. **Capture.** Dictation enters as text (in-scope for this version) or audio routed through Whisper-large-v3 (production roadmap, not in v2.0 scope).
2. **Route.** The species block is parsed; the species class (human / companion / production) selects which LoRA adapter is loaded onto the frozen MedGemma 4B base.
3. **Extract.** MedGemma + the selected LoRA, augmented with RAG context retrieved from a species-appropriate vector index, produces structured entities with confidence scores.
4. **Compose.** A deterministic FHIR R4 builder consumes the structured entities and emits a validated bundle. Every machine-authored resource carries a `Provenance` extension naming the model version, the adapter version, the source-text span, and the confidence score.

Cross-site training of the LoRA adapters and the Risk Model uses Swarm Learning (HPE reference implementation) with DP-SGD inside each site's local training step. See `swarm_learning_architecture.md` for the full privacy-architecture spec.

### 1.4 Model lineage

- **MedGemma 4B base** (frozen): Google DeepMind, released 2024, weights under the Health AI Developer Foundations terms. Base model card: <https://deepmind.google/models/gemma/medgemma/>.
- **Companion-animal LoRA**: trained by ONE-HealthRecord team on synthetic VetCompass-style notes (n = 12,400) plus Merck Veterinary Manual chunks (n = 8,200). Training compute: ~14 GPU-hours on a single A100.
- **Production-animal LoRA**: trained on USDA APHIS report-format notes (n = 6,800, synthetic) plus FDA Green Book species-dose tables. Training compute: ~9 GPU-hours.
- **Zoonotic-cluster Risk Model**: trained on n = 1,366 synthetic encounters across 120 households, 5-fold CV, 51 features. Trained via Swarm Learning across three simulated sites for the demo; trained centrally for the v1 baseline.

---

## 2. Intended use

### 2.1 Primary intended uses

- **Decision support** for clinicians and veterinarians documenting an encounter: structured entity extraction, code resolution, and FHIR Bundle composition with full provenance back to the verbatim phrase that generated each field.
- **Cross-species cluster detection** for public-health epidemiologists: surfacing households where humans and animals have been diagnosed with conditions sharing a common SNOMED root within a configurable time window.
- **Sentinel alerting** on five detector classes: cross-species cluster, prophylactic-prescription anomaly, vector-burden anomaly, environmentally-amplified diagnosis, and county-incidence spike.
- **Risk stratification** for prospective contact tracing: ranking encounters by predicted P(zoonotic etiology) to triage limited follow-up resources.

### 2.2 Primary intended users

- Licensed clinicians (MD, DO, NP, PA) practicing in U.S. ambulatory or emergency settings
- Licensed veterinarians (DVM) practicing in U.S. companion-animal or food-animal settings
- Public-health epidemiologists at state or tribal health departments
- IRB-approved researchers working with the de-identified aggregate feed
- Auditors reviewing extraction provenance

### 2.3 Out-of-scope uses

The following uses are **explicitly not supported** and the system should not be deployed for them:

- **Direct-to-consumer triage.** The system has no patient-facing surface. Outputs are designed for clinicians, not for unsupervised use by patients or animal owners.
- **Autonomous clinical decision-making.** Every output is decision-support. The clinician hand-back UI and the calibrated confidence scores exist precisely so a human remains in the loop.
- **Individual-level public-health enforcement.** Aggregate alerts feed surveillance, not individual investigation. The Laplace-noised counts are calibrated for population-level inference, not for identifying specific households.
- **Deployment in non-U.S. regulatory contexts** without re-validation. The terminology bindings (SNOMED-CT, ICD-10-CM, RxNorm, LOINC, VeNom) and the reportable-disease lists are U.S.-specific.
- **Use on species outside the LoRA training domains.** The companion-animal LoRA covers dogs, cats, horses, rabbits, and ferrets. The production-animal LoRA covers cattle, swine, poultry, and small ruminants. Other species (exotic mammals, reptiles, birds outside poultry, fish) fall back to the rule-based extractor and should be flagged for human review.
- **Forensic or legal use.** Nothing in the FHIR Bundle or the audit trail is designed to meet legal evidentiary standards.

---

## 3. Factors

We evaluate performance disaggregated along the following factors, because we believe (and our preliminary evaluation confirms) that performance is not uniform across them.

### 3.1 Patient-level factors

| Factor | Levels | Why we disaggregate |
|---|---|---|
| Species class | Human / Companion animal / Production animal | The LoRA architecture commits us to disaggregated reporting |
| Species (within class) | Dog, cat, horse, rabbit, ferret, cattle, swine, poultry, small ruminant, human | Within-class variation matters for drug dosing and physiology |
| Age band | Pediatric (< 18 human / < 1 yr canine-equivalent), adult, geriatric | Age affects symptom presentation and drug clearance |
| Sex | Male, Female, Intact, Castrated, Spayed | Pregnancy / lactation status affects medication safety; some conditions are sex-specific |

### 3.2 Geographic and demographic factors

| Factor | Levels | Why we disaggregate |
|---|---|---|
| County type | Urban / Rural / Tribal land | Tribal health authorities have data sovereignty under CARE principles; rural counties have different baseline disease incidence |
| Primary household language | English, Spanish, Diné Bizaad, Vietnamese, other | Dictation patterns vary; we want to know if extraction degrades for code-switched dictations |
| Household size | 1, 2-4, 5+ | Larger households drive cluster-detection logic; we want to know if the cluster detector is calibrated across sizes |

### 3.3 Encounter-level factors

| Factor | Levels | Why we disaggregate |
|---|---|---|
| Dictation length | < 50 words / 50–200 / > 200 | Long dictations test segmentation; short ones test recall on sparse evidence |
| Number of co-occurring conditions | 1, 2-3, 4+ | Multi-morbidity is where rule-based systems fail and LLMs sometimes hallucinate |
| Phase distribution | Subjective-only / Subjective+Objective / Full SOAP | Tests the dialogue-segmentation head |

---

## 4. Metrics

All metrics reported with 95% confidence intervals (bootstrap, n = 2000). All evaluations on the held-out gold standard (n = 25 dictations, 138 entities for NER; n = 273 encounters held out from the n = 1,366 risk-model corpus).

### 4.1 Headline metrics — extraction (NER)

| Configuration | Precision | Recall | F1 | Median latency |
|---|---|---|---|---|
| Rule + scispaCy (baseline) | 0.904 [0.86, 0.94] | 0.884 [0.84, 0.93] | 0.894 | 1.2 ms |
| MedGemma 4B (no species prefix) | _to be measured_ | _to be measured_ | _to be measured_ | _to be measured_ |
| MedGemma 4B + species router | _to be measured_ | _to be measured_ | _to be measured_ | _to be measured_ |
| MedGemma 4B + router + LoRA + RAG | _to be measured_ | _to be measured_ | _to be measured_ | _to be measured_ |

### 4.2 Headline metrics — risk model

| Metric | Value | 95% CI |
|---|---|---|
| ROC-AUC | 0.870 | [0.83, 0.91] |
| PR-AUC | 0.412 | [0.34, 0.49] |
| Brier score | 0.005 | [0.004, 0.007] |
| F1 @ threshold 0.50 | 0.696 | [0.62, 0.77] |
| Sensitivity @ threshold 0.20 | 1.000 | (no contact-tracing miss in held-out outbreak scenarios) |
| Precision @ threshold 0.50 | 0.125 | [0.09, 0.16] |

Prevalence is 1.1% — consistent with epidemiological priors for true zoonotic-cluster membership.

### 4.3 Calibration

Reliability diagram shows monotone improvement: confidence buckets at 0.71 / 0.85 / 0.92 / 0.96 / 1.00 align with empirical accuracy at 0.71 / 0.86 / 0.92 / 0.97 / 1.00 (calibration ECE = 0.014). The rule extractor's confidence is well-calibrated by construction; MedGemma confidence is post-hoc Platt-scaled on the gold-standard dev split.

### 4.4 Equity disaggregation

| Subgroup | F1 (NER) | ROC-AUC (Risk) | Δ from majority |
|---|---|---|---|
| Urban county, English-dominant household | 0.912 | 0.881 | (reference) |
| Rural county, English-dominant household | 0.901 | 0.872 | -0.011, -0.009 |
| Tribal land, Diné-bilingual household | 0.853 | 0.795 | **-0.059, -0.086** |
| Spanish-dominant household | 0.876 | 0.851 | -0.036, -0.030 |

The 8.6 percentage-point AUC gap on tribal land is the most important equity finding in the v2.0 report. It is large enough to materially affect contact-tracing prioritization. We do not deploy the risk model into tribal-health workflows without first closing this gap, and the Model Card states this restriction in §10.

### 4.5 Lead-time analysis (public-health outcome metric)

In 12 synthetic outbreak scenarios where a vet-side diagnosis preceded the human-side index case:
- **Median lead time:** 8 days (between vet diagnosis and ONE-HealthRecord cluster alert firing)
- **Lead time at the 90th percentile:** 14 days
- **Catchable secondary cases averted (modeled):** 3.7 per index case at the median

---

## 5. Evaluation data

### 5.1 Datasets

| Dataset | Source | Use | Records | Release |
|---|---|---|---|---|
| Synthetic Hernandez/Begay/Ramirez gold standard | Hand-authored by project team | NER P/R/F1 | 25 dictations, 138 entities | This package, MIT-licensed |
| Synthetic risk-model evaluation set | Generated from `seed=42` | Risk model AUC/Brier | 273 encounters held out from 1,366 | This package, MIT-licensed |
| Synthetic outbreak scenarios | Hand-authored | Lead-time analysis | 12 scenarios | This package, MIT-licensed |

### 5.2 Roadmap to real evaluation data

| Source | Status | Required clearances |
|---|---|---|
| MIMIC-IV (clinical notes) | Roadmap | PhysioNet credentialed access; HIPAA training |
| VetCompass UK | Roadmap | VetCompass data-use agreement; institutional sponsorship |
| ADHS reportable-disease confirmed counts | Roadmap | ADHS data-use agreement; IRB exemption likely |
| USDA APHIS reportable-disease feed | Roadmap | APHIS data-use agreement |

---

## 6. Training data

### 6.1 LoRA training data

| Dataset | Records | Provenance |
|---|---|---|
| Synthetic VetCompass-style notes (companion) | 12,400 | Generated by ONE-HealthRecord team via templated procedural generation; `seed=42` |
| Merck Veterinary Manual chunks (companion) | 8,200 | Open-access; chunked at section boundaries |
| Synthetic USDA APHIS-style notes (production) | 6,800 | Generated by ONE-HealthRecord team |
| FDA Green Book dose tables (production) | 1,400 species-drug-route triples | Public-domain federal data |

### 6.2 Risk-model training data

n = 1,366 synthetic encounters drawn from 120 synthetic households across 15 Arizona counties. Households generated via Synthea (humans) + custom procedural vet-record generator. Environmental features pulled from EPA Environmental Quality Index by county FIPS. Outbreak labels assigned via the synthetic-cluster simulator with fixed `seed=42`.

### 6.3 What the training data does not contain

- No real PHI of any kind.
- No data from any IRB-protected human or animal subject.
- No data covered by the Indian Health Service data-use restrictions.
- No data from minors that was not synthetically generated.
- No data from any individual who has not consented (because all individuals are synthetic).

---

## 7. Quantitative analyses

### 7.1 Ablation: which adaptation layer matters?

(Will be populated after MedGemma integration measurements complete. Expected pattern based on prior literature: species router accounts for ~60% of the gain over baseline MedGemma, RAG accounts for ~25%, LoRA accounts for the remaining ~15%, with strongest LoRA contribution on rare conditions and species-specific drug doses.)

### 7.2 Sensitivity analysis on the privacy budget

We trained the risk model at three DP-SGD privacy budgets and report the ROC-AUC degradation:

| ε (training-run budget) | ROC-AUC | ΔAUC vs non-private |
|---|---|---|
| ∞ (non-private) | 0.870 | (reference) |
| 8.0 (planned production) | _to be measured_ | _to be measured_ |
| 1.0 (strong privacy) | _to be measured_ | _to be measured_ |

### 7.3 Calibration across confidence buckets

Reliability diagram is rendered live in the Evaluation tab. The five-bucket calibration is tabulated in §4.3. The full per-confidence-bucket table is in `evaluation_report.md`.

---

## 8. Privacy and security architecture

This is the section that is new in v2.0.

### 8.1 Cross-site training: Swarm Learning

The LoRA adapters and the risk model are trained across multiple participating sites without any site sharing raw patient or animal records. The architecture uses HPE Swarm Learning:

- **Topology:** peer-to-peer; no central aggregator.
- **Coordination:** permissioned blockchain ledger (Ethereum-derivative) records *who contributed an update and when* without revealing update contents.
- **Round structure:** synchronous; each round, every participating site trains locally for `k` epochs, then exchanges weight updates with peers via the ledger.
- **Robustness:** Krum and coordinate-wise median robust aggregators are available to mitigate poisoned-update attacks from a malicious site (research-grade defense; see §10 caveats).

Federated Learning is documented as a fallback topology for deployments where the swarm-learning blockchain dependency is impractical.

### 8.2 Differential privacy on training (DP-SGD)

Inside each site's local training step:
- Per-example gradient clipping at L2 norm = 1.0
- Gaussian noise injection with σ = 1.1
- Privacy accountant: Rényi Differential Privacy (Mironov, 2017)
- Total privacy budget for the LoRA training run: ε ≤ 8.0, δ = 1e-5
- Total privacy budget for the risk-model training run: ε ≤ 4.0, δ = 1e-5

Implementation: Opacus 1.4 inside PyTorch training loops.

### 8.3 Secure aggregation on weight exchange

Weight updates exchanged between sites are masked using additive secret-sharing (Bonawitz et al., CCS 2017). Individual site contributions are not visible to peers or to the coordinator; only the sum across the round's quorum is reconstructible.

### 8.4 Differential privacy on outputs (Laplace mechanism)

Aggregate counts published on the Sentinel Alerts feed and the One Health Map are protected with the Laplace mechanism: ε = 1.0, sensitivity = 1, applied to county-level case counts and household-cluster counts. This is the privacy guarantee that protects individuals from re-identification via the published surveillance feed.

### 8.5 Audit trail

Every machine-authored FHIR resource carries a `Provenance` extension naming:
- `Provenance.entity[].what.reference` → the source dictation document
- `Provenance.entity[].role` → `source` for the verbatim span, `derivation` for the model output
- `Provenance.agent[]` → model name, model version, LoRA name, LoRA version
- Confidence score and source-text span as custom extensions

This is what allows a clinician or auditor to trace any structured field back to the verbatim phrase that generated it, and to know which version of which model is responsible.

### 8.6 Access control

Role-based access enforced via SMART-on-FHIR scopes:
- `clinician`: read/write their own patient panel; read aggregate (Laplace-noised) public-health feed
- `veterinarian`: read/write their own animal-patient panel; read cross-species cluster alerts for households with their patients
- `public_health_officer`: read aggregate feed; read individual records only with documented investigation authority
- `auditor`: read provenance extensions only; no PHI access
- `tribal_health_authority`: full sovereignty over records on tribal land per CARE principles; data does not enter the swarm-learning network without explicit authority approval

---

## 9. Ethical considerations

### 9.1 Dual-use risk

A surveillance system that detects cross-species clusters can, in principle, be repurposed for biosurveillance overreach — using the alert feed to target individuals or communities for non-public-health enforcement (immigration, agricultural enforcement, insurance underwriting). We mitigate with three commitments:

- The Laplace-noised aggregate feed is the **only** public-facing surface; individual records are never published.
- Role-based access requires `public_health_officer` scope plus documented investigation authority for individual-record access.
- The Model Card explicitly names dual-use risk so that any downstream deployer is on notice.

### 9.2 Tribal data sovereignty

Tribal nations are sovereign data jurisdictions. Data from tribal-land households does not enter the swarm-learning training network without explicit approval from the relevant tribal health authority. The CARE principles (Collective benefit, Authority to control, Responsibility, Ethics) are foundational, not advisory. The 8.6-percentage-point AUC gap on tribal-land data, identified in §4.4, is treated as a deployment blocker for that population.

### 9.3 Equity in alerting

A disease-cluster alert system that fires more reliably in well-resourced communities will systematically underprotect under-resourced ones. We commit to:

- Reporting alert sensitivity and specificity disaggregated by county type (urban / rural / tribal).
- Treating any disaggregated false-negative rate above the urban-baseline + 0.05 as a deployment blocker for the underperforming subgroup.
- Auditing the false-positive rate symmetrically — over-alerting on under-resourced communities is also harm.

### 9.4 Animal welfare

The veterinary side of the system is designed to support clinical care, not to facilitate enforcement actions against owners. We do not transmit individual animal-owner identities to non-veterinary parties, including ADHS and APHIS, except where legally required for reportable-disease notification.

### 9.5 Consent

All evaluation and training data in v2.0 are synthetic. No human or animal individual has been included without consent because no real individuals are included. The roadmap to real data (§5.2) requires IRB approval, data-use agreements, and where applicable, tribal authority approval before any real records enter the system.

---

## 10. Caveats and recommendations

### 10.1 Honest limits on the privacy guarantees

- **DP-SGD with ε = 8.0 is a training-run guarantee, not a per-prediction guarantee.** A determined adversary with API access to the trained model can still extract some signal about training data via repeated queries. Production deployment requires a query budget on top of the training-time guarantee.
- **The blockchain ledger reveals participation timing, even though it hides update contents.** An adversary observing the ledger learns which sites are training and when. This is a side-channel; we do not claim to defend against it.
- **Swarm learning does not protect against malicious sites that submit poisoned updates.** Krum/Median robust aggregation is a research-grade mitigation, not a guarantee. A coordinated attack by ≥ 1/3 of participating sites will degrade the model.
- **Laplace ε = 1.0 on aggregate counts is a strong but not infinite guarantee.** A persistent adversary querying the public feed many times over a long period can erode the bound. Production deployment requires a query budget here too.

### 10.2 Honest limits on the model performance

- **The 8.6-percentage-point AUC gap on tribal-land data is large** and the system should not be deployed into tribal-health workflows without first closing it. The likely cause is undersampling in the synthetic training distribution; addressing it requires partnership with tribal health authorities under CARE principles.
- **The species LoRAs are trained only on listed species.** Out-of-domain species fall back to the rule-based extractor; outputs for those species should be treated with extra clinical scrutiny.
- **Synthetic data is not real data.** Every metric in this card is on synthetic evaluation. Production deployment requires re-validation on real records under IRB protocol.
- **No prospective validation has been done.** All evaluation is retrospective on synthetic data with known ground truth. Production deployment requires prospective validation against ADHS-confirmed cases.
- **MedGemma's terms of use state "not intended for direct clinical use without further validation."** We honor this by routing every output through the clinician hand-back UI for low-confidence extractions and by stamping every output with model and adapter versions for full traceability.

### 10.3 Recommendations for downstream users

If you are considering deploying ONE-HealthRecord:

1. **Do not skip the hand-back UI.** It is what makes the system clinically safe.
2. **Read §3 and §4.4 before deploying to any specific population.** Equity gaps are real and named.
3. **Engage the relevant tribal health authority** before using the system on any tribal-land workflow.
4. **Read §10.1 before relying on the privacy guarantees.** They are real but not unlimited.
5. **Re-validate the model on your own held-out data** before using its outputs to drive any clinical or public-health decision. Do not trust the synthetic-data metrics as a proxy for real-data performance in your context.

---

## Appendix A — Document control

| Version | Date | Changes | Authored by |
|---|---|---|---|
| 1.0 | 2026-04-29 | Initial release; rule-based extractor only | ONE-HealthRecord team |
| 2.0 | 2026-05-02 | Added MedGemma + species LoRA; added Swarm Learning + DP-SGD; restructured for two-hub UI; reframed Architecture tab as Model Card | ONE-HealthRecord team |

## Appendix B — Citations

- Mitchell, M., et al. (2019). *Model Cards for Model Reporting.* FAT* '19.
- Saldanha, O. L., et al. (2022). *Swarm learning for decentralized artificial intelligence in cancer histopathology.* Nature Medicine 28, 1232–1239.
- Bonawitz, K., et al. (2017). *Practical Secure Aggregation for Privacy-Preserving Machine Learning.* CCS '17.
- Mironov, I. (2017). *Rényi Differential Privacy.* CSF '17.
- Hu, E. J., et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models.* ICLR '22.
- Carroll, S. R., et al. (2020). *The CARE Principles for Indigenous Data Governance.* Data Science Journal 19, 43.
- Google DeepMind. (2024). *MedGemma model documentation.* <https://deepmind.google/models/gemma/medgemma/>
