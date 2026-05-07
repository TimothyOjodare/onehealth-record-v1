"""
Contact tracing module.

Given a confirmed index case, traces three tiers of contacts:
- Tier 1 — household: same household humans + animals (close contact)
- Tier 2 — shared exposure: same exposure pathway (e.g. same canal water,
  same dust storm region, same workplace), pulled from environment + narrative
- Tier 3 — vector / spatial: same county within an active vector anomaly window

Each contact is risk-scored using the trained gradient boosting model from
train_models.py. Public-health-grade evaluation:

  - Sensitivity (recall):  of true secondary cases, what fraction did we catch?
  - Precision:             of contacts flagged, what fraction were true secondaries?
  - Mean lead time:        days between contact-tracing flag and the secondary
                            case's own clinical presentation
  - Contacts per index:    operational burden estimate

Outputs:
- data/synthetic/contact_tracing.json — for the demo + report
"""
from __future__ import annotations

import json
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
import pandas as pd

from build_labels import (  # type: ignore[import-not-found]
    OUTBREAK_DISEASES,
    OUTBREAK_INDEX_DATES,
    PINAL_FIPS,
    PINAL_VECTOR_WINDOW,
)


def _drop_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["encounter_id", "household_id", "subject_ref", "period_start"])


def _to_date(s: str) -> datetime:
    return datetime.strptime(s[:10], "%Y-%m-%d")


def _members_of(h: dict) -> List[Tuple[str, str, str]]:
    """Yield (subject_ref, name, kind) for all humans+animals in a household."""
    out = []
    for member in (h.get("humans", []) or []):
        ref = f"Patient/{member['id']}"
        name_parts = (member.get("name") or [{}])[0]
        full = " ".join(name_parts.get("given", []) + [name_parts.get("family", "")]).strip()
        out.append((ref, full or "Patient", "Person"))
    for animal in (h.get("animals", []) or []):
        ref = f"AnimalPatient/{animal['id']}"
        out.append((ref, animal.get("name", "Animal"), "Animal"))
    return out


def trace_contacts(
    index_household_id: str,
    index_date: str,
    households: List[dict],
    encounters: List[dict],
    transmission: str,
    window_days: int = 14,
) -> List[dict]:
    """
    Build the contact list for one index case.

    Returns a list of contact records with tier, distance, days from index,
    and metadata for risk scoring.
    """
    hh_by_id = {h["household_id"]: h for h in households}
    index_h = hh_by_id.get(index_household_id)
    if index_h is None:
        return []
    index_dt = _to_date(index_date)
    contacts: List[dict] = []

    # Tier 1: same household
    for ref, name, kind in _members_of(index_h):
        contacts.append({
            "tier":               1,
            "tier_label":         "Household",
            "subject_ref":        ref,
            "subject_name":       name,
            "subject_kind":       kind,
            "household_id":       index_household_id,
            "household_name":     index_h.get("name"),
            "county":             (index_h.get("county") or {}).get("name"),
            "rationale":          f"Direct household contact in {index_h.get('name')} household",
            "transmission_route": transmission or "unknown",
        })

    # Tier 2: shared exposure (env-driven). For environmental-transmission
    # outbreaks, broaden to other households with a matching environmental
    # signature in the same county.
    if transmission in {"environmental", "vector_tick", "vector_mosquito", "vector_flea",
                         "water_animal", "rodent_excreta", "vector_tick_rabbit", "livestock_aerosol"}:
        index_county = (index_h.get("county") or {}).get("fips")
        for h in households:
            if h["household_id"] == index_household_id:
                continue
            if (h.get("county") or {}).get("fips") != index_county:
                continue
            # Limit to close shared-exposure neighbors: handcrafted households
            # in same county represent shared environmental setting
            for ref, name, kind in _members_of(h):
                contacts.append({
                    "tier":               2,
                    "tier_label":         "Shared exposure",
                    "subject_ref":        ref,
                    "subject_name":       name,
                    "subject_kind":       kind,
                    "household_id":       h["household_id"],
                    "household_name":     h.get("name"),
                    "county":             (h.get("county") or {}).get("name"),
                    "rationale":          f"Same county ({(index_h.get('county') or {}).get('name')}), shared environmental risk for {transmission}",
                    "transmission_route": transmission,
                })

    # Tier 3: vector / spatial — county-level mosquito/tick/etc anomaly
    if transmission in {"vector_tick", "vector_mosquito", "vector_flea", "vector_tick_rabbit"}:
        index_county = (index_h.get("county") or {}).get("fips")
        # If Pinal vector anomaly is active, county-wide spatial flag
        in_pinal_window = (
            index_county == PINAL_FIPS and
            _to_date(PINAL_VECTOR_WINDOW[0]) <= index_dt <= _to_date(PINAL_VECTOR_WINDOW[1])
        )
        if in_pinal_window:
            for h in households:
                if h["household_id"] == index_household_id:
                    continue
                if (h.get("county") or {}).get("fips") != index_county:
                    continue
                if h["household_id"] in {c["household_id"] for c in contacts}:
                    continue
                for ref, name, kind in _members_of(h):
                    contacts.append({
                        "tier":               3,
                        "tier_label":         "Vector spatial",
                        "subject_ref":        ref,
                        "subject_name":       name,
                        "subject_kind":       kind,
                        "household_id":       h["household_id"],
                        "household_name":     h.get("name"),
                        "county":             (h.get("county") or {}).get("name"),
                        "rationale":          "Active vector anomaly in same county",
                        "transmission_route": transmission,
                    })

    # Annotate each contact with their most-recent encounter post-index
    enc_by_subject: Dict[str, List[dict]] = defaultdict(list)
    for e in encounters:
        enc_by_subject[e["subject"]["reference"]].append(e)
    for subj, encs in enc_by_subject.items():
        encs.sort(key=lambda x: x["period"]["start"])

    for c in contacts:
        encs = enc_by_subject.get(c["subject_ref"], [])
        future = [e for e in encs if _to_date(e["period"]["start"]) >= index_dt]
        if future:
            first = future[0]
            c["next_encounter_date"] = first["period"]["start"]
            c["days_until_next_encounter"] = (_to_date(first["period"]["start"]) - index_dt).days
            c["next_encounter_id"] = first["id"]
        else:
            c["next_encounter_date"] = None
            c["days_until_next_encounter"] = None
            c["next_encounter_id"] = None

    return contacts


def score_contacts(
    contacts: List[dict],
    encounters_by_id: Dict[str, dict],
    feature_df: pd.DataFrame,
    model,
) -> List[dict]:
    """Add a model-derived risk score and recommended action for each contact."""
    feature_df_indexed = feature_df.set_index("encounter_id")
    feature_cols = [c for c in feature_df.columns if c not in {"encounter_id", "household_id", "subject_ref", "period_start"}]

    for c in contacts:
        eid = c.get("next_encounter_id")
        if eid and eid in feature_df_indexed.index:
            row = feature_df_indexed.loc[[eid]][feature_cols]
            c["risk_score"] = float(model.predict_proba(row)[0, 1])
        else:
            # No encounter yet — use household + tier as a heuristic prior
            tier_prior = {1: 0.45, 2: 0.18, 3: 0.10}
            c["risk_score"] = tier_prior.get(c["tier"], 0.05)

        # Recommended action
        rs = c["risk_score"]
        if rs >= 0.50:
            c["recommended_action"] = "Active outreach and same-day testing"
        elif rs >= 0.20:
            c["recommended_action"] = "Outreach for symptom screening within 48h"
        elif rs >= 0.05:
            c["recommended_action"] = "Passive monitoring with self-report instructions"
        else:
            c["recommended_action"] = "Routine surveillance"

    return contacts


def evaluate_contact_tracing(
    all_traces: Dict[str, List[dict]],
    labels: List[dict],
    encounters: List[dict],
    risk_thresholds: List[float] = [0.05, 0.10, 0.20, 0.30, 0.50],
) -> Dict:
    """
    PH-grade evaluation: sensitivity, precision, lead time, burden.

    A "true secondary case" is any encounter labeled positive that occurs in
    the index household AT or AFTER the index date but is NOT the index
    encounter itself.

    Pre-index positives are reported separately as "could not be caught
    prospectively" — the limitation we want to be honest about.

    The evaluation is computed at multiple risk thresholds to show the
    operational tradeoff curve (typical PH program reports this as a
    "triage table").
    """
    # Build lookups
    label_by_enc = {r["encounter_id"]: r for r in labels}
    enc_by_id = {e["id"]: e for e in encounters}

    # Determine pre/post-index positives per household
    pre_index_positives_total = 0
    post_index_positives_total = 0
    pre_per_hh = defaultdict(int)
    post_secondaries_by_hh: Dict[str, set] = defaultdict(set)

    for r in labels:
        if r["label"] != 1:
            continue
        idx_date_str = OUTBREAK_INDEX_DATES.get(r["household_id"])
        if not idx_date_str:
            continue
        enc_dt = _to_date(r["period_start"])
        idx_dt = _to_date(idx_date_str)
        # Identify the index encounter itself (occurs on the index date)
        if r["period_start"] == idx_date_str:
            continue
        if enc_dt < idx_dt:
            pre_index_positives_total += 1
            pre_per_hh[r["household_id"]] += 1
        else:
            post_index_positives_total += 1
            post_secondaries_by_hh[r["household_id"]].add(r["encounter_id"])

    # Per-threshold operational metrics
    by_threshold = []
    for thr in risk_thresholds:
        tp = 0  # flagged AND truly post-index secondary
        fp = 0  # flagged AND NOT a true secondary
        fn = 0  # true post-index secondary NOT flagged
        flagged_total = 0
        lead_times = []

        for index_hid, contacts in all_traces.items():
            if not contacts:
                continue
            idx_date_str = OUTBREAK_INDEX_DATES.get(index_hid)
            if not idx_date_str:
                continue
            idx_dt = _to_date(idx_date_str)

            true_secondaries = set(post_secondaries_by_hh.get(index_hid, set()))
            flagged_secondary_eids: Set[str] = set()

            for c in contacts:
                if c.get("risk_score", 0.0) < thr:
                    continue
                flagged_total += 1
                eid = c.get("next_encounter_id")
                if eid and eid in true_secondaries:
                    tp += 1
                    flagged_secondary_eids.add(eid)
                    enc = enc_by_id.get(eid)
                    if enc:
                        lead = (_to_date(enc["period"]["start"]) - idx_dt).days
                        lead_times.append(lead)
                else:
                    fp += 1

            # FN = true secondaries that we did NOT flag
            fn += len(true_secondaries - flagged_secondary_eids)

        sens = tp / max(tp + fn, 1)
        prec = tp / max(tp + fp, 1)

        by_threshold.append({
            "risk_threshold":     thr,
            "tp":                 tp,
            "fp":                 fp,
            "fn":                 fn,
            "flagged_total":      flagged_total,
            "sensitivity":        sens,
            "precision":          prec,
            "f1":                 (2 * prec * sens / (prec + sens)) if (prec + sens) > 0 else 0.0,
            "mean_lead_time_days": float(np.mean(lead_times)) if lead_times else None,
            "n_lead_time_obs":    len(lead_times),
        })

    # Per-index summary (at a default threshold of 0.20)
    default_thr = 0.20
    per_index = []
    for index_hid, contacts in all_traces.items():
        if not contacts:
            continue
        idx_date_str = OUTBREAK_INDEX_DATES.get(index_hid)
        if not idx_date_str:
            continue
        idx_dt = _to_date(idx_date_str)
        true_secondaries = set(post_secondaries_by_hh.get(index_hid, set()))

        flagged = [c for c in contacts if c.get("risk_score", 0.0) >= default_thr]
        flagged_secs = {c.get("next_encounter_id") for c in flagged if c.get("next_encounter_id") in true_secondaries}
        per_index.append({
            "household_id":       index_hid,
            "index_date":         idx_date_str,
            "n_contacts_total":   len(contacts),
            "n_flagged_at_0.20":  len(flagged),
            "n_secondaries_total": len(true_secondaries),
            "n_secondaries_caught_at_0.20": len(flagged_secs),
            "n_pre_index_positives_uncatchable": pre_per_hh.get(index_hid, 0),
            "tier1_count":        sum(1 for c in contacts if c["tier"] == 1),
            "tier2_count":        sum(1 for c in contacts if c["tier"] == 2),
            "tier3_count":        sum(1 for c in contacts if c["tier"] == 3),
        })

    summary = {
        "n_indices_traced":              len(all_traces),
        "total_contacts_traced":         sum(len(v) for v in all_traces.values()),
        "tier1_contacts_total":          sum(sum(1 for c in v if c["tier"] == 1) for v in all_traces.values()),
        "tier2_contacts_total":          sum(sum(1 for c in v if c["tier"] == 2) for v in all_traces.values()),
        "tier3_contacts_total":          sum(sum(1 for c in v if c["tier"] == 3) for v in all_traces.values()),
        "post_index_secondaries_total":  post_index_positives_total,
        "pre_index_positives_uncatchable": pre_index_positives_total,
        "by_threshold":                  by_threshold,
        "per_index":                     per_index,
    }

    return summary


def main() -> None:
    base = Path(__file__).resolve().parents[2]
    hh = json.load(open(base / "data/synthetic/households.json"))["households"]
    enc = json.load(open(base / "data/synthetic/encounters.json"))["encounters"]
    labels = json.load(open(base / "data/synthetic/labels.json"))["labels"]
    feature_df = pd.read_parquet(base / "data/synthetic/features.parquet")

    with open(base / "data/synthetic/models.pkl", "rb") as f:
        bundle = pickle.load(f)
    gbt = bundle["models"]["gradient_boosting"]

    encounters_by_id = {e["id"]: e for e in enc}

    # Run contact tracing for every hand-crafted outbreak household
    all_traces: Dict[str, List[dict]] = {}
    for hid, idx_date in OUTBREAK_INDEX_DATES.items():
        if idx_date is None:
            continue
        transmission = (OUTBREAK_DISEASES.get(hid) or {}).get("transmission") or "unknown"
        contacts = trace_contacts(hid, idx_date, hh, enc, transmission)
        contacts = score_contacts(contacts, encounters_by_id, feature_df, gbt)
        all_traces[hid] = contacts

    # Evaluate
    evaluation = evaluate_contact_tracing(all_traces, labels, enc)
    print("Contact-tracing evaluation:")
    print(f"  indices traced:                 {evaluation['n_indices_traced']}")
    print(f"  total contacts traced:          {evaluation['total_contacts_traced']}")
    print(f"    tier 1 (household):           {evaluation['tier1_contacts_total']}")
    print(f"    tier 2 (shared exposure):     {evaluation['tier2_contacts_total']}")
    print(f"    tier 3 (vector spatial):      {evaluation['tier3_contacts_total']}")
    print(f"  post-index secondaries (truth): {evaluation['post_index_secondaries_total']}")
    print(f"  pre-index uncatchable:          {evaluation['pre_index_positives_uncatchable']}")
    print()
    print("  Risk-triage tradeoff curve:")
    print("  threshold | flagged | TP | FP | FN | sensitivity | precision | F1   | mean lead (d)")
    for r in evaluation["by_threshold"]:
        ml = f"{r['mean_lead_time_days']:.1f}" if r['mean_lead_time_days'] is not None else " — "
        print(f"     {r['risk_threshold']:.2f}   |  {r['flagged_total']:5d}  | {r['tp']:2d} | {r['fp']:3d} | {r['fn']:2d} |    {r['sensitivity']:.3f}    |   {r['precision']:.3f}   | {r['f1']:.3f} |     {ml}")

    payload = {
        "_metadata": {
            "n_indices_traced":    evaluation["n_indices_traced"],
            "schema_version":      "0.1.0",
        },
        "evaluation":  evaluation,
        "traces":      all_traces,
    }
    out_path = base / "data/synthetic/contact_tracing.json"
    json.dump(payload, open(out_path, "w"), indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
