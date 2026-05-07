"""
Phase 6 — USDA APHIS VSPS animal-disease reporting generator.

Generates structured payloads equivalent to USDA APHIS VS Form 1-7
('Report of Veterinary Activity') for confirmed reportable animal diseases.

Reference:
  - USDA APHIS Veterinary Services Process Streamlining (VSPS)
  - Arizona Department of Agriculture (ADA) reportable animal disease list
  - WOAH (formerly OIE) Terrestrial Animal Health Code

Unlike NNDSS (HL7 v2.5.1 ELR), VSPS does NOT use HL7 messaging. APHIS
accepts JSON payloads via REST through the VSPS API, with paper VS Form 1-7
as the legacy fallback. Arizona ADA mirrors APHIS for federal reportables
and adds state-specific reportables (e.g., bovine TB always reports to ADA
even when APHIS doesn't require it).

Usage:
   from src.cds.vsps_message import generate_vsps_report
   payload = generate_vsps_report(disease_id, animal, vet, ...)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]


# Map disease_id → USDA APHIS reportable status + WOAH code + AZ ADA state-reportable status
APHIS_REPORTABLE = {
    "rmsf":                  {"federal_reportable": False, "az_state_reportable": True,  "woah_code": None,           "name": "Rocky Mountain Spotted Fever (canine)"},
    "plague":                {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B158",         "name": "Plague (Yersinia pestis) — animal case"},
    "west_nile":             {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "WNV",          "name": "West Nile virus disease — equine/avian"},
    "ehrlichiosis":          {"federal_reportable": False, "az_state_reportable": True,  "woah_code": None,           "name": "Canine Ehrlichiosis"},
    "leptospirosis":         {"federal_reportable": False, "az_state_reportable": True,  "woah_code": "B051",         "name": "Canine Leptospirosis"},
    "q_fever":               {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B106",         "name": "Q Fever (Coxiella burnetii) — caprine/ovine"},
    "psittacosis":           {"federal_reportable": False, "az_state_reportable": True,  "woah_code": "B260",         "name": "Avian Chlamydiosis (Chlamydia psittaci)"},
    "tularemia":             {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B258",         "name": "Tularemia — feline"},
    "rabies":                {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B058",         "name": "Rabies — animal confirmed/suspect"},
    "salmonellosis":         {"federal_reportable": False, "az_state_reportable": False, "woah_code": None,           "name": "Salmonella shedding — backyard poultry/reptile"},
    "tuberculosis_zoonotic": {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B105",         "name": "Bovine Tuberculosis (Mycobacterium bovis)"},
    "brucellosis":           {"federal_reportable": True,  "az_state_reportable": True,  "woah_code": "B103",         "name": "Brucellosis (caprine/bovine)"},
    "valley_fever":          {"federal_reportable": False, "az_state_reportable": False, "woah_code": None,           "name": "Coccidioidomycosis (canine/feline) — informational"},
    "hantavirus":            {"federal_reportable": False, "az_state_reportable": True,  "woah_code": None,           "name": "Hantavirus (rodent surveillance signal)"},
}


def generate_vsps_report(
    *,
    disease_id: str,
    animal: dict,
    vet: dict,
    clinic: dict,
    onset_date: str,
    diagnostic_findings: list[dict] | None = None,
    case_id: str | None = None,
) -> dict:
    """
    Build an APHIS VSPS report payload.

    animal:  { id, name, species, breed, sex, dob, owner_name (optional, restricted) }
    vet:     { id, name, license_number, phone }
    clinic:  { id, name, premises_id (USDA premises ID, synthetic), address }
    diagnostic_findings: list of { test, result, performed_by, performed_date }

    Returns: { case_id, payload, destinations, sent_at }
    """
    meta = APHIS_REPORTABLE.get(disease_id, {"federal_reportable": False, "az_state_reportable": False,
                                              "name": disease_id, "woah_code": None})
    case_id = case_id or f"AZ-VS-{datetime.now().strftime('%Y%m%d')}-{animal.get('id','000000')[:8]}"

    if not diagnostic_findings:
        diagnostic_findings = [{
            "test": "PCR",
            "result": "Positive",
            "performed_by": "IDEXX Reference Laboratories",
            "performed_date": onset_date,
        }]

    destinations = []
    if meta["federal_reportable"]:
        destinations.append({
            "agency": "USDA APHIS Veterinary Services",
            "endpoint": "https://vsps.aphis.usda.example/r4/$report-disease",
            "form": "VS Form 1-7 (Report of Veterinary Activity) — JSON equivalent",
            "timeline": "Required within 48 hours of confirmed diagnosis (high-impact reportables: 24 hours)",
        })
    if meta["az_state_reportable"]:
        destinations.append({
            "agency": "Arizona Department of Agriculture, Animal Services Division",
            "endpoint": "https://reportable.azda.az.example/v1/animal-disease",
            "form": "ADA-AD-101 — JSON",
            "timeline": "Required within 24 hours for state reportables",
        })
    # Cross-species link: human-side reporting to ADHS happens via NNDSS in parallel
    if disease_id in {"plague", "west_nile", "rabies", "q_fever", "tularemia", "brucellosis"}:
        destinations.append({
            "agency": "Arizona Department of Health Services (cross-species notification)",
            "endpoint": "https://surveillance.adhs.az.example/r4/$cross-species-zoonotic",
            "form": "ONE-HealthRecord cross-species sentinel notification",
            "timeline": "Real-time notification to alert ADHS that an animal sentinel signal has fired in this county",
        })

    payload = {
        "report_metadata": {
            "case_id": case_id,
            "report_type": "Confirmed reportable animal disease",
            "submission_date": datetime.now(timezone.utc).isoformat(),
            "submitting_system": "ONE-HealthRecord (synthetic)",
            "submitting_system_version": "2.1.0",
            "submission_method": "REST POST application/json",
        },
        "disease": {
            "common_name":              meta["name"],
            "internal_disease_id":      disease_id,
            "woah_code":                meta["woah_code"],
            "is_federal_reportable":    meta["federal_reportable"],
            "is_az_state_reportable":   meta["az_state_reportable"],
        },
        "animal": {
            "animal_id":  animal.get("id", ""),
            "name":       animal.get("name", ""),
            "species":    (animal.get("species") or {}).get("display") or animal.get("species", ""),
            "breed":      animal.get("breed", ""),
            "sex":        animal.get("sex", ""),
            "date_of_birth": animal.get("dob", ""),
            "household_id": animal.get("household_id", ""),    # for the cross-species linkage
            "premises_id": clinic.get("premises_id", "AZ-PREM-SYNTHETIC"),
        },
        "owner": {
            # Owner identifying information is restricted per VSPS guidance —
            # we send only what's required for the zoonotic-disease investigation.
            "owner_residence_county_fips": animal.get("owner_county_fips", ""),
            "owner_residence_zip":         animal.get("owner_zip", ""),
            "owner_consent_to_contact":    True,    # would be captured at intake
        },
        "veterinarian": {
            "vet_id":         vet.get("id", ""),
            "name":           vet.get("name", ""),
            "license_number": vet.get("license_number", "AZ-VET-SYNTHETIC"),
            "license_state":  "AZ",
            "phone":          vet.get("phone", ""),
            "facility":       clinic.get("name", ""),
        },
        "clinic": {
            "clinic_id":   clinic.get("id", ""),
            "name":        clinic.get("name", ""),
            "address":     clinic.get("address", ""),
            "premises_id": clinic.get("premises_id", "AZ-PREM-SYNTHETIC"),
        },
        "clinical_information": {
            "onset_date":    onset_date,
            "report_date":   datetime.now(timezone.utc).date().isoformat(),
            "case_status":   "confirmed",
            "outcome":       "under_treatment",
            "exposure_history": (
                "Outdoor exposure consistent with disease's typical environmental "
                "or vector-borne transmission route."
            ),
        },
        "diagnostic_findings": diagnostic_findings,
        "one_health_context": {
            "linked_human_household_id": animal.get("household_id", ""),
            "cross_species_sentinel": True,
            "sentinel_direction": "animal_to_human",
            "rationale": (
                "Animal case reported as sentinel signal under Arizona's One "
                "Health Surveillance Program. ADHS will be notified via "
                "parallel cross-species notification feed for any potential "
                "human-side prophylactic or surveillance action."
            ),
        },
        "destinations": destinations,
    }

    return {
        "case_id": case_id,
        "destinations": destinations,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "format": "USDA APHIS VSPS JSON (VS Form 1-7 equivalent)",
        "byte_count": len(json.dumps(payload)),
    }


def generate_aphis_ack(case_id: str) -> dict:
    """Synthetic APHIS acknowledgement."""
    aphis_case_id = f"USDA-{datetime.now().strftime('%Y')}-AZ-{case_id[-8:]}"
    return {
        "ack_id": f"ACK-{case_id}",
        "received_at": datetime.now(timezone.utc).isoformat(),
        "aphis_case_id": aphis_case_id,
        "status": "received_for_review",
        "next_steps": [
            "USDA APHIS Region 7 Veterinary Services will review within 24 hours.",
            "If federally reportable, a USDA Veterinary Medical Officer may contact the practice.",
            "Premises ID flagged for follow-up surveillance if needed.",
        ],
    }


if __name__ == "__main__":
    sample_animal = {
        "id": "anim-rocco-001",
        "name": "Rocco",
        "species": {"display": "Canis lupus familiaris (dog)"},
        "breed": "Border Collie mix",
        "sex": "MN",
        "dob": "2019-03-12",
        "household_id": "HH-AZ-PIMA-001",
        "owner_county_fips": "04019",
    }
    sample_vet = {
        "id": "vet-cho",
        "name": "Hannah Cho, DVM",
        "license_number": "AZ-VET-12345",
        "phone": "+1-520-555-0123",
    }
    sample_clinic = {
        "id": "vet_tucson",
        "name": "Tucson Companion-Animal Vet",
        "address": "1234 E Grant Rd, Tucson, AZ 85710",
        "premises_id": "AZ-PREM-04019-0042",
    }
    result = generate_vsps_report(
        disease_id="plague",
        animal=sample_animal,
        vet=sample_vet,
        clinic=sample_clinic,
        onset_date="2026-04-12",
    )
    print(f"Case ID: {result['case_id']}")
    print(f"Bytes:   {result['byte_count']}")
    print(f"Destinations: {len(result['destinations'])}")
    for d in result["destinations"]:
        print(f"  → {d['agency']}")
    print()
    print(json.dumps(result["payload"], indent=2)[:1500])
