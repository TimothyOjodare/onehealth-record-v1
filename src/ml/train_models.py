"""
Train logistic regression, random forest, and gradient boosting on the
cluster-prediction task. Evaluate with stratified cross-validation.

Outputs:
- data/synthetic/models.pkl       - trained models (sklearn pickle)
- data/synthetic/ml_evaluation.json - metrics for the demo / report
"""
from __future__ import annotations

import json
import pickle
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

RANDOM_STATE = 42


def _drop_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["encounter_id", "household_id", "subject_ref", "period_start"])


def make_models() -> Dict[str, Pipeline]:
    """Return a dict of named sklearn pipelines."""
    imputer = SimpleImputer(strategy="median")
    return {
        "logistic_regression": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                random_state=RANDOM_STATE,
                C=1.0,
            )),
        ]),
        "random_forest": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            )),
        ]),
        "gradient_boosting": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", GradientBoostingClassifier(
                n_estimators=300,
                max_depth=3,
                learning_rate=0.05,
                random_state=RANDOM_STATE,
            )),
        ]),
    }


def evaluate_cv(model: Pipeline, X: pd.DataFrame, y: np.ndarray, n_splits: int = 5) -> Dict:
    """Stratified K-fold cross-validation. Returns mean metrics + per-fold."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)

    fold_metrics = []
    all_proba = np.zeros(len(y))
    all_pred = np.zeros(len(y), dtype=int)

    for fold_i, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        # Handle gradient boosting which doesn't accept class_weight: use sample_weight
        is_gb = "gradient_boosting" in str(type(model.named_steps["clf"]).__name__).lower()
        sw = None
        if is_gb:
            pos_weight = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
            sw = np.where(y_tr == 1, pos_weight, 1.0)

        t0 = time.perf_counter()
        if sw is not None:
            model.fit(X_tr, y_tr, clf__sample_weight=sw)
        else:
            model.fit(X_tr, y_tr)
        train_time = time.perf_counter() - t0

        proba = model.predict_proba(X_te)[:, 1]
        all_proba[test_idx] = proba
        pred = (proba >= 0.5).astype(int)
        all_pred[test_idx] = pred

        fold_metrics.append({
            "fold":         fold_i,
            "n_train":      int(len(train_idx)),
            "n_test":       int(len(test_idx)),
            "n_pos_test":   int(y_te.sum()),
            "roc_auc":      float(roc_auc_score(y_te, proba)) if y_te.sum() > 0 else None,
            "pr_auc":       float(average_precision_score(y_te, proba)) if y_te.sum() > 0 else None,
            "brier":        float(brier_score_loss(y_te, proba)),
            "train_seconds": float(train_time),
        })

    # Aggregate metrics across folds (use out-of-fold predictions)
    overall = {
        "roc_auc":           float(roc_auc_score(y, all_proba)),
        "pr_auc":            float(average_precision_score(y, all_proba)),
        "brier":             float(brier_score_loss(y, all_proba)),
        "precision_at_50":   float(precision_score(y, all_pred, zero_division=0)),
        "recall_at_50":      float(recall_score(y, all_pred, zero_division=0)),
        "f1_at_50":          float(f1_score(y, all_pred, zero_division=0)),
    }

    # ROC and PR curves for plotting in the demo
    fpr, tpr, roc_thresholds = roc_curve(y, all_proba)
    prec, rec, pr_thresholds = precision_recall_curve(y, all_proba)
    cm = confusion_matrix(y, all_pred).tolist()

    # Calibration bins
    bins = np.linspace(0, 1, 6)
    calibration = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (all_proba >= lo) & (all_proba < hi)
        if mask.sum() > 0:
            calibration.append({
                "bin_lo":      float(lo),
                "bin_hi":      float(hi),
                "n":           int(mask.sum()),
                "mean_pred":   float(all_proba[mask].mean()),
                "mean_actual": float(y[mask].mean()),
            })

    return {
        "fold_metrics":  fold_metrics,
        "overall":       overall,
        "roc_curve":     {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "thresholds": roc_thresholds.tolist()},
        "pr_curve":      {"precision": prec.tolist(), "recall": rec.tolist(), "thresholds": pr_thresholds.tolist()},
        "confusion_matrix": cm,
        "calibration":   calibration,
        "oof_proba":     all_proba.tolist(),
    }


def fit_final(model: Pipeline, X: pd.DataFrame, y: np.ndarray) -> Pipeline:
    """Refit on the full dataset for use in the demo / contact tracing."""
    is_gb = "gradient_boosting" in str(type(model.named_steps["clf"]).__name__).lower()
    if is_gb:
        pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)
        sw = np.where(y == 1, pos_weight, 1.0)
        model.fit(X, y, clf__sample_weight=sw)
    else:
        model.fit(X, y)
    return model


def fit_decision_tree_baseline(X: pd.DataFrame, y: np.ndarray) -> Tuple[DecisionTreeClassifier, str]:
    """Fit a small interpretable decision tree as the human-readable baseline."""
    imp = SimpleImputer(strategy="median")
    X_imp = pd.DataFrame(imp.fit_transform(X), columns=X.columns)
    dt = DecisionTreeClassifier(max_depth=4, class_weight="balanced", random_state=RANDOM_STATE, min_samples_leaf=10)
    dt.fit(X_imp, y)
    rules = export_text(dt, feature_names=list(X.columns), max_depth=4, decimals=2)
    return dt, rules


def main() -> None:
    base = Path(__file__).resolve().parents[2]
    df = pd.read_parquet(base / "data/synthetic/features.parquet")
    labels = json.load(open(base / "data/synthetic/labels.json"))["labels"]
    label_by_id = {r["encounter_id"]: r["label"] for r in labels}

    df["label"] = df["encounter_id"].map(label_by_id)
    print(f"loaded features: {df.shape}, prevalence: {df['label'].mean():.3%}")

    # Drop ID and label
    X = _drop_id_cols(df).drop(columns=["label"])
    y = df["label"].astype(int).values
    feature_names = X.columns.tolist()
    print(f"feature matrix: {X.shape},  positives: {y.sum()},  features: {len(feature_names)}")

    # Train and evaluate three models
    results = {}
    final_models = {}
    models = make_models()

    for name, model in models.items():
        print(f"\n=== {name} ===")
        res = evaluate_cv(model, X, y)
        print(f"  ROC-AUC: {res['overall']['roc_auc']:.3f}   PR-AUC: {res['overall']['pr_auc']:.3f}   Brier: {res['overall']['brier']:.3f}")
        print(f"  P@0.5={res['overall']['precision_at_50']:.3f}   R@0.5={res['overall']['recall_at_50']:.3f}   F1={res['overall']['f1_at_50']:.3f}")
        results[name] = res
        # Refit on all data for downstream use
        final_models[name] = fit_final(make_models()[name], X, y)

    # Decision tree baseline
    print("\n=== decision_tree_baseline ===")
    dt, dt_rules = fit_decision_tree_baseline(X, y)
    final_models["decision_tree_baseline"] = dt
    print(dt_rules.split("\n")[0])
    print(f"  depth={dt.get_depth()}, leaves={dt.get_n_leaves()}")

    # Save models
    models_path = base / "data/synthetic/models.pkl"
    with open(models_path, "wb") as f:
        pickle.dump({"models": final_models, "feature_names": feature_names}, f)
    print(f"\nwrote {models_path}")

    # Save evaluation
    metadata = {
        "n_encounters":       int(len(df)),
        "n_positives":        int(y.sum()),
        "prevalence":         float(y.mean()),
        "n_features":         len(feature_names),
        "feature_names":      feature_names,
        "cv_folds":           5,
        "random_state":       RANDOM_STATE,
        "decision_tree_rules": dt_rules,
    }
    eval_payload = {
        "_metadata": metadata,
        "models":    results,
    }
    eval_path = base / "data/synthetic/ml_evaluation.json"
    json.dump(eval_payload, open(eval_path, "w"), indent=2)
    print(f"wrote {eval_path}")


if __name__ == "__main__":
    main()
