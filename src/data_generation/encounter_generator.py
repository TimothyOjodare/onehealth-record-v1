"""
Longitudinal encounter generator.

For each patient (human + animal) in the household bundle, generate a
plausible visit history spanning the past 24 months. Each encounter has:
    - a date
    - a provider type (PCP / specialist / vet / urgent care / ED)
    - a chief complaint
    - vital signs (where appropriate)
    - associated conditions / medications

The generator is deterministic (seeded). Patients with chronic conditions
get more visits and condition-specific vital trends. The hand-crafted
scenario index cases get realistic timelines (annual physical → cold →
the big diagnosis).

Output: data/synthetic/encounters.json
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"


def _new_id() -> str:
    return str(uuid.uuid4())


def _date_offset(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


# ---------------------------------------------------------------------------
# Encounter templates by category
# ---------------------------------------------------------------------------
HUMAN_ENCOUNTER_TYPES = {
    "annual_physical": {
        "provider": "Primary Care",
        "chief_complaint": "Annual physical examination",
        "weight": 1.0,
    },
    "url_acute_resp": {
        "provider": "Urgent Care",
        "chief_complaint": "Upper respiratory infection",
        "weight": 0.4,
    },
    "url_minor_inj": {
        "provider": "Urgent Care",
        "chief_complaint": "Minor injury / laceration",
        "weight": 0.2,
    },
    "spec_chronic": {
        "provider": "Specialist",
        "chief_complaint": "Chronic disease follow-up",
        "weight": 0.0,  # only assigned to patients with chronic conditions
    },
    "med_refill": {
        "provider": "Primary Care",
        "chief_complaint": "Medication refill / management",
        "weight": 0.0,
    },
    "ed_chest_pain": {
        "provider": "Emergency Department",
        "chief_complaint": "Chest pain (workup negative)",
        "weight": 0.05,
    },
    "behavioral_h": {
        "provider": "Behavioral Health",
        "chief_complaint": "Routine mental health follow-up",
        "weight": 0.05,
    },
}

VET_ENCOUNTER_TYPES = {
    "wellness": {"chief_complaint": "Annual wellness exam + vaccinations", "weight": 1.0},
    "acute_gi":  {"chief_complaint": "Acute vomiting / diarrhea",          "weight": 0.4},
    "skin":      {"chief_complaint": "Pruritus / skin lesion",             "weight": 0.3},
    "lameness":  {"chief_complaint": "Lameness or limping",                "weight": 0.25},
    "dental":    {"chief_complaint": "Dental cleaning",                    "weight": 0.20},
    "ear":       {"chief_complaint": "Otitis externa",                     "weight": 0.15},
    "uri":       {"chief_complaint": "Upper respiratory signs",            "weight": 0.10},
}

# Vitals generators ---------------------------------------------------------
def _human_vitals(rng: random.Random, age: int, has_htn: bool, has_dm: bool):
    bp_sys = rng.randint(160, 180) if has_htn else rng.randint(112, 132)
    bp_dia = rng.randint(92, 102) if has_htn else rng.randint(70, 82)
    if age > 65:
        bp_sys += rng.randint(0, 10)
    hr = rng.randint(62, 88)
    rr = rng.randint(14, 18)
    spo2 = rng.choice([97, 98, 99, 99, 100])
    temp = round(98.0 + rng.random() * 1.4, 1)
    glucose = rng.randint(140, 220) if has_dm else rng.randint(82, 108)
    return {
        "bp": f"{bp_sys}/{bp_dia}",
        "hr": hr, "rr": rr, "spo2": spo2, "temp_f": temp,
        "glucose_mg_dl": glucose,
    }


def _vet_vitals(rng: random.Random, species: str, age: int):
    if species == "dog":
        return {"hr": rng.randint(70, 120), "rr": rng.randint(15, 30),
                "temp_f": round(101.0 + rng.random() * 1.5, 1),
                "weight_kg": round(rng.uniform(8, 35), 1)}
    if species == "cat":
        return {"hr": rng.randint(140, 200), "rr": rng.randint(20, 35),
                "temp_f": round(101.0 + rng.random() * 1.5, 1),
                "weight_kg": round(rng.uniform(3, 7), 1)}
    if species == "horse":
        return {"hr": rng.randint(28, 44), "rr": rng.randint(8, 16),
                "temp_f": round(99.5 + rng.random() * 1.5, 1),
                "weight_kg": rng.randint(380, 600)}
    if species == "bird":
        return {"hr": rng.randint(200, 600), "rr": rng.randint(20, 40),
                "weight_g": rng.randint(80, 1200)}
    if species == "goat":
        return {"hr": rng.randint(70, 90), "rr": rng.randint(15, 30),
                "temp_f": round(102.0 + rng.random() * 1.5, 1),
                "weight_kg": rng.randint(35, 80)}
    return {}


# ---------------------------------------------------------------------------
def encounter_record(*, encounter_id, subject_ref, subject_kind, subject_label,
                     date_iso, provider, chief_complaint, vitals, narrative,
                     condition_codes=None, medications=None, household_id=None):
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "subject": {"reference": subject_ref, "label": subject_label, "kind": subject_kind},
        "household_id": household_id,
        "period": {"start": date_iso},
        "provider": provider,
        "chief_complaint": chief_complaint,
        "vitals": vitals,
        "narrative": narrative,
        "conditions_recorded": condition_codes or [],
        "medications_recorded": medications or [],
        "source": "machine_authored",
    }


# ---------------------------------------------------------------------------
# Generate encounters for a single patient
# ---------------------------------------------------------------------------
def _generate_human_encounters(rng, patient, household_id, household_active_conditions):
    encounters = []
    given = patient["name"][0]["given"][0]
    family = patient["name"][0]["family"]
    label = f"{given} {family}"
    pref = f"Patient/{patient['id']}"
    chronic = patient.get("chronic_conditions", []) or []
    has_htn = "Essential hypertension" in chronic
    has_dm = "Type 2 diabetes mellitus" in chronic
    has_lipid = "Hyperlipidemia" in chronic
    age = date.today().year - int(patient["birthDate"][:4])

    # Annual physical(s) over the past 24 months
    n_physicals = 2 if rng.random() < 0.7 else 1
    physical_offsets = sorted(rng.sample(range(60, 720), n_physicals), reverse=True)
    for offset in physical_offsets:
        v = _human_vitals(rng, age, has_htn, has_dm)
        narrative = (f"{age}-year-old {patient['gender']} for annual exam. "
                     + ("Known hypertensive. " if has_htn else "")
                     + ("Type 2 diabetic on metformin. " if has_dm else "")
                     + ("Hyperlipidemia, on atorvastatin. " if has_lipid else "")
                     + f"Vitals: BP {v['bp']}, HR {v['hr']}, Temp {v['temp_f']} F, SpO2 {v['spo2']}%. "
                     + ("Plan: continue antihypertensive, recheck BP in 3 months. " if has_htn else "")
                     + ("Plan: continue metformin, A1c at next visit. " if has_dm else "")
                     + "Routine labs ordered. Return in 12 months unless concerns.")
        meds = []
        if has_htn: meds.append("Lisinopril 10 mg oral tablet")
        if has_dm: meds.append("Metformin 500 mg oral tablet")
        if has_lipid: meds.append("Atorvastatin 20 mg oral tablet")
        encounters.append(encounter_record(
            encounter_id=_new_id(), subject_ref=pref, subject_kind="Person",
            subject_label=label, date_iso=_date_offset(offset),
            provider="Primary Care", chief_complaint="Annual physical examination",
            vitals=v, narrative=narrative, medications=meds, household_id=household_id))

    # Chronic disease follow-ups (specialist or PCP) — 3-6 over 24 months if chronic conditions
    if chronic:
        n_followup = rng.randint(3, 6)
        offsets = sorted(rng.sample(range(20, 700), n_followup), reverse=True)
        for offset in offsets:
            v = _human_vitals(rng, age, has_htn, has_dm)
            cc = "Chronic disease follow-up — " + ", ".join(chronic[:2])
            narrative = (f"Follow-up for {', '.join(chronic)}. "
                         f"BP {v['bp']}, HR {v['hr']}. "
                         + (f"Glucose today {v['glucose_mg_dl']} mg/dL. " if has_dm else "")
                         + "Doing well overall. Continue current regimen.")
            meds = []
            if has_htn: meds.append("Lisinopril 10 mg oral tablet")
            if has_dm:  meds.append("Metformin 500 mg oral tablet")
            if has_lipid: meds.append("Atorvastatin 20 mg oral tablet")
            encounters.append(encounter_record(
                encounter_id=_new_id(), subject_ref=pref, subject_kind="Person",
                subject_label=label, date_iso=_date_offset(offset),
                provider="Primary Care", chief_complaint=cc, vitals=v,
                narrative=narrative, medications=meds, household_id=household_id))

    # Acute encounters (URI, minor injury, etc.)
    n_acute = rng.choices([0, 1, 2, 3], weights=[40, 35, 20, 5])[0]
    for _ in range(n_acute):
        offset = rng.randint(20, 700)
        v = _human_vitals(rng, age, has_htn, has_dm)
        cc_type = rng.choice(["upper respiratory infection","minor laceration","seasonal allergies",
                              "low back pain","urinary tract infection","ankle sprain","viral gastroenteritis"])
        narrative = f"Patient with self-limited {cc_type}. Symptomatic management. Return precautions reviewed."
        encounters.append(encounter_record(
            encounter_id=_new_id(), subject_ref=pref, subject_kind="Person",
            subject_label=label, date_iso=_date_offset(offset),
            provider="Urgent Care", chief_complaint=cc_type.capitalize(),
            vitals=v, narrative=narrative, household_id=household_id))

    # Mental health follow-up if MDD
    if "Major depressive disorder" in chronic:
        for _ in range(rng.randint(2, 4)):
            offset = rng.randint(30, 700)
            encounters.append(encounter_record(
                encounter_id=_new_id(), subject_ref=pref, subject_kind="Person",
                subject_label=label, date_iso=_date_offset(offset),
                provider="Behavioral Health",
                chief_complaint="Depression follow-up",
                vitals={}, narrative="Stable on sertraline 50 mg. PHQ-9 = 6. Continue current dose; review in 3 months.",
                medications=["Sertraline 50 mg oral tablet"], household_id=household_id))

    # Index-case encounter for hand-crafted scenarios — most recent.
    for cond in household_active_conditions:
        if cond["subject"]["reference"] == pref:
            onset = cond["onsetDateTime"][:10]
            offset_days = (date.today() - date.fromisoformat(onset)).days
            v = _human_vitals(rng, age, has_htn, has_dm)
            cc_text = cond["code"]["text"]
            narrative = (f"{age}-year-old presenting with symptoms ultimately diagnosed as {cc_text}. "
                         f"See clinical note. Vitals today: BP {v['bp']}, HR {v['hr']}, "
                         f"Temp {v['temp_f']} F, SpO2 {v['spo2']}%.")
            encounters.append(encounter_record(
                encounter_id=_new_id(), subject_ref=pref, subject_kind="Person",
                subject_label=label, date_iso=_date_offset(offset_days),
                provider="Primary Care", chief_complaint=f"Workup leading to {cc_text} dx",
                vitals=v, narrative=narrative,
                condition_codes=[cond["code"]["coding"][0]["code"]],
                household_id=household_id))

    return sorted(encounters, key=lambda e: e["period"]["start"])


def _generate_animal_encounters(rng, animal, household_id, household_active_conditions):
    encounters = []
    aref = f"AnimalPatient/{animal['id']}"
    label = f"{animal['name']} ({animal['species']['code']})"
    species = animal["species"]["code"]
    age = date.today().year - int(animal["birthDate"][:4])

    # Annual wellness — 1-2 visits
    n_wellness = 2 if rng.random() < 0.6 else 1
    for offset in sorted(rng.sample(range(60, 720), n_wellness), reverse=True):
        v = _vet_vitals(rng, species, age)
        narrative = (f"Annual wellness exam for {animal['name']}, "
                     f"a {age}-year-old {animal['breed']} {species}. "
                     "Bright, alert, responsive. Vaccines updated. "
                     "Discussed parasite prevention and dental care. "
                     "Recommend recheck in 12 months.")
        encounters.append(encounter_record(
            encounter_id=_new_id(), subject_ref=aref, subject_kind="Animal",
            subject_label=label, date_iso=_date_offset(offset),
            provider="Veterinarian", chief_complaint="Annual wellness exam + vaccinations",
            vitals=v, narrative=narrative, household_id=household_id))

    # Acute vet visits
    n_acute = rng.choices([0, 1, 2, 3], weights=[35, 35, 25, 5])[0]
    acute_choices = list(VET_ENCOUNTER_TYPES.keys())
    acute_choices.remove("wellness")
    for _ in range(n_acute):
        offset = rng.randint(15, 700)
        kind = rng.choice(acute_choices)
        v = _vet_vitals(rng, species, age)
        cc = VET_ENCOUNTER_TYPES[kind]["chief_complaint"]
        narrative = f"{animal['name']} presents for {cc.lower()}. Treated symptomatically. Recheck PRN."
        encounters.append(encounter_record(
            encounter_id=_new_id(), subject_ref=aref, subject_kind="Animal",
            subject_label=label, date_iso=_date_offset(offset),
            provider="Veterinarian", chief_complaint=cc,
            vitals=v, narrative=narrative, household_id=household_id))

    # Index-case visits
    for cond in household_active_conditions:
        if cond["subject"]["reference"] == aref:
            onset = cond["onsetDateTime"][:10]
            offset_days = (date.today() - date.fromisoformat(onset)).days
            v = _vet_vitals(rng, species, age)
            cc_text = cond["code"]["text"]
            narrative = (f"{animal['name']} presented with symptoms diagnosed as {cc_text}. "
                         f"Diagnostic workup complete; treatment initiated. "
                         f"Owner counseled re: zoonotic implications and household exposure.")
            encounters.append(encounter_record(
                encounter_id=_new_id(), subject_ref=aref, subject_kind="Animal",
                subject_label=label, date_iso=_date_offset(offset_days),
                provider="Veterinarian", chief_complaint=f"{cc_text} workup and dx",
                vitals=v, narrative=narrative,
                condition_codes=[cond["code"]["coding"][0]["code"]],
                household_id=household_id))

    return sorted(encounters, key=lambda e: e["period"]["start"])


# ---------------------------------------------------------------------------
def generate_all(seed: int = 42) -> dict:
    rng = random.Random(seed)
    households = json.loads((SYNTH_DIR / "households.json").read_text())["households"]

    encounters: list[dict] = []
    for hh in households:
        active = hh.get("conditions", [])
        for p in hh["humans"]:
            encounters.extend(_generate_human_encounters(rng, p, hh["household_id"], active))
        for a in hh["animals"]:
            encounters.extend(_generate_animal_encounters(rng, a, hh["household_id"], active))

    bundle = {
        "_metadata": {
            "n_encounters": len(encounters),
            "n_human_encounters": sum(1 for e in encounters if e["subject"]["kind"] == "Person"),
            "n_animal_encounters": sum(1 for e in encounters if e["subject"]["kind"] == "Animal"),
            "schema_version": "0.1.0",
        },
        "encounters": encounters,
    }
    out = SYNTH_DIR / "encounters.json"
    out.write_text(json.dumps(bundle, indent=2))
    return bundle


if __name__ == "__main__":
    b = generate_all()
    md = b["_metadata"]
    print(f"Encounters: {md['n_encounters']} "
          f"(human {md['n_human_encounters']}, animal {md['n_animal_encounters']})")
