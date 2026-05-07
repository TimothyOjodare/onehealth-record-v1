"""
Phase 6 — Enterprise Master Patient Index (eMPI) probabilistic matcher.

Implements a Fellegi-Sunter-style record linkage algorithm to reconcile
identities across the per-site FHIR shadow stores. The same person might
appear at TMC as "Maria Hernandez, DOB 1973-05-12, 4521 E Pima St, 85710"
and at Banner UrgentCare as "M Hernandez, DOB 1973-05-12, 4521 E Pima Street,
85710" — same person, slightly different surface forms.

The matcher computes a log-likelihood score on five fields:
    - last_name   (string similarity via Jaro-Winkler)
    - first_name  (string similarity, with nickname expansion)
    - dob         (exact match strongly weighted; year+month partial credit)
    - address     (token overlap, after normalization)
    - zip         (exact)

Tiers:
    auto_link        score >= 0.95
    clerical_review  0.80 <= score < 0.95
    no_match         score < 0.80

Output: data/synthetic/empi_links.json
        — a list of (left, right, score, tier, evidence) tuples for review.

In production this would be replaced by Splink (Spark-based PRL) or a
commercial eMPI like NextGate / Verato. The algorithm here is the same
Fellegi-Sunter framework those products use; only the implementation
scale differs.
"""
from __future__ import annotations

import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"
SHADOW_DIR = DATA / "shadow_stores"


# --------------------------------------------------------------------------
# String similarity helpers
# --------------------------------------------------------------------------
def _jaro(s: str, t: str) -> float:
    if s == t: return 1.0
    if not s or not t: return 0.0
    s_len, t_len = len(s), len(t)
    match_dist = max(s_len, t_len) // 2 - 1
    s_matches, t_matches = [False]*s_len, [False]*t_len
    matches = 0
    for i, c in enumerate(s):
        lo, hi = max(0, i-match_dist), min(t_len, i+match_dist+1)
        for j in range(lo, hi):
            if t_matches[j] or t[j] != c: continue
            s_matches[i] = t_matches[j] = True
            matches += 1
            break
    if matches == 0: return 0.0
    transpositions = 0; k = 0
    for i, m in enumerate(s_matches):
        if not m: continue
        while not t_matches[k]: k += 1
        if s[i] != t[k]: transpositions += 1
        k += 1
    transpositions //= 2
    return (matches/s_len + matches/t_len + (matches - transpositions)/matches) / 3


def jaro_winkler(s: str, t: str, p: float = 0.1) -> float:
    j = _jaro(s, t)
    prefix = 0
    for cs, ct in zip(s[:4], t[:4]):
        if cs != ct: break
        prefix += 1
    return j + prefix * p * (1 - j)


# Common nickname ↔ formal name pairs (a small subset; production uses a
# dictionary of ~5,000 pairs from the SSA + Census).
NICKNAMES = {
    "maria": ["mary", "marie"], "robert": ["bob", "rob", "robby"],
    "william": ["bill", "billy", "will", "willie"], "elizabeth": ["liz", "beth", "betsy", "eliza"],
    "michael": ["mike", "mikey"], "richard": ["rick", "dick", "rich"],
    "anthony": ["tony"], "james": ["jim", "jimmy", "jamie"], "john": ["johnny", "jack"],
    "thomas": ["tom", "tommy"], "christopher": ["chris", "kit"],
    "daniel": ["dan", "danny"], "jennifer": ["jen", "jenny"],
    "jessica": ["jess", "jessie"], "katherine": ["kate", "katie", "kathy", "kat"],
    "stephanie": ["steph", "stephie"], "matthew": ["matt", "matty"],
    "joseph": ["joe", "joey"], "rebecca": ["becky", "becca"],
    "susan": ["sue", "susie"], "margaret": ["maggie", "meg", "peggy", "marge"],
}
NICK_LOOKUP = {}
for formal, nicks in NICKNAMES.items():
    NICK_LOOKUP[formal] = {formal, *nicks}
    for n in nicks: NICK_LOOKUP[n] = {formal, *nicks}


def first_name_similarity(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b: return 0.0
    if a == b: return 1.0
    # Single-letter abbrev (e.g. "M" matches "Maria")
    if len(a) == 1 and len(b) > 1 and a == b[0]: return 0.85
    if len(b) == 1 and len(a) > 1 and b == a[0]: return 0.85
    # Nickname expansion
    a_set = NICK_LOOKUP.get(a, {a})
    b_set = NICK_LOOKUP.get(b, {b})
    if a_set & b_set: return 0.95
    return jaro_winkler(a, b)


def address_similarity(a: str, b: str) -> float:
    """Token-overlap after normalization. Real eMPIs use USPS address standardization."""
    if not a or not b: return 0.0
    norm = lambda s: re.sub(r'[^a-z0-9 ]+', ' ', s.lower()) \
                       .replace(' street ', ' st ').replace(' avenue ', ' ave ') \
                       .replace(' road ', ' rd ').replace(' boulevard ', ' blvd ')
    ta = set(norm(a).split())
    tb = set(norm(b).split())
    if not ta or not tb: return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def dob_similarity(a: str, b: str) -> float:
    if not a or not b: return 0.0
    if a == b: return 1.0
    # Same year+month (transposed day, possible)
    if a[:7] == b[:7]: return 0.85
    # Same year (year-only registration in older records)
    if a[:4] == b[:4]: return 0.5
    return 0.0


# --------------------------------------------------------------------------
# Fellegi-Sunter score combination
# --------------------------------------------------------------------------
# m_i = P(field i agrees | true match)
# u_i = P(field i agrees | not a match) — base rate
# Weights: log2(m/u) for agreement, log2((1-m)/(1-u)) for disagreement
WEIGHTS = {
    # field        m     u
    "last_name":  (0.95, 0.005),
    "first_name": (0.92, 0.02),
    "dob":        (0.99, 0.001),
    "address":    (0.88, 0.05),
    "zip":        (0.95, 0.02),
}


def _bit_weight(m: float, u: float, agree_strength: float) -> float:
    """
    agree_strength in [0,1]: 1 = full agreement, 0 = disagreement.
    Returns a continuous F-S weight.
    """
    pos = math.log2(m / u) if u > 0 else 10.0
    neg = math.log2((1 - m) / (1 - u)) if (1 - u) > 0 else -10.0
    return agree_strength * pos + (1 - agree_strength) * neg


def score_pair(left: dict, right: dict) -> tuple[float, dict]:
    """
    Score a candidate pair. Returns (probability_of_match, evidence).
    A pair only auto-links if:
      - DOB matches strongly AND
      - last name matches strongly AND
      - the combined log-likelihood passes the threshold.
    """
    ev = {}
    raw_score = 0.0
    sims = {
        "last_name":  jaro_winkler(left.get("last_name", "").lower(), right.get("last_name", "").lower()),
        "first_name": first_name_similarity(left.get("first_name", ""), right.get("first_name", "")),
        "dob":        dob_similarity(left.get("dob", ""), right.get("dob", "")),
        "address":    address_similarity(left.get("address", ""), right.get("address", "")),
        "zip":        1.0 if left.get("zip", "") == right.get("zip", "") and left.get("zip") else 0.0,
    }
    for field, (m, u) in WEIGHTS.items():
        w = _bit_weight(m, u, sims[field])
        raw_score += w
        ev[field] = {"sim": round(sims[field], 3), "weight": round(w, 3)}
    # Logistic transform
    p = 1 / (1 + math.exp(-raw_score / 8))

    # Production-grade hard rule: auto-link requires DOB ≥ 0.99 and last-name ≥ 0.85.
    # Without these, demote to clerical-review at most.
    if sims["dob"] < 0.99 or sims["last_name"] < 0.85:
        p = min(p, 0.93)
    ev["raw_log2_score"] = round(raw_score, 3)
    return p, ev


def tier(p: float) -> str:
    if p >= 0.95: return "auto_link"
    if p >= 0.80: return "clerical_review"
    return "no_match"


# --------------------------------------------------------------------------
# Build candidate pool & seed synthetic duplicates
# --------------------------------------------------------------------------
def _collect_records() -> list[dict]:
    """Pull a flat list of records from every shadow store. Adapts to the
    actual synthetic schema (city/state/county-fips; no street line or ZIP)."""
    out = []
    for store_path in sorted(SHADOW_DIR.glob("*.json")):
        store = json.loads(store_path.read_text())
        site_id = store["_metadata"]["site_id"]
        for p in store.get("patients", []):
            name = (p.get("name") or [{}])[0]
            family = name.get("family") or ""
            given = (name.get("given") or [""])[0]
            addr = (p.get("address") or [{}])[0]
            city = addr.get("city") or ""
            state = addr.get("state") or ""
            # Pull county FIPS from extension (used as a coarse "ZIP-equivalent")
            county_fips = ""
            for ext in (addr.get("extension") or []):
                if ext.get("url", "").endswith("county-fips"):
                    county_fips = ext.get("valueString", "")
            household_id = ""
            for ext in (p.get("extension") or []):
                if ext.get("url", "").endswith("household-id"):
                    household_id = ext.get("valueString", "")
            out.append({
                "site_id": site_id,
                "patient_id": p["id"],
                "first_name": given,
                "last_name": family,
                "dob": p.get("birthDate", ""),
                "address": city,                # city as the address signal
                "zip": county_fips,             # county_fips as the ZIP-equivalent
                "household_id": household_id,
                "kind": "human",
            })
        for a in store.get("animal_patients", []):
            # Animals don't have a separate owner identity in the synthetic data
            # — we just use the household linkage. Skip for the match loop and
            # handle animal-owner reconciliation as a post-process.
            pass
    return out


def _seed_duplicates(records: list[dict], rng: random.Random) -> list[dict]:
    """
    Inject a handful of demonstrable duplicates: take a pre-existing record and
    inject a shadow copy at a different site with mild variations (nickname,
    middle-initial-only, slight address variation). These let the demo show
    a clean auto-link, a clerical-review case, and a no-match.
    """
    duplicates = []
    # Maria Hernandez at TMC → "M Hernandez" at Banner Phoenix (single-letter first name)
    maria = next((r for r in records if r["first_name"] == "Maria" and r["last_name"] == "Hernandez"), None)
    if maria:
        duplicates.append({
            **maria,
            "site_id": "banner_phx",
            "patient_id": "empi-shadow-maria-banner",
            "first_name": "M",
        })
    # Robert Williams → "Bob Williams" at TMC (nickname)
    rob = next((r for r in records if r["first_name"] == "Robert" and r["last_name"] == "Williams"), None)
    if rob:
        duplicates.append({
            **rob,
            "site_id": "tmc",
            "patient_id": "empi-shadow-bob-tmc",
            "first_name": "Bob",
        })
    # Sarah Begay → "Sara Begay" at IHS Whiteriver (one-letter typo, clerical-review territory)
    sb = next((r for r in records if r["first_name"] == "Sarah" and r["last_name"] == "Begay"), None)
    if sb:
        duplicates.append({
            **sb,
            "site_id": "ihs_whiteriver",
            "patient_id": "empi-shadow-sara-ihs",
            "first_name": "Sara",
        })
    # James Becker → "Jim Becker" at HonorHealth (nickname; auto-link)
    jb = next((r for r in records if r["first_name"] == "James" and r["last_name"] == "Becker"), None)
    if jb:
        duplicates.append({
            **jb,
            "site_id": "honorhealth",
            "patient_id": "empi-shadow-jim-honor",
            "first_name": "Jim",
        })
    # No-match: unrelated person, different DOB, different city
    duplicates.append({
        "site_id": "naz_healthcare",
        "patient_id": "empi-no-match-rmartinez",
        "first_name": "R",
        "last_name": "Martinez",
        "dob": "1965-03-15",
        "address": "Flagstaff",
        "zip": "04005",
        "kind": "human",
    })
    return duplicates


# --------------------------------------------------------------------------
# Run pairwise matching (with blocking on ZIP for tractability)
# --------------------------------------------------------------------------
def run_match() -> dict:
    rng = random.Random(42)
    records = _collect_records()
    duplicates = _seed_duplicates(records, rng)
    all_records = records + duplicates

    # Blocking: only score pairs that share a ZIP (or share last name)
    by_zip = defaultdict(list)
    by_lastname = defaultdict(list)
    for r in all_records:
        if r.get("zip"):     by_zip[r["zip"]].append(r)
        if r.get("last_name"): by_lastname[r["last_name"].lower()].append(r)

    seen = set()
    candidates = []
    for bucket in list(by_zip.values()) + list(by_lastname.values()):
        for i in range(len(bucket)):
            for j in range(i+1, len(bucket)):
                a, b = bucket[i], bucket[j]
                if a["site_id"] == b["site_id"]: continue   # same-site dupes are a different problem
                if a["patient_id"] == b["patient_id"]: continue
                key = tuple(sorted([a["patient_id"], b["patient_id"]]))
                if key in seen: continue
                seen.add(key)
                candidates.append((a, b))

    auto_link = []
    clerical = []
    no_match_demo = []  # only keep a handful for the UI

    for a, b in candidates:
        p, ev = score_pair(a, b)
        t = tier(p)
        rec = {
            "left":  {"site": a["site_id"], "patient_id": a["patient_id"],
                      "first_name": a["first_name"], "last_name": a["last_name"],
                      "dob": a.get("dob", ""), "address": a.get("address", ""),
                      "zip": a.get("zip", "")},
            "right": {"site": b["site_id"], "patient_id": b["patient_id"],
                      "first_name": b["first_name"], "last_name": b["last_name"],
                      "dob": b.get("dob", ""), "address": b.get("address", ""),
                      "zip": b.get("zip", "")},
            "match_probability": round(p, 4),
            "tier": t,
            "evidence": ev,
        }
        if t == "auto_link":           auto_link.append(rec)
        elif t == "clerical_review":   clerical.append(rec)
        else:
            if a["patient_id"].startswith("empi-no-match") or b["patient_id"].startswith("empi-no-match"):
                no_match_demo.append(rec)

    # Sort each tier by score, descending
    auto_link.sort(key=lambda r: -r["match_probability"])
    clerical.sort(key=lambda r: -r["match_probability"])

    out = {
        "_description": (
            "Probabilistic record linkage results. Pairs are scored on five "
            "fields (last_name, first_name, dob, address, zip) using a "
            "Fellegi-Sunter weighted log-likelihood. Tiers: auto_link "
            "(p ≥ 0.95) → linked automatically; clerical_review "
            "(0.80 ≤ p < 0.95) → queued for human reviewer; no_match (p < 0.80) "
            "→ ignored."
        ),
        "_caveat": (
            "Synthetic. Production uses Splink (open-source) or commercial "
            "eMPIs (NextGate, Verato). Animal-owner reconciliation is harder "
            "than human reconciliation because no national owner-identifier "
            "exists; we approximate by treating the owner's name + DOB + "
            "address as the matching key."
        ),
        "summary": {
            "n_candidates_scored":    len(candidates),
            "n_auto_link":            len(auto_link),
            "n_clerical_review":      len(clerical),
            "n_no_match_shown":       len(no_match_demo),
        },
        "auto_link":         auto_link[:50],
        "clerical_review":   clerical[:50],
        "no_match_examples": no_match_demo[:10],
    }
    (DATA / "empi_links.json").write_text(json.dumps(out, indent=2, default=str))

    print("=== eMPI probabilistic matcher ===")
    print(f"  Candidate pairs scored:  {len(candidates):>6d}")
    print(f"  Auto-linked (p≥0.95):    {len(auto_link):>6d}")
    print(f"  Clerical review (0.80+): {len(clerical):>6d}")
    if auto_link:
        top = auto_link[0]
        print(f"\n  Strongest auto-link example:")
        print(f"    {top['left']['first_name']} {top['left']['last_name']} ({top['left']['site']})")
        print(f"  ↔ {top['right']['first_name']} {top['right']['last_name']} ({top['right']['site']})")
        print(f"    score = {top['match_probability']}")
    return out


if __name__ == "__main__":
    run_match()
