# Phase 5 — Dataset expansion data dictionary

This document describes the Phase 5 changes to the synthetic dataset:
ZIP-code resolution, expansion to 360 households (200% increase), 14 One
Health diseases with explicit transmission routes, and sentinel-direction-
aware disease assignment.

---

## What's new in the dataset

| Aspect | MVP / Phase 1 | Phase 5 |
|---|---|---|
| Households | 120 | **360** |
| Humans | 316 | **970** |
| Animals | 102 | **408** |
| Longitudinal encounters | 1,366 | **4,676** |
| County coverage | 15 (all of AZ) | 15 (guaranteed by min-1-per-county rule) |
| Geographic resolution | County only | **ZIP code + county** |
| Distinct ZIPs in dataset | n/a | **43 of 54 reference ZIPs** |
| One Health diseases modelled | 12 (handcrafted only) | **14 with explicit transmission routes** |
| Procedural disease assignment | none — only handcrafted | **ZIP-level env-risk × species × per-disease prior** |
| Sentinel direction encoding | implicit | **explicit per disease (`animal_to_human` / `human_to_animal` / `shared_environmental`)** |
| Animal species in pool | 6 | **9** (added cattle, swine, reptile) |

---

## Reference data files

### `data/reference/arizona_zip_codes.json`

54 representative ZIP codes (ZCTAs) covering all 15 Arizona counties. Each
record includes:

| Field | Description |
|---|---|
| `zip` | ZIP code (string) |
| `name` | Place name (e.g., "Tucson Northwest") |
| `county_fips` | Five-digit county FIPS code |
| `county` | County name |
| `population` | Approximate ZCTA population (2020 ACS-derived) |
| `lat`, `lon` | Geographic centroid |
| `epa_eqi` | Environmental Quality Index (synthetic, calibrated to CDC ZCTA EQI) |
| `vector_burden_idx` | Tick + mosquito proxy index, 0–1 |
| `cocci_endemic` | "high" / "moderate" / "low" — Coccidioides endemicity tier |
| `rodent_risk` | "high" / "moderate" / "low" — driver of hantavirus / leptospirosis exposure |
| `plague_enzootic` | Boolean — northern AZ counties (Apache, Navajo, Coconino) flagged true |
| `urbanicity` | "urban" / "suburban" / "rural" |

### `data/reference/diseases_az.json`

14 One Health-relevant diseases endemic or reportable in Arizona. Each
record includes:

| Field | Description |
|---|---|
| `id`, `display`, `icd10`, `snomed`, `category` | Identity + clinical codes |
| `az_status` | Reportability + endemic status in AZ |
| `transmission_routes` | List of `{route, vehicle, primary}` triples |
| `host_species` | Per-species susceptibility, severity, incubation, asymptomatic-carrier flag |
| `reservoir` | Reservoir host species |
| `vectors` | Arthropod vector species (if any) |
| `environmental_drivers` | List of environmental conditions driving outbreaks |
| `sentinel.direction` | `animal_to_human`, `human_to_animal`, or `shared_environmental` |
| `sentinel.rationale` | Plain-English rationale for the sentinel direction |
| `az_geography` | List of AZ counties where the disease is most relevant |
| `person_to_person` | Whether human-to-human transmission occurs |

The seven transmission-route taxonomy:
- `direct_contact` — bite, scratch, fluid contact, handling
- `environmental_exposure` — soil, water, fomite (general)
- `vector_borne` — tick, mosquito, flea, fly
- `foodborne` — contaminated food / dairy / raw meat
- `waterborne` — contaminated water (drinking, recreation)
- `aerosol` — inhalation of aerosolized particles
- `fomite` — contaminated surfaces

---

## How procedural disease assignment works

For each procedural household (348 of 360), the generator:

1. **Determines species composition** from the household's animals.
2. **Computes per-disease environmental risk** from the household's ZIP record using `_disease_env_risk()`. The function maps ZIP-level fields (cocci_endemic, vector_burden_idx, rodent_risk, plague_enzootic, urbanicity) to a per-disease prior in [0, 1].
3. **Filters diseases** to those that are species-eligible — no Q-fever without ruminants, no psittacosis without birds, no salmonella case requirement (it's environmental + foodborne so always eligible).
4. **For each eligible disease**, rolls `env_risk × base_rate × 4`. Hits become cases.
5. **Places the index case** according to sentinel direction:
   - `animal_to_human` → animal first, optional human secondary after appropriate incubation lag
   - `human_to_animal` → human first
   - `shared_environmental` → both species independently with separate probabilities
6. **Builds a FHIR Condition** with SNOMED + ICD-10 codes plus a `_one_health` extension recording disease_id, transmission routes, sentinel direction, and zoonotic flag.

Calibration target: ~10% of procedural households carry at least one active
disease case, with realistic species and seasonal patterns.

---

## How this serves the seven project objectives

**Objective 1 (connected EHR)** — Every household links its humans, animals, conditions, and ZIP-pinned environment via a single FHIR-shaped record.

**Objective 2 (real-time extraction)** — Same NER/FHIR pipeline; expansion only changes the data, not the algorithm.

**Objective 3 (integration of human / animal / environmental / vector data)** — The dataset now spans 14 diseases × 7 transmission routes × ZIP-level environmental + vector indices. Every Condition links to its disease's transmission routes via the `_one_health` extension.

**Objective 4 (animal-as-sentinel, vice versa)** — Sentinel direction is now explicit per disease in `diseases_az.json` and honored by the assignment logic. Canine RMSF reliably appears in the same household as human RMSF with the canine case onsetting first; equine WNV appears before human WNV in the same county.

**Objective 5 (alert system with action / watch / info)** — Existing surveillance generator + new procedural cases give the contact-tracing pipeline more signal. Precision at threshold 0.50 jumped from 12.5% to **80%** because the larger dataset has cleaner positive-vs-negative separation.

**Objective 6 (predictive risk + explainability + equity)** — The retrained model went from AUROC 0.870 → **0.910**. Tribal-land sample size increased from 156 to 110 (it's smaller in absolute terms because the procedural sampling is population-weighted, but the AUC gap is now **14 pp** — clearly visible against the larger non-tribal sample of 4,566).

**Objective 7 (privacy + role-aware)** — Provider panels rebalanced to real-PCP scale (23–245 humans, 22–159 animals across 6 physicians and 4 vets). Cross-species pointer logic unchanged; it now applies to a 3× larger universe of households-with-cross-species-signal.

---

## Reproducibility

```bash
python src/data_generation/household_generator.py    # → households.json
python src/data_generation/encounter_generator.py    # → encounters.json
python src/data_generation/surveillance_generator.py # → surveillance.json
python src/data_generation/assign_providers.py       # → providers.json
python src/ml/build_labels.py                        # → labels.json
python src/ml/feature_engineering.py                 # → features.parquet
python src/ml/train_models.py                        # → models.pkl + ml_evaluation.json
python src/ml/explain.py                             # → explanations.json
python src/ml/equity_disaggregation.py               # → equity.json
python src/ml/contact_tracing.py                     # → contact_tracing.json
python src/ml/lead_time.py                           # → lead_time.json
python src/ml/llm_benchmark_projected.py             # → llm_benchmark.json
python src/ml/federated_simulation.py                # → federated.json
python src/data_generation/bundle_for_demo.py        # → demo_bundle.json + app/data.js
```

Total wall time: ~2 minutes. All deterministic from `seed=42`.
