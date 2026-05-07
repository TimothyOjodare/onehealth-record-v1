"""
Outbreak labeling for the predictive task.

The predictive task: given an encounter, predict whether this presentation is
part of a zoonotic cluster requiring public-health follow-up within 14 days.

Labeling strategy:
- Each of the 12 hand-crafted households is a known outbreak. Their members'
  encounters within +/-60 days of the index date are POSITIVE.
- Non-cluster procedural households are background (NEGATIVE).
- The Pinal vector anomaly upgrades all encounters in Pinal County during the
  4-week anomaly window with a tick-borne CC to POSITIVE.

This is binary classification with synthetic ground truth — exactly what real PH
data never gives you cleanly, which is why synthetic data is a feature here.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set


# Outbreak index dates for the 12 hand-crafted scenarios.
# Where the household has a recorded condition.onsetDateTime we use that.
# Where the narrative implies an event but no condition was recorded, we use
# a synthetic April 2026 anchor (the demo "now" date).
OUTBREAK_INDEX_DATES: Dict[str, str] = {
    "HH-AZ-PIMA-001":      "2026-04-15",  # Hernandez Valley Fever
    "HH-AZ-PINAL-002":     "2026-04-21",  # Johnson ehrlichiosis/RMSF
    "HH-AZ-MARICOPA-003":  "2026-04-22",  # Williams hantavirus exposure (narrative)
    "HH-AZ-YUMA-004":      "2026-04-26",  # Patel leptospirosis
    "HH-AZ-COCONINO-005":  None,          # Chen healthy control - NEGATIVE
    "HH-AZ-APACHE-006":    "2026-04-25",  # Begay plague
    "HH-AZ-COCHISE-007":   "2026-04-17",  # Ramirez WNV
    "HH-AZ-MOHAVE-008":    "2026-04-19",  # Thompson rabies exposure
    "HH-AZ-SANTACRUZ-009": "2026-04-11",  # Becker Q fever
    "HH-AZ-MARICOPA-010":  "2026-04-15",  # Nguyen psittacosis
    "HH-AZ-PINAL-011":     "2026-04-23",  # Sanchez tularemia
    "HH-AZ-NAVAJO-012":    "2026-04-20",  # Yazzie salmonellosis
}


# Outbreak diseases per household — used for cross-species linkage and
# contact-tracing scoring.
OUTBREAK_DISEASES: Dict[str, Dict[str, str]] = {
    "HH-AZ-PIMA-001":      {"disease": "valley_fever",   "snomed_root": "5294002",   "transmission": "environmental"},
    "HH-AZ-PINAL-002":     {"disease": "ehrlichiosis",   "snomed_root": "27944800",  "transmission": "vector_tick"},
    "HH-AZ-MARICOPA-003":  {"disease": "hantavirus",     "snomed_root": "59881000",  "transmission": "rodent_excreta"},
    "HH-AZ-YUMA-004":      {"disease": "leptospirosis",  "snomed_root": "26726000",  "transmission": "water_animal"},
    "HH-AZ-COCONINO-005":  {"disease": None,             "snomed_root": None,        "transmission": None},
    "HH-AZ-APACHE-006":    {"disease": "plague",         "snomed_root": "58750007",  "transmission": "vector_flea"},
    "HH-AZ-COCHISE-007":   {"disease": "west_nile",      "snomed_root": "23502006",  "transmission": "vector_mosquito"},
    "HH-AZ-MOHAVE-008":    {"disease": "rabies",         "snomed_root": "14168008",  "transmission": "animal_bite"},
    "HH-AZ-SANTACRUZ-009": {"disease": "q_fever",        "snomed_root": "75570004",  "transmission": "livestock_aerosol"},
    "HH-AZ-MARICOPA-010":  {"disease": "psittacosis",    "snomed_root": "75116005",  "transmission": "bird_aerosol"},
    "HH-AZ-PINAL-011":     {"disease": "tularemia",      "snomed_root": "76664006",  "transmission": "vector_tick_rabbit"},
    "HH-AZ-NAVAJO-012":    {"disease": "salmonellosis",  "snomed_root": "302231008", "transmission": "reptile_contact"},
}


# Pinal county vector anomaly window — generates additional positive encounters
# beyond the hand-crafted households.
PINAL_VECTOR_WINDOW = ("2026-03-25", "2026-04-22")
PINAL_FIPS = "04021"

# Cluster window in days around the index date
CLUSTER_WINDOW_DAYS = 60


def _to_date(s: str) -> datetime:
    return datetime.strptime(s[:10], "%Y-%m-%d")


def is_outbreak_household(household_id: str) -> bool:
    return OUTBREAK_INDEX_DATES.get(household_id) is not None


def label_encounter(encounter: dict, household: dict) -> Tuple[int, str]:
    """
    Return (label, reason) for one encounter.

    label: 1 = positive (part of cluster), 0 = negative
    reason: short string explaining the label decision
    """
    hid = encounter.get("household_id")
    if not hid:
        return 0, "no household"

    enc_date = _to_date(encounter["period"]["start"])

    # Tier 1: hand-crafted outbreak household
    idx_str = OUTBREAK_INDEX_DATES.get(hid)
    if idx_str is not None:
        idx_date = _to_date(idx_str)
        delta_days = abs((enc_date - idx_date).days)
        if delta_days <= CLUSTER_WINDOW_DAYS:
            return 1, f"in cluster window (Δ={delta_days}d from {hid} index)"

    # Tier 2: Pinal vector anomaly window with tick-borne CC
    county_fips = household.get("county", {}).get("fips")
    if county_fips == PINAL_FIPS:
        win_start = _to_date(PINAL_VECTOR_WINDOW[0])
        win_end = _to_date(PINAL_VECTOR_WINDOW[1])
        if win_start <= enc_date <= win_end:
            cc = (encounter.get("chief_complaint") or "").lower()
            tick_indicators = ["fever", "rash", "ehrlichiosis", "rmsf", "rocky mountain", "tick", "headache"]
            if any(t in cc for t in tick_indicators):
                return 1, "Pinal vector anomaly window + tick-borne CC"

    return 0, "background"


def build_labels(households: List[dict], encounters: List[dict]) -> List[dict]:
    """
    Walk every encounter and produce a label record.
    Returns list of dicts with encounter_id, household_id, subject_ref, period,
    label, reason.
    """
    hh_by_id = {h["household_id"]: h for h in households}
    out = []
    for enc in encounters:
        h = hh_by_id.get(enc["household_id"])
        if h is None:
            continue
        label, reason = label_encounter(enc, h)
        out.append({
            "encounter_id":  enc["id"],
            "household_id":  enc["household_id"],
            "subject_ref":   enc["subject"]["reference"],
            "subject_label": enc["subject"].get("label", ""),
            "subject_kind":  enc["subject"].get("kind", "Person"),
            "period_start":  enc["period"]["start"],
            "label":         label,
            "reason":        reason,
        })
    return out


if __name__ == "__main__":
    import json
    from pathlib import Path
    base = Path(__file__).resolve().parents[2]
    hh = json.load(open(base / "data/synthetic/households.json"))["households"]
    enc = json.load(open(base / "data/synthetic/encounters.json"))["encounters"]
    labels = build_labels(hh, enc)
    pos = sum(1 for r in labels if r["label"] == 1)
    print(f"total={len(labels)}  positive={pos}  negative={len(labels) - pos}  prevalence={pos / len(labels):.3%}")

    out_path = base / "data/synthetic/labels.json"
    json.dump({"_metadata": {"n": len(labels), "n_positive": pos}, "labels": labels}, open(out_path, "w"), indent=2)
    print(f"wrote {out_path}")
