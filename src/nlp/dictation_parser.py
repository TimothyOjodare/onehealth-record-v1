"""
Dictation parser — segments raw clinician dictation into clinical phases.

Phase taxonomy follows standard SOAP + extended sections:
    CC   = Chief Complaint
    HPI  = History of Present Illness
    PMH  = Past Medical History
    ROS  = Review of Systems
    PE   = Physical Examination
    LAB  = Laboratory / Diagnostics
    A    = Assessment / Impression
    P    = Plan
    EXP  = Exposure history (One-Health-specific extension)

The parser is deliberately rule-based for explainability — every
phase boundary is traceable to a header pattern or topical heuristic.
In production this layer would be replaced or augmented by a
fine-tuned dialogue-segmentation model.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Header patterns. Order matters — most specific first.
PHASE_HEADERS: list[tuple[str, re.Pattern]] = [
    ("CC",  re.compile(r"\b(chief complaint|cc|presenting complaint|presents (?:with|today))\b", re.I)),
    ("HPI", re.compile(r"\b(history of present illness|hpi|history of presenting|present illness)\b", re.I)),
    ("PMH", re.compile(r"\b(past medical history|pmh|known (?:hypertensive|diabetic)|medical history)\b", re.I)),
    ("ROS", re.compile(r"\b(review of systems|ros|review of system)\b", re.I)),
    ("PE",  re.compile(r"\b(physical exam(?:ination)?|on examination|on exam|exam findings|vital signs|vitals)\b", re.I)),
    ("LAB", re.compile(r"\b(laboratory|labs?|investigations?|diagnostics?|imaging)\b", re.I)),
    ("A",   re.compile(r"\b(assessment|impression|differential|diagnosis|working diagnosis)\b", re.I)),
    ("P",   re.compile(r"\b(plan|management|treatment|disposition|recommendations)\b", re.I)),
    ("EXP", re.compile(r"\b(exposure(?:s)? history|exposures?|environmental history|household exposures?|recent travel|animal contact|tick exposure|rodent exposure)\b", re.I)),
]

# When no explicit headers, fall back to topical heuristics.
TOPIC_HEURISTICS: list[tuple[str, re.Pattern]] = [
    ("CC",  re.compile(r"\b(presents?|came in|brought in|seen for|here for|c/o|complains? of)\b", re.I)),
    ("HPI", re.compile(r"\b(\d+\s*(day|week|month|year)s? ago|since|started|began|onset|times? (one|two|three|four|five|\d+))\b", re.I)),
    ("PMH", re.compile(r"\b(history of|h/o|known|chronic|established|long-?standing)\b", re.I)),
    ("PE",  re.compile(r"\b(\bbp\b|\bhr\b|\brr\b|\btemp\b|\bspo2\b|auscult|palpation|tender|edema|rash|murmur)\b", re.I)),
    ("EXP", re.compile(r"\b(dog|cat|pet|tick|rodent|mouse|mice|hike|garden(ing)?|canal|farm|outdoor|pmlives? near|works? at)\b", re.I)),
    ("A",   re.compile(r"\b(suspect|consistent with|likely|probable|consider(?:ed)?|differential includes|rule out|r/o)\b", re.I)),
    ("P",   re.compile(r"\b(start|prescrib|order|admit|discharge|follow[- ]up|f/u|return|recheck|refer)\b", re.I)),
]


@dataclass
class Sentence:
    text: str
    char_start: int
    char_end: int
    phase: str = "UNKNOWN"
    phase_evidence: str = ""
    confidence: float = 0.0


@dataclass
class ParsedDictation:
    raw_text: str
    sentences: list[Sentence] = field(default_factory=list)

    @property
    def phases(self) -> dict[str, list[Sentence]]:
        out: dict[str, list[Sentence]] = {}
        for s in self.sentences:
            out.setdefault(s.phase, []).append(s)
        return out


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[Sentence]:
    text = re.sub(r"\s+", " ", text).strip()
    cursor, sents = 0, []
    pieces = _SENT_SPLIT.split(text)
    for p in pieces:
        if not p.strip():
            continue
        start = text.find(p, cursor)
        sents.append(Sentence(text=p.strip(), char_start=start, char_end=start + len(p)))
        cursor = start + len(p)
    return sents


def _classify(sent: Sentence, current_phase: str) -> tuple[str, str, float]:
    # Strong: explicit header match.
    for label, pat in PHASE_HEADERS:
        m = pat.search(sent.text)
        if m:
            return label, f"header:{m.group(0)}", 0.95
    # Weak: topical heuristic.
    matches = []
    for label, pat in TOPIC_HEURISTICS:
        m = pat.search(sent.text)
        if m:
            matches.append((label, m.group(0)))
    if matches:
        # Topical heuristics combined; first wins for now.
        label, evidence = matches[0]
        return label, f"topical:{evidence}", 0.65
    # Sticky: inherit current phase.
    return current_phase, "inherited", 0.40


def parse(text: str) -> ParsedDictation:
    """Parse a raw clinician dictation into phase-labeled sentences."""
    sents = _split_sentences(text)
    pd = ParsedDictation(raw_text=text)
    current = "CC"  # First sentence is almost always the chief complaint.
    for i, s in enumerate(sents):
        phase, evidence, conf = _classify(s, current)
        s.phase, s.phase_evidence, s.confidence = phase, evidence, conf
        current = phase
        # First sentence override — if no clear marker, force CC.
        if i == 0 and conf < 0.5:
            s.phase, s.phase_evidence, s.confidence = "CC", "default:first-sentence", 0.55
            current = "CC"
        pd.sentences.append(s)
    return pd


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = (
        "Fifty-six-year-old male, known hypertensive and diabetic with ESRD on "
        "maintenance hemodialysis, presents with shortness of breath times one "
        "week and bilateral lower extremity edema times one month. "
        "He missed his last two dialysis sessions. "
        "On examination, BP 168/94, HR 102, RR 22, SpO2 91% on room air. "
        "Bilateral basilar crackles on auscultation. 3+ pitting edema to mid-shin. "
        "Labs pending. "
        "Assessment: acute fluid overload secondary to missed dialysis. "
        "Plan: emergent dialysis, admit, cardiology consult."
    )
    parsed = parse(sample)
    for s in parsed.sentences:
        print(f"[{s.phase:5}] (conf={s.confidence:.2f}, ev={s.phase_evidence})\n   {s.text}")
