"""
Synthetic Arizona One Health household generator (expanded).

Hand-crafted scenarios (12 total — story-rich, used in the demo):
    01 Hernandez (Tucson)        — coccidioidomycosis cross-species cluster (human+dog)
    02 Johnson   (Florence)      — ehrlichiosis dog → RMSF human (tick-borne)
    03 Williams  (Maricopa rural)— hantavirus exposure (rodent infestation)
    04 Patel     (Yuma)          — leptospirosis dog from canal
    05 Chen      (Flagstaff)     — healthy control household
    06 Begay     (Apache Co.)    — plague cluster (cat + human, flea/rodent)
    07 Ramirez   (Cochise)       — West Nile virus (horse → mosquito → human)
    08 Thompson  (Mohave)        — rabies exposure (skunk bite, dog quarantine)
    09 Becker    (Santa Cruz)    — Q fever (goat farm, human pneumonia)
    10 Nguyen    (Maricopa urb.) — psittacosis (parrot + human)
    11 Sanchez   (Pinal)         — tularemia (rabbit hunting, tick-borne)
    12 Yazzie    (Navajo)        — salmonellosis (reptile pet → child)

Procedural generator: produces 108 additional procedural households for scale,
with chronic conditions for longitudinal demos.
"""
from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = PROJECT_ROOT / "data" / "reference"
OUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_reference() -> dict[str, Any]:
    counties = json.loads((REF_DIR / "arizona_counties.json").read_text())["counties"]
    zips     = json.loads((REF_DIR / "arizona_zip_codes.json").read_text())["zip_codes"]
    diseases = json.loads((REF_DIR / "diseases_az.json").read_text())["diseases"]
    terms    = json.loads((REF_DIR / "clinical_terminologies.json").read_text())
    return {"counties": counties, "zips": zips, "diseases": diseases, "terms": terms}


REF = _load_reference()
COUNTIES = {c["name"]: c for c in REF["counties"]}
DISEASES = {d["id"]: d for d in REF["diseases"]}

# Group ZIPs by county for weighted selection
ZIPS_BY_COUNTY: dict[str, list[dict]] = {}
for _z in REF["zips"]:
    ZIPS_BY_COUNTY.setdefault(_z["county"], []).append(_z)


def _human_condition(display: str) -> dict[str, str]:
    for c in REF["terms"]["conditions_human"]:
        if c["display"].lower().startswith(display.lower()):
            return c
    raise KeyError(f"unknown human condition: {display}")


def _animal_condition(display: str) -> dict[str, str]:
    for c in REF["terms"]["conditions_animal"]:
        if c["display"].lower().startswith(display.lower()):
            return c
    raise KeyError(f"unknown animal condition: {display}")


def _new_id() -> str:
    return str(uuid.uuid4())


def _today_offset(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _patient_resource(pid, given, family, gender, dob, county, household_id,
                      chronic_conditions=None):
    res = {
        "resourceType": "Patient",
        "id": pid,
        "meta": {"profile": ["http://onehealthrecord.org/StructureDefinition/HumanPatient"]},
        "extension": [
            {"url": "http://onehealthrecord.org/household-id", "valueString": household_id},
        ],
        "name": [{"family": family, "given": [given]}],
        "gender": gender,
        "birthDate": dob,
        "address": [{
            "city": county["seat"], "state": "AZ", "country": "US",
            "extension": [
                {"url": "http://hl7.org/fhir/StructureDefinition/geolocation",
                 "extension": [
                     {"url": "latitude",  "valueDecimal": county["lat"]},
                     {"url": "longitude", "valueDecimal": county["lon"]},
                 ]},
                {"url": "http://onehealthrecord.org/county-fips",
                 "valueString": county["fips"]},
            ],
        }],
    }
    if chronic_conditions:
        res["chronic_conditions"] = chronic_conditions
    return res


def _condition_resource(subject_ref, condition, onset, *, is_animal=False,
                        confidence=0.92, status="active"):
    code_system = ("http://snomed.info/sct-vet" if is_animal else "http://snomed.info/sct")
    snomed = condition["snomed_vet"] if is_animal else condition["snomed"]
    coding = [{"system": code_system, "code": snomed, "display": condition["display"]}]
    if not is_animal and "icd10" in condition:
        coding.append({"system": "http://hl7.org/fhir/sid/icd-10-cm",
                       "code": condition["icd10"], "display": condition["display"]})
    return {
        "resourceType": "Condition",
        "id": _new_id(),
        "subject": {"reference": subject_ref},
        "code": {"coding": coding, "text": condition["display"]},
        "onsetDateTime": onset,
        "recordedDate": onset,
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                       "code": status}]},
        "extension": [
            {"url": "http://onehealthrecord.org/one-health-relevant",
             "valueBoolean": condition.get("one_health_relevant", False)},
            {"url": "http://onehealthrecord.org/authorship",
             "valueString": "machine-authored"},
            {"url": "http://onehealthrecord.org/confidence",
             "valueDecimal": confidence},
        ],
    }


def _animal_record(aid, name, species, breed, sex, dob, county, household_id):
    species_display = {"dog":"Canis lupus familiaris","cat":"Felis catus",
                       "horse":"Equus caballus","bird":"Aves spp.",
                       "goat":"Capra aegagrus hircus","rabbit":"Oryctolagus cuniculus",
                       "reptile":"Reptilia spp."}.get(species, species)
    return {
        "resourceType": "AnimalPatient",
        "id": aid,
        "meta": {"profile": ["http://onehealthrecord.org/StructureDefinition/AnimalPatient"]},
        "household_id": household_id,
        "name": name,
        "species": {"system": "http://onehealthrecord.org/species",
                    "code": species, "display": species_display},
        "breed": breed,
        "sex": sex,
        "birthDate": dob,
        "address": {
            "city": county["seat"], "state": "AZ", "country": "US",
            "geolocation": {"lat": county["lat"], "lon": county["lon"]},
            "county_fips": county["fips"],
        },
    }


def _pick_zip(rng: random.Random, county_name: str) -> dict:
    """Pick a ZIP within the given county, weighted by ZIP population."""
    zips = ZIPS_BY_COUNTY.get(county_name, [])
    if not zips:
        # Fallback: synthesize a county-level pseudo-ZIP if county has no entries
        c = COUNTIES.get(county_name, {"name": county_name, "fips": "04000", "lat": 0, "lon": 0})
        return {
            "zip": "00000", "name": county_name, "county_fips": c.get("fips", "04000"),
            "county": county_name, "population": 1000, "lat": c.get("lat", 0), "lon": c.get("lon", 0),
            "epa_eqi": c.get("epa_eqi", 0.5), "vector_burden_idx": 0.5,
            "cocci_endemic": c.get("cocci_endemic", "low"), "rodent_risk": "moderate",
            "plague_enzootic": False, "urbanicity": "rural"
        }
    weights = [max(z.get("population", 100), 100) for z in zips]
    return rng.choices(zips, weights=weights, k=1)[0]


def _disease_env_risk(zip_record: dict) -> dict[str, float]:
    """
    Compute a per-disease environmental-risk score in [0, 1] for this ZIP, used
    by the disease-assignment step. Higher score → higher prior probability
    that a household at this ZIP carries an active case of the disease.

    Scores are calibrated to match the published epidemiology in diseases_az.json
    plus the ZIP-level environmental fields (cocci_endemic, vector_burden_idx,
    rodent_risk, plague_enzootic, urbanicity).
    """
    cocci = {"high": 0.85, "moderate": 0.45, "low": 0.10}.get(zip_record.get("cocci_endemic", "low"), 0.10)
    vector = float(zip_record.get("vector_burden_idx", 0.5))
    rodent = {"high": 0.85, "moderate": 0.45, "low": 0.15}.get(zip_record.get("rodent_risk", "moderate"), 0.45)
    plague = 0.85 if zip_record.get("plague_enzootic") else 0.05
    urbanicity = zip_record.get("urbanicity", "rural")
    rural_bonus = 1.0 if urbanicity == "rural" else (0.7 if urbanicity == "suburban" else 0.4)

    return {
        "valley_fever":          cocci,
        "rmsf":                  vector * 0.9,
        "plague":                plague,
        "west_nile":             vector * 0.85,
        "hantavirus":            rodent * rural_bonus,
        "ehrlichiosis":          vector * 0.75,
        "leptospirosis":         (rodent * 0.7 + (0.6 if urbanicity != "urban" else 0.2)) / 2,
        "q_fever":               rural_bonus * 0.65,
        "psittacosis":           0.30 if urbanicity != "rural" else 0.20,
        "tularemia":             rural_bonus * 0.55,
        "rabies":                rural_bonus * 0.45,
        "salmonellosis":         0.55,
        "tuberculosis_zoonotic": 0.30 if urbanicity == "rural" else 0.10,
        "brucellosis":           0.35 if urbanicity == "rural" else 0.10,
    }


def _environmental_profile(household_id: str, county: dict, zip_record: dict | None = None) -> dict:
    """Environmental profile pinned to a specific ZIP code."""
    z = zip_record or {}
    eqi = float(z.get("epa_eqi", county.get("epa_eqi", 0.5)))
    return {
        "resourceType": "EnvironmentalProfile",
        "id": _new_id(),
        "household_id": household_id,
        "zip": z.get("zip", "00000"),
        "zip_name": z.get("name", ""),
        "county_fips": county["fips"],
        "county_name": county["name"],
        "epa_eqi": eqi,
        "epa_eqi_interpretation": (
            "better-than-average" if eqi < -0.2
            else "worse-than-average" if eqi > 0.2 else "average"
        ),
        "coccidioides_endemicity": z.get("cocci_endemic", county.get("cocci_endemic", "low")),
        "vector_burden_idx":       float(z.get("vector_burden_idx", 0.5)),
        "rodent_risk":             z.get("rodent_risk", "moderate"),
        "plague_enzootic":         bool(z.get("plague_enzootic", False)),
        "urbanicity":              z.get("urbanicity", "rural"),
        "geolocation": {
            "lat": float(z.get("lat", county.get("lat", 0))),
            "lon": float(z.get("lon", county.get("lon", 0))),
        },
        "disease_environmental_risk": _disease_env_risk(z) if z else {},
    }


@dataclass
class Household:
    household_id: str
    name: str
    county: dict[str, Any]
    humans: list[dict] = field(default_factory=list)
    animals: list[dict] = field(default_factory=list)
    conditions: list[dict] = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    narrative: str = ""


# ---------------------------------------------------------------------------
# Hand-crafted scenarios
# ---------------------------------------------------------------------------
def scenario_hernandez():
    county = COUNTIES["Pima"]; hh_id = "HH-AZ-PIMA-001"
    h = Household(household_id=hh_id, name="Hernandez", county=county,
                  narrative=("Hernandez household, Tucson (Pima Co.). Maria (52) was diagnosed with "
                             "coccidioidomycosis 14 days ago. Family dog Rocco was diagnosed by their "
                             "veterinarian 6 days ago with the same organism. Husband Carlos (54) "
                             "presented today with a 3-week cough not yet worked up."))
    maria = _patient_resource(_new_id(),"Maria","Hernandez","female","1973-04-18",county,hh_id)
    carlos = _patient_resource(_new_id(),"Carlos","Hernandez","male","1971-09-02",county,hh_id,
                               chronic_conditions=["Type 2 diabetes mellitus"])
    sofia = _patient_resource(_new_id(),"Sofia","Hernandez","female","2009-11-30",county,hh_id)
    h.humans = [maria, carlos, sofia]
    rocco = _animal_record(_new_id(),"Rocco","dog","Labrador Retriever","MN","2019-06-02",county,hh_id)
    h.animals = [rocco]
    cocci_h = _human_condition("Coccidioidomycosis"); cocci_v = _animal_condition("Coccidioidomycosis")
    h.conditions = [
        _condition_resource(f"Patient/{maria['id']}", cocci_h, _today_offset(14)),
        _condition_resource(f"AnimalPatient/{rocco['id']}", cocci_v, _today_offset(6), is_animal=True),
    ]
    h.environment = _environmental_profile(hh_id, county)
    return h


def scenario_johnson():
    county = COUNTIES["Pinal"]; hh_id = "HH-AZ-PINAL-002"
    h = Household(household_id=hh_id, name="Johnson", county=county,
                  narrative=("Johnson household, Florence (Pinal Co.). Dog Bella was diagnosed with "
                             "ehrlichiosis 8 days ago. Tom (47) was bitten by a tick and presents today "
                             "with fever, headache, and developing maculopapular rash."))
    tom = _patient_resource(_new_id(),"Tom","Johnson","male","1978-01-22",county,hh_id)
    rachel = _patient_resource(_new_id(),"Rachel","Johnson","female","1980-07-14",county,hh_id)
    h.humans = [tom, rachel]
    bella = _animal_record(_new_id(),"Bella","dog","German Shepherd","FS","2020-03-15",county,hh_id)
    h.animals = [bella]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{bella['id']}", _animal_condition("Ehrlichiosis"),
                            _today_offset(8), is_animal=True),
    ]
    h.environment = _environmental_profile(hh_id, county)
    return h


def scenario_williams():
    county = COUNTIES["Maricopa"]; hh_id = "HH-AZ-MARICOPA-003"
    h = Household(household_id=hh_id, name="Williams", county=county,
                  narrative=("Williams household, rural Maricopa Co. Couple (Robert 68, Linda 65) with "
                             "rodent infestation in detached garage that they cleaned out 10 days ago. "
                             "Robert presents today with fever, myalgia, and progressive dyspnea. HPS "
                             "must be flagged."))
    robert = _patient_resource(_new_id(),"Robert","Williams","male","1957-11-08",county,hh_id,
                               chronic_conditions=["Essential hypertension","Hyperlipidemia"])
    linda = _patient_resource(_new_id(),"Linda","Williams","female","1960-02-19",county,hh_id)
    h.humans = [robert, linda]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["recent_exposures"] = [
        {"type":"rodent_infestation","date":_today_offset(10),"location":"detached_garage",
         "remediation":"self_cleaned_no_PPE"},
    ]
    return h


def scenario_patel():
    county = COUNTIES["Yuma"]; hh_id = "HH-AZ-YUMA-004"
    h = Household(household_id=hh_id, name="Patel", county=county,
                  narrative=("Patel household, Yuma. Dog Rex was diagnosed with leptospirosis 3 days "
                             "ago after swimming in an irrigation canal where the family also swims. "
                             "Prophylactic alert recommended."))
    arjun = _patient_resource(_new_id(),"Arjun","Patel","male","1985-05-12",county,hh_id)
    priya = _patient_resource(_new_id(),"Priya","Patel","female","1987-08-30",county,hh_id)
    aanya = _patient_resource(_new_id(),"Aanya","Patel","female","2015-01-04",county,hh_id)
    h.humans = [arjun, priya, aanya]
    rex = _animal_record(_new_id(),"Rex","dog","Border Collie","MN","2018-09-12",county,hh_id)
    h.animals = [rex]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{rex['id']}", _animal_condition("Leptospirosis"),
                            _today_offset(3), is_animal=True),
    ]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["shared_exposures"] = [
        {"type":"freshwater_canal","frequency":"weekly","shared_with":"household_dog"},
    ]
    return h


def scenario_chen():
    county = COUNTIES["Coconino"]; hh_id = "HH-AZ-COCONINO-005"
    h = Household(household_id=hh_id, name="Chen", county=county,
                  narrative=("Chen household, Flagstaff. Healthy young family. Negative control."))
    mei = _patient_resource(_new_id(),"Mei","Chen","female","1992-06-21",county,hh_id)
    david = _patient_resource(_new_id(),"David","Chen","male","1990-12-03",county,hh_id)
    h.humans = [mei, david]
    h.environment = _environmental_profile(hh_id, county)
    return h


def scenario_begay():
    county = COUNTIES["Apache"]; hh_id = "HH-AZ-APACHE-006"
    h = Household(household_id=hh_id, name="Begay", county=county,
                  narrative=("Begay household, near St. Johns (Apache Co.). Outdoor cat Shadow caught "
                             "and consumed multiple ground squirrels in the past month. Cat presented "
                             "to vet 4 days ago with high fever and lymphadenopathy — diagnosed plague. "
                             "Now Sarah Begay (38) presents today with fever, painful inguinal lymph "
                             "node, and rapid decline. Plague is a Class A reportable disease."))
    sarah = _patient_resource(_new_id(),"Sarah","Begay","female","1987-03-14",county,hh_id)
    daniel = _patient_resource(_new_id(),"Daniel","Begay","male","1985-08-21",county,hh_id)
    h.humans = [sarah, daniel]
    shadow = _animal_record(_new_id(),"Shadow","cat","Domestic Shorthair","FS","2021-04-10",county,hh_id)
    h.animals = [shadow]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{shadow['id']}", _animal_condition("Plague"),
                            _today_offset(4), is_animal=True, confidence=0.95),
    ]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["recent_exposures"] = [
        {"type":"rodent_predation","date":_today_offset(30),"location":"outdoor",
         "details":"cat brought home prey weekly"},
    ]
    return h


def scenario_ramirez():
    county = COUNTIES["Cochise"]; hh_id = "HH-AZ-COCHISE-007"
    h = Household(household_id=hh_id, name="Ramirez", county=county,
                  narrative=("Ramirez household, near Bisbee (Cochise Co.). Owns small horse stable. "
                             "Horse Trigger developed ataxia and weakness 12 days ago — vet confirmed "
                             "WNV. Standing water on property after monsoon rains. Today, Roberto "
                             "Ramirez (59) presents with severe headache, fever, and confusion. "
                             "Suspect West Nile encephalitis — both share the mosquito vector exposure."))
    roberto = _patient_resource(_new_id(),"Roberto","Ramirez","male","1966-11-05",county,hh_id,
                                chronic_conditions=["Essential hypertension"])
    elena = _patient_resource(_new_id(),"Elena","Ramirez","female","1968-04-22",county,hh_id)
    h.humans = [roberto, elena]
    trigger = _animal_record(_new_id(),"Trigger","horse","Quarter Horse","MN","2014-05-18",county,hh_id)
    h.animals = [trigger]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{trigger['id']}", _animal_condition("West Nile virus infection"),
                            _today_offset(12), is_animal=True, confidence=0.91),
    ]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["shared_exposures"] = [
        {"type":"standing_water","frequency":"continuous","shared_with":"horse",
         "details":"property has standing water from monsoon"},
    ]
    return h


def scenario_thompson():
    county = COUNTIES["Mohave"]; hh_id = "HH-AZ-MOHAVE-008"
    h = Household(household_id=hh_id, name="Thompson", county=county,
                  narrative=("Thompson household, near Kingman (Mohave Co.). Dog Buddy was attacked by "
                             "a skunk in the yard 6 days ago — skunk tested positive for rabies. Dog is "
                             "currently in 45-day strict observation. Today, son Jake (12) presents "
                             "with a small unhealed wound on his hand from breaking up the encounter. "
                             "Post-exposure prophylaxis indicated."))
    michael = _patient_resource(_new_id(),"Michael","Thompson","male","1981-07-09",county,hh_id)
    sarah = _patient_resource(_new_id(),"Sarah","Thompson","female","1983-02-14",county,hh_id)
    jake = _patient_resource(_new_id(),"Jake","Thompson","male","2014-09-02",county,hh_id)
    h.humans = [michael, sarah, jake]
    buddy = _animal_record(_new_id(),"Buddy","dog","Mixed Breed","MN","2020-06-15",county,hh_id)
    h.animals = [buddy]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["recent_exposures"] = [
        {"type":"wildlife_attack","date":_today_offset(6),"location":"backyard",
         "details":"rabid skunk confirmed by lab; dog attacked, child sustained scratch"},
    ]
    return h


def scenario_becker():
    county = COUNTIES["Santa Cruz"]; hh_id = "HH-AZ-SANTACRUZ-009"
    h = Household(household_id=hh_id, name="Becker", county=county,
                  narrative=("Becker family, small goat dairy near Patagonia (Santa Cruz Co.). Three "
                             "goats had spontaneous abortions over the past 3 weeks — Coxiella burnetii "
                             "confirmed. James Becker (44) presents today with 2 weeks of dry cough, "
                             "fever, and fatigue. Q fever should be on the differential given direct "
                             "exposure to placental tissue during goat birthing."))
    james = _patient_resource(_new_id(),"James","Becker","male","1981-12-17",county,hh_id)
    rebecca = _patient_resource(_new_id(),"Rebecca","Becker","female","1983-08-04",county,hh_id)
    h.humans = [james, rebecca]
    daisy = _animal_record(_new_id(),"Daisy","goat","Nubian","FI","2020-03-08",county,hh_id)
    bessie = _animal_record(_new_id(),"Bessie","goat","Nubian","FI","2019-11-22",county,hh_id)
    h.animals = [daisy, bessie]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{daisy['id']}", _animal_condition("Q fever"),
                            _today_offset(18), is_animal=True, confidence=0.88),
    ]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["occupational_exposures"] = [
        {"type":"livestock_handling","frequency":"daily","details":"goat dairy operations"},
    ]
    return h


def scenario_nguyen():
    county = COUNTIES["Maricopa"]; hh_id = "HH-AZ-MARICOPA-010"
    h = Household(household_id=hh_id, name="Nguyen", county=county,
                  narrative=("Nguyen household, central Phoenix. Pet parrot Mango has been listless and "
                             "fluffed-up for 2 weeks; vet confirmed Chlamydia psittaci. Today, Lan "
                             "Nguyen (34) presents with 5 days of high fever, dry cough, and severe "
                             "headache. Atypical pneumonia with bird exposure → psittacosis must be "
                             "considered."))
    lan = _patient_resource(_new_id(),"Lan","Nguyen","female","1991-05-28",county,hh_id)
    minh = _patient_resource(_new_id(),"Minh","Nguyen","male","1989-10-11",county,hh_id)
    h.humans = [lan, minh]
    mango = _animal_record(_new_id(),"Mango","bird","African Grey","M","2018-08-20",county,hh_id)
    h.animals = [mango]
    h.conditions = [
        _condition_resource(f"AnimalPatient/{mango['id']}", _animal_condition("Psittacosis"),
                            _today_offset(14), is_animal=True, confidence=0.86),
    ]
    h.environment = _environmental_profile(hh_id, county)
    return h


def scenario_sanchez():
    county = COUNTIES["Pinal"]; hh_id = "HH-AZ-PINAL-011"
    h = Household(household_id=hh_id, name="Sanchez", county=county,
                  narrative=("Sanchez household, near Florence (Pinal Co.). Carlos Sanchez (51) is an "
                             "avid hunter; field-dressed wild rabbits 8 days ago without gloves after "
                             "noting one rabbit appeared sick. Now presents with fever, painful axillary "
                             "lymph node, and a non-healing skin ulcer at the field-dressing site. "
                             "Tularemia (ulceroglandular form) highly suspected."))
    carlos = _patient_resource(_new_id(),"Carlos","Sanchez","male","1974-09-19",county,hh_id)
    maria_s = _patient_resource(_new_id(),"Maria","Sanchez","female","1977-03-04",county,hh_id)
    h.humans = [carlos, maria_s]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["occupational_exposures"] = [
        {"type":"wildlife_handling","date":_today_offset(8),
         "details":"field-dressed wild rabbits, one appeared ill"},
    ]
    return h


def scenario_yazzie():
    county = COUNTIES["Navajo"]; hh_id = "HH-AZ-NAVAJO-012"
    h = Household(household_id=hh_id, name="Yazzie", county=county,
                  narrative=("Yazzie household, near Holbrook (Navajo Co.). Pet bearded dragon Spike. "
                             "Daughter Ellie (5) presents today with 4 days of severe diarrhea, fever, "
                             "and dehydration. Salmonella isolated from stool. Pet reptile is a "
                             "well-known reservoir; child handles Spike daily."))
    william = _patient_resource(_new_id(),"William","Yazzie","male","1990-01-30",county,hh_id)
    angela = _patient_resource(_new_id(),"Angela","Yazzie","female","1992-07-15",county,hh_id)
    ellie = _patient_resource(_new_id(),"Ellie","Yazzie","female","2021-02-08",county,hh_id)
    h.humans = [william, angela, ellie]
    spike = _animal_record(_new_id(),"Spike","reptile","Bearded Dragon","M","2019-10-04",county,hh_id)
    h.animals = [spike]
    h.environment = _environmental_profile(hh_id, county)
    h.environment["recent_exposures"] = [
        {"type":"reptile_contact","frequency":"daily","details":"young child handles bearded dragon"},
    ]
    return h


HANDCRAFTED = [
    scenario_hernandez, scenario_johnson, scenario_williams, scenario_patel, scenario_chen,
    scenario_begay, scenario_ramirez, scenario_thompson, scenario_becker,
    scenario_nguyen, scenario_sanchez, scenario_yazzie,
]


# ---------------------------------------------------------------------------
# Procedural generator
# ---------------------------------------------------------------------------
_SURNAMES = [
    "Garcia","Martinez","Rodriguez","Lopez","Anderson","Thompson","Nguyen","Brown","Davis",
    "Wilson","Lee","Khan","Singh","Patel","Kim","Park","Gomez","Reyes","Diaz","Torres",
    "Cruz","Castillo","Romero","Vargas","Mendoza","Robinson","Walker","Young","Allen",
    "Wright","Scott","Green","Adams","Baker","Nelson","Carter","Mitchell","Roberts",
    "Phillips","Campbell","Parker","Evans","Edwards","Collins","Morris","Murphy","Cook",
    "Morgan","Bell","Bailey",
]
_GIVEN_M = ["James","Michael","Daniel","Hassan","Wei","Diego","Andre","Owen","Lucas","Mason",
            "Ethan","Alexander","Henry","Sebastian","Jack","Jackson","Aiden","Elijah","Carter",
            "Wyatt","Mateo","Anthony","Dylan","Leo","Asher"]
_GIVEN_F = ["Mary","Susan","Aisha","Yuki","Sofia","Fatima","Olivia","Zara","Emma","Charlotte",
            "Amelia","Mia","Harper","Evelyn","Abigail","Emily","Elizabeth","Avery","Ella",
            "Madison","Scarlett","Victoria","Aria","Grace","Layla"]
_DOG_NAMES = ["Buddy","Max","Luna","Charlie","Daisy","Cooper","Ruby","Milo","Bailey","Lucy",
              "Sadie","Maggie","Rocky","Duke","Bear","Tucker","Riley","Zeus","Chloe","Bella"]
_CAT_NAMES = ["Whiskers","Shadow","Ginger","Oreo","Smokey","Mittens","Tigger","Felix","Pumpkin",
              "Salem","Cleo","Loki","Simba","Mochi","Boots"]
_BIRD_NAMES = ["Kiwi","Sunny","Pico","Sky","Echo","Tango"]
_HORSE_NAMES = ["Thunder","Star","Comet","Whiskey","Bandit","Blue"]
_GOAT_NAMES = ["Daisy","Pepper","Clover","Poppy"]
_RABBIT_NAMES = ["Hopper","Coco","Smudge","Pip"]


def _random_dob(min_age, max_age, rng):
    age = rng.randint(min_age, max_age)
    days = rng.randint(0, 364)
    return (date.today() - timedelta(days=age * 365 + days)).isoformat()


_CHRONIC_POOL = [
    "Essential hypertension","Type 2 diabetes mellitus","Hyperlipidemia",
    "Hypothyroidism","Asthma","Chronic obstructive pulmonary disease",
    "Major depressive disorder",
]


# ---------------------------------------------------------------------------
# Disease assignment for procedural households
# ---------------------------------------------------------------------------
# A small synthetic registry mapping disease_id → SNOMED/ICD-10 codes for
# downstream FHIR Condition resources.

_HUMAN_CONDITION_NAMES = {
    "valley_fever":          "Coccidioidomycosis (Valley Fever)",
    "rmsf":                  "Rocky Mountain Spotted Fever",
    "plague":                "Plague (Yersinia pestis)",
    "west_nile":             "West Nile Virus infection",
    "hantavirus":            "Hantavirus Pulmonary Syndrome",
    "ehrlichiosis":          "Ehrlichiosis",
    "leptospirosis":         "Leptospirosis",
    "q_fever":               "Q Fever",
    "psittacosis":           "Psittacosis",
    "tularemia":             "Tularemia",
    "rabies":                "Rabies post-exposure prophylaxis",
    "salmonellosis":         "Salmonellosis (non-typhoidal)",
    "tuberculosis_zoonotic": "Zoonotic Tuberculosis",
    "brucellosis":           "Brucellosis",
}
_ANIMAL_CONDITION_NAMES = {
    "valley_fever":  "Coccidioidomycosis (canine/feline)",
    "rmsf":          "Rocky Mountain Spotted Fever (canine)",
    "plague":        "Plague (feline / canine — Yersinia pestis)",
    "west_nile":     "West Nile Virus infection (equine / avian)",
    "ehrlichiosis":  "Canine Ehrlichiosis",
    "leptospirosis": "Canine Leptospirosis",
    "q_fever":       "Caprine Q Fever (Coxiella burnetii abortion)",
    "psittacosis":   "Avian Chlamydiosis (Chlamydia psittaci)",
    "tularemia":     "Feline Tularemia",
    "rabies":        "Rabies (animal — confirmed or suspect)",
    "salmonellosis": "Salmonella shedding (asymptomatic carrier)",
    "tuberculosis_zoonotic": "Bovine Tuberculosis",
    "brucellosis":   "Caprine / bovine Brucellosis",
}


def _make_condition(disease_id: str, subject_ref: str, onset_date: str, *, is_animal: bool) -> dict:
    """Build a FHIR Condition for a procedural disease assignment."""
    d = DISEASES.get(disease_id, {})
    text = (_ANIMAL_CONDITION_NAMES if is_animal else _HUMAN_CONDITION_NAMES).get(
        disease_id, d.get("display", disease_id))
    return {
        "resourceType": "Condition",
        "id": _new_id(),
        "subject": {"reference": subject_ref},
        "code": {
            "text": text,
            "coding": [
                {"system": "http://snomed.info/sct", "code": d.get("snomed") or "", "display": text},
                {"system": "http://hl7.org/fhir/sid/icd-10", "code": d.get("icd10") or "", "display": text},
            ],
        },
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category",
                                  "code": "encounter-diagnosis"}]}],
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                                       "code": "active"}]},
        "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                                           "code": "confirmed"}]},
        "onsetDateTime": onset_date,
        "_one_health": {
            "disease_id": disease_id,
            "transmission_routes": [r["route"] for r in d.get("transmission_routes", [])],
            "sentinel_direction": d.get("sentinel", {}).get("direction"),
            "is_zoonotic": d.get("category", "").find("zoonotic") >= 0,
        },
    }


def _eligible_diseases_for_household(species_present: set[str]) -> list[str]:
    """
    Return the disease IDs that could plausibly affect this household given its
    species composition. (No Q-fever without ruminants; no psittacosis without
    birds; etc.)
    """
    eligible = []
    for did, d in DISEASES.items():
        host_species = set(d.get("host_species", {}).keys())
        # 'human' is always present, so we check whether the disease has at
        # least one non-human host species that overlaps the household, OR
        # whether it's primarily human-driven via environmental exposure.
        non_human_hosts = host_species - {"human"}
        # Map disease's animal hosts to household species categories
        animal_household_map = {
            "dog": {"dog"},
            "cat": {"cat"},
            "horse": {"horse"},
            "cattle": {"cattle"},
            "goat": {"goat"},
            "sheep": {"sheep", "goat"},  # sheep approximated by goat in our species pool
            "swine": {"swine"},
            "bird": {"bird"},
            "parrot": {"bird"},
            "poultry": {"bird"},
            "rabbit": {"rabbit"},
            "reptile": {"reptile"},
            "deer_mouse": set(),       # wildlife — not in household pool
            "prairie_dog": set(),
            "bat": set(), "skunk": set(), "fox": set(),
        }
        required_species: set[str] = set()
        for host in non_human_hosts:
            required_species |= animal_household_map.get(host, set())

        if did in {"valley_fever", "hantavirus", "rabies", "salmonellosis"}:
            # Environmental / wildlife / dietary — eligible regardless of species composition
            eligible.append(did)
        elif required_species & species_present:
            eligible.append(did)
        # else: skip — household lacks the required animal species
    return eligible


def _assign_disease_to_household(rng: random.Random, hh: "Household",
                                  zip_record: dict, env_risk: dict[str, float]) -> None:
    """
    For a procedural household, decide whether to seed a disease case based on
    the ZIP-level environmental risk × species composition × per-disease prior.

    Approach:
      1. Determine which diseases are species-eligible for this household.
      2. Compute a per-disease probability = env_risk[did] × base_rate[did].
      3. Roll a single die per eligible disease. Multiple hits possible but rare.
      4. For each hit, place the index case in the appropriate sentinel species
         first (e.g., dog gets RMSF before any human in the household), then
         with secondary probability spread to the sentinel-target species.
    """
    species_present = set()
    for a in hh.animals:
        sc = (a.get("species") or {}).get("code") if isinstance(a.get("species"), dict) else None
        if sc:
            species_present.add(sc)

    # Base rate calibration — keeps overall procedural-disease prevalence ~10%
    BASE_RATE = {
        "valley_fever":          0.020,
        "rmsf":                  0.012,
        "plague":                0.004,
        "west_nile":             0.012,
        "hantavirus":            0.006,
        "ehrlichiosis":          0.014,
        "leptospirosis":         0.010,
        "q_fever":               0.008,
        "psittacosis":           0.006,
        "tularemia":             0.005,
        "rabies":                0.003,
        "salmonellosis":         0.018,
        "tuberculosis_zoonotic": 0.003,
        "brucellosis":           0.003,
    }

    eligible = _eligible_diseases_for_household(species_present)

    today = date.today()

    for did in eligible:
        env = env_risk.get(did, 0.0)
        base = BASE_RATE.get(did, 0.0)
        p = env * base * 4.0   # 4× scaling so an average ZIP gets a plausible cluster rate
        if rng.random() >= p:
            continue

        d = DISEASES[did]
        sentinel_dir = d.get("sentinel", {}).get("direction", "shared_environmental")
        host_species = set(d.get("host_species", {}).keys())
        animal_hosts = host_species - {"human"}

        # Onset within the past 60 days
        onset = today - timedelta(days=rng.randint(2, 60))
        onset_str = onset.isoformat()

        # Place the index case according to sentinel direction
        if sentinel_dir == "animal_to_human" and hh.animals:
            # Find an animal whose species is in animal_hosts
            candidates = [a for a in hh.animals
                           if (a.get("species") or {}).get("code") in
                           {k for k, v in {"dog":"dog","cat":"cat","horse":"horse","goat":"goat",
                                            "rabbit":"rabbit","bird":"bird","reptile":"reptile",
                                            "cattle":"cattle"}.items() if k in animal_hosts}]
            if candidates:
                animal = rng.choice(candidates)
                hh.conditions.append(_make_condition(
                    did, f"AnimalPatient/{animal['id']}", onset_str, is_animal=True))
                # Secondary spread to a household human after appropriate lag
                if hh.humans and rng.random() < 0.35:
                    incub = d.get("host_species", {}).get("human", {}).get("incubation_days", [14, 7, 28])
                    lag = rng.randint(int(incub[1]), int(incub[2]))
                    onset_h = onset + timedelta(days=lag)
                    if onset_h <= today:
                        human = rng.choice(hh.humans)
                        hh.conditions.append(_make_condition(
                            did, f"Patient/{human['id']}", onset_h.isoformat(), is_animal=False))

        elif sentinel_dir == "human_to_animal" and hh.humans:
            human = rng.choice(hh.humans)
            hh.conditions.append(_make_condition(
                did, f"Patient/{human['id']}", onset_str, is_animal=False))

        else:  # shared_environmental — both species exposed to same source
            if hh.humans and rng.random() < 0.7:
                human = rng.choice(hh.humans)
                hh.conditions.append(_make_condition(
                    did, f"Patient/{human['id']}", onset_str, is_animal=False))
            if hh.animals and animal_hosts and rng.random() < 0.5:
                candidates = [a for a in hh.animals
                               if (a.get("species") or {}).get("code") in animal_hosts]
                if candidates:
                    animal = rng.choice(candidates)
                    hh.conditions.append(_make_condition(
                        did, f"AnimalPatient/{animal['id']}", onset_str, is_animal=True))


def random_household(rng, idx):
    surname = rng.choice(_SURNAMES)
    # Phase 5 — weight county selection by population (more cases in Maricopa/Pima)
    counties_pool = REF["counties"]
    county_obj = rng.choices(
        counties_pool,
        weights=[max(c.get("population", 1000), 1000) for c in counties_pool],
        k=1
    )[0]
    # Phase 5 — pick a ZIP within the county, weighted by ZIP population
    zip_record = _pick_zip(rng, county_obj["name"])
    hh_id = f"HH-AZ-{county_obj['name'].upper().replace(' ', '')}-G{idx:03d}"

    n_humans = rng.choices([1, 2, 3, 4, 5], weights=[10, 30, 35, 20, 5])[0]
    n_animals = rng.choices([0, 1, 2, 3], weights=[30, 35, 25, 10])[0]

    h = Household(household_id=hh_id, name=surname, county=county_obj,
                  narrative=f"Procedurally generated {surname} household, "
                            f"{zip_record['name']} ({zip_record['zip']}, {county_obj['name']} Co.).")

    for i in range(n_humans):
        gender = rng.choice(["male", "female"])
        given = rng.choice(_GIVEN_M if gender == "male" else _GIVEN_F)
        dob = _random_dob(28, 75, rng) if i < 2 else _random_dob(2, 22, rng)
        chronic = []
        if i < 2 and rng.random() < 0.30:
            n_cc = rng.choices([1, 2], weights=[70, 30])[0]
            chronic = rng.sample(_CHRONIC_POOL, k=min(n_cc, len(_CHRONIC_POOL)))
        h.humans.append(_patient_resource(_new_id(), given, surname, gender, dob,
                                          county_obj, hh_id, chronic_conditions=chronic or None))

    # Phase 5 — animal species mix calibrated by urbanicity
    urbanicity = zip_record.get("urbanicity", "rural")
    if urbanicity == "rural":
        species_weights = {"dog": 35, "cat": 18, "bird": 4, "horse": 12, "rabbit": 3,
                           "goat": 12, "cattle": 12, "reptile": 1, "swine": 3}
    elif urbanicity == "suburban":
        species_weights = {"dog": 50, "cat": 28, "bird": 6, "horse": 5, "rabbit": 4,
                           "goat": 3, "cattle": 1, "reptile": 3, "swine": 0}
    else:  # urban
        species_weights = {"dog": 55, "cat": 32, "bird": 6, "horse": 1, "rabbit": 3,
                           "goat": 0, "cattle": 0, "reptile": 3, "swine": 0}
    species_choices = [k for k, v in species_weights.items() if v > 0]
    species_w       = [v for k, v in species_weights.items() if v > 0]

    for _ in range(n_animals):
        species = rng.choices(species_choices, weights=species_w, k=1)[0]
        breeds = REF["terms"]["vet_breeds"].get(species, ["Mixed"])
        breed = rng.choice(breeds)
        names_pool = {
            "dog": _DOG_NAMES, "cat": _CAT_NAMES, "bird": _BIRD_NAMES,
            "horse": _HORSE_NAMES, "goat": _GOAT_NAMES, "rabbit": _RABBIT_NAMES,
            "cattle": _GOAT_NAMES, "reptile": _BIRD_NAMES, "swine": _GOAT_NAMES,
        }.get(species, _DOG_NAMES)
        sex = rng.choice(["MN", "FS", "M", "F"])
        dob = _random_dob(1, 14, rng)
        h.animals.append(_animal_record(_new_id(), rng.choice(names_pool), species, breed,
                                         sex, dob, county_obj, hh_id))

    h.environment = _environmental_profile(hh_id, county_obj, zip_record)

    # Phase 5 — assign realistic disease cases based on ZIP + species
    env_risk = h.environment.get("disease_environmental_risk", {})
    _assign_disease_to_household(rng, h, zip_record, env_risk)

    return h


# ---------------------------------------------------------------------------
def generate_all(extra_households=348, seed=42):
    rng = random.Random(seed)
    households = [s() for s in HANDCRAFTED]

    # Phase 5 — backfill ZIPs onto handcrafted households
    zip_rng = random.Random(seed + 1)
    for hh in households:
        zip_record = _pick_zip(zip_rng, hh.county["name"])
        hh.environment = _environmental_profile(hh.household_id, hh.county, zip_record)

    # Phase 5 — guarantee at least one procedural household per county for
    # full state coverage (small counties like Greenlee/La Paz/Apache wouldn't
    # otherwise be reliably sampled by population-weighted selection).
    handcrafted_counties = {hh.county["name"] for hh in households}
    all_counties = {c["name"] for c in REF["counties"]}
    underrepresented = sorted(all_counties - handcrafted_counties)

    procedural_idx = 0
    for county_name in underrepresented:
        if procedural_idx >= extra_households:
            break
        # Reuse the random_household routine but pin the county
        county_obj = COUNTIES[county_name]
        hh = _random_household_in_county(rng, procedural_idx, county_obj)
        households.append(hh)
        procedural_idx += 1

    while procedural_idx < extra_households:
        households.append(random_household(rng, procedural_idx))
        procedural_idx += 1

    # Aggregate disease counts for the metadata block
    disease_counts: dict[str, int] = {}
    for hh in households:
        for c in hh.conditions:
            did = (c.get("_one_health") or {}).get("disease_id")
            if did:
                disease_counts[did] = disease_counts.get(did, 0) + 1

    bundle = {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_households": len(households),
            "n_handcrafted": len(HANDCRAFTED),
            "n_procedural": extra_households,
            "n_humans": sum(len(h.humans) for h in households),
            "n_animals": sum(len(h.animals) for h in households),
            "n_conditions": sum(len(h.conditions) for h in households),
            "n_zips_used": len({(h.environment or {}).get("zip", "") for h in households if h.environment}),
            "n_counties_used": len({h.county["name"] for h in households}),
            "n_diseases_distributed": len(disease_counts),
            "disease_distribution": disease_counts,
            "seed": seed,
            "schema_version": "0.3.0",
            "_phase": "Phase 5 — ZIP-resolution dataset expansion (200% scale, 14 One Health diseases, transmission-route-aware)",
        },
        "households": [asdict(h) for h in households],
    }
    out = OUT_DIR / "households.json"
    out.write_text(json.dumps(bundle, indent=2, default=str))
    return bundle


def _random_household_in_county(rng: random.Random, idx: int, county_obj: dict) -> "Household":
    """Same as random_household, but pinned to a specific county."""
    surname = rng.choice(_SURNAMES)
    zip_record = _pick_zip(rng, county_obj["name"])
    hh_id = f"HH-AZ-{county_obj['name'].upper().replace(' ', '')}-G{idx:03d}"

    n_humans = rng.choices([1, 2, 3, 4, 5], weights=[10, 30, 35, 20, 5])[0]
    n_animals = rng.choices([0, 1, 2, 3], weights=[30, 35, 25, 10])[0]

    h = Household(household_id=hh_id, name=surname, county=county_obj,
                  narrative=f"Procedurally generated {surname} household, "
                            f"{zip_record['name']} ({zip_record['zip']}, {county_obj['name']} Co.).")

    for i in range(n_humans):
        gender = rng.choice(["male", "female"])
        given = rng.choice(_GIVEN_M if gender == "male" else _GIVEN_F)
        dob = _random_dob(28, 75, rng) if i < 2 else _random_dob(2, 22, rng)
        chronic = []
        if i < 2 and rng.random() < 0.30:
            n_cc = rng.choices([1, 2], weights=[70, 30])[0]
            chronic = rng.sample(_CHRONIC_POOL, k=min(n_cc, len(_CHRONIC_POOL)))
        h.humans.append(_patient_resource(_new_id(), given, surname, gender, dob,
                                          county_obj, hh_id, chronic_conditions=chronic or None))

    urbanicity = zip_record.get("urbanicity", "rural")
    if urbanicity == "rural":
        species_weights = {"dog": 35, "cat": 18, "bird": 4, "horse": 12, "rabbit": 3,
                           "goat": 12, "cattle": 12, "reptile": 1, "swine": 3}
    elif urbanicity == "suburban":
        species_weights = {"dog": 50, "cat": 28, "bird": 6, "horse": 5, "rabbit": 4,
                           "goat": 3, "cattle": 1, "reptile": 3, "swine": 0}
    else:
        species_weights = {"dog": 55, "cat": 32, "bird": 6, "horse": 1, "rabbit": 3,
                           "goat": 0, "cattle": 0, "reptile": 3, "swine": 0}
    species_choices = [k for k, v in species_weights.items() if v > 0]
    species_w       = [v for k, v in species_weights.items() if v > 0]

    for _ in range(n_animals):
        species = rng.choices(species_choices, weights=species_w, k=1)[0]
        breeds = REF["terms"]["vet_breeds"].get(species, ["Mixed"])
        breed = rng.choice(breeds)
        names_pool = {
            "dog": _DOG_NAMES, "cat": _CAT_NAMES, "bird": _BIRD_NAMES,
            "horse": _HORSE_NAMES, "goat": _GOAT_NAMES, "rabbit": _RABBIT_NAMES,
            "cattle": _GOAT_NAMES, "reptile": _BIRD_NAMES, "swine": _GOAT_NAMES,
        }.get(species, _DOG_NAMES)
        sex = rng.choice(["MN", "FS", "M", "F"])
        dob = _random_dob(1, 14, rng)
        h.animals.append(_animal_record(_new_id(), rng.choice(names_pool), species, breed,
                                         sex, dob, county_obj, hh_id))

    h.environment = _environmental_profile(hh_id, county_obj, zip_record)
    env_risk = h.environment.get("disease_environmental_risk", {})
    _assign_disease_to_household(rng, h, zip_record, env_risk)
    return h


if __name__ == "__main__":
    bundle = generate_all()
    md = bundle["_metadata"]
    print(f"Generated {md['n_households']} households "
          f"({md['n_handcrafted']} hand-crafted + {md['n_procedural']} procedural)")
    print(f"  → {md['n_humans']} humans, {md['n_animals']} animals, {md['n_conditions']} active conditions")
    diseases: dict[str, int] = {}
    for h in bundle["households"]:
        for c in h["conditions"]:
            d = c["code"]["text"]
            diseases[d] = diseases.get(d, 0) + 1
    print("\n  Hand-crafted diseases:")
    for d, n in sorted(diseases.items(), key=lambda x: -x[1]):
        print(f"    {d}: {n}")
