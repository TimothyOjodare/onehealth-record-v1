# Video Walkthrough Script

**Target length:** 8–10 minutes.
**Format:** Screen recording with voice-over. No camera, no live face.
**Recording tool suggestions:** macOS QuickTime (free), Loom (free tier sufficient), OBS Studio (free, more control).
**Resolution:** 1920×1080 minimum. If your laptop is 16:10, record the full screen at native resolution and let the host scale.

This script mirrors the in-person presenter script but is written for an asynchronous audience that can pause, rewind, and watch at 1.5x. Sentences are slightly shorter; the pacing is tighter; clicks are explicit.

Open `app/index.html` in a maximized browser window before you hit record. Have `docs/ONE-HealthRecord_Capstone.pdf` open in a second tab so you can flip to slides for context.

---

## 0:00 – 0:30 — Title and framing

> **Hi. This is ONE-HealthRecord — a capstone project that takes clinician and veterinarian dictation and turns it into a structured, FAIR, One Health electronic health record in real time.**
>
> **Everything you're about to see runs in a browser, with no installation, on synthetic data. Let me walk you through it.**

*[Cut from the title slide of the deck to the browser app.]*

---

## 0:30 – 1:30 — The Encounter tab and the Hernandez scenario

*[Click the Hernandez clinician scenario.]*

> **This is the live encounter view. I just clicked a pre-baked scenario: Maria Hernandez, 52, in Tucson, three weeks of cough, exposure to wind-blown soil dust during yard work. And — this is the One Health detail — her family dog Rocco was diagnosed with Valley Fever last week by their vet.**
>
> **Watch the right panel. The engine just produced a FHIR R4 bundle. 23 entities, mean confidence 0.87. The colored highlights are the entity types — red conditions, blue symptoms, green vitals, amber medications, brown exposures.**

*[Hover over "valley fever".]*

> **Hover any phrase and you see the SNOMED code, the ICD-10 code, the source phase, and the confidence. Every structured field is auditable back to the words that produced it.**

---

## 1:30 – 2:30 — Provider Workspace, clinician's view

*[Click the Provider Workspace tab.]*

> **This is the screen a clinician would actually use. A patient list on the left, filterable by role — clinician, vet, or both. Patients in households with active alerts surface first. Notice the cardinal-red dot.**
>
> *[Select Maria.]*
>
> **The chart shows Maria's active conditions — Valley Fever onset 14 days ago, confidence 0.93. Her chronic conditions, her active medications, a BP trend, and her encounter timeline.**
>
> **The right column is the One Health context. There's an active cross-species cluster alert. The household members include Maria, Carlos, Sofia, **and Rocco the dog**. County-level disease trends from the synthetic ADHS feed.**
>
> **A clinician seeing Maria already sees the dog. They didn't have to look anywhere else.**

---

## 2:30 – 3:15 — Provider Workspace, vet's view

*[Switch the role filter to Vet. Click vet_rocco scenario in the Encounter tab to populate Rocco's record, then return to workspace.]*

> **Now the same workspace, filtered to vet patients. Same household graph. Rocco's chart shows his Valley Fever diagnosis, his medications, his vet encounter timeline.**
>
> **And the right column shows Maria's case, flagged with the cross-species link. Same alert, same household graph, just a different point of care.**
>
> **This is what "One Health by default" means in practice. The cross-species link is not a special feature. It's the default behavior of the system.**

---

## 3:15 – 4:00 — Knowledge graph

*[Click the Knowledge Graph tab.]*

> **694 nodes. 680 edges. Households, people, animals, diseases, counties, exposures — all linked.**
>
> *[Drag the Hernandez node.]*
>
> **The dashed cardinal-red edges are cross-species links. Same SNOMED root code, different terminology editions. Twelve zoonotic diseases are modelled across 120 households: Valley Fever, ehrlichiosis, RMSF, leptospirosis, hantavirus, plague, West Nile, rabies, Q fever, psittacosis, tularemia, salmonellosis.**
>
> **In production this becomes Neo4j, and a heterogeneous graph neural network handles cases where the SNOMED codes disagree but the underlying biology is the same.**

---

## 4:00 – 5:00 — Sentinel surveillance, the Pinal anomaly

*[Click the Sentinel Alerts tab.]*

> **The sentinel engine fires twelve alerts on this synthetic dataset. The headline one is at the top.**
>
> *[Click the Pinal vector anomaly alert.]*
>
> **27.2 standard deviations above baseline tick burden in Pinal County, last four weeks against a 22-week baseline. p less than 0.001. The chart shows the spike clearly.**
>
> **Below the chart you can see the differential privacy disclosure. The true count stays internal. The Laplace-noised count, at epsilon equals 1.0, is what would be released to public-facing dashboards.**
>
> **And here's the One Health link: when this alert fires, the disposition of every ehrlichiosis or RMSF presentation in Pinal County is upgraded to elevated risk. A clinician seeing a feverish patient from Casa Grande sees that risk in real time, in the Provider Workspace. They don't have to remember to check a public-health website.**

---

## 5:00 – 6:00 — Hand-back UI

*[Click the Encounter tab. Open a scenario with low-confidence extractions — try the ESRD scenario.]*

> **Machine-authored doesn't mean clinician-bypassed. Watch the dictation panel.**
>
> **Any extraction with confidence below 0.75 is highlighted in amber. There's a banner at the top showing how many low-confidence items are pending review.**
>
> *[Click an amber span.]*
>
> **A clinician can confirm, reject, or edit any one of these. A confirmed extraction is stamped onto the FHIR Provenance with the reviewer ID. A rejected extraction is removed from the bundle but retained in the audit log.**
>
> **Decisions persist locally — per text, per span, per kind — so the demo remembers what you confirmed across page reloads. In production this becomes a Provenance.entity audit record.**

---

## 6:00 – 7:30 — Evaluation tab

*[Click the Evaluation tab.]*

> **Synthetic gold-standard. 25 dictations. 138 entity annotations. Four entity kinds — vital signs, symptoms, conditions, medications.**
>
> **Overall: precision 0.904, recall 0.884, F1 0.894. Median end-to-end runtime: 1.2 milliseconds per encounter on a CPU-only laptop.**
>
> **Per kind: vitals and medications are effectively solved — F1 1.0 — because they're regex-driven and RxNorm-mapped. The error budget concentrates on conditions and symptoms — F1 0.79 and 0.76. Surface-form overlap, hedge handling, multi-word boundaries. These are exactly the cases a fine-tuned BioClinicalBERT will help with most.**
>
> **The reliability diagram is the story. Predictions in the 0.70 to 0.80 confidence bucket are correct 71% of the time. The 0.80 to 0.90 bucket: 92%. The 0.90 and up bucket: essentially 100%. The model is well-calibrated. That's what makes the 0.75 hand-back threshold a principled choice, not a guess.**

---

## 7:30 – 8:30 — On synthetic data + future work

*[Flip to slide 11 of the deck — On Synthetic Data.]*

> **A note on the data. Everything you just saw is synthetic. No protected health information. No real Arizona resident represented. This is a strength, not a limitation.**
>
> **It's reproducible. The entire bundle — 120 households, 1,366 encounters, 12 alerts — regenerates from `seed=42`. No data-use agreement, no IRB friction, no version skew.**
>
> **It's edge-case-friendly. I planted a 27-sigma tick anomaly in Pinal because I knew the ground truth. Real data doesn't let you do that for free.**
>
> *[Flip to slide 12 — Limitations and Future Work.]*
>
> **The future-work list is concrete and addressable. BioClinicalBERT for NER. Neo4j and a GNN for the graph. A variational autoencoder for anomaly detection. MIMIC-IV plus VetCompass for real-data evaluation. Whisper plus dialogue segmentation for audio dictation. Full DP-SGD for formal privacy.**
>
> **Each of these is a component swap, not an architectural rewrite. The interfaces, schemas, evaluation harness, and FHIR profile are already in place.**

---

## 8:30 – 9:00 — Close

*[Flip to slide 14 — Thank you.]*

> **To close — three sentences.**
>
> **The structured record is no longer the lossy artifact. The dictation is the source of truth. And One Health follows automatically when the schema is shared.**
>
> **The repository contains the model card, the evaluation report, and full source. Everything is reproducible from `seed=42`. Thank you.**

*[Stop recording.]*

---

## Editing notes

- **Trim aggressively.** Aim for the final cut to be under 9 minutes. Anything over 10 minutes loses asynchronous viewers.
- **Cut click-latency.** When the engine takes a beat to render a graph, cut that beat out in post unless you're explicitly highlighting runtime.
- **Burn captions.** The committee may watch on mute. Even auto-generated captions are better than none.
- **No background music.** It distracts from the numbers, which are the substance.
- **Export at 1080p H.264.** That's the lowest common denominator for committee laptops.

## File handoff

When done, the deliverable is a single video file. Suggested name:

```
ONE-HealthRecord_walkthrough_v1.mp4
```

Drop it into the repo at `docs/walkthrough.mp4` (gitignore-d if large) and link from `README.md`.
