# Veterinary FHIR Profile — R5-vet-ballot

## Why this exists

Standard FHIR R4 has no Patient profile for animals. Every veterinary EHR vendor that has tried to be FHIR-compatible has either built a custom extension on Patient (creating a non-portable record that breaks at the first cross-system query) or shoehorned animal-specific data into Person resources marked with `extension[is-animal]=true`. Neither approach scales across organizations.

In 2024 the HL7 Veterinary Care Workgroup began drafting an official **R5-vet-ballot** profile that adds an `AnimalPatient` resource as a first-class citizen. The ballot is in active review through 2026; vendors including IDEXX, Covetrus, and AVImark have published implementation guides anticipating final passage.

ONE-HealthRecord's MVP uses a **shim implementation** of the R5-vet-ballot pattern: we represent animals as `AnimalPatient` resources with the fields that the HL7 ballot specifies, but published as FHIR R4 because the partner sites in our federation manifest are still on R4. When the ballot passes and partner servers upgrade, our `AnimalPatient` resources transition cleanly because the field shapes match.

## What an AnimalPatient looks like

```json
{
  "resourceType": "AnimalPatient",
  "id": "anim-rocco-001",
  "meta": {
    "profile": ["http://hl7.org/fhir/StructureDefinition/AnimalPatient"]
  },
  "name": "Rocco",
  "species": {
    "code": "dog",
    "display": "Canis lupus familiaris",
    "system": "http://snomed.info/sct",
    "snomed_code": "448771007"
  },
  "breed": "Border Collie mix",
  "sex": "MN",
  "birthDate": "2019-03-12",
  "address": [{
    "city": "Tucson",
    "state": "AZ",
    "country": "USA",
    "extension": [{ "url": "county-fips", "valueString": "04019" }]
  }],
  "extension": [
    { "url": "household-id", "valueString": "HH-AZ-PIMA-001" },
    { "url": "premises-id", "valueString": "AZ-PREM-04019-0042" }
  ],
  "owner": {
    "reference": "Patient/...",
    "display": "Owner record on the human-medicine side; cross-species linkage requires consent (see Consent resource)."
  }
}
```

## Differences from human Patient

| Field | Human Patient (R4) | AnimalPatient (R5-vet-ballot) | Notes |
|---|---|---|---|
| `name` | Structured `HumanName` (family, given, prefix, suffix) | Single string (call name) | Animals don't have surnames; they have call names |
| `species` | Implicit (always human) | Required `CodeableConcept` with SNOMED-CT 448771007 / 448169003 / etc. | Drives all clinical decision support; required field |
| `breed` | N/A | Optional string keyed to species | Critical for breed-specific risk assessment (cocci in working breeds, brachycephalic pneumonia) |
| `sex` | Standard administrative gender | Vet-specific code: `M` (intact male), `MN` (neutered male), `F` (intact female), `FS` (spayed female) | Reflects the clinical reality that intact/altered status changes risk profile |
| `birthDate` | Required | Often estimated for shelter intake | Vet medicine routinely deals with unknown DOB |
| `identifier` | MRN | Microchip ID + AVID/HomeAgain registry ID | Microchip is the closest analogue to an MRN, but it's an industry-issued identifier, not a clinic-issued one |
| `address` | Patient's address | The owner's address — animals don't have legal addresses | Critical distinction for surveillance: an animal "lives at" its owner's residence |
| `owner` | N/A | Optional reference to a human Patient | Cross-species linkage point. **Requires explicit consent** before published. |
| `premises_id` | N/A | USDA Premises ID | For livestock; required for federal reportable disease tracking |

## What this enables in ONE-HealthRecord

**1. Cross-species cluster detection.** Both `Patient` and `AnimalPatient` carry `household-id` extensions. The cross-species cluster detector queries `Condition` resources whose `subject` references either type, groups by household, and surfaces clusters that span both. Without a first-class `AnimalPatient` profile, this would require fragile string-matching on extensions.

**2. Vet-side reportable disease push.** The `species` field is required, which means `AnimalPatient` records are unambiguous when fed into the USDA APHIS VSPS report generator. Without the profile, the vet-side reporting workflow would have to infer species from clinical text — error-prone for cluster surveillance.

**3. Federation across mixed FHIR versions.** Each partner's shadow store (`data/synthetic/shadow_stores/<site_id>.json`) carries a `fhir_version` field. The four vet sites in our federation manifest are tagged `R5-vet-ballot`; the six hospital systems are tagged `R4`. The federation client (`app/federation.js`) uses this metadata to pick the right query shape for each target. When the ballot passes and hospital systems upgrade to R5, the federation client can drop the version-specific branching.

## Open issues in the ballot (as of 2025)

- **Multi-owner households.** A horse boarded at a barn might have three legal owners, of whom two are joint and one is the lessee. Current ballot says `owner` is 0..1 — the workgroup is debating bumping to 0..*.
- **Species sub-classification.** Should `species` carry breed at the same level (`Canis_lupus_familiaris/Border_Collie`), or should breed live in a separate field? Current ballot has them as separate fields; the working-group concern is that breed-specific risk drives some clinical decisions (e.g., MDR1 sensitivity in Collies).
- **Cross-species linkage representation.** Whether `owner` itself is enough or whether a separate `OwnerLink` resource is needed to capture consent. We use the `Consent` resource pattern (see `data/synthetic/consents.json`) which is consistent with how human-side privacy is modeled, and we believe this is the right approach.
- **Wildlife.** The ballot is scoped to companion animals and livestock. Wildlife sentinel cases (prairie-dog plague die-offs, dead corvids for WNV) need a different representation — currently being drafted in a parallel ballot for `WildlifeObservation`.

## Implementation guide for partner sites

A partner vet practice (e.g., Tucson Companion-Animal Vet at IDEXX FHIR) joining the ONE-HealthRecord federation would:

1. **Map their internal record** to the AnimalPatient profile shown above. IDEXX's reference implementation handles this; AVImark (Cochise Large-Animal Vet) needs a shim layer.
2. **Publish a FHIR endpoint** (e.g., `https://fhir.tucson-vet.example/r5/AnimalPatient`) with SMART-on-FHIR authentication.
3. **Register with the federation manifest** — add the site to `data/synthetic/federation_manifest.json` with kind `vet_clinic`, vendor, FHIR version, endpoint URL, and lat/lon for the topology view.
4. **Map their VeNom-coded conditions** to SNOMED-CT for cross-species cluster detection. The crosswalk is at `data/reference/venom_snomed_crosswalk.json`. Where the crosswalk is `tier: approximated`, the cluster detector treats matches as candidate-only and routes them through human review.
5. **Register the `Consent` workflow.** At intake, the practice's front-desk staff captures the One Health consent decision via the OHR-CONSENT-01 form (or its equivalent in the practice's intake software). The Consent resource is published to the federation; the cross-species pointer respects it.

## References

- HL7 Veterinary Care Workgroup: https://confluence.hl7.org/display/VET (active ballot tracking)
- FHIR R5 Animal Patient draft: https://build.fhir.org/animalpatient.html (ballot version)
- VeNom Coding Group: https://venomcoding.org (UK-maintained reference vocabulary)
- IDEXX FHIR for Veterinary: https://developer.idexx.com/fhir
- USDA Premises ID system: https://www.aphis.usda.gov/animal-health/national-premises-identification

## Caveats

This document describes the implementation pattern, not a deployment. The shim implementation in this MVP demonstrates the pattern using FHIR R4 transport with the R5-vet-ballot field shapes. A production deployment would:

- Use a real FHIR R5 server (HAPI FHIR has an R5 build path).
- Acquire a real USDA Premises ID for each participating practice.
- Wire the SMART-on-FHIR auth flow against each vet vendor's identity provider.
- Operate under data-use agreements with each participating practice, with the practice retaining ownership of its primary clinical records.
