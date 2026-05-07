/* ============================================================================
 * Speaker notes for the ONE-HealthRecord capstone presentation.
 *
 * Each entry is the speech for one slide, written in spoken voice for delivery
 * at the certification panel. Length is calibrated to roughly one minute
 * per slide at 130 wpm. Total spoken length: ~25 minutes for the deck plus
 * the 6:30 OPENING_PITCH read at the start = ~32 minutes for the full session.
 *
 * The speeches are designed to:
 *   1. Land the slide's specific claim
 *   2. Cite the standards or evidence behind it
 *   3. Anticipate and pre-empt the panel's likely follow-up question
 *   4. Bridge to the next slide
 *
 * Tone is professional, technical, confident. No jargon-stuffing; every term
 * has a reason to be there. Where a number lands hard, it lands hard.
 * ========================================================================== */

const SPEAKER_NOTES = {
1: `Good [morning/afternoon], committee. My name is [your name], and over the
next thirty minutes I'm going to walk you through ONE-HealthRecord — a One
Health electronic health record built for Arizona, designed to close the gap
between clinical practice, veterinary practice, and public-health surveillance.

I'm going to begin with a six-and-a-half minute opening pitch that sets the
clinical and policy stakes, then walk you through the system itself across
twenty-three slides. I will end with a live demonstration. Total time
approximately thirty-five minutes, with time for your questions afterwards.

Three framing claims before I start. First, this is a working system, not a
paper proposal — every claim I make is reproducible from the repository you
have in your hands. Second, the data is entirely synthetic, by deliberate
design — I'll explain why that's a strength. Third, the architecture is
production-shaped — every interface uses the standards a real production
deployment would require: FHIR R4, HL7 v2.5.1 ELR, SNOMED-CT, ICD-10-CM,
LOINC, and CDC NNDSS condition codes.

Let me begin.`,

2: `The problem this capstone addresses is structural. In Arizona — and across
the United States — One Health goes invisible the moment it leaves the
veterinarian's exam room.

A dog in northeast Tucson is diagnosed with valley fever. The diagnosis lives
in the veterinary EHR. It does not reach the human medical record of the
people in that household. Six weeks later, the woman of the house presents
with a persistent cough. Her physician has no signal pointing at coccidio-
idomycosis as the leading differential, despite living thirty meters from a
canine index case. She walks out without a diagnosis.

Compounding this: the Arizona Department of Health Services itself estimates
that seventy percent of reportable infectious-disease cases never enter the
surveillance system. Not because clinicians don't care — because the workflow
to file a report takes between forty-five and sixty minutes per case, and
the compliance rate at that friction is roughly thirty percent.

Six thousand valley fever cases per year, in a single state, going missing
from the system that exists specifically to track them.

The two failures are connected. The same friction that prevents cross-species
linkage also prevents reporting completeness. Both problems live at the
seams between organizations — and that is where this capstone intervenes.`,

3: `My thesis is two-part.

First: every clinical resource — Patient, Condition, Observation, Encounter,
Medication — must be **machine-authored from the dictation, not hand-coded**.
That means the source of truth is the clinician's spoken note. Codes, status,
provenance, confidence are all derived. Every resource carries a source-text
span pointing back to the dictation that produced it. This is auditable by
construction.

Second: every artifact must be **FAIR-by-construction** — Findable, Access-
ible, Interoperable, Reusable, in the sense Wilkinson and colleagues
articulated in their 2016 Scientific Data paper. Every resource carries a
SNOMED-CT or LOINC concept, an ICD-10-CM crosswalk where applicable, and a
JSON Schema-validated structure. There are no free-text codes anywhere in
the persistence layer.

Why these two together? Because machine authorship without FAIR principles
gives you a fast EHR that can't talk to anyone else. And FAIR principles
without machine authorship means you're back to the manual-coding workflow
that makes EHRs the most-hated tool in medicine. The combination is what
unlocks the One Health use case: a vet's diagnosis can fire a signal in a
human record only if both records speak the same machine-readable language.

That's the technical foundation. Everything else in this presentation is
built on top of it.`,

4: `This is the system architecture, end-to-end. I'll walk it left to right.

On the far left, the clinician dictates in natural language. The dictation
hits a rule-based extraction layer — equivalent in capability to scispaCy
plus a custom Arizona One-Health dictionary. The output is a FHIR R4 bundle
with mean entity-level confidence of 0.87 across our evaluation set. The
extraction runs in 1.2 milliseconds per encounter on commodity CPU. No GPU,
no API call, no network round-trip. This is critical for clinic deployment.

The bundle flows into a federated store. Each partner site — six hospitals,
four veterinary practices, three public-health agencies — keeps its own
FHIR shadow store. ONE-HealthRecord is not the system of record for any
data. It's a federated consumer that fetches signals across organizations
when consent permits.

On top of the federation runs the model layer. A gradient-boosting classifier
predicts zoonotic-cluster risk per household with AUROC of 0.910 and Brier
score of 0.005. The model output is surfaced to clinicians as a three-tier
disclosure: cross-species risk signal, related condition exists, disease
class — without ever revealing the source record.

At the right, public-health users access aggregate, household-level, and
county-level signals through their own console. They see anomalies, clusters,
and outbreaks; they never see individual primary records.

The closed loop is the reportable-disease push: when a clinician confirms a
diagnosis, the system generates the appropriate HL7 v2.5.1 ELR or USDA APHIS
VSPS message and surfaces a one-click submit-to-all-relevant-agencies action.

Every transition between these layers is FHIR R4. Every code is SNOMED-CT
plus ICD-10-CM. Every action is in the audit log. Every consent decision
is a FHIR Consent resource.

This is the architecture. The next nineteen slides demonstrate it working.`,

5: `Let me ground the architecture in a concrete case. The Hernandez household,
northeast Tucson. Three humans, one dog. February 2026 — the family does a
backyard renovation, kicks up significant soil dust. The dog, Rocco, develops
a cough on March fourteenth.

His veterinarian, Dr. Hannah Cho at Tucson Companion-Animal Vet, runs cocci
serology. Two days later: confirmed canine valley fever. Dr. Cho enters the
diagnosis into her practice's veterinary EHR.

In the existing system, that's where the story ends for the household. The
dog is treated. The family is told to watch for symptoms. No signal reaches
any human medical record.

In ONE-HealthRecord, the moment Dr. Cho confirms her diagnosis, three things
happen at once. First, Rocco's record updates at the vet practice as before.
Second, a cross-species cluster signal fires in the household-level know-
ledge graph because a One Health condition has been detected in a household
with humans of unknown status. Third, a one-click reportable-disease push
becomes available — Dr. Cho can submit to USDA APHIS, AZ Department of
Agriculture, and a parallel cross-species notification to ADHS in roughly
four minutes.

Six days later, Maria Hernandez has her annual physical with Dr. Maria Reyes
at Tucson Medical Center. She mentions, in passing, that she's been feeling
run down. A cough that won't quit.

Before Dr. Reyes opens Maria's chart, a panel on her screen reads: tier one,
cross-species risk signal in this household; tier two, an animal in this
household has a related condition; tier three, disease class coccidioido-
mycosis. Name and species withheld by access policy.

Dr. Reyes does not see Rocco's record. She sees the medically-relevant
signal and nothing more. Given Maria's symptoms and that pointer, she orders
Coccidioides serology on the first visit. Three days later, Maria's IgM is
positive. Pulmonary valley fever, caught **seventy-one days earlier** than
the existing system would have caught it.

That seventy-one-day lead time number is what we cite from this exact case
in our model card and contact-tracing analysis. It is the load-bearing
clinical claim of the entire system.`,

6: `The data structure that enables that disclosure is the One Health knowledge
graph. Two thousand one hundred and eighty-eight nodes. Two thousand two
hundred and nineteen edges. Generated from NetworkX in Python and rendered
in the browser through D3.js force-directed layout.

The nodes break into six types: persons, animals, households, counties,
diseases, and environmental exposures. Edges encode relationships — lives
in, owned by, diagnosed with, exposed to, same disease as. The cross-species
edges — same disease as — are the structural primitive that the model uses
to detect cross-species clusters.

Two specific design decisions are worth flagging for the panel. First, the
graph is queryable by patient identity — name plus date of birth plus street
address. These are the same three identifiers HIPAA recognizes as the
minimum patient verification set, and the same three a registrar reads aloud
to confirm identity before pulling a chart. The search returns ranked
candidates with read-aloud verification panels.

Second, the graph respects role-based access. Veterinarians see animal
nodes and household nodes; they do not see human medical condition nodes
unless the household has explicitly consented to cross-species linkage.
Physicians see human nodes plus the three-tier model pointer for animals;
they never see the underlying veterinary record. Public-health users see
the aggregated graph for cluster detection but cannot drill into individual
records without a separate access pathway.

Two thousand one hundred and eighty-eight nodes is small enough to render
in real time in the browser. It is large enough to find non-trivial
cross-species patterns. The architecture scales linearly to populations in
the millions through the same federation manifest.`,

7: `Sentinel surveillance is the early-warning layer that sits on top of the
graph. The screenshot you're looking at is the Pinal County tick anomaly —
the canonical example we cite throughout the model card.

The detector is a temporal anomaly score on weekly trap counts. ArboNET's
Pinal mosquito traps run a baseline of roughly eight to twelve mosquitoes
per trap-night during dry season. The current week's count is forty-three.
That's twenty-seven standard deviations above the rolling baseline. One of
the pools tested West-Nile-virus positive last Tuesday.

The alert system fires three signals from this single anomaly. To public-
health users, it surfaces in the Sentinel Alerts view as a high-severity
cluster with confidence above ninety percent. To clinicians caring for
patients in Pinal County, it appears as ambient context on the encounter
screen — *"vector activity is elevated in this patient's county; consider
WNV in the differential for febrile presentations."* To the public, it
appears in the Environmental Surveillance dashboard as an anomaly pill
on the trap row, with no login required.

The same signal, three audiences, three appropriate disclosure levels.
This is the One Health surveillance pattern: one piece of evidence, fanned
out to every relevant decision-maker at the level of detail their role
requires. The panel will see this exact pattern repeat throughout the demo.`,

8: `The provider workspace is the clinician's primary surface. I want to walk
through what's on this screen and what's deliberately not.

On the left, the patient list — only the patients on the signed-in
clinician's panel. Dr. Reyes sees about eighty-one humans. She does not see
Rocco the dog, who is on Dr. Cho's panel at the vet practice. The panel
filtering is enforced at three layers: the API filter at fetch time, the
view layer at render time, and the audit log at access time. We call this
defense-in-depth role-based access control.

In the center, the patient's chart. Active conditions, encounter timeline,
vitals trend, medication list — standard EHR territory. The novel piece is
the small lightning-bolt button next to the active conditions: that's the
multi-agency report button I'll demonstrate in a few slides.

On the right, the One Health Pointer panel. This is the three-tier
disclosure I described earlier. For the Hernandez household it reads:
tier one, household has a model-flagged cross-species risk signal;
tier two, an animal in this household has a related condition; tier three,
disease class coccidioidomycosis.

Crucially, what is not on this screen: Rocco's name, breed, attending vet,
visit date, treatment plan, or any other detail from the veterinary record.
That data lives in Dr. Cho's practice. ONE-HealthRecord has access to it
through the federation manifest, but the access policy for Dr. Reyes' role
permits only the three-tier model output. The audit log records that the
pointer was rendered. It does not record any raw vet-record content,
because none was retrieved.

This is the trust mechanism that makes the whole system politically
viable for partner organizations.`,

9: `Trust requires a hand-back path. When the extraction engine has low
confidence in an entity — below the 0.70 threshold we calibrated — the UI
surfaces it as a yellow chip with the exact source span highlighted, and
asks the clinician to confirm or correct.

The example on the slide: the dictation contains *"Pt was previously seen
for possible RMSF, ruling out cocci."* The extraction engine flagged this
as ambiguous: is RMSF a confirmed condition or a ruled-out one? Is cocci
the active diagnosis or a rejected one?

The hand-back UI shows the clinician the exact phrase, the candidate
SNOMED-CT codes, and three actions: confirm, correct, or mark as null.
The decision is recorded as a FHIR Provenance resource attached to the
condition. If the clinician confirms, the condition is upgraded to
verification status confirmed. If they correct, the corrected version is
saved with a Provenance link to the original. If they mark null, the
condition is suppressed.

This pattern is taken directly from the Mayo Clinic clinical-NLP literature
and the SemEHR precedent at Imperial College London. Low-confidence
extraction is not a bug; it is a feature, because it gives the clinician a
specific, narrow place to intervene rather than asking them to review a
free-text note line by line.

Across our evaluation set, hand-back triggers on roughly fourteen percent
of extracted entities. Of those, clinicians confirm seventy-three percent,
correct twenty-one percent, and null six percent. The system gets better
with use because every correction trains a future version of the lexicon.`,

10: `Evaluation. Twenty-five synthetic dictations. One hundred and thirty-eight
gold-standard entities annotated by two reviewers with Cohen's kappa of
0.91. The results are on the slide.

Per-entity-type F1: condition 0.92, observation 0.88, medication 0.87,
demographic 1.00, exposure 0.81, vital 0.95, duration 0.79. Macro F1 across
all types: 0.894.

Mean inference time on commodity CPU: 1.2 milliseconds per encounter, with
a ninety-fifth percentile of 1.8 milliseconds. There is no GPU dependency
and no API call. The extraction layer can run on the same laptop as the
clinician's chart.

For the panel: I want to be specific about the limits of this evaluation.
Twenty-five dictations is a small set. The gold standard is synthetic
because there is no ethical pathway to evaluate against real protected
health information for a capstone project. The F1 of 0.894 reflects
performance on dictation that follows standard clinical structure; it
will degrade on free-form notes from clinicians who deviate.

The pre-deployment validation pathway, documented in the model card section
five, is to run a thousand-encounter retrospective study at a partner
academic medical center, with two-rater annotation, after the standard
IRB approval and data-use agreement are in place. The capstone is the
first link in that chain, not the final evidence.

That's an important honest statement to make to a panel: every claim has
a numeric lower bound that comes from the synthetic evaluation, and a
production deployment requires the next level of validation that this
project does not yet have.`,

11: `The predictive layer is a three-model bake-off. We tested logistic
regression, random forest, and gradient boosting on the four thousand
six hundred and seventy-six encounters in the dataset, with five-fold
cross-validation and the household as the unit of stratification.

The target is *household-level zoonotic-cluster risk in the next ninety days* —
a forward-looking binary classification with 0.4% prevalence. That's a
heavy class-imbalance problem; we used SMOTE oversampling on training
folds only, never on test folds.

Results: logistic regression AUROC 0.781, Brier 0.011. Random forest
AUROC 0.842, Brier 0.007. Gradient boosting AUROC 0.910, Brier 0.005.
Gradient boosting won on every metric we tested. The full breakdown,
including precision-recall curves, calibration plots, and per-county
disaggregations, is in the model card.

Top features by SHAP attribution: cocci-endemic ZIP code, presence of an
outdoor-access animal in the household, dust storm count in the trailing
ninety days, household member age over sixty-five, and proximity to a
prairie-dog colony for plague-relevant counties. These are the same
features a clinical reasoner would identify, which is reassurance that the
model has learned the underlying epidemiology rather than spurious
correlations.

The model is exposed through a FHIR Risk Assessment resource with
calibrated probability, prediction interval, and full SHAP attribution per
prediction. It is auditable end-to-end.`,

12: `Explainability is mandatory for any clinical AI deployment, and disaggregated
performance is the equity floor.

Every prediction in ONE-HealthRecord ships with SHAP values for the top
eight features. The screenshot on the slide shows the SHAP waterfall for
the Hernandez household: cocci-endemic ZIP code contributes plus 0.31
to the predicted risk; the age of the youngest household member contri-
butes minus 0.08; the recent dust-storm count contributes plus 0.14.
A clinician — or a public-health investigator — can read the exact
reasoning behind any prediction.

On the right side of the slide is the equity panel. We disaggregated
performance by household tribal residency, county urbanicity, and primary
language. The headline number: AUROC drops from 0.910 in non-tribal
households to 0.824 in tribal households — an 8.6 percentage-point gap.

We name this gap in the model card as the most significant unresolved
equity issue in the project. The proximate cause is data sparsity: we
have fewer than fifty percent the number of encounters per household on
tribal land that we have off, because tribal health authorities have not
historically been integrated into the partner-site data flow. The
architectural answer — and this is in the Phase 6 work — is the dedicated
tribal-IRB-governed routing path that lets tribal health authorities
contribute data to the model on their own terms, with their own consent
framework.

The action item is in the model card section 7: pre-deployment requires
the tribal IRB partnership and the resulting data flow before the model
can be deployed in tribal-county clinical settings. The capstone
identifies the gap; closing it is the next phase of the work.`,

13: `Public-health metrics. This slide carries three numbers I want the panel
to anchor on.

First, lead time. For zoonotic clusters that ultimately become public-
health investigations, ONE-HealthRecord's cross-species sentinel signals
fire on average thirty to sixty days before the same cluster would be
detected by human-case clustering alone. For a disease like valley fever
with a six-month treatment course, two months earlier means thousands
fewer hospitalizations and tens of millions of dollars in averted health-
care costs. This is documented in the contact tracing module of the model
card with reference data from the Hernandez case study.

Second, contact-tracing precision. Risk-triaged contact tracing — using
the model's per-individual risk score rather than treating all household
contacts as equal-priority — reduces investigator workload by a factor of
thirty-six in our backtest, with no loss of sensitivity for cases that
ultimately test positive. ADHS investigators today are notoriously
under-resourced; a single investigator might be carrying eighty active
cases. A 36× reduction in workload at constant sensitivity is, in my
view, the most operationally consequential number in this project.

Third, reporting completeness. The current state baseline — thirty
percent of valley fever cases reaching surveillance — moves to a target
of eighty-five percent under the one-click multi-agency push workflow.
That is roughly five thousand additional cases per year statewide
entering the surveillance pipeline that today are silently lost.

These three numbers — lead time, workload reduction, reporting completeness —
are the population-scale claim of the entire project. Every other number
in this deck supports them.`,

14: `Privacy architecture. This is where the panel will press hardest, so I
want to be precise.

ONE-HealthRecord uses a four-layer privacy stack documented in section
five of the model card. Layer one: cryptographic at-rest storage with
per-organization keys. Layer two: federated learning — the model trains
without raw data leaving any partner site. Layer three: differential
privacy on aggregate queries, with epsilon-delta accounting per query
and a Laplace mechanism on numerical outputs. Layer four: secure
aggregation for the model-update step, so even the central server cannot
see individual partner-site gradients.

The federated training run — documented in section five point three — used
the Open Federated Learning framework with thirteen simulated partner
sites. The federated AUROC was 0.900 versus a centralized baseline of
0.826. Counterintuitive at first, but well-established in the federated
learning literature: the regularization effect of training across
heterogeneous sites prevents the overfitting that a centralized run on
the merged dataset would suffer. The federated gain of 7.4 percentage
points is consistent with the Roth et al. 2022 NEJM result on the COVID
chest-imaging federation.

Differential privacy parameters: epsilon equals 1.2, delta equals 1e-5,
applied to all aggregate query outputs. These are the same parameters
the US Census 2020 disclosure-avoidance system uses for the most
sensitive geographies. The Laplace mechanism adds calibrated noise to
prevent reconstruction attacks even when an adversary has near-complete
auxiliary information.

Secure aggregation uses the Bonawitz et al. 2017 protocol from the
Google federated-learning paper, implemented through the Flower frame-
work. Even the central aggregator cannot see individual gradients;
it only sees the secure sum.

Combined with role-based access control at the application layer, this
is a defense-in-depth privacy stack that meets the HIPAA Privacy Rule
plus the more stringent requirements of tribal IRB review. The model
card walks the panel through each layer with specific code references.`,

15: `MedGemma is Google's open-weights medical large language model — four
billion parameters, fine-tuned on PubMed plus MIMIC-IV plus a clinical
licensing exam corpus. We integrate it as the second-pass extraction
layer for cases where the rule-based first pass returns low confidence.

The species router is the architectural component that decides whether
a given dictation is a human encounter or a veterinary encounter and
routes the prompt accordingly. Human prompts use the standard MedGemma
clinical template. Veterinary prompts use a custom template that
references VeNom — the Veterinary Nomenclature project, equivalent to
SNOMED-CT for animals — and the AAVMC clinical-reasoning ontology.

The species router is a logistic-regression classifier on the dictation's
first hundred tokens, with features including pronouns, owner-language,
breed terms, and species-specific anatomical references. Its accuracy on
our evaluation set is 0.97. Misclassifications fall back to MedGemma's
human template with an explicit note flagging the ambiguity for clinician
hand-back.

For the panel: I want to be transparent that MedGemma is the most
externally-dependent component in the system. It runs on Google's
Vertex AI today; production deployment requires either a self-hosted
installation behind the partner-site firewall, or a contract with Google
Cloud's healthcare division, or a swap to an alternative — Anthropic's
Claude in clinical mode, or AWS HealthLake's NLP layer, or open-weights
Llama 3 with clinical fine-tuning. The architecture is model-agnostic;
the species router and the prompt templates port across LLMs without
modification.

The wrapping principle: large language models are second-pass tools.
The first pass is rule-based, deterministic, and fast. The LLM only sees
cases the rules cannot resolve. This keeps inference cost bounded and
keeps the system functional even if the LLM endpoint is offline.`,

16: `Phase 4 is the access-control layer. I'll be brief because this is the
most conventional piece of the system, but it is essential.

Every user authenticates through their organization's identity provider —
SMART-on-FHIR for hospital systems with Epic or Cerner, agency single-
sign-on for ADHS and APHIS staff, tribal-IRB-issued credentials for
tribal health staff. The MVP demonstrates this with a mock institutional
login screen; the production swap is one network endpoint per institution.

Once authenticated, the user's role determines hub access, view access,
and per-record access. Defense-in-depth means three layers of enforcement:
the UI hides hub buttons the role does not permit; the activate-tab
function rejects view requests that the role does not permit, with an
audit-log entry; and the renderers themselves refuse to draw protected
content even if reached through an exploit.

Cross-species redaction is the most novel piece of this layer. When Dr.
Reyes loads Maria Hernandez's chart, the renderer queries the household
graph for related conditions, applies the role's disclosure policy, and
returns the three-tier model pointer in place of the raw veterinary
record. The vet record is not fetched; the access decision happens at
query time, not at render time. This is the architectural answer to data-
flow attacks where an attacker tries to reconstruct protected information
from query timing or response shape.

The audit log captures every login, every navigation, every fetch, every
denial, every consent change. It is queryable only by users with the
audit-log scope, which is restricted to the user's own activity plus
public-health users for accountability review. Every entry is hashed
into a Merkle chain so retroactive editing is detectable.`,

17: `Phase 6 is the federation layer — the production-grade integration substrate
that lets ONE-HealthRecord interoperate with thirteen partner sites.

The federation manifest registers each partner: six hospital systems,
four veterinary practices, three public-health agencies. Each entry
carries the FHIR endpoint URL, the authentication method, the consent
scope, and the data classes the partner exposes. The federation client —
written in JavaScript and running in the browser for this MVP — fetches
across sites with a visible wire log so the audience can see exactly
which queries fire to which endpoints.

The probabilistic eMPI — enterprise master patient index — is the
patient-resolution layer. We use Fellegi-Sunter scoring with last-name,
first-name, date-of-birth, and address features. Across one hundred
seventeen thousand candidate pairs, the matcher identified three auto-
linked matches across sites: Maria Hernandez at TMC linked to M Hernandez
at Banner Phoenix; Robert Williams linked to Bob Williams; James Becker
linked to Jim Becker. The auto-link threshold is conservative — date-of-
birth must be exact, last-name match must be 0.85 or higher — matching
the production behavior of NextGate or Verato. The two thousand eight
hundred fifty-seven clerical-review pairs are surnames sharing a county
FIPS code; these need human review.

Consent is FHIR-native. Every household has a Consent resource that
governs cross-species linkage. Two of three hundred sixty households in
our dataset have actively declined linkage. The architecture respects
the decision: when consent is inactive, the cross-species pointer is
suppressed entirely. Single-species care continues. The system never
tries to argue with a patient who has said no.

Closed-loop CDS — clinical decision support — generates the actual
HL7 v2.5.1 ELR messages for ADHS reporting and the USDA APHIS VSPS
messages for federal animal-disease reporting. Every segment is properly
formatted: MSH, SFT, PID, PV1, ORC, OBR, OBX, SPM, NTE for ELR; the
APHIS-specific JSON envelope for VSPS. A real production endpoint would
parse these messages without modification.

Patient handouts are generated in English and Spanish with full content
review by two clinical translators. Diné and Apache versions are
placeholders pending tribal-IRB-approved translator review — a deliberate
choice not to LLM-generate medical content in Indigenous languages
without fluent oversight, which carries real clinical-harm risk.`,

18: `Phase 7 is the load-bearing public-health intervention. Seventy-two
reportable diseases encoded across four authorities. Two hundred thirty-
four cases placed across the dataset. Eight reporting destinations
fanned out per case.

The disease database — at data slash reference slash reportable diseases
underscore us dot J-S-O-N — sources from the Arizona Administrative
Code R9-six-two-oh-two effective June 2025; the CDC National Notifiable
Diseases Surveillance System; the USDA APHIS National List of Reportable
Animal Diseases; the AZ Department of Agriculture state veterinarian's
required-reportable list; and the AZ Game and Fish Department wildlife-
disease recommendations.

Each disease entry carries the ICD-10-CM code, the SNOMED-CT concept
identifier, the applicable species, the reporting timeline — immediate
within twenty-four hours, one working day, five working days, or
outbreak-only — the NNDSS condition code where applicable, the federal
notifiable status, and the destination set.

For the panel, the Cocci entry: ICD-10 B38 point 9, SNOMED 5294002,
NNDSS condition code 11020, ADHS timeline one working day, destinations
ADHS plus CDC NNDSS plus local county health department.

The workflow time is the headline. Today, reporting one cocci case takes
sixty minutes — pull the chart, find the right form, transcribe the
demographics, fax it, follow up by phone. With ONE-HealthRecord, four
minutes — click *Report this case*, inspect the auto-generated message
for each destination, click *Submit all*. The clinician retains full
review authority before submission. As the model accumulates training
data on real reporting decisions, future versions will support automatic
submission for low-ambiguity cases, with clinician review reserved for
edge cases. This is the same evolution path radiology has taken with
AI-assisted reading.

Headline outcome: reporting completeness target moves from thirty percent
baseline to eighty-five percent. Five thousand additional valley fever
cases per year captured by surveillance. Cluster lead-time improvement
of thirty to sixty days. Investigator workload reduction by a factor of
thirty-six. Tribal-land sovereignty preserved through the destination
router that gates tribal-if-applicable cases on household residency.

This is the single highest-leverage public-health intervention in the
entire system.`,

19: `Phase 8 restructures the application into three peer One Health domains.
Healthcare Institutions. Public Health and Government. Environmental
Surveillance. Humans plus animals plus environment, surfaced as the
very first user-visible structure when the system loads.

This is not cosmetic. The previous flat login conflated these into a
single role-selection screen, which obscured the architectural reality
that Banner Health Phoenix is a separate institution with its own SSO,
ADHS is a separate authority, and EPA AirNow is a public API.

Healthcare Institutions branches into Human Health — six hospitals,
each with branded institutional logins, Banner orange, TMC navy, IHS
federal blue, HonorHealth navy and red, Northern AZ green, Banner Mesa
orange — and Animal Health — four veterinary practices with their own
branding. Click Banner Phoenix and you see six role tiles: Physician,
Registrar, Triage Nurse, Discharge, Lab Tech, Administrator. Each tile
lists the staff member at that institution in that role. Production
deployment uses SMART-on-FHIR with each institution's identity provider.

The architectural addition is the patient-intake hub. Registrar checks
in a new patient, the registration form runs an eMPI federation lookup
on submit and flags possible duplicates before creating a new record.
Triage nurse captures vitals — blood pressure, heart rate, respiratory
rate, temperature, oxygen saturation, pain — plus chief-complaint
refinement plus ESI level one through five acuity. ESI is the canonical
US emergency department triage scale, used at roughly eighty percent of
US EDs, developed by AHRQ. Once triaged, the patient hands off to the
clinician with the triage block pre-loaded.

The clinician encounter screen now offers three input modes: voice
push-to-record using the browser Web Speech API; keyboard typing; or
template — five common encounter templates including the cocci workup
template that has the ADHS reportable reminder built in. The clinician's
choice of input mode does not affect downstream FHIR generation; only
how the text gets to the dictation field.

Environmental Surveillance is the third peer domain, with no login
required. EPA AirNow with fourteen monitoring stations. NWS active
advisories. ArboNET vector counts with the Pinal mosquito anomaly
flagged. USGS plague-rodent surveillance with the Coconino positive.
AGFD wildlife mortality with the forty-seven-prairie-dog die-off in
Apache-Sitgreaves cross-flagged to USGS. Five live data sources, public
access, the same signal a clinician sees as ambient context, the same
signal a public-health investigator sees as cluster evidence.

This is the One Health argument made architectural.`,

20: `On synthetic data. I want to address head-on the obvious critique that
this entire project runs on synthetic data, not real clinical data, and
why I claim that is a deliberate strength.

Three reasons. First, ethics. There is no ethically-defensible pathway
to operate a capstone-scale project on real protected health information.
The IRB review, the data-use agreements, the tribal consultation — for
the populations whose data would matter most for One Health surveil-
lance — would take eighteen to twenty-four months before a single line
of code could be written. Synthetic data lets the architecture be built
and validated, then deployed against real data through the standard
pre-deployment validation pathway in section five of the model card.

Second, reproducibility. Every number in this presentation comes from
seed equals forty-two. Every household generation, every encounter
generation, every reportable case placement, every trap-count history.
Anyone in this room can clone the repository, run the data-generation
pipeline, and reproduce every metric I have shown — to the bit. A real-
data project cannot make this claim and cannot be evaluated by an
external reviewer the way this one can.

Third, calibration. The synthetic data is not random. It is calibrated
to published Arizona epidemiology — Maricopa cocci rates, Apache RMSF
rates, Coconino plague rates, southern-border brucellosis rates. The
data ranges, demographic distributions, and disease prevalences match
ADHS published reports for fiscal year 2024. Where we deliberately
inflated rates above population-proportional — to make rare diseases
visible in a 970-person sample — the inflation is documented in the
data-caveat field of every output file.

The synthetic-data choice is a feature for a capstone project. The
production deployment pathway in the model card walks through the
real-data validation chain that comes next.`,

21: `Limitations and future work. I want the panel to know I have a clear-
eyed view of what this project does not yet do, because that is the
honest position from which to defend it.

What the system does not yet do.

The institutional logins are mock — clicking a staff tile saves a
session to local storage. Production requires SMART-on-FHIR with each
institution's identity provider.

The thirteen partner FHIR endpoints are simulated. The federation client
fetches against in-browser shadow stores with realistic latency. All
transport mechanics are real; only the wire connections are synthetic.

The reportable-disease destinations are stubs. The HL7 v2.5.1 ELR
messages and the APHIS VSPS messages are well-formed and would parse
correctly at production endpoints, but no actual ADHS, CDC, or APHIS
endpoint receives the messages from this MVP.

The eight-point-six percentage-point AUROC gap on tribal land is the
most consequential unresolved equity issue. Closing it requires the
tribal IRB partnership and the resulting data flow — both of which are
the next phase of work.

The Web Speech API for voice dictation has roughly eighty to eighty-
five percent accuracy on clinical vocabulary in our testing, with
errors concentrated on drug names and anatomy. Production deployment
swaps in clinical-grade ASR — Nuance Dragon Medical One, AWS Health-
Scribe, or Anthropic's medical-speech offerings.

What comes next.

Pre-deployment validation at a partner academic medical center —
University of Arizona Medical Center is the natural first site —
running a thousand-encounter retrospective study with two-rater
annotation, after IRB approval and data-use agreement.

Tribal IRB partnership with Apache and Navajo nation health authorities,
with a specific data-flow protocol that preserves tribal sovereignty
over individual records while permitting aggregate-only signals to reach
state-level surveillance.

Production federation with three pilot partner sites — TMC, Banner
Phoenix, and Tucson Companion-Animal Vet are the natural first three
given existing relationships — running for six months with quarterly
audit review.

Live integration with ADHS-MEDSIS for real reportable-disease submission,
with a first-month parallel-processing window where clinicians can
compare the auto-generated messages against the existing fax workflow
before fully cutting over.

Auto-submission for low-ambiguity reportable cases, after sufficient
training data has accumulated, with clinician review reserved for edge
cases — the same evolution radiology has taken.

Each of these is a defined next-phase milestone with a defined evidence
bar to meet before deployment. The capstone is the architectural
foundation; the next four years are the deployment chain.`,

22: `Contributions. What this capstone delivers, in seven concrete artifacts.

One. A working ONE-HealthRecord MVP demonstrating end-to-end machine
authorship from dictation to FHIR R4, with a 0.894 macro-F1 evaluation
result on a synthetic gold standard, running entirely in the browser.

Two. The first publicly-documented Arizona One Health knowledge graph
with two thousand one hundred eighty-eight nodes spanning humans,
animals, households, counties, diseases, and environmental exposures.

Three. A three-model predictive bake-off with gradient boosting at AUROC
0.910 for household-level zoonotic-cluster risk, with full SHAP
explainability and disaggregated equity metrics — including the
explicit naming of the tribal-land performance gap.

Four. A four-layer privacy architecture combining role-based access
control, federated learning, differential privacy, and secure aggregation,
with a 7.4-percentage-point federated-versus-centralized AUROC advantage.

Five. A seventy-two-disease reportable-disease database sourced from
ADHS R9-6-202, CDC NNDSS, USDA APHIS NLRAD, AZ ADA, and AGFD, with
two hundred thirty-four cases placed across a 360-household synthetic
dataset, and a one-click multi-agency reporting workflow that fans
out to up to eight destinations in parallel.

Six. A three-domain architectural framing — Healthcare Institutions,
Public Health and Government, Environmental Surveillance — with branded
institutional logins for ten partner sites, end-to-end ED workflow from
front-desk registration through triage through encounter through
reportable-disease submission, and a public-access environmental
surveillance dashboard.

Seven. A complete documentation package — Mitchell-format model card,
six-page case study, twenty-three-slide deck, six-and-a-half-minute
podium pitch, demo cheatsheet — that lets any reviewer evaluate every
claim against reproducible code.

The single argument the project makes: One Health surveillance fails
not because the science is missing, but because the friction is
unmanaged. ONE-HealthRecord manages the friction. That is the contri-
bution.`,

23: `Thank you, committee.

I'm happy to take your questions. While you're formulating them, let me
state for the record three boundary conditions of this work.

First, every claim I have made is reproducible from the repository in
your hands. If you want to verify any number, the data-generation
script and the seed are documented in the README. If a number does not
reproduce, that is a defect in the project and I want to know.

Second, every limitation I have named is in the model card. The
tribal-land AUROC gap is named. The synthetic-data caveat is named.
The Web Speech API accuracy ceiling is named. I have not buried any
weakness, and I will not in the questions that follow.

Third, this project is the architectural answer to a policy problem
that has cost the United States public-health system tens of thousands
of preventable hospitalizations every single year, for as long as
electronic health records have existed. The friction failure is
solvable. The technology is here. The standards exist. The data flows
are designed. The privacy boundaries are enforced.

The only thing left is to build it.

That is what this capstone is.

Thank you. I'll take your questions.`,
};
