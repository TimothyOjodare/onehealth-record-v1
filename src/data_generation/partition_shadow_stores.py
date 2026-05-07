"""
Phase 6 — Per-site FHIR shadow store partitioner.

Splits the central synthetic dataset into ten per-site FHIR shadow stores
(`data/synthetic/shadow_stores/<site_id>.json`), each containing only the
resources owned by that site. Also produces a federation manifest
(`data/synthetic/federation_manifest.json`) that tells the front-end
fetcher where each patient's records live.

Architecture:

    [ ONE-HealthRecord App ]
              │
              │ federated FHIR queries (simulated in-browser)
              │
    ┌─────────┼─────────┬─────────────────┐
    ▼         ▼         ▼                 ▼
  TMC      Banner-PHX   IDEXX-Pinal     ADHS
  shadow   shadow       shadow          surveillance
  store    store        store           feed

Each shadow store is a plain JSON file; in production each would be a
HAPI FHIR server (or Epic / Cerner FHIR API endpoint, or IDEXX Practice
FHIR for veterinary).

The federation manifest maps:
    patient_id  → site_id          (where Patient/AnimalPatient lives)
    site_id     → endpoint URL     (where to fetch from)

The app uses the manifest to compose cross-site queries for a household.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"
SHADOW_DIR = DATA / "shadow_stores"
SHADOW_DIR.mkdir(exist_ok=True)


# Site identity — id, kind (hospital_system / vet_clinic / public_health),
# fhir_endpoint, vendor (Epic / Cerner / Practice Fusion / IDEXX / etc.),
# location for the federation network diagram.
SITES = [
    # Hospital systems — 6
    {"id": "tmc",            "facility": "Tucson Medical Center",         "kind": "hospital_system", "vendor": "Epic",          "fhir_version": "R4", "endpoint": "https://fhir.tmc.example/r4",                 "lat": 32.252, "lon": -110.873},
    {"id": "banner_phx",     "facility": "Banner Health Phoenix",         "kind": "hospital_system", "vendor": "Cerner",        "fhir_version": "R4", "endpoint": "https://fhir.banner-phoenix.example/r4",     "lat": 33.487, "lon": -112.060},
    {"id": "banner_mesa",    "facility": "Banner Health Mesa",            "kind": "hospital_system", "vendor": "Cerner",        "fhir_version": "R4", "endpoint": "https://fhir.banner-mesa.example/r4",        "lat": 33.416, "lon": -111.831},
    {"id": "honorhealth",    "facility": "HonorHealth Scottsdale",        "kind": "hospital_system", "vendor": "Epic",          "fhir_version": "R4", "endpoint": "https://fhir.honorhealth.example/r4",        "lat": 33.494, "lon": -111.926},
    {"id": "ihs_whiteriver", "facility": "IHS Whiteriver Service Unit",   "kind": "hospital_system", "vendor": "Cerner-IHS",    "fhir_version": "R4", "endpoint": "https://fhir.whiteriver.ihs.example/r4",     "lat": 33.840, "lon": -109.969},
    {"id": "naz_healthcare", "facility": "Northern AZ Healthcare",        "kind": "hospital_system", "vendor": "Epic",          "fhir_version": "R4", "endpoint": "https://fhir.nazh.example/r4",                "lat": 35.198, "lon": -111.651},
    # Veterinary practice networks — 4 (using IDEXX FHIR for veterinary or Covetrus)
    {"id": "vet_pinal",      "facility": "Pinal Mixed-Practice Vet",      "kind": "vet_clinic",      "vendor": "IDEXX-VetFHIR", "fhir_version": "R5-vet-ballot", "endpoint": "https://fhir.pinal-vet.example/r5",  "lat": 33.058, "lon": -111.992},
    {"id": "vet_tucson",     "facility": "Tucson Companion-Animal Vet",   "kind": "vet_clinic",      "vendor": "Covetrus",      "fhir_version": "R5-vet-ballot", "endpoint": "https://fhir.tucson-vet.example/r5", "lat": 32.252, "lon": -110.910},
    {"id": "vet_cochise",    "facility": "Cochise Large-Animal Vet",      "kind": "vet_clinic",      "vendor": "AVImark+VetFHIR-shim", "fhir_version": "R5-vet-ballot", "endpoint": "https://fhir.cochise-vet.example/r5", "lat": 31.554, "lon": -110.300},
    {"id": "vet_phx",        "facility": "Phoenix Companion-Animal Vet",  "kind": "vet_clinic",      "vendor": "IDEXX-VetFHIR", "fhir_version": "R5-vet-ballot", "endpoint": "https://fhir.phx-vet.example/r5",      "lat": 33.487, "lon": -112.060},
    # Public health / regulatory — 3 (data sinks for surveillance, not full FHIR shadows)
    {"id": "adhs",           "facility": "Arizona Department of Health Services", "kind": "public_health", "vendor": "ADHS-MEDSIS",     "fhir_version": "R4-PH-profile",   "endpoint": "https://surveillance.adhs.az.example/r4", "lat": 33.448, "lon": -112.077},
    {"id": "apache_tribal",  "facility": "Apache Tribal Health Authority",       "kind": "public_health", "vendor": "RPMS+FHIR-shim",  "fhir_version": "R4",              "endpoint": "https://fhir.apache-tribal.example/r4",   "lat": 33.840, "lon": -109.969},
    {"id": "usda_aphis",     "facility": "USDA APHIS Region 7",                  "kind": "public_health", "vendor": "USDA-VSPS",       "fhir_version": "R4-vet-PH-profile","endpoint": "https://vsps.aphis.usda.example/r4",     "lat": 38.000, "lon": -100.000},
]
SITE_BY_ID = {s["id"]: s for s in SITES}


# Map provider_id → site_id (already encoded in the provider directory by facility name)
def _build_provider_to_site(prov_dir: dict) -> dict[str, str]:
    facility_to_site = {s["facility"]: s["id"] for s in SITES}
    out = {}
    for p in prov_dir["physicians"]:    out[p["id"]] = facility_to_site[p["facility"]]
    for v in prov_dir["veterinarians"]: out[v["id"]] = facility_to_site[v["facility"]]
    for p in prov_dir["public_health"]: out[p["id"]] = facility_to_site[p["facility"]]
    return out


def main() -> None:
    households_bundle = json.loads((DATA / "households.json").read_text())
    encounters_bundle = json.loads((DATA / "encounters.json").read_text())
    providers         = json.loads((DATA / "providers.json").read_text())

    prov_to_site = _build_provider_to_site(providers)
    # patient_id → site_id (humans → physician's site; animals → vet's site)
    patient_to_site: dict[str, str] = {}
    patient_to_provider: dict[str, str] = {}
    for a in providers["patient_assignments"]:
        site = prov_to_site.get(a["provider_id"], "tmc")  # safe fallback
        patient_to_site[a["patient_id"]] = site
        patient_to_provider[a["patient_id"]] = a["provider_id"]

    # Build per-site shadow stores
    shadows: dict[str, dict] = defaultdict(lambda: {
        "patients": [],          # FHIR Patient (humans)
        "animal_patients": [],   # AnimalPatient (vet R5 profile)
        "encounters": [],        # FHIR Encounter
        "conditions": [],        # FHIR Condition
        "household_refs": set(), # household_ids the site participates in
    })

    # Distribute patients
    for hh in households_bundle["households"]:
        for h in hh.get("humans", []):
            site = patient_to_site.get(h["id"])
            if not site: continue
            shadows[site]["patients"].append({
                **h,
                "_provenance": {
                    "site": site,
                    "site_facility": SITE_BY_ID[site]["facility"],
                    "vendor": SITE_BY_ID[site]["vendor"],
                    "fhir_version": SITE_BY_ID[site]["fhir_version"],
                    "endpoint": SITE_BY_ID[site]["endpoint"],
                    "primary_provider_id": patient_to_provider[h["id"]],
                }
            })
            shadows[site]["household_refs"].add(hh["household_id"])
        for a in hh.get("animals", []):
            site = patient_to_site.get(a["id"])
            if not site: continue
            shadows[site]["animal_patients"].append({
                **a,
                "_provenance": {
                    "site": site,
                    "site_facility": SITE_BY_ID[site]["facility"],
                    "vendor": SITE_BY_ID[site]["vendor"],
                    "fhir_version": SITE_BY_ID[site]["fhir_version"],
                    "endpoint": SITE_BY_ID[site]["endpoint"],
                    "primary_provider_id": patient_to_provider[a["id"]],
                }
            })
            shadows[site]["household_refs"].add(hh["household_id"])
        for c in hh.get("conditions", []):
            # Condition follows its subject's site
            ref = c.get("subject", {}).get("reference", "")
            pid = ref.split("/", 1)[-1] if "/" in ref else ""
            site = patient_to_site.get(pid)
            if not site: continue
            shadows[site]["conditions"].append({**c, "_site": site})

    # Encounters follow the patient's site
    for enc in encounters_bundle["encounters"]:
        pid_ref = (enc.get("subject") or {}).get("reference", "")
        pid = pid_ref.split("/", 1)[-1] if "/" in pid_ref else ""
        site = patient_to_site.get(pid)
        if not site: continue
        shadows[site]["encounters"].append({**enc, "_site": site})

    # Convert sets to sorted lists, write each shadow store
    for site_id, store in shadows.items():
        site_meta = SITE_BY_ID[site_id]
        out = {
            "_metadata": {
                "site_id": site_id,
                "facility": site_meta["facility"],
                "kind": site_meta["kind"],
                "vendor": site_meta["vendor"],
                "fhir_version": site_meta["fhir_version"],
                "endpoint": site_meta["endpoint"],
                "lat": site_meta["lat"],
                "lon": site_meta["lon"],
                "n_patients":        len(store["patients"]),
                "n_animal_patients": len(store["animal_patients"]),
                "n_encounters":      len(store["encounters"]),
                "n_conditions":      len(store["conditions"]),
                "n_households_participating": len(store["household_refs"]),
                "_caveat": (
                    "Synthetic shadow store. Production: each site runs a real FHIR server "
                    f"({site_meta['vendor']} {site_meta['fhir_version']}) populated from its native EHR. "
                    "Authentication via SMART-on-FHIR; cross-site queries enforced at the API layer."
                ),
            },
            "patients":         store["patients"],
            "animal_patients":  store["animal_patients"],
            "encounters":       store["encounters"],
            "conditions":       store["conditions"],
            "household_refs":   sorted(store["household_refs"]),
        }
        (SHADOW_DIR / f"{site_id}.json").write_text(json.dumps(out, indent=2, default=str))

    # ADHS / tribal / APHIS shadow stores hold ZERO patient records — only
    # surveillance feeds. Generate empty placeholders so the topology is complete.
    for ph_site in ["adhs", "apache_tribal", "usda_aphis"]:
        site_meta = SITE_BY_ID[ph_site]
        out = {
            "_metadata": {
                "site_id": ph_site,
                "facility": site_meta["facility"],
                "kind": "public_health",
                "vendor": site_meta["vendor"],
                "fhir_version": site_meta["fhir_version"],
                "endpoint": site_meta["endpoint"],
                "lat": site_meta["lat"],
                "lon": site_meta["lon"],
                "n_patients": 0,
                "n_animal_patients": 0,
                "n_encounters": 0,
                "n_conditions": 0,
                "_role": "surveillance_sink",
                "_caveat": "Public-health authorities receive aggregate surveillance feeds and reportable-disease ELRs only. They do not hold primary clinical records.",
            },
            "patients": [], "animal_patients": [], "encounters": [], "conditions": [],
            "household_refs": [],
            "surveillance_feeds": [
                "ADHS Reportable Disease ELR (NNDSS HL7 v2.5.1)" if ph_site == "adhs" else "",
                "ADHS Vector Surveillance Feed (CDC ArboNET-equivalent)" if ph_site == "adhs" else "",
                "Apache Tribal Health surveillance feed" if ph_site == "apache_tribal" else "",
                "USDA VSPS Reportable Animal Disease feed" if ph_site == "usda_aphis" else "",
            ],
        }
        out["surveillance_feeds"] = [f for f in out["surveillance_feeds"] if f]
        (SHADOW_DIR / f"{ph_site}.json").write_text(json.dumps(out, indent=2, default=str))

    # Federation manifest
    manifest = {
        "_description": (
            "Federation manifest. Maps every patient and every household to the "
            "site that owns the primary record. The ONE-HealthRecord application "
            "uses this manifest to compose cross-site FHIR queries — it does NOT "
            "hold primary clinical data itself."
        ),
        "_caveat": (
            "Synthetic. Production: this manifest is itself a federated structure "
            "— each site publishes its own /Patient catalog, and an enterprise "
            "Master Patient Index (eMPI) reconciles identities across sites."
        ),
        "sites": SITES,
        "patient_index": [
            {"patient_id": pid, "site_id": s, "provider_id": patient_to_provider.get(pid, "")}
            for pid, s in sorted(patient_to_site.items())
        ],
        "household_index": [
            {
                "household_id": hh["household_id"],
                "participating_sites": sorted({
                    patient_to_site.get(p["id"]) for p in hh.get("humans", []) if patient_to_site.get(p["id"])
                } | {
                    patient_to_site.get(a["id"]) for a in hh.get("animals", []) if patient_to_site.get(a["id"])
                }),
                "n_humans": len(hh.get("humans", [])),
                "n_animals": len(hh.get("animals", [])),
            }
            for hh in households_bundle["households"]
        ],
    }
    (DATA / "federation_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))

    # Console summary
    print("=== Per-site FHIR shadow stores ===\n")
    print(f"{'Site':28s}  {'Kind':18s}  {'Vendor':22s}  {'Patients':>9s}  {'Animals':>8s}  {'Encs':>6s}")
    print("-" * 100)
    total_p = total_a = total_e = 0
    for s in SITES:
        store_path = SHADOW_DIR / f"{s['id']}.json"
        meta = json.loads(store_path.read_text())["_metadata"]
        print(f"{s['facility'][:28]:28s}  {s['kind']:18s}  {s['vendor'][:22]:22s}  {meta['n_patients']:>9d}  {meta['n_animal_patients']:>8d}  {meta['n_encounters']:>6d}")
        total_p += meta["n_patients"]; total_a += meta["n_animal_patients"]; total_e += meta["n_encounters"]
    print("-" * 100)
    print(f"{'TOTAL':28s}  {'':18s}  {'':22s}  {total_p:>9d}  {total_a:>8d}  {total_e:>6d}")
    print()

    # Cross-site households (the One Health linkage points)
    cross_site = sum(1 for h in manifest["household_index"] if len(h["participating_sites"]) > 1)
    print(f"Multi-site households (cross-org One Health linkage): {cross_site}")
    print(f"Manifest written to {DATA / 'federation_manifest.json'}")


if __name__ == "__main__":
    main()
