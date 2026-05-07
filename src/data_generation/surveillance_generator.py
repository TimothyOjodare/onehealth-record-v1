"""
Synthetic ADHS-style aggregate disease counts + vector surveillance.

Uses real CDC/ADHS-published magnitudes (rounded) so the numbers look
plausible to a public-health audience. All values are synthetic but
calibrated to actual Arizona endemicity patterns.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = PROJECT_ROOT / "data" / "reference"
OUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

COUNTIES = json.loads((REF_DIR / "arizona_counties.json").read_text())["counties"]


# Approximate annual case-rate per 100k by county endemicity (Valley Fever).
# Real ADHS 2023: Maricopa ~120/100k, Pima ~110/100k, Pinal ~140/100k.
COCCI_RATE_BY_ENDEMICITY = {"high": 120, "moderate": 35, "low": 8}

# Tick density baseline (ticks per trap-night) by approximate ecoregion.
TICK_BASELINE_BY_COUNTY = {
    "Maricopa": 2.1, "Pima": 3.4, "Pinal": 4.2, "Yuma": 1.8, "Coconino": 0.6,
    "Mohave": 1.5, "Yavapai": 2.0, "Cochise": 3.8, "Santa Cruz": 4.0,
    "Apache": 0.8, "Navajo": 0.9, "Gila": 2.4, "Graham": 2.7, "Greenlee": 2.5,
    "La Paz": 1.6,
}


def adhs_disease_counts(seed: int = 42) -> list[dict]:
    """Monthly aggregate counts by county for the past 12 months."""
    rng = random.Random(seed)
    rows = []
    today = date.today()

    for c in COUNTIES:
        annual_cocci = int(c["population"] / 100_000 * COCCI_RATE_BY_ENDEMICITY[c["cocci_endemic"]])
        # Cocci has a seasonal pattern peaking Sep-Nov; spread monthly w/ peak weighting.
        monthly_weights = [0.06, 0.05, 0.04, 0.05, 0.06, 0.08, 0.09, 0.10, 0.13, 0.14, 0.12, 0.08]
        for m in range(12):
            month_date = (today.replace(day=1) - timedelta(days=30 * m)).replace(day=1)
            mi = month_date.month - 1
            cocci_count = max(0, int(annual_cocci * monthly_weights[mi]
                                     * rng.uniform(0.8, 1.25)))
            rows.append({
                "year": month_date.year, "month": month_date.month,
                "county_fips": c["fips"], "county_name": c["name"],
                "condition_snomed": "5294002",
                "condition_display": "Coccidioidomycosis",
                "case_count": cocci_count,
                "population": c["population"],
                "rate_per_100k": round(cocci_count / c["population"] * 100_000, 2),
            })
            # RMSF is rare — single-digit counts in endemic counties.
            rmsf_count = rng.choices([0, 0, 0, 1, 2], weights=[60, 20, 10, 7, 3])[0]
            if c["cocci_endemic"] == "low" and rng.random() < 0.7:
                rmsf_count = 0
            rows.append({
                "year": month_date.year, "month": month_date.month,
                "county_fips": c["fips"], "county_name": c["name"],
                "condition_snomed": "186772009",
                "condition_display": "Rocky Mountain spotted fever",
                "case_count": rmsf_count,
                "population": c["population"],
                "rate_per_100k": round(rmsf_count / c["population"] * 100_000, 3),
            })
            # Hantavirus — extremely rare, mostly rural counties.
            hanta_count = 1 if (c["population"] < 250_000 and rng.random() < 0.04) else 0
            rows.append({
                "year": month_date.year, "month": month_date.month,
                "county_fips": c["fips"], "county_name": c["name"],
                "condition_snomed": "26726000",
                "condition_display": "Hantavirus pulmonary syndrome",
                "case_count": hanta_count,
                "population": c["population"],
                "rate_per_100k": round(hanta_count / c["population"] * 100_000, 4),
            })
    return rows


def vector_surveillance(seed: int = 42) -> list[dict]:
    """Weekly tick collection counts by county for the past 26 weeks."""
    rng = random.Random(seed + 1)
    rows = []
    today = date.today()
    for c in COUNTIES:
        baseline = TICK_BASELINE_BY_COUNTY[c["name"]]
        for w in range(26):
            wk_date = today - timedelta(days=7 * w)
            # Seasonal multiplier: ticks peak May-Aug.
            seasonal = 1.0 + 0.9 * max(0, (1 - abs(wk_date.month - 6.5) / 5))
            count = max(0, int(baseline * seasonal * 24 * rng.uniform(0.6, 1.5)))
            # Inject a 5x anomaly in Pinal Co. for the most recent 4 weeks (demo).
            if c["name"] == "Pinal" and w < 4:
                count = int(count * 5.2)
            rows.append({
                "year": wk_date.year, "week": wk_date.isocalendar().week,
                "county_fips": c["fips"], "county_name": c["name"],
                "trap_hours": 24, "tick_count": count,
                "ticks_per_trap_hour": round(count / 24, 2),
                "predominant_species": (
                    "Rhipicephalus sanguineus" if c["name"] in ("Pima", "Pinal", "Maricopa", "Yuma")
                    else "Dermacentor variabilis"),
            })
    return rows


def generate_all(seed: int = 42) -> dict:
    adhs = adhs_disease_counts(seed)
    vectors = vector_surveillance(seed)
    bundle = {
        "_metadata": {
            "seed": seed,
            "n_adhs_rows": len(adhs),
            "n_vector_rows": len(vectors),
            "schema_version": "0.1.0",
            "_caveat": "All values synthetic; magnitudes calibrated to ADHS/CDC public reports.",
        },
        "adhs_disease_counts": adhs,
        "vector_surveillance": vectors,
    }
    out = OUT_DIR / "surveillance.json"
    out.write_text(json.dumps(bundle, indent=2))
    return bundle


if __name__ == "__main__":
    b = generate_all()
    md = b["_metadata"]
    print(f"ADHS rows: {md['n_adhs_rows']}, Vector rows: {md['n_vector_rows']}")
    # Quick sanity check
    pinal_recent = [r for r in b["vector_surveillance"]
                    if r["county_name"] == "Pinal"][:4]
    print("Pinal Co. recent tick counts (anomaly window):",
          [r["tick_count"] for r in pinal_recent])
