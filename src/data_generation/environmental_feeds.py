"""
Phase 8 — Environmental Surveillance feeds.

Generates synthetic-but-realistic environmental health data calibrated to
real Arizona conditions across 5 sources:

  1. EPA AirNow — PM2.5, AQI per county-of-station for 14 AZ stations
  2. NWS — heat, dust, monsoon advisories
  3. ArboNET — mosquito + tick vector surveillance counts
  4. USGS — plague-rodent surveillance (flea index in prairie-dog colonies)
  5. AGFD — wildlife mortality reports (deer, bird, prairie dog)

All values are seeded from random.Random(42) for reproducibility.
Calibrated against published AZ ranges:
  - PM2.5 typical: 5-12 µg/m³; dust storm spike: 40-150
  - AQI typical: 30-80; "moderate" alert: 100-150
  - Anopheles mosquito counts: 0-50/trap-night in monsoon
  - Plague-flea-index: 0.05-0.40 in enzootic colonies
"""
from __future__ import annotations
import json
import random
from datetime import date, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "synthetic"

# AZ EPA AirNow stations (14 reference stations across the state)
AIRNOW_STATIONS = [
    {"id": "AZ-04013-001", "name": "Phoenix - JLG Supersite",     "county": "Maricopa", "lat": 33.503, "lon": -112.096},
    {"id": "AZ-04013-002", "name": "Phoenix - Central",            "county": "Maricopa", "lat": 33.458, "lon": -112.072},
    {"id": "AZ-04013-003", "name": "Mesa - Brooks",                "county": "Maricopa", "lat": 33.396, "lon": -111.866},
    {"id": "AZ-04013-004", "name": "Glendale",                     "county": "Maricopa", "lat": 33.541, "lon": -112.169},
    {"id": "AZ-04019-001", "name": "Tucson - Children's Park",     "county": "Pima",     "lat": 32.207, "lon": -110.880},
    {"id": "AZ-04019-002", "name": "Tucson - Geronimo",            "county": "Pima",     "lat": 32.314, "lon": -110.957},
    {"id": "AZ-04021-001", "name": "Casa Grande",                  "county": "Pinal",    "lat": 32.879, "lon": -111.751},
    {"id": "AZ-04025-001", "name": "Prescott Valley",              "county": "Yavapai",  "lat": 34.610, "lon": -112.316},
    {"id": "AZ-04005-001", "name": "Flagstaff - West",             "county": "Coconino", "lat": 35.198, "lon": -111.652},
    {"id": "AZ-04017-001", "name": "Holbrook",                     "county": "Navajo",   "lat": 34.901, "lon": -110.158},
    {"id": "AZ-04001-001", "name": "Window Rock",                  "county": "Apache",   "lat": 35.679, "lon": -109.060},
    {"id": "AZ-04023-001", "name": "Nogales",                      "county": "Santa Cruz","lat": 31.341, "lon": -110.940},
    {"id": "AZ-04003-001", "name": "Sierra Vista",                 "county": "Cochise",  "lat": 31.555, "lon": -110.303},
    {"id": "AZ-04027-001", "name": "Yuma - 32nd Street",           "county": "Yuma",     "lat": 32.694, "lon": -114.622},
]

# NWS forecast offices serving AZ
NWS_OFFICES = [
    {"office": "PSR", "name": "Phoenix",   "lat": 33.4, "lon": -112.0},
    {"office": "TWC", "name": "Tucson",    "lat": 32.2, "lon": -110.9},
    {"office": "FGZ", "name": "Flagstaff", "lat": 35.2, "lon": -111.6},
]

# ArboNET vector surveillance traps (mosquito + tick)
ARBONET_TRAPS = [
    {"id": "MOSQ-MARI-001", "kind": "mosquito",  "species_target": ["Culex tarsalis", "Aedes aegypti"], "county": "Maricopa", "site": "Salt River corridor"},
    {"id": "MOSQ-MARI-002", "kind": "mosquito",  "species_target": ["Culex tarsalis"], "county": "Maricopa", "site": "Tres Rios wetland"},
    {"id": "MOSQ-PIMA-001", "kind": "mosquito",  "species_target": ["Aedes aegypti", "Culex"], "county": "Pima", "site": "Rillito wash"},
    {"id": "MOSQ-PINAL-001","kind": "mosquito",  "species_target": ["Culex tarsalis"], "county": "Pinal", "site": "Picacho reservoir"},
    {"id": "MOSQ-YUMA-001", "kind": "mosquito",  "species_target": ["Anopheles freeborni", "Culex"], "county": "Yuma", "site": "Colorado River"},
    {"id": "MOSQ-COCO-001", "kind": "mosquito",  "species_target": ["Culex"], "county": "Coconino", "site": "Lake Mary"},
    {"id": "TICK-PINAL-001","kind": "tick",      "species_target": ["Rhipicephalus sanguineus"], "county": "Pinal", "site": "Tribal land surveillance"},
    {"id": "TICK-APACH-001","kind": "tick",      "species_target": ["Rhipicephalus sanguineus"], "county": "Apache", "site": "Whiteriver"},
    {"id": "TICK-NAVAJ-001","kind": "tick",      "species_target": ["Rhipicephalus sanguineus"], "county": "Navajo", "site": "Window Rock"},
    {"id": "TICK-PIMA-001", "kind": "tick",      "species_target": ["Dermacentor", "Rhipicephalus"], "county": "Pima", "site": "Tohono O'odham Nation"},
]

# USGS plague-rodent surveillance sites
USGS_PLAGUE_SITES = [
    {"id": "USGS-COCO-PD-01", "county": "Coconino", "site": "Wupatki National Monument", "host": "Gunnison's prairie dog", "elevation_ft": 4500},
    {"id": "USGS-COCO-PD-02", "county": "Coconino", "site": "Bonito Park",                "host": "Gunnison's prairie dog", "elevation_ft": 7000},
    {"id": "USGS-APACH-PD-01","county": "Apache",   "site": "Apache-Sitgreaves National Forest", "host": "Black-tailed prairie dog", "elevation_ft": 6800},
    {"id": "USGS-NAVAJ-PD-01","county": "Navajo",   "site": "Hopi Reservation (with permission)", "host": "Gunnison's prairie dog", "elevation_ft": 6200},
    {"id": "USGS-YAV-RD-01",  "county": "Yavapai",  "site": "Prescott National Forest",   "host": "Round-tailed ground squirrel", "elevation_ft": 5400},
]

# AGFD wildlife mortality reporting sites
AGFD_SITES = [
    {"id": "AGFD-COCO-001", "county": "Coconino", "site": "Coconino National Forest"},
    {"id": "AGFD-MARI-001", "county": "Maricopa", "site": "Tonto National Forest"},
    {"id": "AGFD-PIMA-001", "county": "Pima",     "site": "Saguaro National Park"},
    {"id": "AGFD-COCH-001", "county": "Cochise",  "site": "Coronado National Forest"},
    {"id": "AGFD-APACH-001","county": "Apache",   "site": "Apache-Sitgreaves National Forest"},
]


def gen_airnow(rng: random.Random):
    """Generate today's AirNow readings + 30-day history per station."""
    today = date(2026, 5, 5)
    obs = []
    for station in AIRNOW_STATIONS:
        # Maricopa + Pinal have higher baseline PM2.5 (urbanization + agriculture)
        # Northern stations have lower baseline (high elevation, lower density)
        if station["county"] in ("Maricopa", "Pinal", "Yuma"):
            baseline = rng.uniform(8, 15)
        elif station["county"] in ("Coconino", "Apache", "Navajo"):
            baseline = rng.uniform(3, 8)
        else:
            baseline = rng.uniform(5, 11)

        # 30-day history
        history = []
        for d in range(30, -1, -1):
            day = today - timedelta(days=d)
            # Late April / early May has occasional dust storms in AZ
            spike = 0
            if d in (4, 12, 17):
                spike = rng.uniform(20, 80)
            pm25 = max(0.5, baseline + rng.gauss(0, 2.5) + spike)
            aqi = int(min(500, pm25 * 4.5 + rng.uniform(-10, 10)))  # rough mapping
            history.append({
                "date": day.isoformat(),
                "pm25_ugm3": round(pm25, 1),
                "aqi": aqi,
                "category": _aqi_category(aqi),
            })

        # Today's "live" reading is the last entry
        latest = history[-1]
        obs.append({
            **station,
            "latest_reading": latest,
            "history_30d": history,
            "trend": _trend(history),
            "data_source": "EPA AirNow API",
            "data_caveat": "Synthetic for demo. Production: pulls from https://docs.airnowapi.org/",
        })
    return obs


def _aqi_category(aqi):
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"


def _trend(history):
    recent = sum(h["pm25_ugm3"] for h in history[-7:]) / 7
    prior = sum(h["pm25_ugm3"] for h in history[-21:-7]) / 14
    if recent > prior * 1.15: return "rising"
    if recent < prior * 0.85: return "falling"
    return "stable"


def gen_nws(rng: random.Random):
    """Generate active NWS advisories."""
    today = date(2026, 5, 5).isoformat()
    advisories = [
        {
            "id": "NWS-PSR-2026-1284",
            "office": "PSR",
            "type": "Excessive Heat Watch",
            "severity": "Moderate",
            "areas": ["Phoenix Metro", "Maricopa County (lower elevations)"],
            "headline": "Excessive Heat Watch in effect from Thursday afternoon through Sunday evening",
            "expected_temps_f": "108-114°F daytime; 80-86°F overnight",
            "issued": "2026-05-05T14:00:00Z",
            "expires": "2026-05-08T22:00:00Z",
            "one_health_relevance": "Heat-illness ED visits expected to rise 30-50%. ADHS heat-illness reporting threshold may trigger."
        },
        {
            "id": "NWS-PSR-2026-1285",
            "office": "PSR",
            "type": "Blowing Dust Advisory",
            "severity": "Minor",
            "areas": ["Pinal County", "Maricopa County (south)"],
            "headline": "Blowing dust expected late Wednesday afternoon along I-10",
            "expected_temps_f": "Visibility ¼ mile or less in heaviest dust",
            "issued": "2026-05-05T11:00:00Z",
            "expires": "2026-05-05T22:00:00Z",
            "one_health_relevance": "Coccidioides spore aerosolization risk elevated. Valley fever case ascertainment expected to rise 14-21 days post-event.",
        },
        {
            "id": "NWS-FGZ-2026-0844",
            "office": "FGZ",
            "type": "Red Flag Warning",
            "severity": "Major",
            "areas": ["Coconino County", "Yavapai County north"],
            "headline": "Critical fire weather conditions Wednesday afternoon",
            "expected_temps_f": "RH 8-15%, sustained wind 25-35 mph, gusts to 50",
            "issued": "2026-05-05T05:00:00Z",
            "expires": "2026-05-05T20:00:00Z",
            "one_health_relevance": "Smoke inhalation surveillance activated. Wildlife displacement may shift plague-host distribution.",
        },
    ]
    return {
        "as_of": today,
        "active_advisories": advisories,
        "data_source": "National Weather Service",
        "data_caveat": "Synthetic for demo. Production: https://api.weather.gov/alerts/active?area=AZ",
    }


def gen_arbonet(rng: random.Random):
    """Generate ArboNET vector surveillance counts per trap."""
    today = date(2026, 5, 5)
    traps = []
    for trap in ARBONET_TRAPS:
        # 90-day count history
        history = []
        for d in range(90, -1, -1):
            day = today - timedelta(days=d)
            # Mosquitoes: increase in monsoon-prep (April-May), peak July-Sept
            if trap["kind"] == "mosquito":
                # Some seasonality
                month = day.month
                if month in (7, 8, 9): seasonal = 1.6
                elif month in (5, 6, 10): seasonal = 1.0
                else: seasonal = 0.4

                base = rng.poisson(8) if hasattr(rng, 'poisson') else max(0, int(rng.gauss(8, 4)))
                count = max(0, int(base * seasonal + rng.gauss(0, 2)))

                # Pinal county has the WNV vector anomaly we use throughout the demo
                if trap["county"] == "Pinal" and (today - day).days < 21:
                    count = max(count, int(rng.gauss(45, 8)))  # 27σ anomaly

            else:  # tick
                base = max(0, int(rng.gauss(4, 1.5)))
                count = base
                # Apache reservation has elevated brown dog tick burden
                if trap["county"] == "Apache":
                    count = int(count * 1.8)

            history.append({"date": day.isoformat(), "count": count, "trap_nights": 1})

        # 7-day average + WNV positive count (for mosquito traps)
        recent = [h["count"] for h in history[-7:]]
        wnv_pos = 0
        if trap["kind"] == "mosquito" and trap["county"] == "Pinal":
            wnv_pos = rng.choice([0, 0, 1, 1, 2])  # occasional positive
        traps.append({
            **trap,
            "latest_count": history[-1]["count"],
            "avg_7d": round(sum(recent)/7, 1),
            "wnv_positive_pools_7d": wnv_pos,
            "history_90d": history,
            "is_anomaly": trap["county"] == "Pinal" and trap["kind"] == "mosquito",
        })
    return {
        "as_of": today.isoformat(),
        "traps": traps,
        "data_source": "ArboNET via CDC + ADHS Vector-borne Disease Program",
        "data_caveat": "Synthetic. Production: pulls from CDC ArboNET feed + ADHS county-level surveillance.",
    }


def gen_usgs_plague(rng: random.Random):
    """Generate USGS plague-rodent surveillance flea index per site."""
    today = date(2026, 5, 5)
    sites = []
    for site in USGS_PLAGUE_SITES:
        history = []
        for d in range(60, -1, -1):
            day = today - timedelta(days=d)
            # Coconino + Apache: enzootic = elevated baseline
            if site["county"] in ("Coconino", "Apache"):
                base_index = rng.uniform(0.18, 0.35)
            else:
                base_index = rng.uniform(0.05, 0.15)
            jitter = rng.gauss(0, 0.04)
            flea_idx = max(0, base_index + jitter)
            history.append({
                "date": day.isoformat(),
                "fleas_per_burrow": round(flea_idx, 3),
                "burrows_sampled": rng.randint(8, 24),
            })

        latest = history[-1]
        # Plague positivity is rare; let's seed a positive in Coconino for the demo
        ypestis_status = "negative"
        if site["county"] == "Coconino" and rng.random() < 0.4:
            ypestis_status = "positive"
        elif site["county"] == "Apache" and rng.random() < 0.2:
            ypestis_status = "positive"

        sites.append({
            **site,
            "latest_flea_index": latest["fleas_per_burrow"],
            "ypestis_status": ypestis_status,
            "last_positive_date": "2026-04-22" if ypestis_status == "positive" else None,
            "history_60d": history,
            "alert_level": _plague_alert_level(latest["fleas_per_burrow"], ypestis_status),
        })
    return {
        "as_of": today.isoformat(),
        "sites": sites,
        "data_source": "USGS National Wildlife Health Center + ADHS partnership",
        "data_caveat": "Synthetic. Production: USGS NWHC flea-index program + ADHS state lab Y. pestis confirmation.",
    }


def _plague_alert_level(idx, status):
    if status == "positive": return "ALERT"
    if idx > 0.30: return "ELEVATED"
    if idx > 0.20: return "MONITOR"
    return "BASELINE"


def gen_agfd_wildlife(rng: random.Random):
    """Generate AGFD wildlife mortality reports."""
    today = date(2026, 5, 5)
    reports = [
        {
            "id": "AGFD-RPT-2026-0415",
            "site_id": "AGFD-COCO-001",
            "species": "Black-billed magpie",
            "n_dead": 12,
            "discovered_date": "2026-04-29",
            "suspected_cause": "West Nile virus (preliminary)",
            "lab_status": "samples submitted to AZ State Vet Lab",
            "one_health_relevance": "Avian die-off precedes human West Nile surge by 3-6 weeks; ADHS notified.",
            "county": "Coconino",
        },
        {
            "id": "AGFD-RPT-2026-0418",
            "site_id": "AGFD-MARI-001",
            "species": "Mule deer",
            "n_dead": 4,
            "discovered_date": "2026-05-02",
            "suspected_cause": "Epizootic hemorrhagic disease (EHD)",
            "lab_status": "lab confirmation pending",
            "one_health_relevance": "EHD is non-zoonotic but indicates Culicoides midge activity; co-vector for bluetongue (zoonotic potential).",
            "county": "Maricopa",
        },
        {
            "id": "AGFD-RPT-2026-0421",
            "site_id": "AGFD-COCH-001",
            "species": "Coyote",
            "n_dead": 2,
            "discovered_date": "2026-05-03",
            "suspected_cause": "Plague (Y. pestis confirmed in 1 of 2)",
            "lab_status": "1 confirmed positive 2026-05-04",
            "one_health_relevance": "Plague confirmation in coyote indicates active prairie-dog die-off in Coronado NF. Cross-flagged to USGS site USGS-COCO-PD-02.",
            "county": "Cochise",
        },
        {
            "id": "AGFD-RPT-2026-0422",
            "site_id": "AGFD-APACH-001",
            "species": "Gunnison's prairie dog",
            "n_dead": 47,
            "discovered_date": "2026-05-04",
            "suspected_cause": "Plague die-off (Y. pestis)",
            "lab_status": "samples submitted; Y. pestis F1 antigen positive",
            "one_health_relevance": "Major die-off — colony at Apache-Sitgreaves NF. ADHS + CDC notified per multi-jurisdictional protocol. Surveillance intensified for human cases in Apache + Navajo counties for the next 60 days.",
            "county": "Apache",
        },
        {
            "id": "AGFD-RPT-2026-0423",
            "site_id": "AGFD-PIMA-001",
            "species": "Greater roadrunner",
            "n_dead": 1,
            "discovered_date": "2026-05-04",
            "suspected_cause": "Trauma (vehicle strike)",
            "lab_status": "no further work",
            "one_health_relevance": "None.",
            "county": "Pima",
        },
    ]
    return {
        "as_of": today.isoformat(),
        "active_reports": reports,
        "data_source": "Arizona Game and Fish Department + AZ State Veterinary Diagnostic Laboratory",
        "data_caveat": "Synthetic. Production: AGFD field-report system + state-lab confirmation.",
    }


def main() -> None:
    rng = random.Random(42)
    feeds = {
        "_metadata": {
            "generated": "2026-05-05",
            "data_caveat": "All values are synthetic, calibrated to realistic AZ ranges. Production deployment swaps in real APIs from EPA AirNow, NWS, ArboNET, USGS NWHC, and AGFD.",
        },
        "epa_airnow": gen_airnow(rng),
        "nws": gen_nws(rng),
        "arbonet": gen_arbonet(rng),
        "usgs_plague": gen_usgs_plague(rng),
        "agfd_wildlife": gen_agfd_wildlife(rng),
    }
    out = DATA / "environmental_feeds.json"
    out.write_text(json.dumps(feeds, indent=2, default=str))

    print("Phase 8 — Environmental Surveillance feeds")
    print(f"  EPA AirNow stations:        {len(feeds['epa_airnow'])}")
    print(f"  NWS active advisories:      {len(feeds['nws']['active_advisories'])}")
    print(f"  ArboNET traps:              {len(feeds['arbonet']['traps'])}")
    print(f"  USGS plague-rodent sites:   {len(feeds['usgs_plague']['sites'])}")
    print(f"  AGFD wildlife reports:      {len(feeds['agfd_wildlife']['active_reports'])}")
    print(f"  Output: {out}  ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
