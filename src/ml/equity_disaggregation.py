"""
Equity disaggregation.

Stratifies model performance and contact-tracing yield by:
- Rural (county population < 100k) vs urban
- Tribal-land counties (Apache, Navajo) vs non-tribal
- County-size strata (small/medium/large)

This is the public-health equity check: even if performance is uniform,
*measuring* it and reporting it in the model card is the PH move.
Disparities in surveillance coverage are a recognized PH equity problem.

Output:
- data/synthetic/equity.json
"""
from __future__ import annotations

import json
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def _drop_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["encounter_id", "household_id", "subject_ref", "period_start"])


TRIBAL_COUNTIES = {"Apache", "Navajo"}


def _strata(row: pd.Series) -> Dict[str, str]:
    """Return all stratification labels for one encounter row."""
    pop = row.get("co_population", 0)
    if pop >= 1_000_000:
        size = "large_metro"
    elif pop >= 100_000:
        size = "small_metro"
    else:
        size = "rural"
    rural = "rural" if pop < 100_000 else "urban"
    tribal = "tribal_land" if row.get("co_is_tribal", 0) == 1 else "non_tribal"
    species = "animal" if row.get("is_animal", 0) == 1 else "human"
    return {
        "size_stratum":     size,
        "rural_urban":      rural,
        "tribal_status":    tribal,
        "species":          species,
    }


def _metrics(y_true: np.ndarray, y_proba: np.ndarray, threshold: float = 0.5) -> Dict:
    """Compute the metrics block for a stratum. Handles edge cases (no positives)."""
    n = int(len(y_true))
    n_pos = int(y_true.sum())
    out = {"n":        n,
           "n_positive": n_pos,
           "prevalence": float(y_true.mean()) if n > 0 else 0.0}

    if n == 0:
        return out
    if n_pos == 0 or n_pos == n:
        # AUC undefined when class is all one
        out.update({"roc_auc": None, "pr_auc": None,
                    "f1": None, "precision": None, "recall": None,
                    "brier": float(brier_score_loss(y_true, y_proba))})
        return out

    y_pred = (y_proba >= threshold).astype(int)
    out["roc_auc"]   = float(roc_auc_score(y_true, y_proba))
    out["pr_auc"]    = float(average_precision_score(y_true, y_proba))
    out["brier"]     = float(brier_score_loss(y_true, y_proba))
    out["f1"]        = float(f1_score(y_true, y_pred, zero_division=0))
    out["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
    out["recall"]    = float(recall_score(y_true, y_pred, zero_division=0))
    return out


def main() -> None:
    base = Path(__file__).resolve().parents[2]
    df = pd.read_parquet(base / "data/synthetic/features.parquet")
    labels = json.load(open(base / "data/synthetic/labels.json"))["labels"]
    label_by_id = {r["encounter_id"]: r["label"] for r in labels}
    df["label"] = df["encounter_id"].map(label_by_id).astype(int)

    # Use OOF predictions from the gradient boosting model — these are the
    # honest, leakage-free predictions we want to disaggregate
    eval_data = json.load(open(base / "data/synthetic/ml_evaluation.json"))
    oof = np.array(eval_data["models"]["gradient_boosting"]["oof_proba"])
    df["oof_proba"] = oof

    # Add strata
    strata_records = df.apply(_strata, axis=1)
    for col in ["size_stratum", "rural_urban", "tribal_status", "species"]:
        df[col] = strata_records.apply(lambda x: x[col])

    # ===== Disaggregated model performance =====
    by_dimension: Dict[str, List[dict]] = {}
    for dim in ["rural_urban", "tribal_status", "species", "size_stratum"]:
        by_dimension[dim] = []
        for level, group in df.groupby(dim):
            m = _metrics(group["label"].values, group["oof_proba"].values)
            m["stratum"] = level
            by_dimension[dim].append(m)

    # Pretty-print summary
    print("=== Equity disaggregation (gradient_boosting OOF) ===\n")
    for dim, rows in by_dimension.items():
        print(f"  By {dim}:")
        for r in rows:
            roc = f"{r['roc_auc']:.3f}" if r.get("roc_auc") is not None else "n/a"
            pr  = f"{r['pr_auc']:.3f}"  if r.get("pr_auc")  is not None else "n/a"
            print(f"    {r['stratum']:15s}  n={r['n']:5d}  pos={r['n_positive']:3d}  ROC-AUC={roc}  PR-AUC={pr}")
        print()

    # ===== Disaggregated contact tracing =====
    contact_tracing = json.load(open(base / "data/synthetic/contact_tracing.json"))
    hh = json.load(open(base / "data/synthetic/households.json"))["households"]
    hh_by_id = {h["household_id"]: h for h in hh}

    ct_by_dim: Dict[str, Dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {
        "n_indices":        0,
        "n_contacts":       0,
        "n_post_secondaries_caught": 0,
    }))
    for index_hid, contacts in contact_tracing["traces"].items():
        h = hh_by_id.get(index_hid, {})
        co = h.get("county", {})
        pop = co.get("population", 0)
        rural = "rural" if pop < 100_000 else "urban"
        tribal = "tribal_land" if co.get("name") in TRIBAL_COUNTIES else "non_tribal"

        for dim, value in [("rural_urban", rural), ("tribal_status", tribal)]:
            ct_by_dim[dim][value]["n_indices"] += 1
            ct_by_dim[dim][value]["n_contacts"] += len(contacts)

    contact_eq = {dim: [{"stratum": k, **v} for k, v in d.items()] for dim, d in ct_by_dim.items()}

    payload = {
        "_metadata": {
            "n_examples":   int(len(df)),
            "n_positives":  int(df["label"].sum()),
            "model":        "gradient_boosting",
            "schema":       "0.1.0",
        },
        "model_performance_by_stratum": by_dimension,
        "contact_tracing_by_stratum":   contact_eq,
    }
    out = base / "data/synthetic/equity.json"
    json.dump(payload, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
