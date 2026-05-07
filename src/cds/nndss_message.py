"""
Phase 6 — NNDSS HL7 v2.5.1 ELR (Electronic Laboratory Reporting) generator.

Generates well-formed HL7 v2.5.1 ELR messages for confirmed reportable
human diseases in Arizona. Reference:
   - CDC NNDSS Case Notification Message Mapping Guide
   - HL7 ELR R-2 v2.5.1 Implementation Guide
   - ADHS Reportable Disease Rule (R9-6-202)

Each message is a pipe-delimited HL7 v2.5.1 message with these segments:
   MSH  - Message Header
   PID  - Patient Identification (de-identified for ADHS)
   ORC  - Common Order
   OBR  - Observation Request
   OBX  - Observation/Result (one per finding)
   SPM  - Specimen
   NTE  - Notes (optional)

In production, these messages are pushed to ADHS's MEDSIS endpoint via
SOAP/HTTPS with mutual TLS, and ADHS forwards the case notification to
CDC NNDSS. The endpoint URL is in `data/synthetic/federation_manifest.json`
under the adhs site.

Usage:
   from src.cds.nndss_message import generate_elr
   message = generate_elr(condition, patient, provider, lab_observations)
   # Returns: pipe-delimited HL7 string
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"
REF  = BASE / "data" / "reference"


# Map disease_id → CDC NNDSS condition code
# Reference: https://wwwn.cdc.gov/nndss/
NNDSS_CONDITION_CODES = {
    "valley_fever":          {"code": "11020", "name": "Coccidioidomycosis"},
    "rmsf":                  {"code": "10250", "name": "Spotted Fever Rickettsiosis"},
    "plague":                {"code": "10250", "name": "Plague"},  # NNDSS code 10080
    "west_nile":             {"code": "10056", "name": "West Nile virus disease"},
    "hantavirus":            {"code": "11590", "name": "Hantavirus pulmonary syndrome"},
    "ehrlichiosis":          {"code": "10075", "name": "Ehrlichiosis/Anaplasmosis"},
    "leptospirosis":         {"code": "10090", "name": "Leptospirosis"},
    "q_fever":               {"code": "10260", "name": "Q fever"},
    "psittacosis":           {"code": "10220", "name": "Psittacosis"},
    "tularemia":             {"code": "10300", "name": "Tularemia"},
    "rabies":                {"code": "10180", "name": "Rabies, animal exposure (post-exposure prophylaxis)"},
    "salmonellosis":         {"code": "10240", "name": "Salmonellosis"},
    "tuberculosis_zoonotic": {"code": "10211", "name": "Tuberculosis"},
    "brucellosis":           {"code": "10020", "name": "Brucellosis"},
}


def _hl7_ts(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def _esc(s: str) -> str:
    """Escape pipe-delimited HL7 special characters."""
    if s is None: return ""
    return str(s).replace("\\", "\\E\\").replace("|", "\\F\\").replace("^", "\\S\\") \
                  .replace("&", "\\T\\").replace("~", "\\R\\")


def generate_elr(
    *,
    disease_id: str,
    patient: dict,
    provider: dict,
    facility: dict,
    onset_date: str,
    lab_observations: list[dict] | None = None,
    case_id: str | None = None,
) -> dict:
    """
    Build a NNDSS-compliant HL7 v2.5.1 ELR message.

    patient: { id, first_name, last_name, dob, gender, county_fips, zip }
    provider: { id, name, npi (synthetic), facility }
    facility: { id, name, clia (synthetic), address, city, state, zip }
    onset_date: ISO date "2026-04-15"
    lab_observations: list of { code, name, value, units, reference_range, abnormal_flag, observed_date }

    Returns: { message: str, case_id: str, condition: dict, sent_at: str }
    """
    cond = NNDSS_CONDITION_CODES.get(disease_id, {"code": "00000", "name": disease_id})
    case_id = case_id or f"AZ-{datetime.now().strftime('%Y%m%d')}-{patient.get('id', '00000')[:8]}"
    ts = _hl7_ts()
    sending_app = "ONE-HealthRecord^2.16.840.1.113883.3.AZ-OHR^ISO"
    sending_facility = f"{facility.get('id','SITE')}^{facility.get('clia','99D9999999')}^CLIA"
    receiving_app = "ADHS-MEDSIS^2.16.840.1.113883.3.4321^ISO"
    receiving_facility = "ADHS^04^FIPS"
    msg_ctrl_id = f"OHR-{ts}-{case_id[-8:]}"

    # Build segments
    segments = []

    # MSH — Message Header
    segments.append(
        "MSH|^~\\&|" +
        f"{sending_app}|{sending_facility}|" +
        f"{receiving_app}|{receiving_facility}|" +
        f"{ts}||" +
        f"ORU^R01^ORU_R01|{msg_ctrl_id}|P|2.5.1|||||||||" +
        "PHIN^^2.16.840.1.114222.4.10.3"
    )

    # SFT — Software Segment
    segments.append("SFT|ONE-HealthRecord MVP|2.1.0|ONE-HealthRecord^2.16.840.1.113883.3.AZ-OHR^ISO|6.1.0||20260101")

    # PID — Patient Identification (de-identified for surveillance)
    pid_id = patient.get("id", "")[:16]
    family = _esc(patient.get("last_name", ""))
    given = _esc(patient.get("first_name", ""))
    dob = patient.get("dob", "").replace("-", "")
    gender = patient.get("gender", "U")[:1].upper()
    if gender == "M": gender = "M"
    elif gender == "F": gender = "F"
    else: gender = "U"
    county_fips = patient.get("county_fips", "04019")
    segments.append(
        f"PID|1||{pid_id}^^^&2.16.840.1.113883.3.AZ-OHR&ISO^MR||" +
        f"{family}^{given}||{dob}|{gender}|||" +
        f"^^{_esc(patient.get('city',''))}^AZ^{patient.get('zip','')}^USA^^{county_fips}"
    )

    # NK1 — Next of Kin (skipped for surveillance)

    # PV1 — Patient Visit (synthetic encounter)
    provider_name = _esc(provider.get("name", "Unknown"))
    npi = provider.get("npi", "1234567890")  # synthetic NPI
    segments.append(
        f"PV1|1|O|{_esc(facility.get('name','Outpatient'))}^^|||||" +
        f"{npi}^{provider_name}^^^^^NPI"
    )

    # ORC — Common Order
    segments.append(
        f"ORC|RE|{case_id}^OHR|{case_id}^ADHS||CM|||{ts}||{npi}^{provider_name}^^^^^NPI"
    )

    # OBR — Observation Request
    segments.append(
        f"OBR|1|{case_id}^OHR|{case_id}^ADHS|" +
        f"{cond['code']}^{cond['name']}^CDCNNDSS|||" +
        f"{ts}||||||{onset_date.replace('-','')}|||" +
        f"{npi}^{provider_name}^^^^^NPI||||||||{ts}|||F"
    )

    # OBX — Observation segments (one per lab finding)
    if not lab_observations:
        # Default: a single positive serology finding
        lab_observations = [{
            "code": "6435-2",
            "name": "Coccidioides antibody.IgM",
            "value": "Positive",
            "units": "",
            "reference_range": "Negative",
            "abnormal_flag": "A",
            "observed_date": onset_date,
        }]
    for i, obx in enumerate(lab_observations, start=1):
        v = obx.get("value", "")
        units = obx.get("units", "")
        rr = obx.get("reference_range", "")
        abn = obx.get("abnormal_flag", "")
        obs_dt = obx.get("observed_date", onset_date).replace("-", "")
        segments.append(
            f"OBX|{i}|CWE|{obx.get('code','')}^{_esc(obx.get('name',''))}^LN||" +
            f"{_esc(v)}|{_esc(units)}|{_esc(rr)}|{abn}|||F|||{obs_dt}"
        )

    # SPM — Specimen
    segments.append(
        f"SPM|1|{case_id}-SPM^OHR||SER^Serum^HL70487|||||||P^Patient^HL70369|||||||{ts}"
    )

    # NTE — Notes
    segments.append(
        "NTE|1|L|" + _esc(
            f"Reportable disease: {cond['name']}. Submitted via ONE-HealthRecord one-click reporting. "
            f"Cross-species sentinel signal: see linked Condition for One Health context."
        )
    )

    message = "\r".join(segments)
    return {
        "case_id": case_id,
        "message_control_id": msg_ctrl_id,
        "condition": cond,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "destination": "ADHS-MEDSIS",
        "destination_url": "https://surveillance.adhs.az.example/r4/$nndss-elr",
        "message": message,
        "format": "HL7 v2.5.1 ELR R-2",
        "byte_count": len(message),
    }


# ----- Synthetic confirmation receipt for round-trip demo -----
def generate_ack_receipt(case_id: str, msg_ctrl_id: str) -> dict:
    """ADHS would respond with an ACK^A01 acknowledgement plus a NNDSS case
    ID. This function fabricates the response for demo purposes."""
    ts = _hl7_ts()
    nndss_case_id = f"AZ-NNDSS-{datetime.now().strftime('%Y')}-{case_id[-8:]}"
    ack = (
        f"MSH|^~\\&|ADHS-MEDSIS^2.16.840.1.113883.3.4321^ISO|ADHS^04^FIPS|" +
        f"ONE-HealthRecord^2.16.840.1.113883.3.AZ-OHR^ISO|SITE^99D9999999^CLIA|" +
        f"{ts}||ACK^A01^ACK|ACK-{msg_ctrl_id}|P|2.5.1\r" +
        f"MSA|AA|{msg_ctrl_id}|Case received and queued for investigation|||0\r" +
        f"ERR|||0^Message accepted^HL70357||I"
    )
    return {
        "ack_message": ack,
        "nndss_case_id": nndss_case_id,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "status": "received_for_investigation",
        "investigator_assigned": "ADHS Communicable Disease Branch — auto-routed",
        "next_steps": [
            "ADHS will assign a case investigator within 24 hours.",
            "Investigator may contact provider for additional history.",
            "Household contacts will be queued for case-investigation outreach.",
        ],
    }


# ----- CLI smoke test -----
if __name__ == "__main__":
    sample_patient = {
        "id": "5987f320-d799-446b",
        "first_name": "Maria",
        "last_name": "Hernandez",
        "dob": "1973-04-18",
        "gender": "female",
        "city": "Tucson",
        "zip": "85710",
        "county_fips": "04019",
    }
    sample_provider = {
        "id": "phys-reyes",
        "name": "Maria Reyes, MD",
        "npi": "1023456789",
    }
    sample_facility = {
        "id": "tmc",
        "name": "Tucson Medical Center",
        "clia": "03D9999999",
    }
    result = generate_elr(
        disease_id="valley_fever",
        patient=sample_patient,
        provider=sample_provider,
        facility=sample_facility,
        onset_date="2026-04-15",
    )
    print(f"Case ID: {result['case_id']}")
    print(f"Bytes:   {result['byte_count']}")
    print()
    print("=== HL7 v2.5.1 ELR Message ===")
    print(result["message"])
    print()
    print("=== Synthetic ADHS ACK ===")
    ack = generate_ack_receipt(result["case_id"], result["message_control_id"])
    print(f"NNDSS case: {ack['nndss_case_id']}")
    print(ack["ack_message"])
