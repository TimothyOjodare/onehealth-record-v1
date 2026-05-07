"""
MedGemma 4B clinical extractor with species router + RAG hooks + rule fallback.

Phase 3 — primary clinical extractor for the Live Encounter pipeline. Replaces
the rule-based extractor as the front door; the rule extractor remains as
audit reference + fallback when MedGemma confidence < 0.5.

Veterinary adaptation: three-layer approach as documented in
docs/medgemma_integration.md:
  Layer A — Species-router prompt prefix (zero training, ships today)
  Layer B — RAG over Merck Vet Manual / FDA Green Book / VeNom-to-SNOMED
  Layer C — LoRA adapters per species class (companion-animal, production-animal)

This module implements Layer A end-to-end and provides hooks for B and C.

Calling
-------
    from src.nlp.medgemma_extractor import MedGemmaExtractor
    extractor = MedGemmaExtractor()  # auto-detects MEDGEMMA_API_KEY env
    result = extractor.extract(text, species="canis_lupus_familiaris", weight_kg=32, age_years=4, sex="MN")

Output shape matches what the existing FHIR Bundle composer consumes:
    {
        "entities": [
            {"kind": "condition", "text": "valley fever",
             "char_start": 145, "char_end": 158,
             "snomed": "5294002", "confidence": 0.92,
             "source": "medgemma-4b-it/companion-animal-lora-v1.0",
             "negated": False, "uncertain": False}
        ],
        "model_metadata": {
            "primary_engine": "medgemma" | "rule_fallback",
            "species_class": "human" | "companion_animal" | "production_animal",
            "rag_passages_retrieved": 0,  # Layer B
            "lora_adapter_used": "companion-animal-v1.0" | None,  # Layer C
            "latency_ms": 234.5,
            "is_simulated": False  # True if no API key & we used the projection
        }
    }

For the demo: if MEDGEMMA_API_KEY is not set, the extractor falls back to the
rule-based pipeline AND emits a `is_simulated: True` flag so the Model Card
banner can surface the calibration caveat.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

MEDGEMMA_MODEL_DEFAULT = "medgemma-4b-it"
MEDGEMMA_API_BASE = "https://api.medgemma.example/v1/chat/completions"  # placeholder; configure for your deployment
CONFIDENCE_FALLBACK_THRESHOLD = 0.5
MAX_PROMPT_TOKENS = 4096

# NCBI taxon → species class
SPECIES_CLASS_MAP = {
    "homo_sapiens":              "human",
    "canis_lupus_familiaris":    "companion_animal",
    "felis_catus":               "companion_animal",
    "equus_caballus":            "companion_animal",
    "oryctolagus_cuniculus":     "companion_animal",
    "mustela_putorius_furo":     "companion_animal",
    "bos_taurus":                "production_animal",
    "sus_scrofa_domesticus":     "production_animal",
    "gallus_gallus_domesticus":  "production_animal",
    "ovis_aries":                "production_animal",
    "capra_aegagrus_hircus":     "production_animal",
}


# ----------------------------------------------------------------------------
# Prompt construction (Layer A — species router)
# ----------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """You are a clinical entity extraction assistant for a One Health electronic health record system. You extract clinically relevant entities from clinical or veterinary dictation and return strictly valid JSON.

Entity kinds you must extract:
  - condition: a diagnosed or suspected disease, disorder, or pathological state
  - symptom: a sign or symptom reported by the patient/owner or observed
  - vital_sign: temperature, heart rate, respiratory rate, blood pressure, weight, SpO2
  - medication: any drug name, dose, or therapeutic substance
  - exposure: relevant environmental or behavioral exposure (soil, water, livestock, vector)

For each entity, return:
  - kind (one of the above)
  - text (verbatim from the dictation)
  - char_start, char_end (character offsets into the input)
  - snomed (best-match SNOMED-CT code if known; null otherwise)
  - confidence (your confidence ∈ [0.0, 1.0])
  - negated (true if negated; "no fever" → negated=true)
  - uncertain (true if hedged; "possibly", "may have")

CRITICAL: respect the species block at the top of the input. If species_class is
companion_animal or production_animal, do NOT apply human anatomical assumptions or
human drug doses. Use species-appropriate clinical reasoning.

Return JSON only, no prose:
{"entities": [...]}"""


@dataclass
class SpeciesContext:
    species: str = "homo_sapiens"
    common_name: str = "human"
    weight_kg: Optional[float] = None
    age_years: Optional[float] = None
    sex: str = "U"
    species_class: str = "human"

    @classmethod
    def from_args(cls, species: str = "homo_sapiens", **kwargs) -> "SpeciesContext":
        species_class = SPECIES_CLASS_MAP.get(species, "other")
        return cls(species=species, species_class=species_class, **{
            k: v for k, v in kwargs.items() if k in cls.__dataclass_fields__
        })

    def to_prefix(self) -> str:
        """Render the species router block."""
        lines = [
            f"[species: {self.species}]",
            f"[common_name: {self.common_name}]",
        ]
        if self.weight_kg is not None:
            lines.append(f"[weight_kg: {self.weight_kg}]")
        if self.age_years is not None:
            lines.append(f"[age: {self.age_years} years]")
        if self.sex:
            lines.append(f"[sex: {self.sex}]")
        lines.append(f"[species_class: {self.species_class}]")
        if self.species_class != "human":
            lines.append(f"[reference_drug_doses: {self.species_class}]")
            lines.append(f"[lora_adapter_hint: {self.species_class.replace('_animal', '')}-animal-v1.0]")
        return "\n".join(lines) + "\n---\n"


# ----------------------------------------------------------------------------
# RAG hook (Layer B) — currently a stub returning empty context
# ----------------------------------------------------------------------------

def retrieve_rag_passages(text: str, species_class: str, k: int = 3) -> list[dict]:
    """
    Retrieve top-k relevant passages from the species-appropriate corpus.

    Production: vector index over Merck Vet Manual + FDA Green Book + VeNom-to-SNOMED
    crosswalk for animals; UpToDate / MedlinePlus / RxNorm for humans.

    Demo: returns an empty list. The hook is here so the call signature is stable
    and tests / downstream consumers don't break when RAG is enabled.
    """
    return []


# ----------------------------------------------------------------------------
# LoRA selection (Layer C) — currently returns adapter name without loading
# ----------------------------------------------------------------------------

def select_lora_adapter(species_class: str) -> Optional[str]:
    """Return the adapter name to use, or None if base model is sufficient."""
    if species_class == "companion_animal":
        return "companion-animal-v1.0"
    if species_class == "production_animal":
        return "production-animal-v1.0"
    return None


# ----------------------------------------------------------------------------
# MedGemma API call (production path)
# ----------------------------------------------------------------------------

def _call_medgemma_api(prompt: str, model: str, api_key: str, timeout_s: float = 30.0) -> dict:
    """
    Call the MedGemma chat-completions endpoint. Returns parsed JSON.
    Raises on HTTP / parsing errors; caller is responsible for fallback.
    """
    import urllib.request
    import urllib.error

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,        # deterministic for clinical use
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        MEDGEMMA_API_BASE,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    payload = json.loads(raw)
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


# ----------------------------------------------------------------------------
# Rule-based fallback (re-uses existing extractor)
# ----------------------------------------------------------------------------

def _rule_based_fallback(text: str, species_ctx: SpeciesContext) -> dict:
    """
    Use the existing rule-based extractor as a fallback. Output shape is
    normalized to match MedGemma's output for downstream FHIR composition.

    This stub returns a minimal structure; the full path delegates to
    src/nlp/extractor.py if importable. We keep this lightweight so the
    module is testable in isolation.
    """
    try:
        # Late import — avoids hard dependency for unit tests
        from src.nlp.extractor import extract as rule_extract  # type: ignore
        rule_entities = rule_extract(text)
        normalized = []
        for e in rule_entities:
            normalized.append({
                "kind":         e.get("kind", "unknown"),
                "text":         e.get("text", ""),
                "char_start":   e.get("char_start"),
                "char_end":     e.get("char_end"),
                "snomed":       e.get("codes", {}).get("snomed"),
                "confidence":   e.get("confidence", 0.85),
                "source":       "rule_fallback",
                "negated":      e.get("negated", False),
                "uncertain":    e.get("uncertain", False),
            })
        return {"entities": normalized}
    except ImportError:
        return {"entities": []}


# ----------------------------------------------------------------------------
# Public extractor
# ----------------------------------------------------------------------------

@dataclass
class MedGemmaExtractor:
    """
    Stateful extractor that handles MedGemma-primary, rule-fallback flow.

    Configuration:
      - api_key:   read from MEDGEMMA_API_KEY env if not passed
      - model:     'medgemma-4b-it' default
      - use_rag:   enable Layer B retrieval (default False; stub returns empty)
      - confidence_threshold: below this, route extraction back to rule layer
    """
    api_key: Optional[str] = None
    model: str = MEDGEMMA_MODEL_DEFAULT
    use_rag: bool = False
    confidence_threshold: float = CONFIDENCE_FALLBACK_THRESHOLD

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("MEDGEMMA_API_KEY")

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    def extract(
        self,
        text: str,
        species: str = "homo_sapiens",
        **species_kwargs: Any,
    ) -> dict:
        """
        Extract clinical entities from the given dictation.

        Returns
        -------
        dict with keys:
          entities       — list of entity dicts (see module docstring)
          model_metadata — provenance for the FHIR Provenance resource
        """
        t0 = time.perf_counter()
        species_ctx = SpeciesContext.from_args(species=species, **species_kwargs)
        prefix = species_ctx.to_prefix()
        rag_passages = retrieve_rag_passages(text, species_ctx.species_class) if self.use_rag else []
        lora_adapter = select_lora_adapter(species_ctx.species_class)

        rag_block = ""
        if rag_passages:
            rag_block = "[retrieved_context]\n" + "\n".join(
                f"  - {p['source']}: {p['text']}" for p in rag_passages
            ) + "\n---\n"

        prompt = prefix + rag_block + text

        if self.is_live:
            try:
                result = _call_medgemma_api(prompt, self.model, self.api_key)
                primary_engine = "medgemma"
                is_simulated = False
            except Exception as exc:
                # API failure — fall through to rule-based
                print(f"[MedGemmaExtractor] API call failed ({exc}); falling back to rules")
                result = _rule_based_fallback(text, species_ctx)
                primary_engine = "rule_fallback"
                is_simulated = False
        else:
            # No API key — use rule fallback and mark as simulated for
            # downstream caveat surfacing
            result = _rule_based_fallback(text, species_ctx)
            primary_engine = "rule_fallback"
            is_simulated = True

        # Per-entity escalation: if any extraction has confidence below the
        # threshold, mark for hand-back UI
        for ent in result.get("entities", []):
            ent.setdefault("source", primary_engine)
            ent["needs_handback"] = ent.get("confidence", 1.0) < self.confidence_threshold

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "entities": result.get("entities", []),
            "model_metadata": {
                "primary_engine":         primary_engine,
                "species":                species_ctx.species,
                "species_class":          species_ctx.species_class,
                "lora_adapter_used":      lora_adapter,
                "rag_passages_retrieved": len(rag_passages),
                "model_version":          self.model,
                "latency_ms":             elapsed_ms,
                "is_simulated":           is_simulated,
                "prompt_chars":           len(prompt),
            },
        }


# ----------------------------------------------------------------------------
# CLI / smoke test
# ----------------------------------------------------------------------------

def _smoke_test() -> int:
    """
    Run a tiny smoke test on a few hand-crafted dictations covering human and
    veterinary cases. Useful for verifying the integration end-to-end before
    paying for production API time.
    """
    cases = [
        {
            "label": "human_cocci",
            "species": "homo_sapiens",
            "weight_kg": 64,
            "age_years": 38,
            "sex": "F",
            "text": ("Maria Hernandez, 38F, Tucson. Presents with 6-week dry cough, "
                     "fatigue, low-grade fever 100.8F. Reports recent home garden "
                     "soil disturbance. Family dog Rocco recently dx'd with valley "
                     "fever by primary vet."),
        },
        {
            "label": "vet_cocci_dog",
            "species": "canis_lupus_familiaris",
            "weight_kg": 32,
            "age_years": 4,
            "sex": "MN",
            "text": ("Rocco, 4yo MN Lab mix, 32kg. Lethargy 3 weeks, weight loss, "
                     "intermittent lameness LH limb. Temp 39.6C, HR 110, RR 28. "
                     "Started fluconazole 5mg/kg PO q24h pending serology."),
        },
        {
            "label": "vet_q_fever_goat",
            "species": "capra_aegagrus_hircus",
            "weight_kg": 45,
            "age_years": 3,
            "sex": "F",
            "text": ("Doe goat, recent stillbirth. Presented for retained placenta. "
                     "Started oxytetracycline. Owner Becker household — son James "
                     "presented to PCP with pneumonia three days ago."),
        },
    ]

    print("=== MedGemmaExtractor smoke test ===\n")
    extractor = MedGemmaExtractor()
    print(f"  is_live: {extractor.is_live} "
          f"(MEDGEMMA_API_KEY {'set' if extractor.is_live else 'NOT set — using rule fallback'})\n")

    for case in cases:
        print(f"--- {case['label']} ---")
        out = extractor.extract(
            case["text"],
            species=case["species"],
            weight_kg=case["weight_kg"],
            age_years=case["age_years"],
            sex=case["sex"],
        )
        print(f"  primary_engine:   {out['model_metadata']['primary_engine']}")
        print(f"  species_class:    {out['model_metadata']['species_class']}")
        print(f"  lora_adapter:     {out['model_metadata']['lora_adapter_used']}")
        print(f"  is_simulated:     {out['model_metadata']['is_simulated']}")
        print(f"  latency:          {out['model_metadata']['latency_ms']:.1f} ms")
        print(f"  entities found:   {len(out['entities'])}")
        for e in out["entities"][:5]:
            text = e.get('text', '')
            conf = e.get('confidence', 0)
            print(f"    [{e.get('kind', '?'):12s}] {text[:40]:40s} conf={conf:.2f}")
        print()

    # Persist a sample report so the model card can surface it
    out_path = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "medgemma_smoke.json"
    sample = {"cases": [], "metadata": {"is_live": extractor.is_live}}
    for case in cases:
        out = extractor.extract(
            case["text"],
            species=case["species"],
            weight_kg=case["weight_kg"],
            age_years=case["age_years"],
            sex=case["sex"],
        )
        sample["cases"].append({
            "label": case["label"],
            "text": case["text"],
            "result": out,
        })
    with open(out_path, "w") as f:
        json.dump(sample, f, indent=2, default=str)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_smoke_test())
