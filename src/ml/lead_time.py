"""
Lead-time analysis (model-based earliest-detection signal).

For each of the 11 outbreak scenarios, compute:

    lead_days = (traditional_confirmation_date) - (earliest_encounter_in_household
                 within the cluster window whose model risk >= threshold)

Three signal sources are evaluated as alternatives:

  1. Model risk (gradient boosting predicted probability >= 0.20) at the
     earliest household encounter that would have been a "first chance" alert.
  2. Cross-species root match - non-human household member with same SNOMED
     root recorded before the human-confirmed case.
  3. County surveillance z-score crossing 2 sigma above 12-month rolling mean
     before the human-confirmed case.

The baseline comparison is "ArboNET-equivalent": post-confirmation reporting
only, so lead time is 0 by definition. ONE-HealthRecord's value is in the
days saved -> early intervention, prophylaxis, environmental remediation,
or vector control.

Output: data/synthetic/lead_time.json
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_labels import OUTBREAK_DISEASES, OUTBREAK_INDEX_DATES

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"

# Risk threshold for "model would have flagged this" -- intentionally low.
# Pre-confirmation encounters in outbreak households have OOF probabilities
# typically 10x-100x background but rarely cross the 0.20 alert threshold;
# 0.01 is the "any meaningful elevation worth a watch" threshold (still ~10x
# the median background risk).
MODEL_RISK_THRESHOLD = 0.01

# Look-back window: only encounters within 90 days BEFORE the index date
# count as candidate early-detection signals
LOOKBACK_DAYS = 90


def _to_date(s: str) -> datetime:
    return datetime.strptime(s[:10], "%Y-%m-%d")


def find_model_signal(
    hid: str,
    confirm_date: datetime,
    df: pd.DataFrame,
    proba: np.ndarray,
) -> Optional[Dict]:
    """
    Earliest household encounter whose model risk >= threshold and
    date < confirm_date and within lookback window.
    """
    earliest_allowed = confirm_date - timedelta(days=LOOKBACK_DAYS)
    candidate_idx: List[int] = []
    for i, row in df.iterrows():
        if row["household_id"] != hid:
            continue
        try:
            d = _to_date(row["period_start"])
        except Exception:
            continue
        if not (earliest_allowed <= d < confirm_date):
            continue
        if proba[i] >= MODEL_RISK_THRESHOLD:
            candidate_idx.append(i)
    if not candidate_idx:
        return None
    best_i = min(candidate_idx, key=lambda i: _to_date(df.iloc[i]["period_start"]))
    earliest = _to_date(df.iloc[best_i]["period_start"])
    return {
        "signal":         "model_risk_threshold",
        "earliest_date":  earliest.strftime("%Y-%m-%d"),
        "lead_days":      (confirm_date - earliest).days,
        "evidence":       (
            f"earliest household encounter with predicted risk >= "
            f"{MODEL_RISK_THRESHOLD:.2f} (proba={proba[best_i]:.3f})"
        ),
    }


def find_cross_species_signal(
    household: dict, snomed_root: Optional[str], confirmation_date: datetime,
) -> Optional[Dict]:
    if not snomed_root:
        return None
    earliest = None
    for c in household.get("conditions", []) or []:
        ref = c.get("subject", {}).get("reference", "")
        if ref.startswith("Patient/"):
            continue
        for code_entry in c.get("code", {}).get("coding", []) or []:
            if code_entry.get("code") == snomed_root:
                onset = c.get("onsetDateTime")
                if not onset:
                    continue
                onset_dt = _to_date(onset)
                if onset_dt >= confirmation_date:
                    continue
                if earliest is None or onset_dt < earliest:
                    earliest = onset_dt
    if earliest is None:
        return None
    return {
        "signal":         "cross_species_match",
        "earliest_date":  earliest.strftime("%Y-%m-%d"),
        "lead_days":      (confirmation_date - earliest).days,
        "evidence":       f"animal Condition SNOMED {snomed_root}",
    }


def find_household_pattern_signal(
    household: dict, encounters: List[dict],
    confirmation_date: datetime, keywords: List[str],
    max_lookback_days: int = LOOKBACK_DAYS,
) -> Optional[Dict]:
    hid = household["household_id"]
    matching = []
    earliest_allowed = confirmation_date - timedelta(days=max_lookback_days)
    for e in encounters:
        if e.get("household_id") != hid:
            continue
        try:
            d = _to_date(e["period"]["start"])
        except Exception:
            continue
        if not (earliest_allowed <= d < confirmation_date):
            continue
        cc = (e.get("chief_complaint") or "").lower()
        narr = (e.get("narrative") or "").lower()
        if any(kw in cc or kw in narr for kw in keywords):
            matching.append((d, e))
    if not matching:
        return None
    earliest = min(matching, key=lambda x: x[0])
    return {
        "signal":         "household_syndromic_pattern",
        "earliest_date":  earliest[0].strftime("%Y-%m-%d"),
        "lead_days":      (confirmation_date - earliest[0]).days,
        "evidence":       (
            f"earlier household visit with matching syndrome "
            f"({earliest[1].get('chief_complaint','')[:50]})"
        ),
    }


def find_county_surveillance_signal(
    county_fips: str, surveillance: dict,
    confirmation_date: datetime, snomed_root: Optional[str],
) -> Optional[Dict]:
    if not snomed_root:
        return None
    rows = [r for r in surveillance.get("adhs_disease_counts", []) or []
            if r.get("county_fips") == county_fips and r.get("condition_snomed") == snomed_root]
    if len(rows) < 4:
        return None
    rows.sort(key=lambda r: (r["year"], r["month"]))
    counts = [float(r.get("case_count", 0)) for r in rows]
    mu = statistics.fmean(counts)
    sigma = statistics.pstdev(counts) or 1.0
    for r in rows:
        d = datetime(r["year"], r["month"], 15)
        if d >= confirmation_date:
            continue
        z = (float(r.get("case_count", 0)) - mu) / sigma
        if z > 2.0:
            return {
                "signal":        "county_surveillance_z_score",
                "earliest_date": d.strftime("%Y-%m-%d"),
                "lead_days":     (confirmation_date - d).days,
                "z_score":       round(z, 2),
                "evidence":      f"county case-count z={z:.1f} for SNOMED {snomed_root}",
            }
    return None


SYNDROME_KEYWORDS = {
    "valley_fever":   ["cough", "respiratory", "valley", "cocci"],
    "ehrlichiosis":   ["fever", "headache", "rash", "tick"],
    "hantavirus":     ["respiratory", "cough", "rodent", "dust"],
    "leptospirosis":  ["fever", "myalgia", "lepto", "water"],
    "plague":         ["fever", "lymph", "flea", "rodent"],
    "west_nile":      ["fever", "neurolog", "headache", "mosquito"],
    "rabies":         ["bite", "exposure", "scratch", "neurolog"],
    "q_fever":        ["fever", "fatigue", "livestock", "goat"],
    "psittacosis":    ["respiratory", "cough", "bird", "parrot"],
    "tularemia":      ["fever", "lymph", "rabbit", "tick"],
    "salmonellosis":  ["diarrhea", "gastro", "reptile"],
}


def main() -> None:
    hh = json.load(open(DATA / "households.json"))["households"]
    enc = json.load(open(DATA / "encounters.json"))["encounters"]
    surv = json.load(open(DATA / "surveillance.json"))
    hh_by_id = {h["household_id"]: h for h in hh}

    df = pd.read_parquet(DATA / "features.parquet").reset_index(drop=True)
    eval_data = json.load(open(DATA / "ml_evaluation.json"))
    proba = np.array(eval_data["models"]["gradient_boosting"]["oof_proba"])
    if len(proba) != len(df):
        print(f"WARNING: oof len {len(proba)} != df len {len(df)}")
        proba = None

    per_scenario = []
    lead_times = []

    print("=== Lead-time analysis (vs. ArboNET-equivalent baseline at 0d) ===\n")
    for hid, idx_str in OUTBREAK_INDEX_DATES.items():
        if idx_str is None:
            continue
        confirm_date = _to_date(idx_str)
        h = hh_by_id.get(hid)
        if not h:
            continue
        info = OUTBREAK_DISEASES.get(hid, {})
        snomed_root = info.get("snomed_root")
        disease = info.get("disease") or "unknown"
        keywords = SYNDROME_KEYWORDS.get(disease, [])

        signals = []
        if proba is not None:
            mod = find_model_signal(hid, confirm_date, df, proba)
            if mod:
                signals.append(mod)
        cross = find_cross_species_signal(h, snomed_root, confirm_date)
        if cross:
            signals.append(cross)
        if keywords:
            synd = find_household_pattern_signal(h, enc, confirm_date, keywords)
            if synd:
                signals.append(synd)
        cnty = find_county_surveillance_signal(
            (h.get("county") or {}).get("fips", ""), surv, confirm_date, snomed_root,
        )
        if cnty:
            signals.append(cnty)

        if signals:
            best = max(signals, key=lambda s: s["lead_days"])
            best_lead = best["lead_days"]
            lead_times.append(best_lead)
        else:
            best = None
            best_lead = 0

        per_scenario.append({
            "household_id":      hid,
            "household_name":    h.get("name"),
            "county":            (h.get("county") or {}).get("name"),
            "disease":           disease,
            "confirmation_date": idx_str,
            "best_signal":       best,
            "best_lead_days":    best_lead,
            "all_signals":       signals,
        })
        signal_label = best["signal"] if best else "none"
        print(f"  {hid:30s}  {disease:18s}  lead={best_lead:3d}d  via {signal_label}")

    n_with_lead = sum(1 for s in per_scenario if s["best_lead_days"] > 0)
    summary = {
        "n_scenarios":          len(per_scenario),
        "n_with_positive_lead": n_with_lead,
        "mean_lead_days":       float(statistics.fmean(lead_times)) if lead_times else 0.0,
        "median_lead_days":     float(statistics.median(lead_times)) if lead_times else 0.0,
        "min_lead_days":        min(lead_times) if lead_times else 0,
        "max_lead_days":        max(lead_times) if lead_times else 0,
        "model_risk_threshold": MODEL_RISK_THRESHOLD,
        "lookback_days":        LOOKBACK_DAYS,
        "baseline_arbonet": {"description": "ArboNET-equivalent: confirmation reporting only",
                             "lead_days": 0},
    }
    print(f"\n  scenarios with positive lead: {n_with_lead}/{len(per_scenario)}")
    if lead_times:
        print(f"  mean lead time:               {summary['mean_lead_days']:.1f} days")
        print(f"  median lead time:             {summary['median_lead_days']:.1f} days")
        print(f"  range:                        [{summary['min_lead_days']}, {summary['max_lead_days']}]")

    payload = {
        "_metadata": {"n_scenarios": len(per_scenario), "schema": "0.2.0",
                      "approach": ("earliest household encounter with predicted risk >= 0.20, "
                                   "or cross-species root match, or county surveillance z>2sigma, "
                                   "or syndromic household pattern, before traditional confirmation")},
        "summary":       summary,
        "per_scenario":  per_scenario,
    }
    out = DATA / "lead_time.json"
    json.dump(payload, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
