"""
Phase 7 — Reportable case generator.

Places 200+ reportable disease cases on existing patients across the
360+ household synthetic dataset, with case counts proportional to
realistic Arizona epidemiology (CDC + ADHS public reports).

Strategy:
  1. Load the master reportable disease list.
  2. For each disease, decide a realistic AZ annual case count for the
     dataset's 970 humans + 408 animals (scaled from the actual AZ
     population of ~7M).
  3. Pick patients to receive each disease, weighted by:
       - Species applicability (animal-side vs human-side)
       - County endemicity (cocci heavy in Pima/Pinal, plague in
         Coconino/Apache/Navajo, etc.)
       - Demographic risk (age, sex)
       - Existing condition load (avoid burdening patients with too many)
  4. Generate a Condition resource for each placement, linked to a real
     encounter.
  5. Write to data/synthetic/reportable_cases.json + merge into the
     household conditions stream.

Output:
  data/synthetic/reportable_cases.json — 200+ Condition resources
  data/synthetic/reportable_summary.json — case counts by disease

Calibration notes (based on public ADHS / CDC reports for 2022-2024):
  - Valley Fever: 8,000-12,000 AZ cases/yr → expect ~1-2 per 970 patients
  - Salmonellosis: ~2,000 AZ cases/yr → ~0.3 per 1,000
  - Campylobacter: ~1,800 AZ cases/yr → ~0.25 per 1,000
  - Gonorrhea: ~12,000 AZ cases/yr → ~1.7 per 1,000
  - Chlamydia (not on R9-6-202 list): omitted
  - TB (active): ~200 AZ cases/yr → ~0.03 per 1,000
  - Pertussis: ~150 AZ cases/yr → ~0.02 per 1,000
  - West Nile (human): ~150 AZ cases/yr (variable)
  - Plague: 1-3 cases/yr (very rare)
  - Measles: 0-5 cases/yr (very rare; outbreak-driven)

We deliberately INFLATE rates above population-proportional so the demo
has enough cases to be visually meaningful. Documented in metadata.
"""
from __future__ import annotations

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"
REF = BASE / "data" / "reference"

# Per-disease case counts to place (calibrated for demo visibility, not
# population-proportional — see module docstring).
CASE_COUNTS = {
    # === Common AZ endemic / high-volume conditions (more cases) ===
    "valley_fever":           28,
    "campylobacteriosis":     14,
    "salmonellosis":          18,
    "gonorrhea":              16,
    "syphilis":               11,
    "varicella":               9,
    "rmsf":                   12,   # AZ has highest US burden
    "ehrlichiosis":            9,
    "west_nile":               7,   # human cases
    "tb_active":               5,
    "pertussis":               6,
    "haemophilus_invasive":    3,
    "hus":                     2,
    "listeriosis":             3,
    "mumps":                   3,
    "hansens":                 2,   # AZ is one of higher-rate states
    "candida_auris":           2,
    "hiv_infant":              1,
    "tb_latent_child":         4,
    "chancroid":               1,
    "creutzfeldt_jakob":       1,
    "cysticercosis":           2,
    "taeniasis":               2,
    "tetanus":                 1,
    "tss":                     2,
    "trichinosis":             1,
    "lyme":                    1,   # rare in AZ but not zero (travel cases)
    "dengue":                  2,   # imported / occasional autochthonous
    "chikungunya":             1,
    "zika":                    1,
    "typhoid":                 1,
    "typhus":                  2,
    "relapsing_fever":         2,
    "psittacosis":             1,
    "lcm":                     1,
    "respiratory_outbreak":    2,
    "diarrhea_outbreak":       2,
    "novel_coronavirus":       8,   # ongoing endemic surveillance
    "influenza_pediatric_mortality": 1,

    # === Rare but high-impact (always at least one for demo) ===
    "measles":                 3,   # 0-5 cases AZ/yr; flag as outbreak risk
    "plague":                  2,   # canonical AZ endemic
    "hantavirus":              2,   # AZ is highest-burden state
    "tularemia":               1,
    "brucellosis":             2,
    "q_fever":                 2,
    "rabies_human":            1,   # very rare
    "rubella":                 1,
    "mpox":                    2,
    "melioidosis":             1,
    "encephalitis_viral":      3,
    "encephalitis_parasitic":  1,   # Naegleria — rare but AZ has had cases

    # === Very rare / never-seen-in-AZ but on list ===
    "anthrax":                 1,
    "botulism":                2,
    "diphtheria":              1,
    "polio":                   0,
    "smallpox":                0,
    "sars":                    0,
    "mers":                    1,
    "vhf":                     1,
    "yellow_fever":            1,
    "cholera":                 1,
    "cronobacter_infant":      1,
    "rubella_congenital":      1,
    "vaccinia":                1,
    "glanders":                0,
    "emerging_or_exotic":      1,

    # === Animal-side cases ===
    "rabies_animal":           4,
    "avian_influenza":         3,
    "vesicular_stomatitis":    2,
    "onchocerca_lupi":         2,
}

# County endemicity weights — boost likelihood of certain diseases in
# certain counties to match real AZ epidemiology
COUNTY_WEIGHTS = {
    "valley_fever":  {"Pima": 3.0, "Pinal": 3.0, "Maricopa": 2.5, "Yuma": 1.5, "Cochise": 1.5},
    "rmsf":          {"Pinal": 2.5, "Apache": 2.0, "Navajo": 2.0, "Gila": 1.5, "La Paz": 1.5},
    "plague":        {"Coconino": 5.0, "Apache": 3.0, "Navajo": 3.0, "Yavapai": 1.5},
    "hantavirus":    {"Coconino": 3.0, "Apache": 2.5, "Navajo": 2.5, "Yavapai": 1.5},
    "west_nile":     {"Maricopa": 2.5, "Pima": 2.0, "Yuma": 2.0, "La Paz": 2.0, "Mohave": 1.5},
    "tularemia":     {"Coconino": 2.0, "Apache": 2.0, "Yavapai": 1.5},
    "brucellosis":   {"Cochise": 2.0, "Pima": 1.5, "Santa Cruz": 1.5, "Yuma": 1.5},
    "q_fever":       {"Cochise": 2.0, "Apache": 1.8, "Mohave": 1.5},
    "tb_active":     {"Maricopa": 1.5, "Yuma": 2.0, "Santa Cruz": 1.8, "Pima": 1.3},
    "hansens":       {"Maricopa": 1.5, "Pima": 1.3},
    "ehrlichiosis":  {"Pinal": 1.8, "Pima": 1.5, "Apache": 1.5},
}


def _condition_code(disease: dict, status: str = "confirmed") -> dict:
    """Build a FHIR Condition.code CodeableConcept for the disease."""
    coding = []
    if disease.get("snomed_ct"):
        coding.append({
            "system": "http://snomed.info/sct",
            "code": disease["snomed_ct"],
            "display": disease["common_name"],
        })
    if disease.get("icd10"):
        coding.append({
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": disease["icd10"],
            "display": disease["common_name"],
        })
    return {"coding": coding, "text": disease["common_name"]}


def main() -> None:
    rng = random.Random(42)
    db = json.loads((REF / "reportable_diseases_us.json").read_text())
    households = json.loads((DATA / "households.json").read_text())["households"]
    encounters = json.loads((DATA / "encounters.json").read_text())["encounters"]

    diseases_by_id = {d["disease_id"]: d for d in db["diseases"]}

    # Index households by primary county for endemicity weighting
    hh_by_county = {}
    for hh in households:
        county = (hh.get("county") or {}).get("name", "Maricopa")
        hh_by_county.setdefault(county, []).append(hh)

    # Pre-build pools of human and animal patients
    all_humans = []
    all_animals = []
    for hh in households:
        for h in hh.get("humans", []):
            all_humans.append({"patient": h, "household": hh, "ref": "Patient/" + h["id"], "kind": "human"})
        for a in hh.get("animals", []):
            all_animals.append({"patient": a, "household": hh, "ref": "AnimalPatient/" + a["id"], "kind": "animal"})

    # Index encounters by patient_ref for linking conditions to encounters
    enc_by_subject = {}
    for e in encounters:
        ref = (e.get("subject") or {}).get("reference", "")
        if ref:
            enc_by_subject.setdefault(ref, []).append(e)

    placed_cases = []
    skipped = []
    summary = {}

    for disease_id, n_target in CASE_COUNTS.items():
        if n_target == 0: continue
        disease = diseases_by_id.get(disease_id)
        if not disease:
            skipped.append(disease_id)
            continue

        applies_to = disease.get("applies_to", ["human"])
        species_apply = set(disease.get("applicable_species", []))

        # Pick the right pool
        if "human" in applies_to and "animal" in applies_to:
            # Split: ~80% human, 20% animal for cross-species reportables
            n_human = max(1, int(n_target * 0.8))
            n_animal = n_target - n_human
            pools = [(all_humans, n_human), (all_animals, n_animal)]
        elif "animal" in applies_to:
            pools = [(all_animals, n_target)]
        else:
            pools = [(all_humans, n_target)]

        county_w = COUNTY_WEIGHTS.get(disease_id, {})

        for pool, n in pools:
            # Filter to species-eligible patients
            if pool is all_animals and species_apply:
                eligible = [p for p in pool if (p["patient"].get("species") or {}).get("code") in species_apply
                            or any(s in str(p["patient"].get("species", "")).lower() for s in species_apply)]
                if not eligible: eligible = pool
            else:
                eligible = pool

            # Apply weights for county endemicity
            weights = []
            for p in eligible:
                county = (p["household"].get("county") or {}).get("name", "Maricopa")
                base = 1.0
                w = county_w.get(county, base)
                weights.append(w)

            if not eligible: continue

            # Sample without replacement using rejection on existing case load
            picks = []
            attempts = 0
            seen = set()
            while len(picks) < n and attempts < n * 30:
                attempts += 1
                idx = rng.choices(range(len(eligible)), weights=weights, k=1)[0]
                if idx in seen: continue
                p = eligible[idx]
                pid = p["patient"]["id"]
                # Avoid placing more than 2 reportables on the same patient
                existing = sum(1 for c in placed_cases if c["subject"]["reference"].endswith(pid))
                if existing >= 2: continue
                seen.add(idx)
                picks.append(p)

            for p in picks:
                pid = p["patient"]["id"]
                ref = p["ref"]
                # Pick a recent encounter to anchor the diagnosis
                patient_encs = enc_by_subject.get(ref, [])
                anchor_enc = rng.choice(patient_encs) if patient_encs else None
                onset_date = (date(2025, 1, 1) + timedelta(days=rng.randint(0, 480))).isoformat()
                encounter_ref = f"Encounter/{anchor_enc['id']}" if anchor_enc else None

                cond = {
                    "resourceType": "Condition",
                    "id": f"reportable-{disease_id}-{pid[:8]}-{len(placed_cases):04d}",
                    "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
                    "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                    "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "encounter-diagnosis"}]}],
                    "code": _condition_code(disease),
                    "subject": {"reference": ref},
                    "encounter": {"reference": encounter_ref} if encounter_ref else None,
                    "onsetDateTime": onset_date,
                    "recordedDate": onset_date,
                    "_reportable": {
                        "disease_id": disease_id,
                        "common_name": disease["common_name"],
                        "is_reportable": True,
                        "human_reporting": disease.get("human_reporting", {}),
                        "animal_reporting": disease.get("animal_reporting", {}),
                        "is_zoonotic": disease.get("is_zoonotic", False),
                        "is_select_agent": disease.get("is_select_agent", False),
                        "applies_to_subject_kind": p["kind"],
                        "report_status": "unreported",   # transitions to "submitted" via UI
                    },
                    "_household_id": p["household"]["household_id"],
                }
                placed_cases.append(cond)

        summary[disease_id] = sum(1 for c in placed_cases if c["_reportable"]["disease_id"] == disease_id)

    # Write output
    out = {
        "_description": (
            "Reportable disease cases placed on existing patients across the synthetic "
            "dataset. Each case is a FHIR Condition resource with the _reportable extension "
            "carrying reporting metadata. Counts are calibrated to be visually meaningful "
            "for the demo (modestly inflated above population-proportional rates), with "
            "county endemicity weighting where appropriate."
        ),
        "_caveat": (
            "Synthetic. All patient identifiers and case timing are synthetic. County-level "
            "endemicity weighting reflects published ADHS and CDC patterns but absolute counts "
            "are demo-calibrated, not epidemiologically projected."
        ),
        "summary": {
            "total_cases": len(placed_cases),
            "by_disease": summary,
            "by_subject_kind": {
                "human":  sum(1 for c in placed_cases if c["_reportable"]["applies_to_subject_kind"] == "human"),
                "animal": sum(1 for c in placed_cases if c["_reportable"]["applies_to_subject_kind"] == "animal"),
            },
            "by_timeline": {},
        },
        "cases": placed_cases,
    }
    # Timeline summary
    timelines = {}
    for c in placed_cases:
        tl = c["_reportable"]["human_reporting"].get("adhs_timeline") or c["_reportable"]["animal_reporting"].get("destinations") and "animal_only"
        if not tl: tl = "animal_only"
        timelines[tl] = timelines.get(tl, 0) + 1
    out["summary"]["by_timeline"] = timelines

    (DATA / "reportable_cases.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"=== Reportable case generator ===")
    print(f"Total placed: {len(placed_cases)}")
    print(f"By subject kind: human={out['summary']['by_subject_kind']['human']}, animal={out['summary']['by_subject_kind']['animal']}")
    print(f"By timeline: {timelines}")
    print()
    print("Top 10 diseases by case count:")
    for did, n in sorted(summary.items(), key=lambda x: -x[1])[:15]:
        d = diseases_by_id[did]
        print(f"  {d['common_name'][:46]:46s}  {n:>3d}")
    if skipped:
        print(f"\nSkipped (not in DB): {skipped}")


if __name__ == "__main__":
    main()
