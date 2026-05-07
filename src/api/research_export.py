"""
ONE-HealthRecord research export API.

Read-only FHIR-compatible endpoints over the synthetic demo bundle.
Designed as the SMART-on-FHIR scaffold referenced in the architecture diagram.

This module is intentionally minimal — it shows the API surface that a
production deployment would expose, runs locally for any reviewer who
installs Python, and integrates with the same data files the browser
demo consumes.

Run:
    pip install fastapi uvicorn
    python -m uvicorn src.api.research_export:app --reload
    open http://127.0.0.1:8000/docs

Endpoints:
    GET  /Patient                        list of synthetic Patient resources
    GET  /Patient/{id}                   single Patient
    GET  /AnimalPatient                  list of veterinary patients (custom)
    GET  /Condition                      list of Conditions (filter by ?subject=)
    GET  /Bundle/encounter               build a fresh Bundle from a free-text dictation
    GET  /OneHealth/clusters             cross-species clusters from the knowledge graph
    GET  /Surveillance/alerts            sentinel alerts (with DP-noised counts)
    GET  /Surveillance/alerts/{kind}     alerts filtered by detector kind

All payloads are FHIR R4-flavoured. The custom AnimalPatient profile and the
provenance/confidence/source-span extensions are documented in
data/reference/profiles/ (production deployment publishes these via HL7).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.nlp.entity_extractor import extract_entities
from src.nlp.fhir_builder import build_bundle, authorship_summary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"


def _load() -> dict[str, Any]:
    """Lazy-load the synthetic data on first request, reload on file change."""
    bundle_path = SYNTH_DIR / "demo_bundle.json"
    if not bundle_path.exists():
        raise RuntimeError("demo_bundle.json missing — run "
                           "`python -m src.data_generation.bundle_for_demo` first.")
    return json.loads(bundle_path.read_text())


app = FastAPI(
    title="ONE-HealthRecord Research Export API",
    version="0.1.0",
    description=("Read-only FHIR-flavoured access to the synthetic ONE-HealthRecord demo dataset. "
                 "All data is synthetic; no real PHI."),
)
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


# ---------------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    return {
        "service": "ONE-HealthRecord Research Export",
        "version": "0.1.0",
        "is_synthetic": True,
        "endpoints": [
            "/Patient", "/Patient/{id}",
            "/AnimalPatient",
            "/Condition?subject=<ref>",
            "/Bundle/encounter?dictation=<text>",
            "/OneHealth/clusters",
            "/Surveillance/alerts",
            "/Surveillance/alerts/{kind}",
        ],
    }


@app.get("/Patient")
def list_patients(county: str | None = Query(None, description="Filter by county name")) -> list[dict]:
    data = _load()
    out = []
    for hh in data["households"]["households"]:
        if county and hh["county"]["name"].lower() != county.lower():
            continue
        out.extend(hh["humans"])
    return out


@app.get("/Patient/{patient_id}")
def get_patient(patient_id: str) -> dict:
    for hh in _load()["households"]["households"]:
        for p in hh["humans"]:
            if p["id"] == patient_id:
                return p
    raise HTTPException(404, f"Patient {patient_id} not found")


@app.get("/AnimalPatient")
def list_animals(species: str | None = Query(None, description="Species code: dog, cat")) -> list[dict]:
    data = _load()
    out = []
    for hh in data["households"]["households"]:
        for a in hh["animals"]:
            if species and a["species"]["code"] != species:
                continue
            out.append(a)
    return out


@app.get("/Condition")
def list_conditions(subject: str | None = Query(None, description="Subject reference")) -> list[dict]:
    data = _load()
    out = []
    for hh in data["households"]["households"]:
        for c in hh["conditions"]:
            if subject and c["subject"]["reference"] != subject:
                continue
            out.append(c)
    return out


@app.get("/Bundle/encounter")
def build_encounter_bundle(dictation: str = Query(..., description="Free-text clinician dictation")) -> dict:
    """End-to-end Machine Authorship Engine demonstration over the API.

    Returns the FHIR Bundle plus an authorship summary.
    """
    if not dictation.strip():
        raise HTTPException(400, "dictation cannot be empty")
    _, entities = extract_entities(dictation)
    bundle = build_bundle(entities, dictation)
    return {"bundle": bundle, "summary": authorship_summary(bundle)}


@app.get("/OneHealth/clusters")
def list_cross_species_clusters() -> list[dict]:
    """Cross-species disease clusters as detected by the knowledge graph."""
    from src.graph.knowledge_graph import build_graph, cross_species_clusters
    data = _load()
    G = build_graph(data["households"])
    return cross_species_clusters(G)


@app.get("/Surveillance/alerts")
def list_alerts(severity: str | None = Query(None, description="action | watch | info")) -> list[dict]:
    alerts = _load()["alerts"]["alerts"]
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    return alerts


@app.get("/Surveillance/alerts/{kind}")
def list_alerts_by_kind(kind: str) -> list[dict]:
    valid_kinds = {"CROSS_SPECIES_CLUSTER", "PROPHYLACTIC_HOUSEHOLD",
                   "VECTOR_ANOMALY", "ENV_AMPLIFIED_RISK", "SENTINEL_CASE"}
    if kind not in valid_kinds:
        raise HTTPException(400, f"unknown kind. valid: {sorted(valid_kinds)}")
    return [a for a in _load()["alerts"]["alerts"] if a["kind"] == kind]


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
