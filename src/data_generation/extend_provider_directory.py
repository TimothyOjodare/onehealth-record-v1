"""
Phase 8 — Extend the provider directory with non-clinician staff.

Adds:
  - 1 Registrar per hospital (6) and per vet (4) = 10
  - 1 Triage Nurse per hospital (6) and 1 Vet Tech per vet (4) = 10
  - 1 Discharge coordinator per hospital (6)
  - 1 Lab Tech per hospital (6)
  - 1 Admin per hospital (6)

Total new staff: 38 across 10 institutions.

Names are seeded with random.Random(42) for reproducibility.
"""
from __future__ import annotations
import json
import random
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"

HOSPITALS = [
    {"id": "tmc",        "name": "Tucson Medical Center",      "city": "Tucson"},
    {"id": "banner-phx", "name": "Banner Health Phoenix",      "city": "Phoenix"},
    {"id": "banner-mesa","name": "Banner Health Mesa",         "city": "Mesa"},
    {"id": "honorhealth","name": "HonorHealth Scottsdale",     "city": "Scottsdale"},
    {"id": "ihs-white",  "name": "IHS Whiteriver Service Unit","city": "Whiteriver"},
    {"id": "naz",        "name": "Northern AZ Healthcare",     "city": "Flagstaff"},
]
VETS = [
    {"id": "vet-pinal",   "name": "Pinal Mixed-Practice Vet",       "city": "Casa Grande"},
    {"id": "vet-tucson",  "name": "Tucson Companion-Animal Vet",    "city": "Tucson"},
    {"id": "vet-cochise", "name": "Cochise Large-Animal Vet",       "city": "Sierra Vista"},
    {"id": "vet-phx",     "name": "Phoenix Companion-Animal Vet",   "city": "Phoenix"},
]

# Realistic name pools — varied ethnic backgrounds matching AZ demographics
GIVEN_NAMES = [
    "Sandra", "Marcus", "Yolanda", "Brian", "Priya", "Hector", "Tonya", "Kevin",
    "Rebecca", "Alejandro", "Kayla", "Daniel", "Maya", "Steven", "Nadia", "Eduardo",
    "Tanya", "Jamal", "Christine", "Luis", "Amber", "Tyrone", "Janet", "Carlos",
    "Diana", "Vincent", "Pearl", "Anthony", "Felicia", "Marcus", "Jasmine", "David",
    "Linda", "Roberto", "Naomi", "Steven", "Whitney", "Andre"
]
FAMILY_NAMES = [
    "Hernandez", "Garcia", "Tsosie", "Begay", "Williams", "Johnson", "Lee", "Patel",
    "Singh", "Nguyen", "Tran", "Lopez", "Martinez", "Brown", "Davis", "Rodriguez",
    "Wilson", "Yazzie", "Manygoats", "Begaye", "Cho", "Park", "Thompson", "Mitchell",
    "Anderson", "Sanchez", "Ramirez", "Castillo", "Morales", "Romero", "Reyes", "Diaz",
    "Becker", "Wright", "Allen", "Castillo", "Bell", "Baker"
]


def main() -> None:
    rng = random.Random(42)
    used_names = set()

    def make_name():
        for _ in range(50):
            g = rng.choice(GIVEN_NAMES)
            f = rng.choice(FAMILY_NAMES)
            if (g, f) not in used_names:
                used_names.add((g, f))
                return g, f
        return rng.choice(GIVEN_NAMES), rng.choice(FAMILY_NAMES)

    new_staff = {
        "registrars": [],
        "triage_nurses": [],
        "discharge_coordinators": [],
        "lab_techs": [],
        "administrators": [],
        "vet_techs": [],
        "vet_registrars": [],
    }

    # Hospital staff
    for h in HOSPITALS:
        # Registrar
        g, f = make_name()
        new_staff["registrars"].append({
            "id": f"reg-{h['id']}-{f.lower()}",
            "name": f"{g} {f}",
            "role": "registrar",
            "facility": h["name"],
            "facility_id": h["id"],
            "title": "Patient Registration Specialist",
        })

        # Triage Nurse
        g, f = make_name()
        new_staff["triage_nurses"].append({
            "id": f"tri-{h['id']}-{f.lower()}",
            "name": f"{g} {f}, RN",
            "role": "triage_nurse",
            "facility": h["name"],
            "facility_id": h["id"],
            "title": "Triage Nurse",
            "credentials": "RN, ENA",
        })

        # Discharge coordinator
        g, f = make_name()
        new_staff["discharge_coordinators"].append({
            "id": f"dis-{h['id']}-{f.lower()}",
            "name": f"{g} {f}, RN",
            "role": "discharge_coordinator",
            "facility": h["name"],
            "facility_id": h["id"],
            "title": "Discharge Care Coordinator",
            "credentials": "RN, BSN",
        })

        # Lab tech
        g, f = make_name()
        new_staff["lab_techs"].append({
            "id": f"lab-{h['id']}-{f.lower()}",
            "name": f"{g} {f}, MLT",
            "role": "lab_tech",
            "facility": h["name"],
            "facility_id": h["id"],
            "title": "Medical Laboratory Technologist",
            "credentials": "MLT (ASCP)",
        })

        # Administrator
        g, f = make_name()
        new_staff["administrators"].append({
            "id": f"adm-{h['id']}-{f.lower()}",
            "name": f"{g} {f}, MHA",
            "role": "administrator",
            "facility": h["name"],
            "facility_id": h["id"],
            "title": "Operations Administrator",
            "credentials": "MHA",
        })

    # Vet staff
    for v in VETS:
        # Vet Registrar (front-desk)
        g, f = make_name()
        new_staff["vet_registrars"].append({
            "id": f"vreg-{v['id']}-{f.lower()}",
            "name": f"{g} {f}",
            "role": "registrar",
            "facility": v["name"],
            "facility_id": v["id"],
            "facility_kind": "vet_clinic",
            "title": "Client Service Representative",
        })

        # Vet Tech
        g, f = make_name()
        new_staff["vet_techs"].append({
            "id": f"vtech-{v['id']}-{f.lower()}",
            "name": f"{g} {f}, RVT",
            "role": "vet_tech",
            "facility": v["name"],
            "facility_id": v["id"],
            "facility_kind": "vet_clinic",
            "title": "Registered Veterinary Technician",
            "credentials": "RVT",
        })

    # Merge into existing providers.json
    providers = json.loads((DATA / "providers.json").read_text())
    providers["registrars"] = new_staff["registrars"] + new_staff["vet_registrars"]
    providers["triage_nurses"] = new_staff["triage_nurses"]
    providers["vet_techs"] = new_staff["vet_techs"]
    providers["discharge_coordinators"] = new_staff["discharge_coordinators"]
    providers["lab_techs"] = new_staff["lab_techs"]
    providers["administrators"] = new_staff["administrators"]

    # Add facility metadata for the institutional login screens
    providers["facilities"] = {
        "hospitals": HOSPITALS,
        "vets": VETS,
    }

    (DATA / "providers.json").write_text(json.dumps(providers, indent=2, default=str))

    n_total = sum(len(v) for k, v in new_staff.items())
    print(f"Phase 8 — staff directory expansion")
    print(f"  Registrars (hospital):     {len(new_staff['registrars'])}")
    print(f"  Registrars (vet):          {len(new_staff['vet_registrars'])}")
    print(f"  Triage nurses:             {len(new_staff['triage_nurses'])}")
    print(f"  Vet techs:                 {len(new_staff['vet_techs'])}")
    print(f"  Discharge coordinators:    {len(new_staff['discharge_coordinators'])}")
    print(f"  Lab techs:                 {len(new_staff['lab_techs'])}")
    print(f"  Administrators:            {len(new_staff['administrators'])}")
    print(f"  Total new staff:           {n_total}")


if __name__ == "__main__":
    main()
