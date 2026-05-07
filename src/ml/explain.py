"""
Explainability layer: SHAP, permutation importance, decision-tree rules.

Outputs:
- data/synthetic/explanations.json   - global + per-patient explanations for the demo
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import shap
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance


def _drop_id_cols(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["encounter_id", "household_id", "subject_ref", "period_start"])


def _human_label(name: str) -> str:
    """Convert feature name to human-readable label for the UI."""
    pretty = {
        "is_animal":            "Subject is an animal",
        "age_years":            "Age (years)",
        "sex_female":           "Sex is female",
        "v_temp_f":             "Temperature (°F)",
        "v_hr":                 "Heart rate",
        "v_rr":                 "Respiratory rate",
        "v_spo2":               "SpO₂",
        "v_bp_sys":             "Systolic BP",
        "v_bp_dia":             "Diastolic BP",
        "v_glucose":            "Glucose",
        "v_fever":              "Fever (>100.4°F)",
        "v_tachy":              "Tachycardia (HR >100)",
        "v_tachypnea":          "Tachypnea (RR >20)",
        "v_hypoxia":            "Hypoxia (SpO₂ <94)",
        "cc_respiratory":       "CC: respiratory",
        "cc_fever":             "CC: fever",
        "cc_neuro":             "CC: neurologic",
        "cc_gi":                "CC: gastrointestinal",
        "cc_rash_skin":         "CC: rash / skin",
        "cc_musculo":           "CC: musculoskeletal",
        "cc_fatigue":           "CC: fatigue / malaise",
        "cc_exposure":          "CC: exposure documented",
        "cc_zoo_specific":      "CC: named zoonotic disease",
        "hh_n_humans":          "Household size (humans)",
        "hh_n_animals":         "Household size (animals)",
        "hh_has_dog":           "Household has dog",
        "hh_has_cat":           "Household has cat",
        "hh_has_livestock":     "Household has livestock",
        "hh_has_bird":          "Household has bird",
        "hh_has_reptile":       "Household has reptile",
        "co_population":        "County population",
        "co_epa_eqi":           "EPA Environmental Quality Index",
        "co_cocci_high":        "Cocci endemicity: high",
        "co_cocci_med":         "Cocci endemicity: medium",
        "co_is_rural":          "Rural county",
        "co_is_tribal":         "Tribal-land county",
        "co_lat":               "County latitude",
        "co_lon":               "County longitude",
        "hh_enc_30d":           "Household encounters in last 30d",
        "hh_enc_90d":           "Household encounters in last 90d",
        "hh_distinct_subjects_90d": "Distinct household subjects in 90d",
        "hh_distinct_cc_90d":   "Distinct CC patterns in household 90d",
        "hh_other_species_cond_90d": "Cross-species condition in household (90d)",
        "hh_distinct_codes_90d": "Distinct disease codes in household (90d)",
        "surv_z_score":         "County surveillance z-score",
        "surv_vector_anomaly":  "County vector anomaly active",
        "surv_recent_cases":    "County recent case count",
        "month":                "Month of encounter",
        "is_summer":            "Encounter in summer",
        "is_monsoon":           "Encounter in monsoon season",
        "day_of_year":          "Day of year",
    }
    return pretty.get(name, name)


def main() -> None:
    base = Path(__file__).resolve().parents[2]
    df = pd.read_parquet(base / "data/synthetic/features.parquet")
    labels = json.load(open(base / "data/synthetic/labels.json"))["labels"]
    label_by_id = {r["encounter_id"]: r["label"] for r in labels}
    df["label"] = df["encounter_id"].map(label_by_id).astype(int)

    with open(base / "data/synthetic/models.pkl", "rb") as f:
        bundle = pickle.load(f)
    models = bundle["models"]
    feature_names = bundle["feature_names"]

    X = _drop_id_cols(df).drop(columns=["label"])
    y = df["label"].values

    # Imputed copy for the explainers (SHAP TreeExplainer expects no NaN)
    imp = SimpleImputer(strategy="median")
    X_imp = pd.DataFrame(imp.fit_transform(X), columns=X.columns)

    # ===== SHAP on the gradient boosting model =====
    print("Computing SHAP values on gradient_boosting...")
    gbt_pipeline = models["gradient_boosting"]
    gbt = gbt_pipeline.named_steps["clf"]
    explainer = shap.TreeExplainer(gbt)
    shap_values = explainer.shap_values(X_imp)
    if isinstance(shap_values, list):  # multiclass case
        shap_values = shap_values[1]
    print(f"shap_values shape: {shap_values.shape}")

    # Global feature importance: mean absolute SHAP value
    mean_abs = np.abs(shap_values).mean(axis=0)
    global_importance = sorted(
        [{"feature": f, "label": _human_label(f), "importance": float(v)} for f, v in zip(feature_names, mean_abs)],
        key=lambda x: x["importance"], reverse=True,
    )
    print(f"top 5: {[(g['feature'], round(g['importance'], 3)) for g in global_importance[:5]]}")

    # ===== Per-patient SHAP for hand-crafted scenarios =====
    handcrafted_household_ids = [
        "HH-AZ-PIMA-001", "HH-AZ-PINAL-002", "HH-AZ-MARICOPA-003", "HH-AZ-YUMA-004",
        "HH-AZ-COCONINO-005", "HH-AZ-APACHE-006", "HH-AZ-COCHISE-007", "HH-AZ-MOHAVE-008",
        "HH-AZ-SANTACRUZ-009", "HH-AZ-MARICOPA-010", "HH-AZ-PINAL-011", "HH-AZ-NAVAJO-012",
    ]

    per_patient = []
    base_value = float(explainer.expected_value if not isinstance(explainer.expected_value, np.ndarray) else explainer.expected_value[-1])

    for hid in handcrafted_household_ids:
        # Pick the encounter with the highest predicted probability for this household
        mask = df["household_id"] == hid
        if mask.sum() == 0:
            continue
        rows = df[mask].copy()
        proba = gbt_pipeline.predict_proba(X[mask])[:, 1]
        rows["proba"] = proba
        rows = rows.sort_values("proba", ascending=False)
        top_row = rows.iloc[0]
        idx = rows.index[0]
        # Position in original df
        pos = df.index.get_loc(idx)
        contributions = sorted(
            [{
                "feature":  feature_names[i],
                "label":    _human_label(feature_names[i]),
                "value":    float(X_imp.iloc[pos][feature_names[i]]),
                "shap":     float(shap_values[pos, i]),
            } for i in range(len(feature_names))],
            key=lambda x: abs(x["shap"]), reverse=True,
        )

        per_patient.append({
            "household_id":       hid,
            "encounter_id":       top_row["encounter_id"],
            "subject_ref":        top_row["subject_ref"],
            "period_start":       top_row["period_start"],
            "predicted_proba":    float(top_row["proba"]),
            "actual_label":       int(top_row["label"]),
            "base_value":         base_value,
            "top_contributions":  contributions[:8],
        })

    # ===== Permutation importance on full dataset =====
    print("Computing permutation importance...")
    perm = permutation_importance(
        gbt_pipeline, X, y,
        n_repeats=5,
        random_state=42,
        scoring="roc_auc",
        n_jobs=1,
    )
    perm_imp = sorted(
        [{
            "feature":      f,
            "label":        _human_label(f),
            "importance":   float(perm.importances_mean[i]),
            "std":          float(perm.importances_std[i]),
        } for i, f in enumerate(feature_names)],
        key=lambda x: x["importance"], reverse=True,
    )

    # ===== Write everything =====
    payload = {
        "_metadata": {
            "model": "gradient_boosting",
            "n_features": len(feature_names),
            "n_examples": int(len(X)),
            "explainer": "shap.TreeExplainer",
            "base_value": base_value,
        },
        "global_shap_importance":     global_importance,
        "permutation_importance":     perm_imp,
        "per_patient_explanations":   per_patient,
    }
    out_path = base / "data/synthetic/explanations.json"
    json.dump(payload, open(out_path, "w"), indent=2)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
