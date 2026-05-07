"""
Clinical entity extractor.

Takes parsed dictation (phase-labeled sentences) and produces structured
clinical entities with codes, confidence scores, and source-span citations.
Pure rule-based + dictionary lookup for the MVP — every extraction is
explainable and traceable. Production deployment would augment this with
a fine-tuned BioClinicalBERT NER head.

Each extracted entity is a typed record with:
    - kind:        "Condition" | "Symptom" | "Medication" | "Vital" |
                   "Demographic" | "Exposure" | "Lab"
    - text:        the verbatim source span
    - char_start:  start offset in the *original* dictation
    - char_end:    end offset in the *original* dictation
    - codes:       list of {system, code, display}
    - attributes:  type-specific structured fields
    - negated:     bool — context-negated (e.g., "no fever")
    - uncertain:   bool — hedged (e.g., "possible pneumonia")
    - phase:       phase label of the source sentence
    - confidence:  float 0..1
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from .dictation_parser import ParsedDictation, parse as parse_dictation

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TERMS = json.loads((PROJECT_ROOT / "data" / "reference" / "clinical_terminologies.json").read_text())


# ---------------------------------------------------------------------------
# Lexicon: phrase -> code lookup, including common abbreviations.
# ---------------------------------------------------------------------------
def _build_condition_lexicon() -> dict[str, dict]:
    lex: dict[str, dict] = {}
    for c in TERMS["conditions_human"]:
        full = c["display"].lower()
        lex[full] = c
        # Also index without the parenthetical disambiguator and the parenthetical alone.
        # e.g. "Coccidioidomycosis (Valley Fever)" -> "coccidioidomycosis" + "valley fever"
        m = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", full)
        if m:
            base, alias = m.group(1).strip(), m.group(2).strip()
            lex.setdefault(base, c)
            lex.setdefault(alias, c)
    # Common abbreviations & synonyms.
    abbrev = {
        "cocci": "Coccidioidomycosis",
        "rmsf": "Rocky Mountain spotted fever",
        "hps": "Hantavirus pulmonary syndrome",
        "hantavirus": "Hantavirus pulmonary syndrome",
        "lepto": "Leptospirosis",
        "htn": "Essential hypertension",
        "hypertension": "Essential hypertension",
        "hypertensive": "Essential hypertension",
        "dm": "Type 2 diabetes mellitus",
        "dm2": "Type 2 diabetes mellitus",
        "type 2 diabetes": "Type 2 diabetes mellitus",
        "diabetic": "Type 2 diabetes mellitus",
        "diabetes": "Type 2 diabetes mellitus",
        "esrd": "End-stage renal disease",
        "end-stage renal disease": "End-stage renal disease",
        "copd": "Chronic obstructive pulmonary disease",
    }
    for surface, canon in abbrev.items():
        for cd in TERMS["conditions_human"]:
            if cd["display"].lower().startswith(canon.lower()):
                lex[surface] = cd
                break
    return lex


def _build_symptom_lexicon() -> dict[str, dict]:
    lex = {s["display"].lower(): s for s in TERMS["symptoms_human"]}
    abbrev = {
        "sob": "Dyspnea",
        "shortness of breath": "Dyspnea",
        "difficulty breathing": "Dyspnea",
        "dyspnea": "Dyspnea",
        "fever": "Fever",
        "febrile": "Fever",
        "cough": "Cough",
        "headache": "Headache",
        "h/a": "Headache",
        "fatigue": "Fatigue",
        "tired": "Fatigue",
        "rash": "Skin rash",
        "diarrhea": "Diarrhea",
        "joint pain": "Joint pain",
        "myalgia": "Joint pain",  # close enough for MVP
        "edema": "Edema (lower extremity)",
        "swelling": "Edema (lower extremity)",
        "leg swelling": "Edema (lower extremity)",
    }
    canon = {s["display"]: s for s in TERMS["symptoms_human"]}
    for surface, target in abbrev.items():
        if target in canon:
            lex[surface] = canon[target]
    return lex


def _build_medication_lexicon() -> dict[str, dict]:
    lex: dict[str, dict] = {}
    for m in TERMS["medications"]:
        # Index by drug name (first word) for partial matching.
        name = m["display"].split()[0].lower()
        lex[name] = m
        lex[m["display"].lower()] = m
    return lex


def _build_animal_condition_lexicon() -> dict[str, dict]:
    lex = {c["display"].lower(): c for c in TERMS["conditions_animal"]}
    for k, v in {
        "ehrlichia": "Ehrlichiosis",
        "tick fever": "Ehrlichiosis",
        "rmsf": "Rocky Mountain spotted fever",
        "leptospirosis": "Leptospirosis",
        "lepto": "Leptospirosis",
        "valley fever": "Coccidioidomycosis",
        "cocci": "Coccidioidomycosis",
    }.items():
        for c in TERMS["conditions_animal"]:
            if c["display"].lower().startswith(v.lower()):
                lex[k] = c
                break
    return lex


CONDITION_LEX = _build_condition_lexicon()
SYMPTOM_LEX = _build_symptom_lexicon()
MEDICATION_LEX = _build_medication_lexicon()
ANIMAL_COND_LEX = _build_animal_condition_lexicon()


# ---------------------------------------------------------------------------
# Regex patterns for vitals, demographics, durations, exposures, hedges
# ---------------------------------------------------------------------------
_AGE_PATTERNS = [
    re.compile(r"\b(\d{1,3})[ -]year[ -]old\b", re.I),
    re.compile(r"\b(\d{1,3})\s*y/?o\b", re.I),
    re.compile(r"\b(\d{1,3})\s*yr\b", re.I),
]
_AGE_WORDS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_AGE_WORDED = re.compile(
    r"\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s-]?(one|two|three|four|five|six|seven|eight|nine)?[\s-]year[\s-]old\b",
    re.I)
_NUM_WORDS_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9,
}

_SEX_MALE = re.compile(r"\b(male|man|gentleman|m/|M\b)\b")
_SEX_FEMALE = re.compile(r"\b(female|woman|lady|f/|F\b)\b")

_VITAL_PATTERNS: dict[str, re.Pattern] = {
    "blood_pressure":      re.compile(r"\bBP\s*[:= ]?\s*(\d{2,3})\s*/\s*(\d{2,3})\b", re.I),
    "heart_rate":          re.compile(r"\bHR\s*[:= ]?\s*(\d{2,3})\b", re.I),
    "respiratory_rate":    re.compile(r"\bRR\s*[:= ]?\s*(\d{1,3})\b", re.I),
    "temperature_f":       re.compile(r"\b(?:T|Temp|Temperature)\s*[:= ]?\s*(\d{2,3}(?:\.\d)?)\s*(?:F|°F)?\b", re.I),
    "spo2":                re.compile(r"\bSpO2\s*[:= ]?\s*(\d{1,3})\s*%?\b", re.I),
}

_DURATION = re.compile(
    r"\b(?:for|since|times?|x)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|week|month|year)s?\b",
    re.I)

_EXPOSURE_PATTERNS = {
    "tick_exposure":    re.compile(r"\btick(?:s|\sbite|\sexposure|\sattached|\sembedded)?\b", re.I),
    "rodent_exposure":  re.compile(r"\b(rodent|mouse|mice|rat\b|rat\s)\b", re.I),
    "dog_exposure":     re.compile(r"\b(dog|canine|puppy)\b", re.I),
    "cat_exposure":     re.compile(r"\b(cat|feline|kitten)\b", re.I),
    "soil_dust":        re.compile(r"\b(dust\sstorm|soil\sdust|excavation|dust\sexposure|gardening)\b", re.I),
    "freshwater":       re.compile(r"\b(canal|pond|lake\sswim|stream|river\sswim|freshwater)\b", re.I),
    "outdoor_activity": re.compile(r"\b(hike|hiking|camp|camping|outdoor)\b", re.I),
}

# Negation cues that should be checked within ~5 tokens BEFORE the entity.
_NEG_CUES = ["no", "denies", "denied", "not", "without", "absent", "negative for", "free of"]
# Hedge cues that indicate uncertainty / differential.
_HEDGE_CUES = ["possible", "probable", "suspected", "consider", "rule out", "r/o",
               "differential", "likely", "suggestive of", "consistent with"]


# ---------------------------------------------------------------------------
# Entity record
# ---------------------------------------------------------------------------
@dataclass
class Entity:
    kind: str
    text: str
    char_start: int
    char_end: int
    codes: list[dict] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    negated: bool = False
    uncertain: bool = False
    phase: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Context detection helpers
# ---------------------------------------------------------------------------
def _sentence_start(parsed: ParsedDictation, off: int) -> int:
    """Return the char_start of the sentence containing offset `off`."""
    for s in parsed.sentences:
        if s.char_start <= off < s.char_end:
            return s.char_start
    return 0


def _preceding_window(text: str, start: int, n_tokens: int = 5,
                      min_offset: int = 0) -> list[str]:
    """Return the n_tokens preceding the start offset, bounded to min_offset."""
    pre = text[min_offset:start].lower()
    tokens = re.findall(r"\b[\w/]+\b", pre)
    return tokens[-n_tokens:]


def _is_negated(text: str, start: int, sentence_start: int = 0) -> bool:
    window = _preceding_window(text, start, 5, sentence_start)
    single = {c for c in _NEG_CUES if " " not in c}
    multi = [c for c in _NEG_CUES if " " in c]
    if any(t in single for t in window):
        return True
    joined = " ".join(window)
    return any(c in joined for c in multi)


def _is_hedged(text: str, start: int, sentence_start: int = 0) -> bool:
    window = _preceding_window(text, start, 6, sentence_start)
    single = {c for c in _HEDGE_CUES if " " not in c}
    multi = [c for c in _HEDGE_CUES if " " in c]
    if any(t in single for t in window):
        return True
    joined = " ".join(window)
    return any(c in joined for c in multi)


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------
def _phase_for_offset(parsed: ParsedDictation, off: int) -> str:
    for s in parsed.sentences:
        if s.char_start <= off < s.char_end:
            return s.phase
    return "UNKNOWN"


def _extract_demographics(text: str, parsed: ParsedDictation) -> list[Entity]:
    out: list[Entity] = []
    # Worded ages first ("fifty-six-year-old"), then numeric.
    for m in _AGE_WORDED.finditer(text):
        tens = _AGE_WORDS.get(m.group(1).lower(), 0)
        ones = _NUM_WORDS_ONES.get((m.group(2) or "").lower(), 0)
        age = tens + ones
        if age:
            out.append(Entity(
                kind="Demographic", text=m.group(0),
                char_start=m.start(), char_end=m.end(),
                attributes={"age_years": age},
                phase=_phase_for_offset(parsed, m.start()),
                confidence=0.95))
    for pat in _AGE_PATTERNS:
        for m in pat.finditer(text):
            # Skip if covered by a worded match already.
            if any(e.char_start <= m.start() < e.char_end for e in out if e.kind == "Demographic"):
                continue
            out.append(Entity(
                kind="Demographic", text=m.group(0),
                char_start=m.start(), char_end=m.end(),
                attributes={"age_years": int(m.group(1))},
                phase=_phase_for_offset(parsed, m.start()),
                confidence=0.97))
    # Sex
    for m in _SEX_MALE.finditer(text):
        out.append(Entity(
            kind="Demographic", text=m.group(0),
            char_start=m.start(), char_end=m.end(),
            attributes={"gender": "male"},
            phase=_phase_for_offset(parsed, m.start()),
            confidence=0.90))
        break
    for m in _SEX_FEMALE.finditer(text):
        out.append(Entity(
            kind="Demographic", text=m.group(0),
            char_start=m.start(), char_end=m.end(),
            attributes={"gender": "female"},
            phase=_phase_for_offset(parsed, m.start()),
            confidence=0.90))
        break
    return out


def _extract_lexicon(text: str, parsed: ParsedDictation,
                     lex: dict[str, dict], kind: str,
                     code_keys: tuple[str, ...]) -> list[Entity]:
    """Generic dictionary matcher. Iterates lexicon longest-phrase-first."""
    out: list[Entity] = []
    # Sort by phrase length descending so "valley fever" wins over "fever".
    phrases = sorted(lex.keys(), key=len, reverse=True)
    consumed: list[tuple[int, int]] = []
    for phrase in phrases:
        # word-boundary match, case-insensitive
        pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.I)
        for m in pat.finditer(text):
            # Skip if overlaps a longer prior match.
            if any(s <= m.start() < e or s < m.end() <= e for s, e in consumed):
                continue
            consumed.append((m.start(), m.end()))
            entry = lex[phrase]
            sent_start = _sentence_start(parsed, m.start())
            codes = []
            for k in code_keys:
                if k == "snomed" and "snomed" in entry:
                    codes.append({"system": "http://snomed.info/sct",
                                  "code": entry["snomed"], "display": entry["display"]})
                elif k == "icd10" and "icd10" in entry:
                    codes.append({"system": "http://hl7.org/fhir/sid/icd-10-cm",
                                  "code": entry["icd10"], "display": entry["display"]})
                elif k == "loinc" and "loinc" in entry:
                    codes.append({"system": "http://loinc.org",
                                  "code": entry["loinc"], "display": entry["display"]})
                elif k == "rxnorm" and "rxnorm" in entry:
                    codes.append({"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                  "code": entry["rxnorm"], "display": entry["display"]})
                elif k == "snomed_vet" and "snomed_vet" in entry:
                    codes.append({"system": "http://snomed.info/sct-vet",
                                  "code": entry["snomed_vet"], "display": entry["display"]})
            out.append(Entity(
                kind=kind, text=m.group(0),
                char_start=m.start(), char_end=m.end(),
                codes=codes,
                attributes={"display": entry["display"]},
                negated=_is_negated(text, m.start(), sent_start),
                uncertain=_is_hedged(text, m.start(), sent_start),
                phase=_phase_for_offset(parsed, m.start()),
                confidence=0.88 if len(phrase) > 6 else 0.78))  # longer phrases more confident
    return out


def _extract_vitals(text: str, parsed: ParsedDictation) -> list[Entity]:
    out: list[Entity] = []
    for vital_name, pat in _VITAL_PATTERNS.items():
        for m in pat.finditer(text):
            attrs: dict[str, Any] = {"vital_type": vital_name}
            if vital_name == "blood_pressure":
                attrs.update({"systolic": int(m.group(1)), "diastolic": int(m.group(2)), "unit": "mmHg"})
            else:
                attrs.update({"value": float(m.group(1)),
                              "unit": {"heart_rate": "bpm", "respiratory_rate": "/min",
                                       "temperature_f": "F", "spo2": "%"}[vital_name]})
            out.append(Entity(
                kind="Vital", text=m.group(0),
                char_start=m.start(), char_end=m.end(),
                attributes=attrs,
                phase=_phase_for_offset(parsed, m.start()),
                confidence=0.97))
    return out


def _extract_durations(text: str, parsed: ParsedDictation) -> list[Entity]:
    out: list[Entity] = []
    word_to_n = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                 "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for m in _DURATION.finditer(text):
        raw_num = m.group(1).lower()
        n = int(raw_num) if raw_num.isdigit() else word_to_n.get(raw_num, 0)
        unit = m.group(2).lower()
        days = n * {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
        out.append(Entity(
            kind="Duration", text=m.group(0),
            char_start=m.start(), char_end=m.end(),
            attributes={"value": n, "unit": unit, "approx_days": days},
            phase=_phase_for_offset(parsed, m.start()),
            confidence=0.85))
    return out


def _extract_exposures(text: str, parsed: ParsedDictation) -> list[Entity]:
    out: list[Entity] = []
    for exp_name, pat in _EXPOSURE_PATTERNS.items():
        for m in pat.finditer(text):
            sent_start = _sentence_start(parsed, m.start())
            out.append(Entity(
                kind="Exposure", text=m.group(0),
                char_start=m.start(), char_end=m.end(),
                attributes={"exposure_type": exp_name},
                negated=_is_negated(text, m.start(), sent_start),
                uncertain=_is_hedged(text, m.start(), sent_start),
                phase=_phase_for_offset(parsed, m.start()),
                confidence=0.75))
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------
def extract_entities(dictation: str | ParsedDictation, *,
                     mode: str = "human") -> tuple[ParsedDictation, list[Entity]]:
    """Extract all entities from a clinician dictation.

    mode: "human" or "veterinary" — chooses the condition lexicon.
    """
    parsed = parse_dictation(dictation) if isinstance(dictation, str) else dictation
    text = parsed.raw_text
    entities: list[Entity] = []
    entities.extend(_extract_demographics(text, parsed))
    entities.extend(_extract_vitals(text, parsed))
    entities.extend(_extract_durations(text, parsed))
    entities.extend(_extract_exposures(text, parsed))
    cond_lex = CONDITION_LEX if mode == "human" else ANIMAL_COND_LEX
    code_keys = ("snomed", "icd10") if mode == "human" else ("snomed_vet",)
    entities.extend(_extract_lexicon(text, parsed, cond_lex, "Condition", code_keys))
    if mode == "human":
        entities.extend(_extract_lexicon(text, parsed, SYMPTOM_LEX, "Symptom", ("snomed", "loinc")))
    entities.extend(_extract_lexicon(text, parsed, MEDICATION_LEX, "Medication", ("rxnorm",)))
    entities.sort(key=lambda e: e.char_start)
    return parsed, entities


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = (
        "Fifty-six-year-old male, known hypertensive and diabetic with ESRD on "
        "maintenance hemodialysis, presenting with difficulty breathing times one "
        "week and bilateral leg swelling times one month. "
        "On examination, BP 168/94, HR 102, RR 22, SpO2 91% on room air. "
        "No fever, no cough. "
        "Assessment: acute fluid overload, possible coccidioidomycosis given Pinal Co. residence. "
        "Plan: start fluconazole 200 mg, admit, dialysis in AM."
    )
    parsed, ents = extract_entities(sample)
    print(f"Extracted {len(ents)} entities:\n")
    for e in ents:
        flags = []
        if e.negated:   flags.append("NEG")
        if e.uncertain: flags.append("UNC")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        codes_str = ", ".join(f"{c['system'].split('/')[-1]}:{c['code']}" for c in e.codes) or "—"
        print(f"  {e.kind:11} '{e.text}'{flag_str}")
        print(f"    span=[{e.char_start},{e.char_end}]  phase={e.phase}  conf={e.confidence:.2f}  codes={codes_str}")
        if e.attributes:
            print(f"    attrs={e.attributes}")
