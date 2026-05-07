"""
Phase 6 — Cross-species linkage consent workflow.

Generates FHIR Consent resources for every household in the synthetic
dataset. Most households grant consent (the demo's default state); two
handcrafted households are designated as 'consent declined' to show the
contrast — the system respects the no-consent state and refuses to fire
cross-species pointers, even when the underlying signal is medically strong.

Consent FHIR resource pattern:
    {
      "resourceType": "Consent",
      "status": "active" | "inactive",
      "scope": { "coding": [{"system": "...", "code": "patient-privacy"}] },
      "category": [{ "coding": [{"system": "onehealthrecord.org", "code": "one-health-cross-species-linkage"}]}],
      "patient": { "reference": "Group/HH-AZ-PIMA-001" },  # household-level
      "dateTime": "...",
      "performer": [{ "reference": "...", "display": "..." }],
      "decision": "permit" | "deny",
      "_decision_basis": "patient_at_intake" | "guardian" | "no_response" | "explicitly_declined",
    }

Real workflow at intake:
   1. Front-desk asks: "We have a One Health surveillance program — if you
      bring an animal here too, would you like us to link your records for
      cross-species disease alerts?"
   2. Patient signs (paper or e-signature) the OHR-CONSENT-01 form.
   3. Form generates a FHIR Consent.
   4. Either site (human or vet) writing future records can check the
      consent state and decide whether to publish to the cross-species
      linkage feed.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "data" / "synthetic"


# Two handcrafted households are designated 'consent declined' for the demo.
# This lets the demo show:
#   1. The consent gate works (cross-species linkage is suppressed).
#   2. The system gracefully degrades — the household graph treats human
#      and animal as separate compartments.
#   3. The surveillance feed sees only the consenting side.
DECLINED_HOUSEHOLDS = {
    "HH-AZ-MARICOPA-003":  {
        "decision_basis": "explicitly_declined",
        "rationale": (
            "Williams household — Robert and Linda. At intake on 2026-02-14, "
            "Robert declined the One Health linkage option, noting privacy "
            "concerns about cross-organization data sharing. No animals are "
            "registered to this household at present, but the consent state "
            "is recorded so any future veterinary visit will not auto-link."
        ),
    },
    "HH-AZ-SANTACRUZ-009": {
        "decision_basis": "explicitly_declined",
        "rationale": (
            "Becker household — James, Rebecca, and 2 dairy goats (Daisy and "
            "Bessie) at Cochise Large-Animal Vet. At intake on 2026-01-22, "
            "James declined linkage. Note the medical irony: this household "
            "has the strongest cross-species signal in the dataset (Q fever "
            "risk via caprine reservoir), but the architecture respects the "
            "consent decision. ADHS would still see aggregate-level "
            "surveillance signals; just no individual cross-species linkage."
        ),
    },
}


def main() -> None:
    households_bundle = json.loads((DATA / "households.json").read_text())
    households = households_bundle["households"]

    consents = []
    summary = {"granted": 0, "declined": 0, "no_animal_no_decision": 0}

    for hh in households:
        hh_id = hh["household_id"]
        has_animals = bool(hh.get("animals"))

        if hh_id in DECLINED_HOUSEHOLDS:
            decision = "deny"
            status = "inactive"
            basis = DECLINED_HOUSEHOLDS[hh_id]["decision_basis"]
            rationale = DECLINED_HOUSEHOLDS[hh_id]["rationale"]
            summary["declined"] += 1
            consent_dt = "2026-01-22T09:30:00Z" if "SANTACRUZ" in hh_id else "2026-02-14T10:15:00Z"
        elif not has_animals:
            # No animals → no decision required. Capture as "informational"
            # so the system records that consent was offered and the household
            # has no current cross-species linkage need.
            decision = "permit"
            status = "active"
            basis = "no_animal_no_decision_required"
            rationale = "Household has no registered animals; consent recorded as default-permit."
            summary["no_animal_no_decision"] += 1
            consent_dt = "2026-02-01T12:00:00Z"
        else:
            decision = "permit"
            status = "active"
            basis = "patient_at_intake"
            rationale = (
                "Consent granted at primary-care intake. Patient was offered "
                "the One Health linkage option and signed the OHR-CONSENT-01 form."
            )
            summary["granted"] += 1
            consent_dt = "2026-02-01T12:00:00Z"

        # Performer: whoever recorded the consent (the front-desk encounter)
        consents.append({
            "resourceType": "Consent",
            "id": f"consent-{hh_id}",
            "meta": {"profile": ["http://onehealthrecord.org/StructureDefinition/CrossSpeciesLinkageConsent"]},
            "status": status,
            "scope": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope",
                                  "code": "patient-privacy"}]},
            "category": [{"coding": [{"system": "http://onehealthrecord.org/CodeSystem/consent-category",
                                      "code": "one-health-cross-species-linkage",
                                      "display": "One Health cross-species linkage"}]}],
            "patient": {"reference": f"Group/{hh_id}",
                        "display": f"{hh.get('name', '')} household"},
            "dateTime": consent_dt,
            "performer": [{"display": "Intake clerk (synthetic)"}],
            "provision": {
                "type": decision,                               # FHIR Consent.provision.type
                "purpose": [{"system": "http://onehealthrecord.org/CodeSystem/consent-purpose",
                             "code": "cross-species-surveillance",
                             "display": "Cross-species disease surveillance"}],
            },
            "_one_health": {
                "household_id": hh_id,
                "decision": decision,
                "decision_basis": basis,
                "rationale": rationale,
                "applies_to": [
                    "cross_species_pointer",
                    "household_graph_linkage",
                    "surveillance_feed_cross_species",
                ],
                "does_not_affect": [
                    "individual_clinical_care",
                    "single_species_records",
                    "aggregate_public_health_surveillance",
                ],
            },
        })

    out = {
        "_description": (
            "Cross-species linkage consent records, household-level. Each "
            "record encodes whether the household has authorized the system "
            "to publish cross-species linkage signals (the One Health "
            "pointer that connects human and animal records in the same "
            "household). Consent is REQUIRED for cross-species linkage. "
            "It is NOT required for individual clinical care or for "
            "aggregate public-health surveillance — those continue regardless."
        ),
        "_caveat": (
            "Synthetic. In production: consent is captured at intake on "
            "the OHR-CONSENT-01 form (paper or e-signature), with explicit "
            "language reviewed by the local IRB. Tribal-land households "
            "follow the local tribal IRB's consent template, not the "
            "default form. Consent can be revoked at any time; revocation "
            "immediately suppresses the cross-species pointer."
        ),
        "summary": {
            "n_households":           len(consents),
            "n_consent_granted":      summary["granted"],
            "n_consent_declined":     summary["declined"],
            "n_no_animal_default":    summary["no_animal_no_decision"],
            "decline_rate_among_animal_households": round(
                summary["declined"] / max(1, summary["granted"] + summary["declined"]), 4),
        },
        "consents": consents,
    }
    (DATA / "consents.json").write_text(json.dumps(out, indent=2, default=str))

    print(f"=== Consent records ===")
    print(f"  Total households:       {out['summary']['n_households']}")
    print(f"  Consent granted:        {out['summary']['n_consent_granted']}")
    print(f"  Consent DECLINED:       {out['summary']['n_consent_declined']}")
    print(f"  No-animal (default):    {out['summary']['n_no_animal_default']}")
    print(f"  Declined households:")
    for hh_id in DECLINED_HOUSEHOLDS:
        print(f"    {hh_id}")


if __name__ == "__main__":
    main()
