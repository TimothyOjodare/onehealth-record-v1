# Demo cheatsheet — Phase 4

**Print this page or keep it on your phone for the talk.**

---

## Before the talk

1. Unzip `one-healthrecord.zip` to anywhere on your laptop
2. Double-click `app/index.html` — it should open in your default browser
3. **First load shows the Login screen.** Three role columns (4 physicians · 3 veterinarians · 3 public-health officers) with a prominent "Demo authentication only" disclaimer
4. Test each role briefly to warm up the JS:
   - Click **Dr. Maria Reyes** → Clinical Workspace appears with her ~81-human panel (245 total assignments — 81 humans + animals would be hers if she were a vet) · click Live Encounter, Provider Workspace · then Sign out
   - Click **Dr. Hannah Cho** → her 77-animal panel appears · then Sign out
   - Click **Dr. Lisa Nakamura** → Public Health Console (Clinical hub button is gone) · click each of Map, Graph, Alerts, Evaluation, Risk Model, Model Card · then Sign out
5. **Inside Risk Model, click each of the four sub-tabs once**: AI metrics → Explainability → Public-health metrics → LLM vs. rules
6. **Inside Model Card, click each of the seven sub-tabs once**: Overview → Components & versions → Metrics → Privacy & security → Ethical considerations → Caveats → **Audit log** (this one warms up the audit-render path)
7. Sign out one final time so the audience sees the login screen at the start
8. Resize the browser to roughly 1500×1000 for the cleanest layout
9. Increase browser zoom to ~110% if you're projecting
10. Open `docs/ONE-HealthRecord_Capstone.pptx` in PowerPoint or Keynote in a second window

---

## Demo flow (~24:00 total spoken — open with the OPENING_PITCH.md, then walk the demo)

**Begin with the OPENING_PITCH.md** (6:30) before anything else. Then walk into the live demo below.

| # | Slide / role | Action | Time | Land this line |
|---|--------------|--------|------|----------------|
| 1 | Slides 1–4 | (decks only) | 2:45 | "The dictation is the source of truth." |
| 2a | **Domain selector** *(Phase 8 — opening shot)* | Show 3-domain card layout | 0:30 | "Three peer domains: Healthcare Institutions, Public Health and Government, Environmental Surveillance. The One Health triad — humans, animals, environment — surfaced as the very first thing you see." |
| 2b | **Click Environmental Surveillance** *(no login)* | Walk through 5 live feeds | 1:30 | "No login. EPA AirNow shows 14 stations across the state. NWS shows the active Excessive Heat Watch and the Pinal dust advisory. ArboNET shows the Pinal mosquito anomaly. USGS shows the plague-positive at Bonito Park. AGFD shows the 47-prairie-dog die-off in Apache-Sitgreaves. *This is what ambient One Health surveillance looks like.*" |
| 2c | **Sign out → Click Healthcare → Human Health → Banner Phoenix** | Show institutional branded login | 0:30 | "Banner Health's own login. Six role tiles — Physician, Registrar, Triage Nurse, Discharge, Lab Tech, Administrator. Each tile lists the staff at that institution. Production: SMART-on-FHIR with each institution's identity provider." |
| 3a | **Sign in as Anthony Tsosie (registrar)** | Land on registration form | 0:30 | "Registrar's view: capture demographics, household, One Health consent. eMPI duplicate check runs on submit against the federation manifest." |
| 3b | **Type 'Maria Hernandez' + DOB → Run eMPI duplicate check** *(Phase 8)* | Show eMPI match found | 0:45 | "The federation found a possible match: Maria Hernandez at Banner Phoenix, household HH-AZ-PIMA-001, 95% match score. The registrar confirms with the patient before creating a duplicate record. *This is the duplicate-MRN problem solved at registration time.*" |
| 3c | **Click Triage Track Board → Open triage form for Carlos Hernandez** *(Phase 8)* | Capture vitals + ESI 3 | 0:45 | "Triage nurse captures vitals, refines chief complaint, assigns ESI 3 acuity. Click 'Hand off to clinician' — Carlos appears on Dr. Reyes's encounter screen with the triage block pre-loaded." |
| 4 | **Sign out → Sign in as Dr. Reyes (TMC physician)** | Land on Live Encounter | 0:30 | "Three input modes: Voice push-to-record, Keyboard, Template. Production: clinical-grade ASR via Nuance Dragon Medical One. Try the cocci workup template — it's pre-loaded with the ADHS reportable reminder." |
| 5 | Live Encounter | Click **Hernandez** scenario | 0:30 | "23 entities, mean confidence 0.87" |
| 6 | hover **valley fever** | Show tooltip | 0:15 | "SNOMED, ICD-10, phase, confidence — auditable." |
| 7 | Provider Workspace | Maria Hernandez selected | 0:45 | "**Patient list shows ~81 humans on Reyes's panel — Rocco the dog is not in it.** The cross-species pointer panel on the right surfaces the model's One Health signal without revealing the vet record." |
| 8 | Read aloud the **3-tier model pointer** | Tier 1 → Tier 2 → Tier 3 → provenance | 0:30 | "The medical signal is delivered. The protected record is not." |
| 9 | **Sign out** → Sign in as Dr. Cho (Tucson Companion-Animal Vet) | Show vet's animal-only panel | 0:30 | "Symmetric. Dr. Cho sees her 77 animals. The pointer for Rocco mentions a human household member with a related condition." |
| 10 | **Sign out** → Sign in as Dr. Nakamura (ADHS) | PH lands on Public Health Console | 0:15 | "Clinical Workspace hub button is *gone entirely*." |
| 11a | **Knowledge Graph** | Force-directed view | 0:15 | "2,188 nodes." |
| 11b | **Patient identity search: 'Hernandez'** *(Phase 8)* | Show 3-match panel + locate node | 0:45 | "Three Hernandez family members. Name, DOB, address, household — the same three identifiers HIPAA recognizes as the minimum verification set. Click 'Locate in graph' — the matching node pulses red and the viewport zooms in. Investigator-grade patient verification." |
| 12 | Sentinel Alerts | click **Pinal tick anomaly** | 0:30 | "27 standard deviations above baseline." |
| 13 | Evaluation | NER metrics + reliability | 0:30 | "F1 0.894 in 1.2 ms." |
| 14 | Risk Model → AI metrics | 3-model bake-off | 0:30 | "Gradient boosting AUROC 0.870, Brier 0.005." |
| 15 | Risk Model → Explainability | click Hernandez household | 0:45 | "SHAP attribution per prediction." |
| 16 | Risk Model → Public-health metrics | contact tracing + equity | 1:00 | "8.6-pp tribal-land AUC gap. Action items in the model card." |
| 17 | Model Card → Privacy & security | 4-layer stack + federated table | 1:00 | "Federated 0.900 vs centralized 0.826." |
| 18 | **Model Card → Federation** *(Phase 6)* | Click trigger button → wire log fills | 0:45 | "13 partner sites federated. ONE-HealthRecord is not the system of record — it's a federated consumer." |
| 19 | **Sign out → Dr. Anderson → Becker household** *(Phase 6)* | Show consent-declined panel | 0:30 | "Becker household declined cross-species linkage at intake. Architecture respects the decision." |
| 20a | **Sign in as Dr. Reyes → Maria Hernandez → ⚡ REPORT THIS CASE** *(Phase 7 — load-bearing)* | Click report button on Cocci condition | 0:30 | "Cocci is reportable to ADHS within one working day. The system already knows that. The button is right next to the diagnosis." |
| 20b | **Modal opens → tab through 3 destinations** *(Phase 7)* | Click each destination tab | 1:30 | "Three destinations. ADHS gets the HL7 v2.5.1 ELR with NNDSS condition code 11020. CDC NNDSS gets it forwarded automatically. Pima County Health gets a case-investigation queue entry. Each message machine-prepared. Each one is right there for me to inspect before I submit." |
| 20c | **Submit all → success panel** *(Phase 7)* | Click 'Submit all' button | 0:30 | "One click. Three destinations in parallel. Three acknowledgement IDs. Workflow time: four minutes. Compared to sixty minutes for the paper-and-fax workflow that today has a thirty-percent compliance rate. Every reportable disease in the ADHS R9-six-two-oh-two list — seventy-two of them — fires this exact workflow." |
| 21 | **Model Card → Audit log** *(PH user only)* | scroll the table | 0:30 | "Every login, navigation, federation fetch, CDS submission, reportable case submission, eMPI check, KG search. Surfaced to the user themselves — accountability control." |
| 22 | (slides only) | Phase 6 + Phase 7 + Phase 8 + synthetic + limitations + contributions + close | 2:00 | "FAIR by construction, role-aware, privacy-preserving, federated, closed-loop, multi-agency-reportable, three-domain-architecture, accountable." |

**Total spoken time: ~22:00.** Tighten by compressing 13–16 (Risk Model walkthrough) if you need 16:00. The Phase 8 additions (steps 2b, 2c, 3a–3c, 11b) are the load-bearing answer to "how does the system actually intake patients" — do not compress those.

---

## The "show that the audit really works" trick (kills any skepticism)

After signing in as a public-health user, **open the browser's JavaScript console** (F12 → Console tab) and type:

```javascript
document.querySelector('button[data-view="encounter"]').click()
```

Nothing visible happens. Now click **Model Card → Audit log** and scroll to the top of the table. You'll see:

> `2026-05-02 14:23:15Z · ph-adhs · public_health · view_access_denied · encounter`

That's the bypass attempt, recorded with timestamp, user_id, role, action, and target. **The audience watches the system catch them in real time.** This is the moment the lecturer's "but how do you really enforce it" question gets answered without words.

---

## If something breaks

- **Login screen doesn't appear.** Clear localStorage: open DevTools → Application → Local Storage → delete `onehr.session`. Reload. Login screen returns.
- **Already signed in from last test.** Click "Sign out" in the header strip; reload to reset to login screen.
- **Wrong patient list when you log in.** Confirm you clicked the right physician. Dr. Reyes = 245, Dr. Patel = 241, Dr. Yazzie = 23, Dr. Anderson = 96, Dr. Nakagawa = 167, Dr. Okafor = 202. If counts are wrong, regenerate `providers.json` with `python src/data_generation/assign_providers.py` and rebundle.
- **Cross-species pointer panel doesn't show.** It only renders when the household contains members of the *other* species. Try Maria Hernandez (Pima), Rachel Johnson (Pinal), Tom Patel (Yuma), or any household with a known animal case.
- **Audit log empty.** Click any tab to generate events. The log starts on first login.
- **Hub gating not working** (PH user sees Clinical button, etc.). Hard-refresh (Cmd+Shift+R or Ctrl+Shift+R) to bust JS cache.
- **Map tiles, D3 graphs blank.** Same Phase 1–3 fallbacks: refresh, or describe what would show.

---

## Lines that always land

- **The structural argument**: "The dictation is the source of truth. The structured record is no longer the lossy artifact."
- **The architecture argument**: "Each future-work row is a localised component swap, not an architectural rewrite."
- **The synthetic-data argument**: "Synthetic data is not a limitation. It's a feature. Reproducible from `seed=42`."
- **The AI argument**: "Gradient boosting AUROC 0.870, Brier 0.005, F1 0.696 — at 1.1 percent prevalence."
- **The equity argument**: "Tribal-land counties show an 8.6-percentage-point AUC gap that uniform metrics hide."
- **The federation argument** *(landed the lecturer's vote on slide 14)*: "Federated AUC 0.900 versus centralized 0.826 — the federation gain holds at scale, and **no patient record ever left a site**."
- **The MedGemma argument**: "We integrate MedGemma 4B and contribute the One Health-specific adaptation layer on top — species router, RAG, LoRA. We don't build the clinical LLM from scratch."
- **The role-gating argument** *(the lecturer's deepest concern)*: "Physicians don't see vet records. Vets don't see human records. Public health sees aggregates only. The model is the integration layer; it surfaces One Health *signal* without leaking the protected *record*."
- **The 3-tier pointer argument**: "Tier 1, signal exists. Tier 2, an animal in this household has a related condition. Tier 3, disease class only — name and species withheld by access policy. The medical signal is delivered. The protected record is not."
- **The defense-in-depth argument**: "UI hiding plus router-level rejection plus renderer-level refusal. In production, layer four — API enforcement at the FHIR server — is the only line that ultimately matters. The MVP demonstrates the policy intent; production wires the same logic to real auth."
- **The accountability argument**: "Architecture describes a system. A Model Card is accountable for it. Showing the audit surface to the user themselves is itself an accountability control."
- **The thesis line**: "FAIR by construction, role-aware, privacy-preserving, accountable."

---

## Questions you'll absolutely get

### Phase 1–3 (carryover)

1. **Why rule-based NLP?** → Deterministic explainability + no annotated corpus we can use without IRB. Rule layer survives in production as audit reference + fallback.
2. **Is F1 on synthetic data meaningful?** → Internal-consistency measurement. Doesn't predict MIMIC-IV / VetCompass performance.
3. **Why gradient boosting instead of deep learning?** → 1,366 encounters, 51 features. GBM wins at this scale. Plus TreeExplainer SHAP for free.
4. **Why is `day_of_year` your top SHAP feature?** → Synthetic outbreaks cluster in April 2026. Permutation importance re-ranks `cc_zoo_specific` first.
5. **Three positives in tribal-land — is the gap significant?** → Sample too small for significance, but large enough and consistent with documented disparities to warrant action.
6. **Contact-tracing precision is 80% — that's high. Is it real?** → Real PH yields 5–20% — the 80% number is unusually high because the synthetic-data positive/negative separation is cleaner than real-world. On real noisy data expect 15–30%. The architectural point is the 137-fold workload reduction (1,371 → 10 contacts) while keeping 100% sensitivity.
7. **Why swarm learning over federated learning?** → No universally-trusted aggregator exists across hospitals + vets + ADHS + tribal + USDA. SL replaces *organizational* trust with *cryptographic* trust.
8. **Federated AUC > centralized — that's suspicious.** → Small-data regularization effect. Two zero-positive sites lift from 0.500 → 0.772.
9. **Why MedGemma instead of building your own?** → Open-weights, multimodal. Our contribution is the *adaptation layer*.
10. **Layer A shipping, B and C scaffolded — what does that mean?** → A is end-to-end runnable; B has stable call signature returning empty; C has adapter selection but no trained weights.

### Phase 4 — login, role gating, redaction, audit

11. **A physician needs to see the vet record. Why can't they?** → Three reasons: legal (vet records are owned by the vet client, outside HIPAA), tribal sovereignty (CARE principles), and dual-use (anti-surveillance). The model delivers the *signal* without the *record* via the 3-tier pointer.
12. **What if the physician really needs the vet record?** → Phone the vet. Or ADHS brokers under public-health authority. The system makes the right path easier than the wrong path.
13. **How big are the patient panels?** → Real PCP sizes — 23 to 245 humans per physician (across 6 physicians), 22 to 159 animals per vet (across 4 vets). Generated by `assign_providers.py`.
14. **What stops a console-level UI bypass?** → Defense in depth. UI hiding, router-level rejection in `activateTab`, renderer-level refusal in `VIEW_INIT.workspace`. Audit log records the attempt.
15. **How do I show the audit really works?** → After signing in as PH, run `document.querySelector('button[data-view="encounter"]').click()` in the JS console. Nothing happens visually. Then click Model Card → Audit log: `view_access_denied · encounter` is at the top with timestamp.
16. **This is just localStorage. It isn't real security.** → Correct, and we say so on the login screen and in the model card caveats. The MVP demonstrates the *policy*; production wires the same logic to a real FHIR server with SMART-on-FHIR + ADHS SSO + tribal-IRB credentials. The architectural decisions transfer; the auth implementation does not.
17. **Why three tiers in the model pointer instead of one?** → Each tier carries different medical value. T1 = act on the signal. T2 = consider household-level prophylaxis. T3 = differential diagnosis. A single message would either over-share or under-share.

Full Q&A bank in `docs/presenter_script.md`. Model card in `docs/model_card.md`. Phase-4 specifics in `docs/model_card.md` §4D.

### Phase 6 — federation, eMPI, consent, closed-loop CDS

- **Q: Are these real partner FHIR endpoints?** No — the partner sites are simulated. Each shadow store is in-browser JSON. The federation client (`app/federation.js`) simulates network calls with realistic latency. **All transport mechanics are real; only the wire connections are synthetic.** Production swaps the simulated transport for real HTTPS calls to actual partner FHIR servers.

- **Q: Are the NNDSS submissions actually going to ADHS?** No. The HL7 v2.5.1 ELR messages are well-formed and would parse correctly at ADHS-MEDSIS, but the destination in this MVP is a stub. Generator at `src/cds/nndss_message.py` — every segment present (MSH, SFT, PID, PV1, ORC, OBR, OBX, SPM, NTE), correct CDC NNDSS condition code, CLIA-formatted facility identifier. Real submission requires production credentials.

- **Q: Why only 3 auto-linked eMPI matches?** Hard rule: requires DOB ≥ 0.99 AND last-name ≥ 0.85 to auto-link, regardless of combined score. This matches NextGate / Verato production behavior. The 2,857 clerical-review pairs are ambiguous cases — surname-collisions sharing a county FIPS — that need human review. **High clerical-review count is a feature, not a bug.**

- **Q: What about households that change consent over time?** FHIR Consent has `status: active | inactive`. Toggling `inactive` immediately suppresses the cross-species pointer (the renderer checks `Consent.status` on every render). Production: toggle is also pushed to participating sites' consent stores; the audit log records every change. We do not modify clinical records — only the linkage signal.

- **Q: The Diné and Apache handouts are placeholders. Why not use an LLM to translate?** Generating medical content in Indigenous languages without fluent medical-translator review carries real clinical-harm risk and real cultural-disrespect risk. The architecture supports the language; the process for filling the slot is itself the work. The placeholder names three concrete tribal-translation contacts. **The placeholder is a feature, not a gap.**

### Phase 8 — three-domain architecture, intake/triage, encounter inputs, KG search, env surveillance

- **Q: Why three domains at the top?** Because that's the One Health triad. Humans, animals, environment. The previous flat login conflated them. The new structure surfaces the architectural reality: Banner Health is its own institution with its own SSO, ADHS is a separate authority, and EPA AirNow is a public API. The three domains are peers, not nested.

- **Q: Are these real institutional logos?** Banner orange and TMC navy are matched to real brand colors. The "B" and "TMC" lockup tiles are stand-ins for the real logos — production deployment with each institution's blessing would license the real marks. The MVP demonstrates the visual segregation pattern.

- **Q: Why both eMPI on registration AND eMPI on the federation?** Same matcher, two entry points. At registration time, the registrar runs eMPI before creating a record (preventing duplicate MRNs). Across the federation, eMPI runs to link the same patient across partner sites (Maria Hernandez at Banner Phoenix = M Hernandez at TMC = same person). Both use Fellegi-Sunter scoring.

- **Q: What if Web Speech API doesn't work on the demo laptop?** The voice tab gracefully degrades — if `window.SpeechRecognition` is undefined, the button shows a message directing to Keyboard or Template input. No crash, no silent failure. Safari has partial support; Firefox falls back. Chrome and Edge work in 100% of testing.

- **Q: ESI 1-5 — is that really the standard?** Yes, ESI (Emergency Severity Index) is the canonical US ED triage scale, developed by AHRQ. Level 1 is resuscitation (immediate physician), Level 5 is non-urgent. It's used at roughly 80% of US emergency departments. Implementing it correctly here matters for credibility with clinical reviewers.

- **Q: Are the EPA AirNow values real-time?** No, they're synthetic and seeded for reproducibility. The data ranges are calibrated to real Arizona PM2.5 distributions (Maricopa baselines 8-15 µg/m³, northern stations 3-8 µg/m³). The architecture demonstrates the integration pattern; production swaps in `https://docs.airnowapi.org/` as a live source.

- **Q: Why does Pinal show a 27σ mosquito anomaly in the demo?** Because that's the cluster signal that drives the West Nile alert in our Phase 2-7 demos. Phase 8 surfaces it as ambient context in the Environmental Surveillance dashboard — public health investigators, clinicians, and even non-authenticated visitors can see the same signal from their respective surfaces. The single signal lights up across all three domains.

- **Q: The KG search uses name + DOB + address — why those three?** They're the minimum patient verification set HIPAA recognizes for identity confirmation. They're also what every front-desk registrar reads aloud to the patient before pulling up their chart. The MVP's search bar mirrors that practice exactly.

---

### Phase 7 — comprehensive reportable disease coverage

- **Q: Where does the disease list come from?** Four authoritative sources, all cited in the database file: ADHS R9-6-202 (effective 2025-06-02), CDC NNDSS, USDA APHIS NLRAD, and the AZ ADA + AGFD veterinarian reporting requirements. 72 diseases total. The compilation date is timestamped; production deployment requires either an API ingestion of the live lists or an annual re-pull.

- **Q: What about diseases on the federal NNDSS list that aren't on the AZ list?** The database is AZ-first by design — every entry is on the ADHS list, and the federal/animal cross-references are added on top. A Wisconsin or Oregon deployment would extend the database with state-specific additions; the schema supports this without code changes.

- **Q: Who decides which destinations a case fans out to?** The disease database itself. Each disease has `human_reporting.destinations` and `animal_reporting.destinations` arrays that enumerate which agencies need this disease for this species. The clinician doesn't decide; the rule decides; the clinician inspects and submits.

- **Q: 234 cases on 970 humans is much higher than real AZ rates. Why?** Calibrated for demo visibility — this is documented in `data/synthetic/reportable_cases.json` `_caveat` field. Real AZ rates would put valley fever closer to 1.7 cases per 1,000 humans per year and most rare diseases at zero in a 970-person sample. The demo dataset is modestly inflated above population-proportional rates so every reportable timeline class (immediate / one-day / five-day / outbreak) has visible cases on screen.

- **Q: Why isn't auto-submit the default?** Three reasons. (1) Reportable disease law in AZ and federally places the obligation on the clinician, not on the EHR — auto-submission would shift legal responsibility in a way that requires regulatory approval. (2) The cross-species signal that triggers the report is a model output; until the model has accumulated real reporting decisions, clinician review is the false-positive filter. (3) Sensitive subjects (HIV in infants, congenital syphilis, TB in children, mpox) have disclosure constraints that need human judgment. **Future direction**: graduated auto-submit for low-ambiguity cases as the model accumulates training data — same evolution radiology AI took.

- **Q: What's the headline?** Sixty minutes of paper-and-fax becomes four minutes of one-click. Thirty-percent compliance becomes eighty-five-percent target. Five thousand additional valley fever cases per year captured by surveillance that today are silently lost. **Closing the reporting loop is the highest-leverage public-health intervention in the system.**

---

### Phase 6 — federation, eMPI, consent, closed-loop CDS

- **Q: Are these real partner FHIR endpoints?** No — the partner sites are simulated. Each shadow store is in-browser JSON. The federation client (`app/federation.js`) simulates network calls with realistic latency. **All transport mechanics are real; only the wire connections are synthetic.** Production swaps the simulated transport for real HTTPS calls to actual partner FHIR servers.

- **Q: Are the NNDSS submissions actually going to ADHS?** No. The HL7 v2.5.1 ELR messages are well-formed and would parse correctly at ADHS-MEDSIS, but the destination in this MVP is a stub. Generator at `src/cds/nndss_message.py` — every segment present (MSH, SFT, PID, PV1, ORC, OBR, OBX, SPM, NTE), correct CDC NNDSS condition code, CLIA-formatted facility identifier. Real submission requires production credentials.

- **Q: Why only 3 auto-linked eMPI matches?** Hard rule: requires DOB ≥ 0.99 AND last-name ≥ 0.85 to auto-link, regardless of combined score. This matches NextGate / Verato production behavior. The 2,857 clerical-review pairs are ambiguous cases — surname-collisions sharing a county FIPS — that need human review. **High clerical-review count is a feature, not a bug.**

- **Q: What about households that change consent over time?** FHIR Consent has `status: active | inactive`. Toggling `inactive` immediately suppresses the cross-species pointer (the renderer checks `Consent.status` on every render). Production: toggle is also pushed to participating sites' consent stores; the audit log records every change. We do not modify clinical records — only the linkage signal.

- **Q: The Diné and Apache handouts are placeholders. Why not use an LLM to translate?** Generating medical content in Indigenous languages without fluent medical-translator review carries real clinical-harm risk and real cultural-disrespect risk. The architecture supports the language; the process for filling the slot is itself the work. The placeholder names three concrete tribal-translation contacts. **The placeholder is a feature, not a gap.**

---

## Last-minute confidence checks

If the lecturer asks: *"How do you ensure a physician can't see the vet record?"* → Three things, in this order: **(a)** Show the model pointer panel on slide 16 / in Maria's chart. **(b)** Quote the 3-tier message verbatim. **(c)** Demo the audit-log bypass-attempt trick.

If asked the headline numbers to remember:
- **AI side:** ***"Gradient boosting AUROC 0.910, Brier 0.0059, on 4,676 encounters at 0.4% prevalence."***
- **PH side:** ***"100% sensitivity at threshold 0.20, 80% precision at 0.50, 71-day lead time on Hernandez."***
- **Privacy side:** ***"Federated AUC 0.900, centralized 0.826. Federation gain holds at scale."***
- **Access-control side:** ***"Three roles, three views. Patient panels 38–130 humans, 30–40 animals. Defense in depth across UI, router, and renderer. Audit log surfaced to the user themselves."***
- **Architecture side:** ***"Two role-based hubs, MedGemma + species router, four-layer privacy stack, three-tier model pointer, live Model Card. Every choice maps to a piece of the lecturer's feedback."***

You've got this.
