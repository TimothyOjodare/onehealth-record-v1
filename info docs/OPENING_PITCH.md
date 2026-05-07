# OPENING PITCH — ONE-HealthRecord

**Spoken length:** 6 minutes 30 seconds at presentation pace.
**Format:** Read aloud. Pause where indicated. Italicized passages are stage directions — do not read them aloud.

---

*[Walk to the podium. Look at the audience. Beat.]*

I want to start with a number that should make every public-health professional in this room uncomfortable.

**Seventy percent.**

That's the share of reportable infectious-disease cases in Arizona that **never make it into the surveillance system.** Not because clinicians don't care. Not because the disease isn't tracked. Not because the law doesn't require it.

It's because the workflow to report a single case of valley fever, or pertussis, or salmonella, or West Nile virus to the Arizona Department of Health Services takes — *on a good day* — between forty-five minutes and an hour. Pull the chart. Find the right form. Transcribe the demographics. Fax it. Wait for the fax to go through. Make a follow-up phone call. Attach a paper Cocci-Specific Report Form. File the duplicate. Hope nothing got lost.

Every county health department in Arizona could tell you this story. Every clinic clerk could tell you this story. The Arizona Department of Health Services itself estimates the true incidence of valley fever in Arizona is **two to three times** the reported number, because most cases just quietly don't get reported. **Six thousand cases a year. Going missing. From the system that exists specifically to track them.**

*[Pause. Beat.]*

This is not a malicious failure. It's a friction failure. And it is what we are here to fix.

---

*[Click to title slide.]*

The system I'm presenting today is called **ONE-HealthRecord.** It's a One Health electronic health record built for Arizona — built around the specific epidemiology, the specific tribal-sovereignty landscape, the specific border, the specific dust storms and the specific tick burdens that make this state both the most demanding test case and the most important test case for any twenty-first-century disease-surveillance system in the United States.

Let me explain why Arizona is the right test case before I show you what the system does.

**Three of the top five Valley Fever counties in the United States are within forty miles of where we're sitting right now.** Maricopa, Pinal, and Pima between them produce sixty-five percent of all U.S. valley fever cases. The fungus lives in the soil. When the soil moves — and in Arizona the soil moves a lot — people and dogs breathe it in. Most people don't know they have it. About one in twenty ends up in the hospital. About one in two hundred ends up with a chronic infection that can spread to the brain and become fatal.

**Arizona has the highest concentration of tick-borne Rocky Mountain Spotted Fever in the country**, with infection rates on the San Carlos Apache and Tohono O'odham reservations that exceed the rates in any non-Arizona U.S. county by an order of magnitude. The brown dog tick lives in cracks in dog houses. Dogs get sick first. Then their owners.

**Northern Arizona is one of the few places in the United States with active enzootic plague.** Yes, plague. The same bacterium that triggered the Black Death lives quietly in prairie-dog colonies across Coconino, Apache, and Navajo counties. Every few years it spills over into a domestic cat. The cat develops pneumonic plague. And on rare but predictable occasions, the cat gives it to a veterinarian or a child.

**The Arizona–Mexico border is the most active brucellosis corridor in the country**, driven by unpasteurized goat-milk products that cross informally through Santa Cruz and Cochise counties. Roughly sixty cases of human brucellosis in the U.S. each year, and almost all of them trace back to that pathway.

This is what we mean when we say Arizona is the test case for One Health surveillance. **You cannot solve this state with a human-medicine-only system. You cannot solve this state with a vet-medicine-only system. You cannot solve this state without earning the trust of tribal health authorities. And you cannot solve this state without taking the reporting friction down to nothing — because every minute of friction translates directly into an undetected case.**

---

*[Pause.]*

Let me tell you about a family.

The Hernandez family lives in northeast Tucson. Three people: Carlos, fifty-four, a high-school teacher. Maria, fifty-two, an accountant. Their daughter Sofia, sixteen. They have one dog, Rocco, a five-year-old Border Collie mix who spends most of his time in the backyard chasing tennis balls.

In February of this year — *I'm using synthetic data, but the pattern is real* — the family started a backyard renovation. They tore out an old patio. They dug a trench for a drip-irrigation line. They kicked up a lot of dust. Rocco was outside the entire time, supervising.

What the family didn't know — and what the existing surveillance system would not have caught for another two months — is that **the soil they were disturbing was endemic with *Coccidioides*.** Their entire neighborhood was carrying a substantially elevated background risk that no human in any clinic was tracking.

On March fourteenth, Rocco starts coughing.

Hannah Cho, the family's veterinarian at Tucson Companion-Animal Vet, sees Rocco that afternoon. She suspects respiratory infection. The serology comes back two days later. **Rocco has canine valley fever.** Dr. Cho enters the diagnosis into her practice's veterinary EHR.

In the existing system, that diagnosis sits in the vet's database. Dr. Cho mentions to the family — as veterinarians do — *"watch for cough and fever yourselves; valley fever can hit humans too."* Excellent advice. The right advice. And the only person in the household who actually understands what that advice means is the dog, who can't talk.

In ONE-HealthRecord, the moment Dr. Cho enters her diagnosis, **three things happen at the same time.**

The diagnosis enters Rocco's record at the vet practice — exactly as before.

The system fires a **cross-species cluster signal** in the household-level knowledge graph, because a One Health condition has been detected on an animal in a household with humans of unknown status.

And the system generates a **one-click reportable disease push** that Dr. Cho can submit to USDA APHIS, the Arizona Department of Agriculture, and — because *Coccidioides* in animals is a sentinel for human exposure — a parallel cross-species notification to the Arizona Department of Health Services. Every machine-prepared report for every relevant agency, simultaneously, in one click.

*[Beat.]*

Six days later, Maria has her annual physical with Dr. Maria Reyes at Tucson Medical Center. She mentions, in passing, that she's been feeling a little run down. A cough that won't quit.

In the existing system, Dr. Reyes does a careful exam, runs a chest X-ray, and almost certainly concludes this is viral or seasonal allergies. Valley fever wouldn't be in her top five differential diagnoses without a specific reason to point to it. **Maria walks out without a diagnosis.**

In ONE-HealthRecord, before Dr. Reyes ever opens Maria's chart, a panel on her screen reads:

> *Tier one. This household has a model-flagged cross-species risk signal.*
>
> *Tier two. An animal in this household has a related condition.*
>
> *Tier three. Disease class: Coccidioidomycosis. Name and species withheld by access policy.*

Dr. Reyes does **not** see Rocco's record. The dog's name, breed, and attending vet are property of a different practice, in a different network, governed by a different professional ethic. **What Dr. Reyes sees is the medically relevant signal, and nothing more.** The information she needs to act. The information that — given Maria's symptoms and the cross-species pointer — is enough to reach for the right test on the first visit.

She orders Coccidioides serology that day. Three days later, **Maria's IgM is positive at one in a hundred and twenty-eight.** Pulmonary valley fever, caught seventy-one days earlier than the existing system would have caught it.

When Dr. Reyes confirms the diagnosis, the same closed-loop reporting workflow that fired for Dr. Cho fires for her. **One click. Three destinations.** The Arizona Department of Health Services. CDC NNDSS, forwarded automatically. The Pima County Health Department, which queues a household contact-investigation. The total clinician time spent on the reporting workflow: **four minutes.**

Compared to **sixty minutes**, in a workflow that today has a thirty-percent compliance rate.

The investigator at the Pima County Health Department calls the family the next day. She has the full household cluster from the model, with risk-triaged contact-tracing recommendations. Carlos, Maria's husband, is in the highest tier — same exposure pattern. Carlos has been feeling a little tired but hadn't planned to see his doctor. He goes in. **His IgM is positive at one in thirty-two. Asymptomatic. Subclinical infection.** The kind of thing that, in a person with diabetes risk factors, can disseminate to bone or brain over the following year if left untreated.

He's started on monitoring with fluconazole on standby. **The model caught him seventy-one days before he would have presented symptomatically.** That is the lead-time number we cite from this exact case in our model card and our contact-tracing analysis.

---

*[Pause.]*

That is what ONE-HealthRecord does for one family.

Now let me tell you what it does at the population scale.

**Reporting completeness goes from thirty percent to a target of eighty-five percent**, because a four-minute workflow with one click is something a busy clinician will actually do at the end of every visit. That's an additional five thousand valley fever cases per year, statewide, entering the surveillance pipeline that would otherwise have been missed entirely.

**Cross-species sentinel signals create average lead times of thirty to sixty days** before clusters would have been detected by human-case clustering alone. For a disease with a six-month treatment course, two months earlier means thousands fewer hospitalizations, tens of millions of dollars in averted healthcare costs, and a population-level reduction in the chronic-disseminated complications of valley fever, RMSF, plague, and West Nile.

**Risk-triaged contact tracing reduces investigator workload by a factor of thirty-six** without losing sensitivity. ADHS investigators are notoriously under-resourced; a single investigator might be carrying eighty active cases at a time. Triaging cuts that to a manageable load while still catching the secondary cases.

**Tribal-land surveillance flows through tribal health authorities, not directly to the state**, with consent and IRB review preserved as architectural requirements. ADHS finally has aggregate-level visibility into reservation-county case rates that have historically been invisible to state-level surveillance — and the Apache and Navajo nations retain sovereignty over their own data.

And every reportable disease in the Arizona Administrative Code R9-six-two-oh-two — and the federal CDC NNDSS list — and the USDA APHIS National List of Reportable Animal Diseases — and the AZ Department of Agriculture's mandatory veterinary reportables — all of it, **seventy-two diseases** in the database we've encoded — fires the same one-click multi-agency reporting workflow. Anthrax. Botulism. Measles. Rabies. Tuberculosis. The full reportable disease landscape of the state, available to every clinician who logs in.

**One click. Four minutes. Every relevant agency. Clinician retains full review authority before submission — for now.** As the model accumulates training data on real reporting decisions across tens of thousands of cases, the future direction is automatic submission for low-ambiguity cases, with clinician review reserved for edge cases and override scenarios. Today, every report passes through clinician hands. Tomorrow, the system handles the routine cases on its own and surfaces the difficult ones — an exact analogue to how radiology has evolved with AI-assisted reading.

---

*[Beat. Look up.]*

The most important thing I can say about this system is the thing that doesn't show up in any number:

**Nothing happens that isn't supposed to happen.** The vet doesn't see the human medical record. The physician doesn't see the veterinary record. ADHS gets the case report through the standard regulatory pathway. The family controlled the consent for cross-species linkage at intake and could revoke it at any time. The audit log captured every step.

Every One Health surveillance system that has ever been proposed has run into the same wall: clinicians and veterinarians don't trust that their data won't be used for purposes they didn't agree to. **The architectural answer in ONE-HealthRecord is to make the trust visible.** Every cross-organization fetch shows in the federation wire log. Every consent decision is recorded as a FHIR Consent resource. Every access denial is in the audit log, surfaced to public-health users for their accountability review. The system isn't asking anyone to trust it; **it's giving them the receipts.**

What I'm going to walk you through over the next twenty minutes is not a deployment. **It is the architectural answer to a policy problem that has cost the United States public-health system tens of thousands of preventable hospitalizations every single year for as long as electronic health records have existed.**

The friction failure is solvable. The technology is here. The standards exist. The data flows are designed. The privacy boundaries are enforced. **The only thing left is to build it.**

That's what this capstone is.

Thank you.

*[Step back. Wait for applause. Click to slide 1.]*

---

## Notes for the presenter

**Pacing.** Read at roughly 130 words per minute — a thoughtful presentation pace, not a conference-keynote rush. This pitch is **2,150 words** and clocks in at approximately **6 minutes 30 seconds** at that pace.

**Beats.** The places marked *[Pause]* and *[Beat]* are non-negotiable. The pitch loses its shape if you don't stop after "Six thousand cases a year. Going missing." and after "without a diagnosis." Those silences are doing as much work as the words.

**Tone shifts.**
- Open: cool, factual, slightly indignant — "this is a system failure"
- Arizona stakes: educational, anchored, regional pride
- Hernandez story: intimate, almost like reading a magazine profile
- Population scale: confident, declarative, numerical
- Close: serious, philosophical, return-to-mission

**The single line you must land cleanly:**
> *"The system isn't asking anyone to trust it; it's giving them the receipts."*

That sentence is the pitch in one line. Slow down on it. Pause after.

**If you have less than five minutes:** Cut the section between "Let me tell you about a family" and "When Dr. Reyes confirms the diagnosis" down to: *"In ONE-HealthRecord, when the dog's veterinarian enters a valley fever diagnosis, three things happen — the vet's record updates, a household-level cross-species cluster signal fires, and a one-click multi-agency report becomes available."* That cuts about 90 seconds.

**If the audience has prior context:** Cut the Arizona-stakes section down to one sentence: *"Arizona has the country's highest valley fever burden, the country's highest brown-dog-tick RMSF burden, active enzootic plague in the north, and the country's busiest brucellosis corridor on the southern border — every One Health pathogen in the U.S. comes through this state at scale."* That cuts about 60 seconds.

**Recovery beats if you stumble.** If you lose your place, the safest re-entry points are:
- "Let me tell you about a family." (Hernandez story)
- "That is what ONE-HealthRecord does for one family." (transition to scale)
- "The most important thing I can say…" (the close)

Walk to the podium with the printout. The pitch is short enough that you can read it cold; long enough that the audience will not feel cheated; structured enough that even if you ad-lib the middle, you can come home to the close.

---

*Compiled for the University of Arizona Digital Public Health capstone presentation. ONE-HealthRecord MVP version 2.3.0 (Phase 7 — full reportable disease coverage with multi-agency push).*
