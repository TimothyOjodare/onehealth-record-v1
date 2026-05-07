"""
Bundle all synthetic data into a single JSON payload for the HTML demo.

Output: data/synthetic/demo_bundle.json

Consumed by the single-file HTML application.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"
REF_DIR = PROJECT_ROOT / "data" / "reference"


def bundle_all() -> dict:
    households = json.loads((SYNTH_DIR / "households.json").read_text())
    surveillance = json.loads((SYNTH_DIR / "surveillance.json").read_text())
    knowledge_graph = json.loads((SYNTH_DIR / "knowledge_graph.json").read_text())
    alerts = json.loads((SYNTH_DIR / "alerts.json").read_text())
    counties = json.loads((REF_DIR / "arizona_counties.json").read_text())
    terms = json.loads((REF_DIR / "clinical_terminologies.json").read_text())
    encounters_path = SYNTH_DIR / "encounters.json"
    encounters = json.loads(encounters_path.read_text()) if encounters_path.exists() else {"encounters": []}
    eval_path = SYNTH_DIR / "evaluation.json"
    evaluation = json.loads(eval_path.read_text()) if eval_path.exists() else None

    # ML pipeline outputs (added in capstone phase 2)
    def _safe_load(filename: str):
        p = SYNTH_DIR / filename
        return json.loads(p.read_text()) if p.exists() else None

    def _safe_load_ref(filename: str):
        p = REF_DIR / filename
        return json.loads(p.read_text()) if p.exists() else None

    ml_evaluation     = _safe_load("ml_evaluation.json")
    explanations      = _safe_load("explanations.json")
    contact_tracing   = _safe_load("contact_tracing.json")
    llm_benchmark     = _safe_load("llm_benchmark.json")
    equity            = _safe_load("equity.json")
    lead_time         = _safe_load("lead_time.json")
    labels            = _safe_load("labels.json")
    federated         = _safe_load("federated.json")
    providers         = _safe_load("providers.json")
    federation_manifest = _safe_load("federation_manifest.json")
    consents          = _safe_load("consents.json")
    empi_links        = _safe_load("empi_links.json")
    reportable_cases  = _safe_load("reportable_cases.json")
    reportable_db     = _safe_load_ref("reportable_diseases_us.json")
    environmental_feeds = _safe_load("environmental_feeds.json")

    # Per-site FHIR shadow stores — load each one
    shadow_dir = SYNTH_DIR / "shadow_stores"
    shadow_stores = {}
    if shadow_dir.exists():
        for f in sorted(shadow_dir.glob("*.json")):
            shadow_stores[f.stem] = json.loads(f.read_text())

    return {
        "_metadata": {
            "schema_version": "0.4.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "project": "ONE-HealthRecord MVP",
            "is_synthetic": True,
            "_caveat": ("All clinical, surveillance, and household data is fully "
                        "synthetic. No real PHI. EPA EQI values approximated. "
                        "ADHS/CDC magnitudes calibrated to public reports."),
        },
        "counties": counties,
        "terminologies": terms,
        "households": households,
        "surveillance": surveillance,
        "knowledge_graph": knowledge_graph,
        "alerts": alerts,
        "encounters": encounters,
        "evaluation": evaluation,
        # === ML pipeline ===
        "ml_evaluation":   ml_evaluation,
        "explanations":    explanations,
        "contact_tracing": contact_tracing,
        "llm_benchmark":   llm_benchmark,
        "equity":          equity,
        "lead_time":       lead_time,
        "labels":          labels,
        "federated":       federated,
        "providers":       providers,
        # === Phase 6: federation, consent, eMPI ===
        "shadow_stores":      shadow_stores,
        "federation_manifest": federation_manifest,
        "consents":           consents,
        "empi_links":         empi_links,
        # === Phase 7: reportable diseases ===
        "reportable_diseases_db": reportable_db,
        "reportable_cases":       reportable_cases,
        # === Phase 8: environmental feeds ===
        "environmental_feeds":    environmental_feeds,
    }


if __name__ == "__main__":
    bundle = bundle_all()
    out = SYNTH_DIR / "demo_bundle.json"
    out.write_text(json.dumps(bundle, default=str))  # compact for embedding
    size_kb = out.stat().st_size / 1024
    print(f"Wrote {out.name} — {size_kb:.1f} KB")
    md = bundle["_metadata"]
    print(f"  {len(bundle['households']['households'])} households, "
          f"{len(bundle['knowledge_graph']['nodes'])} graph nodes, "
          f"{len(bundle['alerts']['alerts'])} alerts")
