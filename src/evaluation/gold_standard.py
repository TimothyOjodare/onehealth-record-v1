"""
Programmatic gold-standard annotator.

Generates ~25 synthetic dictations and produces ground-truth entity
annotations for them by enumerating dictionary spans + simple pattern
rules. Because the dictations and the annotations are produced from the
same source, the gold standard is internally consistent — a credible
proxy for evaluating the rule-based extractor on its target distribution.

We also intentionally inject ambiguities (e.g. "no fever", "denies cough",
"possible pneumonia") so the negation/uncertainty logic is exercised.

Output: data/synthetic/gold_standard.json
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"
REF_DIR = PROJECT_ROOT / "data" / "reference"


# 25 hand-tuned synthetic dictations spanning the 12 disease scenarios.
# These are NOT identical to the demo scenarios (so the eval isn't a memorized lookup);
# they are independently authored to test the extractor on its target distribution.
GOLD_DICTATIONS = [
    # Cocci variants
    ("Sixty-one-year-old female from Tucson, Pima County, with a six-week dry cough and progressive fatigue. "
     "Husband reports their dog Rex was diagnosed with valley fever last month. "
     "Temp 100.2 F, BP 122/78, HR 90, RR 18, SpO2 96%. "
     "Mild crackles right base. No skin rash. Plan: Coccidioides serology and start fluconazole 200 mg twice daily."),
    ("Fifty-year-old male, lives in Phoenix, presents with two weeks of fever and chest pain. "
     "He works in construction and has frequent dust exposure. "
     "On exam Temp 101.0 F, HR 102, RR 20, SpO2 95%. "
     "Right middle lobe consolidation on chest X-ray. Working diagnosis coccidioidomycosis. "
     "Plan: itraconazole 100 mg orally twice daily, follow up in two weeks."),

    # RMSF / Ehrlichiosis
    ("Forty-five-year-old male, lives in rural Pinal County, presents with fever, headache, and a maculopapular rash that started on his wrists. "
     "Tick exposure two weeks ago. Family dog was recently diagnosed with ehrlichiosis. "
     "Temp 102.6 F, BP 118/72, HR 110. "
     "Plan: empiric doxycycline 100 mg twice daily, draw RMSF serology."),
    ("Fifty-two-year-old female, hiking enthusiast, presents with abrupt fever and severe headache. "
     "She removed an attached tick five days ago. No skin rash on initial exam. "
     "Temp 103.4 F, HR 118. Plan: empiric doxycycline, monitor for rash development."),

    # Hantavirus
    ("Sixty-five-year-old female, lives in rural Maricopa County, presents with fever, severe myalgia, and dyspnea. "
     "Cleaned out a rodent-infested shed without respiratory protection one week ago. "
     "Temp 102.0 F, BP 92/56, HR 122, RR 28, SpO2 86%. "
     "Bilateral diffuse crackles. Suspect hantavirus pulmonary syndrome. Plan: ICU admission and supportive care."),

    # Leptospirosis
    ("Thirty-eight-year-old male, lives in Yuma, presents with fever, severe muscle pain, and yellowing of the eyes. "
     "He swims weekly in an irrigation canal where his dog (recently diagnosed with leptospirosis) also swims. "
     "Temp 101.6 F, HR 102. Plan: empiric doxycycline, draw leptospirosis serology."),

    # Plague
    ("Forty-year-old female, lives near St. Johns in Apache County, presents with abrupt fever and a tender lump in the right groin. "
     "Outdoor cat was diagnosed with plague three days ago. "
     "Temp 103.8 F, BP 100/62, HR 124. Painful right inguinal bubo. "
     "Plan: streptomycin 1 g IM twice daily, isolate, notify ADHS and CDC."),

    # West Nile
    ("Sixty-two-year-old male, lives in Cochise County, presents with severe headache, fever, and confusion times three days. "
     "Family horse was recently diagnosed with West Nile virus. "
     "Temp 102.0 F, BP 152/90, HR 96. Mild neck stiffness. "
     "Plan: lumbar puncture, West Nile IgM serology, supportive care."),

    # Rabies / dog bite
    ("Eight-year-old male, presents with a small puncture wound on the left hand sustained when he broke up an attack between his dog and a wild skunk three days ago. "
     "The skunk later tested positive for rabies. "
     "Temp 98.6 F, HR 90. Wound clean, no signs of infection. "
     "Plan: rabies post-exposure prophylaxis with HRIG and rabies vaccine series."),

    # Q fever
    ("Forty-three-year-old male, runs a goat dairy in Santa Cruz County, presents with three weeks of dry cough, low-grade fever, and fatigue. "
     "Three goats had recent abortions, placentas tested positive for Coxiella burnetii. He assisted without PPE. "
     "Temp 100.8 F, HR 88. "
     "Plan: empiric doxycycline 100 mg twice daily for two weeks, draw Q fever phase I and phase II antibodies."),

    # Psittacosis
    ("Twenty-nine-year-old female, lives in Phoenix, presents with five days of high fever, dry cough, and severe headache. "
     "Pet parrot Mango was recently diagnosed with Chlamydia psittaci. "
     "Temp 103.0 F, HR 108, SpO2 93%. Right basilar crackles. "
     "Plan: empiric doxycycline 100 mg twice daily for ten days, chest X-ray."),

    # Tularemia
    ("Fifty-five-year-old male, hunter, presents with fever and a painful axillary lymph node. "
     "He field-dressed a sick wild rabbit ten days ago without gloves. He has a non-healing ulcer on his right index finger. "
     "Temp 102.2 F, HR 110. "
     "Plan: empiric streptomycin, draw Francisella tularensis serology, public health notification."),

    # Salmonellosis from reptile
    ("Five-year-old female with three days of severe diarrhea, fever, and dehydration. "
     "Family has a pet bearded dragon and the child handles the reptile daily. "
     "Temp 102.4 F, HR 130, RR 28. Salmonella isolated from stool. "
     "Plan: rehydration, supportive care, public health notification."),

    # Negation tests
    ("Thirty-year-old female annual physical. No fever, no cough, no chest pain. "
     "Denies headache or rash. BP 118/74, HR 72. Vitals normal. "
     "Plan: routine labs."),
    ("Sixty-year-old male follow-up for hypertension. No new symptoms. Denies dyspnea or syncope. "
     "BP 138/86, HR 78. Continue lisinopril 10 mg daily."),

    # Hedge tests
    ("Forty-five-year-old male with two weeks of cough. Possibly community-acquired pneumonia. "
     "Temp 100.4 F. BP 124/80, HR 88. Right base crackles. "
     "Plan: chest X-ray, may consider empiric amoxicillin."),
    ("Twenty-five-year-old female. Likely viral URI versus seasonal allergies. "
     "Subjective fever. No measured fever in clinic. "
     "Plan: supportive care, return precautions reviewed."),

    # ESRD / chronic
    ("Fifty-eight-year-old male with end-stage renal disease, hypertension, and type 2 diabetes. "
     "Missed two dialysis sessions. Presents with shortness of breath and bilateral leg swelling. "
     "BP 168/96, HR 100, RR 22, SpO2 91%. "
     "Plan: emergent dialysis, admit, continue lisinopril and metformin."),

    # Vet — Cocci dog
    ("Patient Charlie, three-year-old male neutered Beagle, presented for two weeks of cough and lethargy. "
     "Owner reports dog frequently digs in dirt around the property in Maricopa. "
     "Temperature 102.4 F, Heart rate 118, Respiratory rate 30. "
     "Right lung field crackles. Plan: Coccidioides serology and fluconazole 5 mg per kilogram twice daily."),

    # Vet — RMSF dog
    ("Patient Daisy, six-year-old female spayed Labrador Retriever, presented for three days of lethargy and limping. "
     "Multiple ticks removed last week. "
     "Temperature 103.6 F, Heart rate 124. Mild lameness right forelimb. "
     "Plan: empiric doxycycline 5 mg per kilogram twice daily, draw 4Dx panel."),

    # Vet — Lepto dog
    ("Patient Buddy, four-year-old male intact Mixed Breed, presented for vomiting and yellow gums. "
     "Frequent swimmer in canals. "
     "Temperature 103.0 F. Plan: leptospirosis PCR and serology, IV fluids and ampicillin."),

    # Vet — WNV horse
    ("Patient Star, ten-year-old gelding Quarter Horse, presented for two days of progressive ataxia and muscle tremors. "
     "Standing water on property. Temperature 102.0 F. "
     "Marked hindlimb weakness. Plan: West Nile IgM ELISA and supportive care."),

    # Vet — Plague cat
    ("Patient Whiskers, three-year-old female spayed Domestic Shorthair, presented for high fever and a large submandibular lymph node. "
     "Cat is outdoor-access in Apache County and hunts ground squirrels. "
     "Temperature 105.0 F, Heart rate 220. Plan: bubo aspirate Gram stain, gentamicin 5 mg per kilogram daily, isolate."),

    # Vet — Q fever goat
    ("Patient Pepper, four-year-old female Nubian goat, presented for recent late-term abortion. "
     "Two other goats in the herd also aborted. "
     "Temperature 102.8 F. Plan: Coxiella burnetii PCR on placental tissue, herd-level oxytetracycline."),

    # Vet — Psittacosis bird
    ("Patient Sunny, six-year-old male African Grey, presented for two weeks of lethargy, ruffled feathers, and watery droppings. "
     "Owner handles bird daily. "
     "Weight 380 grams. Plan: Chlamydia psittaci PCR, doxycycline 25 mg per kilogram orally daily, isolate."),
]


# ---------------------------------------------------------------------------
# Span-level annotators by entity kind
# ---------------------------------------------------------------------------
TERMS = json.loads((REF_DIR / "clinical_terminologies.json").read_text())

# Build dictionary of normalized strings -> kind/codes
def _build_dictionary() -> dict[str, list[dict]]:
    d: dict[str, list[dict]] = {}
    def add(text, kind, snomed=None, icd10=None, loinc=None, rxnorm=None, snomed_vet=None):
        key = text.lower()
        d.setdefault(key, []).append({
            "kind": kind, "snomed": snomed, "icd10": icd10, "loinc": loinc,
            "rxnorm": rxnorm, "snomed_vet": snomed_vet,
        })
    for c in TERMS["conditions_human"]:
        add(c["display"], "condition_human", snomed=c["snomed"], icd10=c.get("icd10"))
        if "(" in c["display"]:
            short = c["display"].split("(")[0].strip()
            add(short, "condition_human", snomed=c["snomed"], icd10=c.get("icd10"))
        # Common shorthand for valley fever
        if "Coccidioidomycosis" in c["display"]:
            add("valley fever", "condition_human", snomed=c["snomed"])
            add("coccidioides", "condition_human", snomed=c["snomed"])
            add("cocci", "condition_human", snomed=c["snomed"])
        if "Hantavirus" in c["display"]:
            add("hantavirus", "condition_human", snomed=c["snomed"])
            add("hantavirus pulmonary syndrome", "condition_human", snomed=c["snomed"])
            add("hps", "condition_human", snomed=c["snomed"])
        if "Rocky Mountain spotted fever" in c["display"]:
            add("rmsf", "condition_human", snomed=c["snomed"])
        if "Plague" in c["display"]:
            add("bubonic plague", "condition_human", snomed=c["snomed"])
            add("plague", "condition_human", snomed=c["snomed"])
        if "West Nile" in c["display"]:
            add("west nile virus", "condition_human", snomed=c["snomed"])
            add("west nile", "condition_human", snomed=c["snomed"])
            add("west nile encephalitis", "condition_human", snomed=c["snomed"])
        if "Tularemia" in c["display"]:
            add("tularemia", "condition_human", snomed=c["snomed"])
            add("ulceroglandular tularemia", "condition_human", snomed=c["snomed"])
        if "Q fever" in c["display"]:
            add("q fever", "condition_human", snomed=c["snomed"])
        if "Psittacosis" in c["display"]:
            add("psittacosis", "condition_human", snomed=c["snomed"])
        if "Coccidioidomycosis (Valley Fever)" == c["display"]:
            pass
    for c in TERMS["conditions_animal"]:
        add(c["display"], "condition_animal", snomed_vet=c["snomed_vet"])
        if "Coccidioidomycosis" in c["display"]:
            add("cocci", "condition_animal", snomed_vet=c["snomed_vet"])
        if "Ehrlichiosis" in c["display"]:
            add("ehrlichia", "condition_animal", snomed_vet=c["snomed_vet"])
            add("ehrlichiosis", "condition_animal", snomed_vet=c["snomed_vet"])
    for s in TERMS["symptoms_human"]:
        add(s["display"], "symptom", snomed=s["snomed"], loinc=s.get("loinc"))
        if s["display"] == "Cough":
            add("dry cough", "symptom", snomed=s["snomed"])
        if s["display"] == "Dyspnea":
            add("shortness of breath", "symptom", snomed=s["snomed"])
            add("dyspnea", "symptom", snomed=s["snomed"])
        if s["display"] == "Fever":
            add("low-grade fever", "symptom", snomed=s["snomed"])
            add("high fever", "symptom", snomed=s["snomed"])
        if s["display"] == "Skin rash":
            add("rash", "symptom", snomed=s["snomed"])
            add("maculopapular rash", "symptom", snomed=s["snomed"])
            add("petechial rash", "symptom", snomed=s["snomed"])
        if s["display"] == "Confusion (altered mental status)":
            add("confusion", "symptom", snomed=s["snomed"])
            add("altered mental status", "symptom", snomed=s["snomed"])
        if s["display"] == "Joint pain":
            add("arthralgia", "symptom", snomed=s["snomed"])
        if s["display"] == "Myalgia":
            add("muscle pain", "symptom", snomed=s["snomed"])
            add("muscle aches", "symptom", snomed=s["snomed"])
        if s["display"] == "Lymphadenopathy":
            add("lymphadenopathy", "symptom", snomed=s["snomed"])
            add("swollen lymph node", "symptom", snomed=s["snomed"])
            add("painful lymph node", "symptom", snomed=s["snomed"])
            add("tender lymph node", "symptom", snomed=s["snomed"])
            add("inguinal bubo", "symptom", snomed=s["snomed"])
            add("bubo", "symptom", snomed=s["snomed"])
    for m in TERMS["medications"]:
        full = m["display"].lower()
        # full string
        add(m["display"], "medication", rxnorm=m["rxnorm"])
        # also just the drug name (first word + dose+ form)
        first = full.split()[0]
        add(first, "medication", rxnorm=m["rxnorm"])
    return d


DICT = _build_dictionary()


# ---------------------------------------------------------------------------
# Annotator
# ---------------------------------------------------------------------------
NEGATORS = ["no", "denies", "denied", "without", "negative for", "no signs of"]
HEDGERS = ["possible", "possibly", "may", "likely", "probable", "suspect", "suspected",
           "working diagnosis", "consistent with", "differential", "must be considered"]

def annotate(text: str) -> list[dict]:
    """Return ground-truth entity spans for a single dictation."""
    annots = []
    lower = text.lower()
    # Sort dictionary keys longest-first to prefer specific matches.
    keys = sorted(DICT.keys(), key=len, reverse=True)
    seen_spans = []  # list of (start, end) we already covered
    for key in keys:
        idx = 0
        while True:
            pos = lower.find(key, idx)
            if pos < 0:
                break
            end = pos + len(key)
            # Word boundary check — prevents 'cough' inside 'rough'
            left_ok  = pos == 0 or not lower[pos - 1].isalnum()
            right_ok = end == len(lower) or not lower[end].isalnum()
            if not (left_ok and right_ok):
                idx = pos + 1
                continue
            # Skip if any seen span overlaps
            if any(not (end <= s or pos >= e) for (s, e) in seen_spans):
                idx = pos + 1
                continue
            for hit in DICT[key]:
                # Negation: look at preceding 5 tokens
                prefix = lower[max(0, pos - 60):pos]
                negated = any(re.search(r"\b" + re.escape(neg) + r"\b", prefix[-30:]) for neg in NEGATORS)
                hedged  = any(re.search(r"\b" + re.escape(h) + r"\b",   prefix[-50:]) for h in HEDGERS)
                annots.append({
                    "char_start": pos,
                    "char_end": end,
                    "kind": hit["kind"],
                    "text": text[pos:end],
                    "negated": negated,
                    "uncertain": hedged,
                    "codes": {k: v for k, v in hit.items() if k != "kind" and v},
                })
                seen_spans.append((pos, end))
                break
            idx = end
    # Vital signs (regex)
    for m in re.finditer(r"\b(?:temp(?:erature)?|t)\s*[:\.]?\s*(\d{2,3}(?:\.\d)?)\s*°?\s*f\b", text, flags=re.I):
        annots.append({"char_start": m.start(), "char_end": m.end(), "kind": "vital_temp",
                       "text": m.group(0), "negated": False, "uncertain": False,
                       "codes": {"loinc": "8310-5"}})
    for m in re.finditer(r"\bhr\s*[:\.]?\s*(\d{2,3})\b", text, flags=re.I):
        annots.append({"char_start": m.start(), "char_end": m.end(), "kind": "vital_hr",
                       "text": m.group(0), "negated": False, "uncertain": False,
                       "codes": {"loinc": "8867-4"}})
    for m in re.finditer(r"\b(?:bp|blood pressure)\s*[:\.]?\s*(\d{2,3})\s*/\s*(\d{2,3})\b", text, flags=re.I):
        annots.append({"char_start": m.start(), "char_end": m.end(), "kind": "vital_bp",
                       "text": m.group(0), "negated": False, "uncertain": False,
                       "codes": {"loinc": "85354-9"}})
    for m in re.finditer(r"\bspo2\s*[:\.]?\s*(\d{2,3})\s*%?\b", text, flags=re.I):
        annots.append({"char_start": m.start(), "char_end": m.end(), "kind": "vital_spo2",
                       "text": m.group(0), "negated": False, "uncertain": False,
                       "codes": {"loinc": "59408-5"}})
    for m in re.finditer(r"\brr\s*[:\.]?\s*(\d{1,2})\b", text, flags=re.I):
        annots.append({"char_start": m.start(), "char_end": m.end(), "kind": "vital_rr",
                       "text": m.group(0), "negated": False, "uncertain": False,
                       "codes": {"loinc": "9279-1"}})

    return sorted(annots, key=lambda a: (a["char_start"], -(a["char_end"] - a["char_start"])))


def generate_gold() -> dict:
    out = []
    for i, dict_text in enumerate(GOLD_DICTATIONS):
        out.append({
            "id": f"GOLD-{i:03d}",
            "text": dict_text,
            "entities": annotate(dict_text),
        })
    bundle = {
        "_metadata": {
            "n_dictations": len(out),
            "n_entities": sum(len(d["entities"]) for d in out),
            "schema_version": "0.1.0",
        },
        "dictations": out,
    }
    (SYNTH_DIR / "gold_standard.json").write_text(json.dumps(bundle, indent=2))
    return bundle


if __name__ == "__main__":
    b = generate_gold()
    print(f"Gold standard: {b['_metadata']['n_dictations']} dictations, "
          f"{b['_metadata']['n_entities']} entity annotations")
    # Distribution
    by_kind = {}
    for d in b["dictations"]:
        for e in d["entities"]:
            by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
    print("\n  By entity kind:")
    for k, n in sorted(by_kind.items(), key=lambda x: -x[1]):
        print(f"    {k}: {n}")
