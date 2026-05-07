"""
FHIR R4 Bundle builder.

Converts the structured Entity stream from entity_extractor into a
FHIR-compliant Bundle. Each resource carries provenance metadata
identifying it as machine-authored, with confidence scores and
source-text spans for verification.

Resources emitted:
    Patient                — from demographics (age + gender)
    Condition              — from non-negated condition entities
    Observation (symptom)  — from non-negated symptom entities
    Observation (vital)    — from vital sign entities
    Observation (exposure) — from non-negated exposure entities
    MedicationStatement    — from medication entities
    Provenance             — wraps the whole bundle

Negated entities are emitted as Observations with valueBoolean=false
(rather than dropped) — preserves the negative finding for downstream
analytics. Hedged entities get clinicalStatus="provisional".
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from .entity_extractor import Entity


# ---------------------------------------------------------------------------
def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _provenance_extension(entity: Entity) -> list[dict]:
    """Provenance/confidence extensions attached to every machine-authored resource."""
    return [
        {"url": "http://onehealthrecord.org/authorship",      "valueString": "machine-authored"},
        {"url": "http://onehealthrecord.org/confidence",      "valueDecimal": round(entity.confidence, 3)},
        {"url": "http://onehealthrecord.org/source-text",     "valueString": entity.text},
        {"url": "http://onehealthrecord.org/source-span",     "valueString": f"{entity.char_start},{entity.char_end}"},
        {"url": "http://onehealthrecord.org/source-phase",    "valueString": entity.phase},
    ]


# ---------------------------------------------------------------------------
def _patient_from_demographics(demos: list[Entity], household_id: str | None) -> dict:
    age, gender = None, "unknown"
    for e in demos:
        if "age_years" in e.attributes and age is None:
            age = e.attributes["age_years"]
        if "gender" in e.attributes and gender == "unknown":
            gender = e.attributes["gender"]
    pid = _new_id()
    today = date.today()
    dob = (today.replace(year=today.year - age).isoformat()) if age else None
    res: dict = {
        "resourceType": "Patient",
        "id": pid,
        "meta": {"profile": ["http://onehealthrecord.org/StructureDefinition/HumanPatient"]},
        "gender": gender,
    }
    if dob:
        res["birthDate"] = dob
    if household_id:
        res["extension"] = [{"url": "http://onehealthrecord.org/household-id",
                             "valueString": household_id}]
    return res


def _condition(e: Entity, patient_ref: str) -> dict:
    code = e.codes or [{"system": "urn:unknown", "code": "unknown", "display": e.text}]
    clinical_status = "provisional" if e.uncertain else "active"
    verification_status = "differential" if e.uncertain else "confirmed"
    return {
        "resourceType": "Condition",
        "id": _new_id(),
        "subject": {"reference": patient_ref},
        "code": {"coding": code, "text": e.attributes.get("display", e.text)},
        "clinicalStatus":     {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",     "code": clinical_status}]},
        "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",   "code": verification_status}]},
        "recordedDate": _now_iso(),
        "extension": _provenance_extension(e),
    }


def _observation_symptom(e: Entity, patient_ref: str) -> dict:
    code = e.codes or [{"system": "urn:unknown", "code": "unknown", "display": e.text}]
    return {
        "resourceType": "Observation",
        "id": _new_id(),
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": "exam", "display": "Exam"}]}],
        "code": {"coding": code, "text": e.attributes.get("display", e.text)},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": _now_iso(),
        "valueBoolean": not e.negated,
        "extension": _provenance_extension(e),
    }


def _observation_vital(e: Entity, patient_ref: str) -> dict:
    vt = e.attributes["vital_type"]
    loinc = {
        "blood_pressure":  ("85354-9", "Blood pressure panel"),
        "heart_rate":      ("8867-4",  "Heart rate"),
        "respiratory_rate":("9279-1",  "Respiratory rate"),
        "temperature_f":   ("8310-5",  "Body temperature"),
        "spo2":            ("59408-5", "Oxygen saturation"),
    }[vt]
    obs: dict = {
        "resourceType": "Observation",
        "id": _new_id(),
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": "vital-signs", "display": "Vital Signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": loinc[0], "display": loinc[1]}]},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": _now_iso(),
        "extension": _provenance_extension(e),
    }
    if vt == "blood_pressure":
        obs["component"] = [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6",
                                  "display": "Systolic BP"}]},
             "valueQuantity": {"value": e.attributes["systolic"], "unit": "mmHg",
                               "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4",
                                  "display": "Diastolic BP"}]},
             "valueQuantity": {"value": e.attributes["diastolic"], "unit": "mmHg",
                               "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}},
        ]
    else:
        ucum = {"bpm": "/min", "/min": "/min", "F": "[degF]", "%": "%"}.get(e.attributes["unit"], e.attributes["unit"])
        obs["valueQuantity"] = {"value": e.attributes["value"],
                                "unit": e.attributes["unit"],
                                "system": "http://unitsofmeasure.org",
                                "code": ucum}
    return obs


def _observation_exposure(e: Entity, patient_ref: str) -> dict:
    return {
        "resourceType": "Observation",
        "id": _new_id(),
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": "social-history", "display": "Social History"}]}],
        "code": {"coding": [{"system": "http://onehealthrecord.org/exposure",
                             "code": e.attributes["exposure_type"],
                             "display": e.attributes["exposure_type"].replace("_", " ").title()}]},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": _now_iso(),
        "valueBoolean": not e.negated,
        "extension": _provenance_extension(e),
    }


def _medication_statement(e: Entity, patient_ref: str) -> dict:
    code = e.codes or [{"system": "urn:unknown", "code": "unknown", "display": e.text}]
    return {
        "resourceType": "MedicationStatement",
        "id": _new_id(),
        "status": "active",
        "medicationCodeableConcept": {"coding": code, "text": e.attributes.get("display", e.text)},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": _now_iso(),
        "extension": _provenance_extension(e),
    }


def _provenance(bundle_id: str, raw_text: str, n_resources: int) -> dict:
    return {
        "resourceType": "Provenance",
        "id": _new_id(),
        "target": [{"reference": f"Bundle/{bundle_id}"}],
        "recorded": _now_iso(),
        "agent": [{
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                 "code": "author"}]},
            "who": {"display": "ONE-HealthRecord Machine Authorship Engine v0.1"},
        }],
        "activity": {"coding": [{"system": "http://onehealthrecord.org/activity",
                                 "code": "machine-authored",
                                 "display": "Record machine-authored from clinician dictation"}]},
        "extension": [
            {"url": "http://onehealthrecord.org/source-dictation",
             "valueString": raw_text[:8000]},  # cap at 8k for storage
            {"url": "http://onehealthrecord.org/n-resources",
             "valueInteger": n_resources},
            {"url": "http://onehealthrecord.org/engine-version",
             "valueString": "0.1.0-rule-based"},
        ],
    }


# ---------------------------------------------------------------------------
def build_bundle(entities: list[Entity], raw_text: str,
                 *, household_id: str | None = None,
                 patient_ref: str | None = None) -> dict[str, Any]:
    """Convert entity list to a FHIR R4 Bundle.

    If patient_ref is provided (e.g., we're appending to an existing patient
    in our database), no new Patient resource is created and that ref is used
    as subject. Otherwise a Patient resource is created from demographic
    entities and used as subject.
    """
    bundle_id = _new_id()
    entries: list[dict] = []

    demographics = [e for e in entities if e.kind == "Demographic"]
    if patient_ref is None:
        patient = _patient_from_demographics(demographics, household_id)
        patient_ref = f"Patient/{patient['id']}"
        entries.append({"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient})

    for e in entities:
        try:
            if e.kind == "Condition":
                entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                                "resource": _condition(e, patient_ref)})
            elif e.kind == "Symptom":
                entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                                "resource": _observation_symptom(e, patient_ref)})
            elif e.kind == "Vital":
                entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                                "resource": _observation_vital(e, patient_ref)})
            elif e.kind == "Exposure":
                entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                                "resource": _observation_exposure(e, patient_ref)})
            elif e.kind == "Medication":
                entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                                "resource": _medication_statement(e, patient_ref)})
        except Exception as exc:
            # Skip malformed entities rather than crash the bundle.
            entries.append({"fullUrl": f"urn:uuid:{_new_id()}",
                            "resource": {"resourceType": "OperationOutcome",
                                          "issue": [{"severity": "warning",
                                                     "diagnostics": f"Failed to convert {e.kind} '{e.text}': {exc}"}]}})

    prov = _provenance(bundle_id, raw_text, len(entries))
    entries.append({"fullUrl": f"urn:uuid:{prov['id']}", "resource": prov})

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "collection",
        "timestamp": _now_iso(),
        "entry": entries,
        "meta": {"profile": ["http://onehealthrecord.org/StructureDefinition/MachineAuthoredEncounterBundle"]},
    }


# ---------------------------------------------------------------------------
def authorship_summary(bundle: dict) -> dict:
    """Compact summary used by the UI / API for human-readable display."""
    counts: dict[str, int] = {}
    confidence_total, confidence_n = 0.0, 0
    for entry in bundle["entry"]:
        rt = entry["resource"]["resourceType"]
        counts[rt] = counts.get(rt, 0) + 1
        for ext in entry["resource"].get("extension", []) or []:
            if ext.get("url") == "http://onehealthrecord.org/confidence":
                confidence_total += ext["valueDecimal"]
                confidence_n += 1
    return {
        "bundle_id": bundle["id"],
        "n_resources": len(bundle["entry"]),
        "resource_counts": counts,
        "mean_confidence": round(confidence_total / max(1, confidence_n), 3),
        "timestamp": bundle["timestamp"],
    }


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json as _json
    from .entity_extractor import extract_entities

    sample = (
        "Fifty-six-year-old male, known hypertensive and diabetic with ESRD on "
        "maintenance hemodialysis, presenting with difficulty breathing times one "
        "week and bilateral leg swelling times one month. "
        "On examination, BP 168/94, HR 102, RR 22, SpO2 91% on room air. "
        "No fever, no cough. "
        "Patient lives in Pinal County and was recently hiking; denies tick exposure. "
        "Assessment: acute fluid overload, possible coccidioidomycosis. "
        "Plan: start fluconazole 200 mg, admit, dialysis in AM."
    )
    _, ents = extract_entities(sample)
    bundle = build_bundle(ents, sample, household_id="HH-DEMO")
    print(_json.dumps(authorship_summary(bundle), indent=2))
    print(f"\nFirst few resource types: {[e['resource']['resourceType'] for e in bundle['entry'][:6]]}")
