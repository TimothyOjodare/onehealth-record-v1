"""
Assign every human and animal patient to a primary care provider.

Phase 4 — role-based access control demo. This step is deterministic
(seed=42) and produces `data/synthetic/providers.json`, which the
front-end auth layer uses to filter Provider Workspace by login.

Mapping logic (county → primary care provider):
    Pima            → Dr. Reyes (Tucson Medical Center)
    Maricopa        → Dr. Patel (Banner Health Phoenix)
    Apache, Navajo  → Dr. Yazzie (IHS Whiteriver Service Unit)
    Coconino        → Dr. Anderson (Northern AZ Healthcare)
    Cochise, Santa Cruz, Greenlee → Dr. Anderson (overflow)
    Yuma, La Paz    → Dr. Patel (overflow)
    Pinal, Gila     → Dr. Reyes (overflow)
    Mohave, Yavapai → Dr. Anderson (overflow)

Animals:
    Pinal           → Dr. Kim (Pinal Mixed-Practice Vet)
    Pima            → Dr. Cho (Tucson Companion-Animal Vet)
    Cochise + large-animal counties → Dr. Becker (Cochise Large-Animal)
    other counties  → load-balanced across the three vets

Public Health users see no patient mapping; they see aggregates.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"

# ---- Provider directory --------------------------------------------------

PHYSICIANS = [
    {"id": "phys-reyes",    "name": "Dr. Maria Reyes",    "facility": "Tucson Medical Center",
     "role": "physician", "specialty": "Family Medicine"},
    {"id": "phys-patel",    "name": "Dr. Anika Patel",    "facility": "Banner Health Phoenix",
     "role": "physician", "specialty": "Internal Medicine"},
    {"id": "phys-yazzie",   "name": "Dr. Rosa Yazzie",    "facility": "IHS Whiteriver Service Unit",
     "role": "physician", "specialty": "Family Medicine"},
    {"id": "phys-anderson", "name": "Dr. James Anderson", "facility": "Northern AZ Healthcare",
     "role": "physician", "specialty": "Internal Medicine"},
    {"id": "phys-nakagawa", "name": "Dr. Kenji Nakagawa", "facility": "Banner Health Mesa",
     "role": "physician", "specialty": "Family Medicine"},
    {"id": "phys-okafor",   "name": "Dr. Adaeze Okafor",  "facility": "HonorHealth Scottsdale",
     "role": "physician", "specialty": "Internal Medicine"},
]

VETERINARIANS = [
    {"id": "vet-kim",     "name": "Dr. Soo-min Kim",      "facility": "Pinal Mixed-Practice Vet",
     "role": "veterinarian", "specialty": "Mixed Practice"},
    {"id": "vet-cho",     "name": "Dr. Hannah Cho",       "facility": "Tucson Companion-Animal Vet",
     "role": "veterinarian", "specialty": "Small Animal"},
    {"id": "vet-becker",  "name": "Dr. Tom Becker",       "facility": "Cochise Large-Animal Vet",
     "role": "veterinarian", "specialty": "Large Animal"},
    {"id": "vet-rivera",  "name": "Dr. Elena Rivera",     "facility": "Phoenix Companion-Animal Vet",
     "role": "veterinarian", "specialty": "Small Animal"},
]

PUBLIC_HEALTH = [
    {"id": "ph-adhs",   "name": "Dr. Lisa Nakamura",  "facility": "Arizona Department of Health Services",
     "role": "public_health", "specialty": "State Epidemiologist"},
    {"id": "ph-tribal", "name": "Dr. Sarah Begay",    "facility": "Apache Tribal Health Authority",
     "role": "public_health", "specialty": "Tribal Health Officer"},
    {"id": "ph-aphis",  "name": "Dr. Mark Williams",  "facility": "USDA APHIS Region 7",
     "role": "public_health", "specialty": "Veterinary Epidemiologist"},
]


# County → primary-care physician routing.
# Maricopa is split across 3 physicians via household_id hash to keep
# panel sizes near real-PCP scale (target: ~80–180 patients per panel).
COUNTY_TO_PHYSICIAN: dict[str, str] = {
    "Pima":      "phys-reyes",
    "Apache":    "phys-yazzie",
    "Navajo":    "phys-yazzie",
    "Coconino":  "phys-anderson",
    "Cochise":     "phys-anderson",
    "Santa Cruz":  "phys-anderson",
    "Greenlee":    "phys-anderson",
    "Yuma":        "phys-patel",
    "La Paz":      "phys-patel",
    "Pinal":       "phys-reyes",
    "Gila":        "phys-reyes",
    "Mohave":      "phys-anderson",
    "Yavapai":     "phys-anderson",
    "Graham":      "phys-anderson",
}
MARICOPA_PHYSICIANS = ["phys-patel", "phys-nakagawa", "phys-okafor"]

COUNTY_TO_VET: dict[str, str] = {
    "Pima":        "vet-cho",
    "Santa Cruz":  "vet-cho",
    "Cochise":     "vet-becker",
    "Graham":      "vet-becker",
    "Greenlee":    "vet-becker",
    "Apache":      "vet-becker",
    "Navajo":      "vet-becker",
    "Coconino":    "vet-cho",
    "Yavapai":     "vet-cho",
    "Mohave":      "vet-cho",
    "Yuma":        "vet-kim",
    "La Paz":      "vet-kim",
    "Gila":        "vet-kim",
}
# Pinal and Maricopa are high-volume — split across 2 vets via household_id hash
PINAL_VETS    = ["vet-kim", "vet-rivera"]
MARICOPA_VETS = ["vet-rivera", "vet-kim"]


def _route_physician(county_name: str, household_id: str) -> str:
    if county_name == "Maricopa":
        h = sum(map(ord, household_id)) % len(MARICOPA_PHYSICIANS)
        return MARICOPA_PHYSICIANS[h]
    return COUNTY_TO_PHYSICIAN.get(county_name, "phys-reyes")


def _route_vet(county_name: str, household_id: str) -> str:
    if county_name == "Maricopa":
        h = sum(map(ord, household_id)) % len(MARICOPA_VETS)
        return MARICOPA_VETS[h]
    if county_name == "Pinal":
        h = sum(map(ord, household_id)) % len(PINAL_VETS)
        return PINAL_VETS[h]
    return COUNTY_TO_VET.get(county_name, "vet-cho")


def main() -> None:
    households = json.load(open(DATA / "households.json"))["households"]

    patient_assignments: list[dict] = []
    physician_panels: dict[str, list[str]] = {p["id"]: [] for p in PHYSICIANS}
    vet_panels:       dict[str, list[str]] = {v["id"]: [] for v in VETERINARIANS}

    for hh in households:
        county = (hh.get("county") or {}).get("name", "Pima")
        hh_id = hh.get("household_id", "")
        physician_id = _route_physician(county, hh_id)
        vet_id       = _route_vet(county, hh_id)

        for human in hh.get("humans", []) or []:
            patient_assignments.append({
                "patient_id":   human["id"],
                "patient_kind": "human",
                "name":         _human_display_name(human),
                "household_id": hh["household_id"],
                "county":       county,
                "provider_id":  physician_id,
            })
            physician_panels[physician_id].append(human["id"])

        for animal in hh.get("animals", []) or []:
            patient_assignments.append({
                "patient_id":   animal["id"],
                "patient_kind": "animal",
                "name":         animal.get("name", "[unnamed]"),
                "species":      _animal_species(animal),
                "household_id": hh["household_id"],
                "county":       county,
                "provider_id":  vet_id,
            })
            vet_panels[vet_id].append(animal["id"])

    payload = {
        "_metadata": {
            "schema_version": "0.1.0",
            "n_assignments": len(patient_assignments),
            "n_physician_panels": len(physician_panels),
            "n_vet_panels": len(vet_panels),
            "_caveat": ("Demo authentication only. Production uses SMART-on-FHIR + "
                        "ADHS SSO + tribal-IRB-issued credentials with patient-level "
                        "access controls enforced at the API layer."),
        },
        "physicians":     PHYSICIANS,
        "veterinarians":  VETERINARIANS,
        "public_health":  PUBLIC_HEALTH,
        "patient_assignments": patient_assignments,
        "panels": {
            "physicians":   {pid: panel for pid, panel in physician_panels.items()},
            "veterinarians": {pid: panel for pid, panel in vet_panels.items()},
        },
    }

    out = DATA / "providers.json"
    out.write_text(json.dumps(payload, indent=2))

    # Console summary
    print(f"Wrote {out}")
    print(f"  total assignments: {len(patient_assignments)}")
    for p in PHYSICIANS:
        print(f"  {p['name']:25s} ({p['facility']:36s}): {len(physician_panels[p['id']]):3d} patients")
    for v in VETERINARIANS:
        print(f"  {v['name']:25s} ({v['facility']:36s}): {len(vet_panels[v['id']]):3d} patients")


def _human_display_name(human: dict) -> str:
    name = (human.get("name") or [{}])[0]
    given = " ".join(name.get("given") or [])
    family = name.get("family") or ""
    return f"{given} {family}".strip() or human.get("id", "[unnamed]")


def _animal_species(animal: dict) -> str:
    s = animal.get("species") or {}
    if isinstance(s, dict):
        return s.get("display") or s.get("code") or "animal"
    return str(s)


if __name__ == "__main__":
    main()
