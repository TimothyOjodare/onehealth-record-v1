"""
Feature engineering for the cluster-prediction task.

Produces a wide feature matrix from encounters + households + surveillance,
ready for sklearn. Features are designed to be:
- interpretable (every column has a clinical or PH meaning)
- leak-free (no peeking at future encounters within the cluster window)
- the kind of features your professor described for tabular medical ML
  (demographics + vitals + chief-complaint keywords + household + environment + temporal)
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Chief-complaint keyword bags. We bucket the open-text CC into clinically
# meaningful categories that map to zoonotic disease syndromes.
CC_KEYWORDS = {
    "respiratory":  ["cough", "shortness", "dyspnea", "pneumonia", "respiratory", "sob"],
    "fever":        ["fever", "febrile", "temp", "pyrexia"],
    "neuro":        ["headache", "confusion", "encephal", "altered mental", "neuro", "seizure"],
    "gi":           ["diarrhea", "vomit", "nausea", "gastro", "abdominal"],
    "rash_skin":    ["rash", "petechiae", "lesion", "skin", "bite", "wound"],
    "musculo":      ["myalgia", "arthralgia", "muscle", "joint"],
    "fatigue":      ["fatigue", "lethargy", "malaise", "weakness"],
    "exposure":     ["exposure", "contact", "bitten", "scratched", "soil", "dust", "tick", "rodent"],
    "zoo_specific": ["valley fever", "cocci", "ehrlich", "rmsf", "lepto", "hantavirus", "plague", "west nile",
                     "rabies", "q fever", "psittacosis", "tularemia", "salmonell"],
}


def _to_date(s: str) -> datetime:
    return datetime.strptime(s[:10], "%Y-%m-%d")


def _parse_bp(bp: str) -> Tuple[float, float]:
    if not bp or "/" not in str(bp):
        return np.nan, np.nan
    try:
        a, b = str(bp).split("/")
        return float(a.strip()), float(b.strip())
    except Exception:
        return np.nan, np.nan


def _age_at(birth: str, on_date: str) -> float:
    if not birth:
        return np.nan
    try:
        b = _to_date(birth)
        d = _to_date(on_date)
        return (d - b).days / 365.25
    except Exception:
        return np.nan


def _cc_features(cc: str) -> Dict[str, int]:
    cc_l = (cc or "").lower()
    return {f"cc_{k}": int(any(kw in cc_l for kw in v)) for k, v in CC_KEYWORDS.items()}


def _household_summary(h: dict) -> Dict[str, float]:
    humans = h.get("humans", []) or []
    animals = h.get("animals", []) or []
    species_set = set()
    for a in animals:
        sp = a.get("species", {})
        if isinstance(sp, dict):
            species_set.add(sp.get("code", "unknown"))
    return {
        "hh_n_humans":            len(humans),
        "hh_n_animals":           len(animals),
        "hh_has_dog":             int("dog" in species_set),
        "hh_has_cat":             int("cat" in species_set),
        "hh_has_livestock":       int(bool(species_set & {"cow", "goat", "sheep", "chicken", "horse"})),
        "hh_has_bird":            int(bool(species_set & {"parrot", "chicken", "bird"})),
        "hh_has_reptile":         int(bool(species_set & {"reptile", "lizard", "snake", "turtle", "bearded_dragon"})),
        # NB: hh_n_recorded_cond removed — it leaks the outbreak label because
        # all hand-crafted households have recorded conditions and all
        # procedural negatives have zero. We instead let the model use the
        # leak-free 90-day windowed cross-species features.
    }


def _county_features(h: dict) -> Dict[str, float]:
    co = h.get("county", {}) or {}
    return {
        "co_population":          float(co.get("population", 0) or 0),
        "co_epa_eqi":             float(co.get("epa_eqi", 0.0) or 0.0),
        "co_cocci_high":          int((co.get("cocci_endemic") or "low") == "high"),
        "co_cocci_med":           int((co.get("cocci_endemic") or "low") == "medium"),
        "co_is_rural":            int(float(co.get("population", 0) or 0) < 100_000),
        "co_is_tribal":           int(co.get("name") in {"Apache", "Navajo"}),
        "co_lat":                 float(co.get("lat", 0.0) or 0.0),
        "co_lon":                 float(co.get("lon", 0.0) or 0.0),
    }


def _household_recent_activity(
    enc: dict,
    encounters_by_hh: Dict[str, List[dict]],
) -> Dict[str, float]:
    """Encounter density in the same household over the last 30 / 90 days."""
    hid = enc["household_id"]
    enc_date = _to_date(enc["period"]["start"])
    recent_30 = 0
    recent_90 = 0
    distinct_subjects_90 = set()
    distinct_cc_90 = set()
    for other in encounters_by_hh.get(hid, []):
        if other["id"] == enc["id"]:
            continue
        try:
            other_date = _to_date(other["period"]["start"])
        except Exception:
            continue
        if other_date >= enc_date:
            continue  # don't peek into the future
        days = (enc_date - other_date).days
        if 0 < days <= 30:
            recent_30 += 1
        if 0 < days <= 90:
            recent_90 += 1
            distinct_subjects_90.add(other["subject"]["reference"])
            distinct_cc_90.add((other.get("chief_complaint") or "").lower()[:40])
    return {
        "hh_enc_30d":             recent_30,
        "hh_enc_90d":             recent_90,
        "hh_distinct_subjects_90d":   len(distinct_subjects_90),
        "hh_distinct_cc_90d":     len(distinct_cc_90),
    }


def _cross_species_features(enc: dict, household: dict) -> Dict[str, float]:
    """Has the household had a confirmed condition in another species recently?"""
    enc_date = _to_date(enc["period"]["start"])
    subject_ref = enc["subject"]["reference"]
    same_root_other_species = 0
    snomed_codes_in_household = set()
    for c in household.get("conditions", []) or []:
        if c.get("subject", {}).get("reference") == subject_ref:
            continue  # same patient
        try:
            o_date = _to_date(c.get("onsetDateTime", "1900-01-01"))
        except Exception:
            continue
        days = (enc_date - o_date).days
        if 0 <= days <= 90:
            for code in c.get("code", {}).get("coding", []) or []:
                snomed_codes_in_household.add(code.get("code"))
                same_root_other_species += 1
    return {
        "hh_other_species_cond_90d":   int(same_root_other_species > 0),
        "hh_distinct_codes_90d":       len(snomed_codes_in_household),
    }


def _surveillance_features(enc: dict, surveillance_by_county: Dict[str, dict]) -> Dict[str, float]:
    """County-level surveillance signal nearest to the encounter date."""
    co = enc.get("_county_fips")
    if co is None:
        return {"surv_z_score": 0.0, "surv_vector_anomaly": 0, "surv_recent_cases": 0.0}
    sig = surveillance_by_county.get(co, {})
    return {
        "surv_z_score":           float(sig.get("z_score", 0.0)),
        "surv_vector_anomaly":    int(sig.get("vector_anomaly", False)),
        "surv_recent_cases":      float(sig.get("recent_case_count", 0.0)),
    }


def _temporal_features(d: str) -> Dict[str, float]:
    dt = _to_date(d)
    return {
        "month":                  dt.month,
        "is_summer":              int(dt.month in (6, 7, 8)),
        "is_monsoon":             int(dt.month in (7, 8, 9)),  # AZ monsoon → vector spike
        "day_of_year":            dt.timetuple().tm_yday,
    }


def _vital_features(vitals: dict) -> Dict[str, float]:
    if not vitals:
        return {
            "v_temp_f": np.nan, "v_hr": np.nan, "v_rr": np.nan, "v_spo2": np.nan,
            "v_bp_sys": np.nan, "v_bp_dia": np.nan, "v_glucose": np.nan,
            "v_fever": 0, "v_tachy": 0, "v_tachypnea": 0, "v_hypoxia": 0,
        }
    bp_s, bp_d = _parse_bp(vitals.get("bp"))
    temp = float(vitals.get("temp_f", np.nan)) if vitals.get("temp_f") is not None else np.nan
    hr = float(vitals.get("hr", np.nan)) if vitals.get("hr") is not None else np.nan
    rr = float(vitals.get("rr", np.nan)) if vitals.get("rr") is not None else np.nan
    spo2 = float(vitals.get("spo2", np.nan)) if vitals.get("spo2") is not None else np.nan
    return {
        "v_temp_f":              temp,
        "v_hr":                  hr,
        "v_rr":                  rr,
        "v_spo2":                spo2,
        "v_bp_sys":              bp_s,
        "v_bp_dia":              bp_d,
        "v_glucose":             float(vitals.get("glucose_mg_dl", np.nan)) if vitals.get("glucose_mg_dl") is not None else np.nan,
        "v_fever":               int((temp or 0) > 100.4),
        "v_tachy":               int((hr or 0) > 100),
        "v_tachypnea":           int((rr or 0) > 20),
        "v_hypoxia":             int(0 < (spo2 or 100) < 94),
    }


def _build_household_lookups(households: List[dict]) -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Map household_id → household, and subject_ref → (household, member_record)."""
    hh_by_id = {}
    subject_to_hh = {}
    for h in households:
        hh_by_id[h["household_id"]] = h
        for member in (h.get("humans", []) or []):
            ref = f"Patient/{member['id']}"
            subject_to_hh[ref] = (h, member, "Person")
        for animal in (h.get("animals", []) or []):
            ref = f"AnimalPatient/{animal['id']}"
            subject_to_hh[ref] = (h, animal, "Animal")
    return hh_by_id, subject_to_hh


def _build_surveillance_lookup(surveillance: dict) -> Dict[str, dict]:
    """Build a per-county snapshot of recent surveillance signal.

    We summarize: 4-week z-score peak, whether vector_anomaly flagged any time
    in the most recent month, and recent case count.
    """
    by_county: Dict[str, dict] = defaultdict(lambda: {"z_score": 0.0, "vector_anomaly": False, "recent_case_count": 0.0})

    # ADHS disease counts: aggregate recent (2026) per-county case counts
    for row in surveillance.get("adhs_disease_counts", []) or []:
        co = row.get("county_fips")
        if not co:
            continue
        # Only consider 2026 month >= 1 as "recent" surveillance signal
        if int(row.get("year", 0)) >= 2026:
            by_county[co]["recent_case_count"] += float(row.get("case_count", 0))

    # Compute a county-level z-score from the per-month counts within 2026
    monthly_counts = defaultdict(list)
    for row in surveillance.get("adhs_disease_counts", []) or []:
        if int(row.get("year", 0)) >= 2025:
            monthly_counts[row["county_fips"]].append(float(row.get("case_count", 0)))
    import statistics
    for co, vals in monthly_counts.items():
        if len(vals) >= 2:
            mu = statistics.fmean(vals)
            sigma = statistics.pstdev(vals) or 1.0
            if vals:
                by_county[co]["z_score"] = (max(vals) - mu) / sigma

    # Vector surveillance: identify counties with anomalous tick burden
    vector_by_county = defaultdict(list)
    for row in surveillance.get("vector_surveillance", []) or []:
        co = row.get("county_fips")
        if co:
            vector_by_county[co].append(float(row.get("ticks_per_trap_hour", 0.0)))
    for co, vals in vector_by_county.items():
        if len(vals) >= 4:
            mu = statistics.fmean(vals)
            sigma = statistics.pstdev(vals) or 1.0
            recent = vals[-4:]   # last 4 weekly observations
            recent_mean = statistics.fmean(recent)
            z = (recent_mean - mu) / sigma if sigma > 0 else 0
            if z > 3.0:
                by_county[co]["vector_anomaly"] = True

    return dict(by_county)


def build_features(
    encounters: List[dict],
    households: List[dict],
    surveillance: dict,
) -> pd.DataFrame:
    """
    Returns a DataFrame indexed by encounter_id with all engineered features.
    """
    hh_by_id, subject_to_hh = _build_household_lookups(households)

    encounters_by_hh: Dict[str, List[dict]] = defaultdict(list)
    for e in encounters:
        encounters_by_hh[e["household_id"]].append(e)

    surveillance_by_county = _build_surveillance_lookup(surveillance)

    rows = []
    for enc in encounters:
        hid = enc["household_id"]
        h = hh_by_id.get(hid)
        if h is None:
            continue
        enc["_county_fips"] = (h.get("county") or {}).get("fips")

        subject_ref = enc["subject"]["reference"]
        subject_record = subject_to_hh.get(subject_ref, (None, None, "Person"))[1]

        feat = {
            "encounter_id":       enc["id"],
            "household_id":       hid,
            "subject_ref":        subject_ref,
            "period_start":       enc["period"]["start"],
            "is_animal":          int(enc["subject"].get("kind", "Person") == "Animal"),
        }

        # Demographic
        if subject_record is not None:
            birth = subject_record.get("birthDate")
            feat["age_years"] = _age_at(birth, enc["period"]["start"])
            gender = subject_record.get("gender") or subject_record.get("sex") or ""
            feat["sex_female"] = int(str(gender).lower().startswith("f"))
        else:
            feat["age_years"] = np.nan
            feat["sex_female"] = 0

        # Vitals
        feat.update(_vital_features(enc.get("vitals") or {}))
        # Chief complaint keyword bags
        feat.update(_cc_features(enc.get("chief_complaint") or ""))
        # Household summary
        feat.update(_household_summary(h))
        # County / environment
        feat.update(_county_features(h))
        # Recent household activity (no leak)
        feat.update(_household_recent_activity(enc, encounters_by_hh))
        # Cross-species linkage signal
        feat.update(_cross_species_features(enc, h))
        # Surveillance signal
        feat.update(_surveillance_features(enc, surveillance_by_county))
        # Temporal
        feat.update(_temporal_features(enc["period"]["start"]))

        rows.append(feat)

    df = pd.DataFrame(rows)
    return df


if __name__ == "__main__":
    import json
    from pathlib import Path
    base = Path(__file__).resolve().parents[2]
    hh = json.load(open(base / "data/synthetic/households.json"))["households"]
    enc = json.load(open(base / "data/synthetic/encounters.json"))["encounters"]
    surv = json.load(open(base / "data/synthetic/surveillance.json"))

    # Adapt surveillance file shape if needed
    surv_data = surv if isinstance(surv, dict) else {}

    df = build_features(enc, hh, surv_data)
    print(f"feature matrix: {df.shape}")
    print("non-key columns:", df.columns.tolist())
    print("\nfirst 3 rows:")
    print(df.head(3).T)

    out_path = base / "data/synthetic/features.parquet"
    df.to_parquet(out_path)
    print(f"\nwrote {out_path}")
