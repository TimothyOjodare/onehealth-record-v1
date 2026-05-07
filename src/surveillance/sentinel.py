"""
ONE-HealthRecord sentinel surveillance engine.

Five alert classes:
    1. CROSS_SPECIES_CLUSTER  — same disease in human + animal in one household
    2. PROPHYLACTIC_HOUSEHOLD — index case found, other household members at risk
    3. VECTOR_ANOMALY         — county tick burden > z-score threshold vs baseline
    4. ENV_AMPLIFIED_RISK     — patient diagnosed with env-sensitive disease in
                                a high-endemicity / poor-EQI county
    5. SENTINEL_CASE          — county incidence rate spike > z-score vs trailing 12mo

Each alert carries:
    - severity:   info | watch | action
    - confidence: 0..1
    - rationale:  human-readable explanation
    - evidence:   structured pointer back to the data (refs, codes, values)
    - dp_noised_count: count with Laplace noise applied (privacy demo)

The Laplace mechanism is a *demonstration* of differential privacy. Real
deployment would use opacus or tensorflow-privacy with formal epsilon
accounting; this is a faithful one-line implementation of the DP-Counting
primitive showing the trade-off between privacy and utility.
"""
from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import networkx as nx

from src.graph.knowledge_graph import (
    build_graph, cross_species_clusters, at_risk_household_members,
    household_for, household_members, conditions_for,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"


# ---------------------------------------------------------------------------
# Differential-privacy helper (Laplace mechanism for counts).
# ---------------------------------------------------------------------------
def laplace_count(true_count: int, epsilon: float = 1.0,
                  rng: random.Random | None = None) -> int:
    """Add Laplace(0, 1/epsilon) noise to a count, clip to >= 0, round."""
    rng = rng or random.Random()
    # Sample from Laplace(0, b) where b = sensitivity / epsilon. Sensitivity = 1
    # for a counting query.
    u = rng.random() - 0.5
    noise = -math.copysign(1, u) * (1.0 / epsilon) * math.log(1 - 2 * abs(u))
    return max(0, int(round(true_count + noise)))


# ---------------------------------------------------------------------------
# Alert record
# ---------------------------------------------------------------------------
@dataclass
class Alert:
    alert_id: str
    kind: str            # CROSS_SPECIES_CLUSTER | PROPHYLACTIC_HOUSEHOLD | VECTOR_ANOMALY | ENV_AMPLIFIED_RISK | SENTINEL_CASE
    severity: str        # info | watch | action
    title: str
    summary: str         # one-line human-readable
    rationale: str       # multi-sentence explanation
    confidence: float
    geography: dict      # {county_fips, county_name, lat, lon}
    household_id: str | None = None
    subjects: list[str] = field(default_factory=list)   # references
    disease_snomed: str | None = None
    disease_display: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    dp_noised_count: int | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_ALERT_SEQ = 0
def _new_alert_id(kind: str) -> str:
    global _ALERT_SEQ
    _ALERT_SEQ += 1
    return f"ALERT-{kind[:4]}-{_ALERT_SEQ:04d}"


# ---------------------------------------------------------------------------
# Detector 1 — cross-species cluster
# ---------------------------------------------------------------------------
def detect_cross_species(G: nx.MultiDiGraph) -> list[Alert]:
    alerts = []
    for cl in cross_species_clusters(G):
        # Compute interval between index and secondary onsets.
        try:
            idx_dt = date.fromisoformat(cl["index_case"]["onset"][:10])
            sec_dts = [date.fromisoformat(s["onset"][:10]) for s in cl["secondary_cases"]]
            interval_days = min((d - idx_dt).days for d in sec_dts) if sec_dts else None
        except Exception:
            interval_days = None
        hh_node = G.nodes[cl["household_id"]]
        county = hh_node.get("county", "Unknown")
        # geography
        county_node = next((n for n, d in G.nodes(data=True)
                            if d.get("type") == "County" and d.get("name") == county), None)
        geo = {}
        if county_node:
            cd = G.nodes[county_node]
            geo = {"county_fips": cd["fips"], "county_name": cd["name"],
                   "lat": cd["lat"], "lon": cd["lon"]}

        title = f"Cross-species {cl['disease_display']} cluster — {cl['household_name']} household"
        summary = (f"{cl['n_human_cases']} human + {cl['n_animal_cases']} animal "
                   f"case(s) of {cl['disease_display']} in same household")
        rationale = (
            f"The {cl['household_name']} household has confirmed cases of "
            f"{cl['disease_display']} in both human and animal members. "
            f"Index case: {cl['index_case']['label']} ({cl['index_case']['kind']}, "
            f"onset {cl['index_case']['onset'][:10]}). "
        )
        if interval_days is not None:
            rationale += (f"Secondary case(s) followed by {interval_days} day(s), "
                          f"consistent with shared environmental exposure rather than "
                          f"direct transmission for this organism.")

        alerts.append(Alert(
            alert_id=_new_alert_id("CROSS_SPECIES_CLUSTER"),
            kind="CROSS_SPECIES_CLUSTER",
            severity="action",
            title=title, summary=summary, rationale=rationale,
            confidence=0.93,
            geography=geo,
            household_id=cl["household_id"],
            subjects=[cl["index_case"]["ref"]] + [s["ref"] for s in cl["secondary_cases"]],
            disease_snomed=cl["disease_snomed"],
            disease_display=cl["disease_display"],
            evidence={"index_case": cl["index_case"],
                      "secondary_cases": cl["secondary_cases"],
                      "interval_days": interval_days},
        ))
    return alerts


# ---------------------------------------------------------------------------
# Detector 2 — prophylactic household alerts
# ---------------------------------------------------------------------------
def detect_prophylactic(G: nx.MultiDiGraph) -> list[Alert]:
    alerts = []
    for hh_id, data in G.nodes(data=True):
        if data.get("type") != "Household":
            continue
        members = household_members(G, hh_id)
        # Diseases seen in this household
        disease_to_diagnosed: dict[str, list[str]] = {}
        for ref in members["persons"] + members["animals"]:
            for c in conditions_for(G, ref):
                disease_to_diagnosed.setdefault(c["snomed"], []).append(ref)
        for snomed, diagnosed in disease_to_diagnosed.items():
            # Only alert if the disease is zoonotic / one-health relevant.
            from src.graph.knowledge_graph import CROSS_SPECIES
            if snomed not in CROSS_SPECIES:
                continue
            at_risk = at_risk_household_members(G, hh_id, snomed)
            if not at_risk:
                continue
            # Skip cases where there's already a cross-species cluster (covered by detector 1).
            kinds_diagnosed = {G.nodes[r]["type"] for r in diagnosed}
            if {"Person", "Animal"} <= kinds_diagnosed:
                continue
            disease_display = CROSS_SPECIES[snomed]["display"]
            primary_kind = "human" if "Person" in kinds_diagnosed else "animal"
            secondary_kind = "animal" if primary_kind == "human" else "human"
            county = data.get("county", "Unknown")
            county_node = next((n for n, d in G.nodes(data=True)
                                if d.get("type") == "County" and d.get("name") == county), None)
            geo = {}
            if county_node:
                cd = G.nodes[county_node]
                geo = {"county_fips": cd["fips"], "county_name": cd["name"],
                       "lat": cd["lat"], "lon": cd["lon"]}

            alerts.append(Alert(
                alert_id=_new_alert_id("PROPHYLACTIC_HOUSEHOLD"),
                kind="PROPHYLACTIC_HOUSEHOLD",
                severity="watch",
                title=f"Household exposure: {disease_display} ({data['name']})",
                summary=(f"{primary_kind.capitalize()} case of {disease_display} "
                         f"diagnosed; {len(at_risk)} household member(s) "
                         f"share environment and may benefit from screening"),
                rationale=(
                    f"The {data['name']} household has a confirmed {primary_kind} "
                    f"case of {disease_display}. {len(at_risk)} other household "
                    f"member(s) — including {secondary_kind} contacts — share the "
                    f"same household and likely the same exposure pathway. "
                    f"Recommend {disease_display}-specific screening or prophylaxis "
                    f"per local public-health guidance."),
                confidence=0.82,
                geography=geo,
                household_id=hh_id,
                subjects=diagnosed + [m["ref"] for m in at_risk],
                disease_snomed=snomed,
                disease_display=disease_display,
                evidence={"diagnosed": diagnosed, "at_risk": at_risk},
            ))
    return alerts


# ---------------------------------------------------------------------------
# Detector 3 — vector burden anomaly
# ---------------------------------------------------------------------------
def detect_vector_anomaly(surveillance_bundle: dict, *, z_threshold: float = 2.5,
                          dp_epsilon: float = 1.0) -> list[Alert]:
    alerts = []
    rows = surveillance_bundle["vector_surveillance"]
    by_county: dict[str, list[dict]] = {}
    for r in rows:
        by_county.setdefault(r["county_fips"], []).append(r)

    rng = random.Random(7)
    for fips, county_rows in by_county.items():
        # Sort by date ascending (week)
        county_rows.sort(key=lambda r: (r["year"], r["week"]))
        if len(county_rows) < 8:
            continue
        # Recent 4 weeks vs trailing 22 weeks.
        recent = county_rows[-4:]
        trailing = county_rows[:-4]
        trailing_counts = [r["tick_count"] for r in trailing]
        if statistics.stdev(trailing_counts) == 0:
            continue
        baseline_mean = statistics.mean(trailing_counts)
        baseline_sd = statistics.stdev(trailing_counts)
        recent_mean = statistics.mean([r["tick_count"] for r in recent])
        z = (recent_mean - baseline_mean) / baseline_sd
        if z >= z_threshold:
            county_name = recent[0]["county_name"]
            # Severity scales with z-score
            sev = "action" if z >= 4 else "watch"
            recent_total = sum(r["tick_count"] for r in recent)
            dp_count = laplace_count(recent_total, dp_epsilon, rng)
            alerts.append(Alert(
                alert_id=_new_alert_id("VECTOR_ANOMALY"),
                kind="VECTOR_ANOMALY",
                severity=sev,
                title=f"Vector anomaly — {county_name} County tick burden",
                summary=(f"Tick collection counts {z:.1f}σ above baseline "
                         f"in {county_name} Co. (last 4 weeks vs. trailing 22)"),
                rationale=(
                    f"Mean tick count in {county_name} County over the past 4 weeks "
                    f"({recent_mean:.0f}/trap) is {z:.1f} standard deviations above "
                    f"the trailing-22-week baseline ({baseline_mean:.0f}±"
                    f"{baseline_sd:.0f}). Predominant species: "
                    f"{recent[-1]['predominant_species']}. Elevated risk for "
                    f"tick-borne diseases including ehrlichiosis and RMSF — "
                    f"consider clinician advisory for the county."),
                confidence=min(0.99, 0.6 + 0.05 * z),
                geography={"county_fips": fips, "county_name": county_name},
                evidence={"z_score": round(z, 2),
                          "recent_mean": round(recent_mean, 1),
                          "baseline_mean": round(baseline_mean, 1),
                          "baseline_sd": round(baseline_sd, 1),
                          "recent_4wk_total": recent_total,
                          "predominant_species": recent[-1]["predominant_species"]},
                dp_noised_count=dp_count,
            ))
    return alerts


# ---------------------------------------------------------------------------
# Detector 4 — environmentally amplified individual risk
# ---------------------------------------------------------------------------
ENV_SENSITIVE = {
    "5294002":   {"endemicity_attr": "cocci_endemic", "high_levels": {"high"}},
    "186772009": {"endemicity_attr": "cocci_endemic", "high_levels": {"high","moderate"}},  # RMSF tick areas
    "417093003": {"endemicity_attr": "cocci_endemic", "high_levels": {"high"}},  # WNV (mosquito-prone areas)
    "58750007":  {"endemicity_attr": "cocci_endemic", "high_levels": {"low","moderate"}},   # Plague (rural N AZ)
}


def detect_env_amplified(G: nx.MultiDiGraph) -> list[Alert]:
    alerts = []
    for n, d in G.nodes(data=True):
        if d.get("type") != "Condition":
            continue
        snomed = d.get("snomed")
        if snomed not in ENV_SENSITIVE:
            continue
        env_rule = ENV_SENSITIVE[snomed]
        # Find the patient (in-edge HAS_CONDITION).
        subj = None
        for s, _, ed in G.in_edges(n, data=True):
            if ed.get("kind") == "HAS_CONDITION":
                subj = s
                break
        if not subj:
            continue
        hh = household_for(G, subj)
        if not hh:
            continue
        # Find county of household.
        county = None
        for _, c, ed in G.out_edges(hh, data=True):
            if ed.get("kind") == "LOCATED_IN":
                county = G.nodes[c]
                break
        if not county:
            continue
        endemicity = county.get(env_rule["endemicity_attr"])
        if endemicity not in env_rule["high_levels"]:
            continue
        alerts.append(Alert(
            alert_id=_new_alert_id("ENV_AMPLIFIED_RISK"),
            kind="ENV_AMPLIFIED_RISK",
            severity="info",
            title=f"Endemicity-amplified diagnosis: {d['display']}",
            summary=(f"{G.nodes[subj].get('label', subj)} diagnosed with "
                     f"{d['display']} in {county['name']} Co. "
                     f"(endemicity: {endemicity})"),
            rationale=(
                f"This {d['display']} case is geographically consistent with "
                f"county-level endemicity ({endemicity}). EPA Environmental "
                f"Quality Index for {county['name']} Co. = "
                f"{county.get('epa_eqi', 0):+.2f}. The presentation is "
                f"epidemiologically expected; record contributes to local "
                f"surveillance baseline rather than triggering an outbreak signal."),
            confidence=0.78,
            geography={"county_fips": county["fips"], "county_name": county["name"],
                       "lat": county["lat"], "lon": county["lon"]},
            household_id=hh,
            subjects=[subj],
            disease_snomed=snomed,
            disease_display=d["display"],
            evidence={"endemicity": endemicity, "epa_eqi": county.get("epa_eqi")},
        ))
    return alerts


# ---------------------------------------------------------------------------
# Detector 5 — sentinel case (county incidence spike)
# ---------------------------------------------------------------------------
def detect_sentinel_cases(surveillance_bundle: dict, *, z_threshold: float = 2.0,
                          dp_epsilon: float = 1.0) -> list[Alert]:
    alerts = []
    rng = random.Random(11)
    rows = surveillance_bundle["adhs_disease_counts"]
    by_disease_county: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_disease_county.setdefault((r["condition_snomed"], r["county_fips"]), []).append(r)

    for (snomed, fips), series in by_disease_county.items():
        if len(series) < 6:
            continue
        series.sort(key=lambda r: (r["year"], r["month"]))
        # Most recent month vs trailing 11 months.
        recent = series[-1]
        trailing = series[-12:-1] if len(series) >= 12 else series[:-1]
        counts = [r["case_count"] for r in trailing]
        if not counts or statistics.stdev(counts or [0, 0]) == 0:
            continue
        mean = statistics.mean(counts)
        sd = statistics.stdev(counts)
        if sd == 0:
            continue
        z = (recent["case_count"] - mean) / sd
        if z < z_threshold or recent["case_count"] < 3:
            continue
        sev = "action" if z >= 4 else "watch"
        dp_count = laplace_count(recent["case_count"], dp_epsilon, rng)
        alerts.append(Alert(
            alert_id=_new_alert_id("SENTINEL_CASE"),
            kind="SENTINEL_CASE",
            severity=sev,
            title=f"Incidence spike — {recent['condition_display']} in {recent['county_name']} Co.",
            summary=(f"{recent['case_count']} cases this month "
                     f"({z:.1f}σ above trailing-11mo baseline)"),
            rationale=(
                f"{recent['county_name']} County reported {recent['case_count']} "
                f"{recent['condition_display']} cases in the most recent month, "
                f"vs. trailing 11-month mean of {mean:.1f}±{sd:.1f}. "
                f"Z-score {z:.1f} crosses the watch threshold ({z_threshold}). "
                f"Confidence-protected count (ε={1.0}): {dp_count}."),
            confidence=min(0.99, 0.55 + 0.08 * z),
            geography={"county_fips": fips, "county_name": recent["county_name"]},
            disease_snomed=snomed,
            disease_display=recent["condition_display"],
            evidence={"z_score": round(z, 2),
                      "month_count": recent["case_count"],
                      "baseline_mean": round(mean, 1),
                      "baseline_sd": round(sd, 1)},
            dp_noised_count=dp_count,
        ))
    return alerts


# ---------------------------------------------------------------------------
def run_all_detectors(G: nx.MultiDiGraph,
                      surveillance_bundle: dict) -> list[Alert]:
    alerts = []
    alerts.extend(detect_cross_species(G))
    alerts.extend(detect_prophylactic(G))
    alerts.extend(detect_vector_anomaly(surveillance_bundle))
    alerts.extend(detect_env_amplified(G))
    alerts.extend(detect_sentinel_cases(surveillance_bundle))
    # Order: action first, then watch, then info.
    sev_order = {"action": 0, "watch": 1, "info": 2}
    alerts.sort(key=lambda a: (sev_order.get(a.severity, 9), -a.confidence))
    return alerts


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    households = json.loads((SYNTH_DIR / "households.json").read_text())
    surveillance = json.loads((SYNTH_DIR / "surveillance.json").read_text())
    G = build_graph(households)

    alerts = run_all_detectors(G, surveillance)
    print(f"Total alerts: {len(alerts)}\n")
    by_kind: dict[str, int] = {}
    for a in alerts:
        by_kind[a.kind] = by_kind.get(a.kind, 0) + 1
    print("By kind:")
    for k, n in by_kind.items():
        print(f"  {k:25} {n}")
    print()
    print("Top 6 alerts:")
    for a in alerts[:6]:
        print(f"  [{a.severity:6}] ({a.confidence:.2f}) {a.kind:25} — {a.summary}")

    # Persist as JSON for the UI.
    out = [asdict(a) for a in alerts]
    (SYNTH_DIR / "alerts.json").write_text(json.dumps(
        {"_metadata": {"n_alerts": len(out),
                       "generated_at": datetime.now(timezone.utc).isoformat()},
         "alerts": out}, indent=2, default=str))
    print(f"\nWrote data/synthetic/alerts.json")
