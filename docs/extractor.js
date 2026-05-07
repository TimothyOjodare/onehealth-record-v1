/* ============================================================================
   ONE-HealthRecord — Browser-side NLP pipeline
   ----------------------------------------------------------------------------
   This is a JavaScript port of src/nlp/dictation_parser.py + entity_extractor.py
   + fhir_builder.py, allowing live in-browser demonstration of dictation →
   structured FHIR. The Python version remains the canonical implementation;
   they are kept logically equivalent.
   ========================================================================== */

(function () {
    "use strict";

    // ----------------------------------------------------------------------
    // Phase headers (high confidence) and topical heuristics (lower confidence)
    // ----------------------------------------------------------------------
    const PHASE_HEADERS = [
        ["CC",  /\b(chief complaint|cc|presenting complaint|presents (?:with|today))\b/i],
        ["HPI", /\b(history of present illness|hpi|present illness)\b/i],
        ["PMH", /\b(past medical history|pmh|medical history)\b/i],
        ["ROS", /\b(review of systems|ros)\b/i],
        ["PE",  /\b(physical exam(?:ination)?|on examination|on exam|exam findings|vital signs|vitals)\b/i],
        ["LAB", /\b(laboratory|labs?|investigations?|diagnostics?|imaging)\b/i],
        ["A",   /\b(assessment|impression|differential|working diagnosis)\b/i],
        ["P",   /\b(plan|management|treatment|disposition|recommendations)\b/i],
        ["EXP", /\b(exposure(?:s)? history|exposures?|environmental history|household exposures?|recent travel|animal contact|tick exposure|rodent exposure)\b/i],
    ];
    const TOPIC_HEUR = [
        ["CC",  /\b(presents?|came in|brought in|seen for|here for|c\/o|complains? of)\b/i],
        ["HPI", /\b(\d+\s*(day|week|month|year)s? ago|since|started|began|onset|times? (one|two|three|four|five|\d+))\b/i],
        ["PMH", /\b(history of|h\/o|known|chronic|long-?standing)\b/i],
        ["PE",  /\b(\bbp\b|\bhr\b|\brr\b|\btemp\b|\bspo2\b|auscult|palpation|tender|edema|rash|murmur)\b/i],
        ["EXP", /\b(dog|cat|pet|tick|rodent|mouse|mice|hike|garden(ing)?|canal|farm|outdoor)\b/i],
        ["A",   /\b(suspect|consistent with|likely|probable|consider(?:ed)?|differential includes|rule out|r\/o)\b/i],
        ["P",   /\b(start|prescrib|order|admit|discharge|follow[- ]up|f\/u|return|recheck|refer)\b/i],
    ];

    function splitSentences(text) {
        const cleaned = text.replace(/\s+/g, " ").trim();
        const re = /[^.!?]+[.!?]?/g;
        const out = [];
        let m;
        while ((m = re.exec(cleaned)) !== null) {
            const s = m[0].trim();
            if (!s) continue;
            const start = m.index;
            out.push({ text: s, char_start: start, char_end: start + m[0].length });
        }
        return out;
    }

    function classifySentence(text, current) {
        for (const [label, pat] of PHASE_HEADERS) {
            const m = pat.exec(text);
            if (m) return { phase: label, evidence: "header:" + m[0], confidence: 0.95 };
        }
        for (const [label, pat] of TOPIC_HEUR) {
            const m = pat.exec(text);
            if (m) return { phase: label, evidence: "topical:" + m[0], confidence: 0.65 };
        }
        return { phase: current, evidence: "inherited", confidence: 0.4 };
    }

    function parseDictation(text) {
        const sents = splitSentences(text);
        let current = "CC";
        const out = [];
        for (let i = 0; i < sents.length; i++) {
            const c = classifySentence(sents[i].text, current);
            if (i === 0 && c.confidence < 0.5) {
                c.phase = "CC"; c.evidence = "default:first-sentence"; c.confidence = 0.55;
            }
            current = c.phase;
            out.push(Object.assign({}, sents[i], c));
        }
        return { raw_text: text, sentences: out };
    }

    // ----------------------------------------------------------------------
    // Lexicon + extractors
    // ----------------------------------------------------------------------
    function buildLexicons(terms) {
        // Conditions (human) — display + parenthetical-stripped + abbreviations.
        const cond = {};
        const addCond = (k, e) => { if (!cond[k.toLowerCase()]) cond[k.toLowerCase()] = e; };
        for (const c of terms.conditions_human) {
            addCond(c.display, c);
            const m = /^(.+?)\s*\(([^)]+)\)\s*$/.exec(c.display);
            if (m) { addCond(m[1].trim(), c); addCond(m[2].trim(), c); }
        }
        const condAbbrev = {
            "cocci": "Coccidioidomycosis", "rmsf": "Rocky Mountain spotted fever",
            "hps": "Hantavirus pulmonary syndrome", "hantavirus": "Hantavirus pulmonary syndrome",
            "lepto": "Leptospirosis", "htn": "Essential hypertension",
            "hypertension": "Essential hypertension", "hypertensive": "Essential hypertension",
            "dm": "Type 2 diabetes mellitus", "dm2": "Type 2 diabetes mellitus",
            "type 2 diabetes": "Type 2 diabetes mellitus", "diabetic": "Type 2 diabetes mellitus",
            "diabetes": "Type 2 diabetes mellitus", "esrd": "End-stage renal disease",
            "end-stage renal disease": "End-stage renal disease",
            "copd": "Chronic obstructive pulmonary disease",
        };
        for (const [k, target] of Object.entries(condAbbrev)) {
            const match = terms.conditions_human.find(c => c.display.toLowerCase().startsWith(target.toLowerCase()));
            if (match) addCond(k, match);
        }

        // Symptoms.
        const sym = {};
        for (const s of terms.symptoms_human) sym[s.display.toLowerCase()] = s;
        const symAbbrev = {
            "sob": "Dyspnea", "shortness of breath": "Dyspnea", "difficulty breathing": "Dyspnea",
            "fever": "Fever", "febrile": "Fever", "cough": "Cough",
            "headache": "Headache", "h/a": "Headache", "fatigue": "Fatigue",
            "tired": "Fatigue", "rash": "Skin rash", "diarrhea": "Diarrhea",
            "joint pain": "Joint pain", "myalgia": "Joint pain",
            "edema": "Edema (lower extremity)", "swelling": "Edema (lower extremity)",
            "leg swelling": "Edema (lower extremity)",
        };
        for (const [k, target] of Object.entries(symAbbrev)) {
            const match = terms.symptoms_human.find(s => s.display === target);
            if (match) sym[k] = match;
        }

        // Medications: index by first word and full display.
        const meds = {};
        for (const m of terms.medications) {
            meds[m.display.split(" ")[0].toLowerCase()] = m;
            meds[m.display.toLowerCase()] = m;
        }
        return { cond, sym, meds };
    }

    // Demographics regex.
    const AGE_PATS = [
        /\b(\d{1,3})[ -]year[ -]old\b/i, /\b(\d{1,3})\s*y\/?o\b/i, /\b(\d{1,3})\s*yr\b/i
    ];
    const AGE_WORDS = { twenty:20, thirty:30, forty:40, fifty:50, sixty:60, seventy:70, eighty:80, ninety:90 };
    const NUM_ONES = { one:1, two:2, three:3, four:4, five:5, six:6, seven:7, eight:8, nine:9 };
    const AGE_WORDED_RE = /\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s-]?(one|two|three|four|five|six|seven|eight|nine)?[\s-]year[\s-]old\b/gi;
    const SEX_M = /\b(male|man|gentleman|m\/)\b/gi;
    const SEX_F = /\b(female|woman|lady|f\/)\b/gi;

    const VITAL_PATS = {
        blood_pressure:   /\bBP\s*[:= ]?\s*(\d{2,3})\s*\/\s*(\d{2,3})\b/gi,
        heart_rate:       /\bHR\s*[:= ]?\s*(\d{2,3})\b/gi,
        respiratory_rate: /\bRR\s*[:= ]?\s*(\d{1,3})\b/gi,
        temperature_f:    /\b(?:T|Temp|Temperature)\s*[:= ]?\s*(\d{2,3}(?:\.\d)?)\s*(?:F|°F)?\b/gi,
        spo2:             /\bSpO2\s*[:= ]?\s*(\d{1,3})\s*%?\b/gi,
    };
    const DURATION_RE = /\b(?:for|since|times?|x)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(day|week|month|year)s?\b/gi;
    const EXPOSURE_PATS = {
        tick_exposure:    /\btick(?:s|\sbite|\sexposure|\sattached|\sembedded)?\b/gi,
        rodent_exposure:  /\b(rodent|mouse|mice|rat\b|rat\s)\b/gi,
        dog_exposure:     /\b(dog|canine|puppy)\b/gi,
        cat_exposure:     /\b(cat|feline|kitten)\b/gi,
        soil_dust:        /\b(dust\sstorm|soil\sdust|excavation|dust\sexposure|gardening)\b/gi,
        freshwater:       /\b(canal|pond|lake\sswim|stream|river\sswim|freshwater)\b/gi,
        outdoor_activity: /\b(hike|hiking|camp|camping|outdoor)\b/gi,
    };
    const NEG_CUES = ["no", "denies", "denied", "not", "without", "absent"];
    const NEG_MULTI = ["negative for", "free of"];
    const HEDGE_CUES = ["possible", "probable", "suspected", "consider", "likely"];
    const HEDGE_MULTI = ["rule out", "r/o", "differential includes", "suggestive of", "consistent with"];

    function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

    function precedingTokens(text, start, n, minOff) {
        const pre = text.substring(minOff || 0, start).toLowerCase();
        const toks = pre.match(/\b[\w/]+\b/g) || [];
        return toks.slice(-n);
    }
    function isNegated(text, start, sentStart) {
        const win = precedingTokens(text, start, 5, sentStart);
        if (win.some(t => NEG_CUES.includes(t))) return true;
        const joined = win.join(" ");
        return NEG_MULTI.some(c => joined.includes(c));
    }
    function isHedged(text, start, sentStart) {
        const win = precedingTokens(text, start, 6, sentStart);
        if (win.some(t => HEDGE_CUES.includes(t))) return true;
        const joined = win.join(" ");
        return HEDGE_MULTI.some(c => joined.includes(c));
    }

    function sentenceStart(parsed, off) {
        for (const s of parsed.sentences) {
            if (s.char_start <= off && off < s.char_end) return s.char_start;
        }
        return 0;
    }
    function phaseFor(parsed, off) {
        for (const s of parsed.sentences) {
            if (s.char_start <= off && off < s.char_end) return s.phase;
        }
        return "UNKNOWN";
    }

    function extractDemographics(text, parsed) {
        const out = [];
        let m;
        // Worded ages first.
        const wre = new RegExp(AGE_WORDED_RE.source, AGE_WORDED_RE.flags);
        while ((m = wre.exec(text)) !== null) {
            const tens = AGE_WORDS[m[1].toLowerCase()] || 0;
            const ones = NUM_ONES[(m[2] || "").toLowerCase()] || 0;
            const age = tens + ones;
            if (age) out.push({
                kind: "Demographic", text: m[0],
                char_start: m.index, char_end: m.index + m[0].length,
                attributes: { age_years: age }, codes: [],
                negated: false, uncertain: false,
                phase: phaseFor(parsed, m.index), confidence: 0.95,
            });
        }
        for (const pat of AGE_PATS) {
            const re2 = new RegExp(pat.source, pat.flags + "g");
            while ((m = re2.exec(text)) !== null) {
                if (out.some(e => e.kind === "Demographic" && e.char_start <= m.index && m.index < e.char_end)) continue;
                out.push({
                    kind: "Demographic", text: m[0],
                    char_start: m.index, char_end: m.index + m[0].length,
                    attributes: { age_years: parseInt(m[1], 10) }, codes: [],
                    negated: false, uncertain: false,
                    phase: phaseFor(parsed, m.index), confidence: 0.97,
                });
            }
        }
        const mm = SEX_M.exec(text);
        if (mm) {
            out.push({ kind: "Demographic", text: mm[0],
                char_start: mm.index, char_end: mm.index + mm[0].length,
                attributes: { gender: "male" }, codes: [], negated: false, uncertain: false,
                phase: phaseFor(parsed, mm.index), confidence: 0.90 });
        }
        SEX_M.lastIndex = 0;
        const mf = SEX_F.exec(text);
        if (mf) {
            out.push({ kind: "Demographic", text: mf[0],
                char_start: mf.index, char_end: mf.index + mf[0].length,
                attributes: { gender: "female" }, codes: [], negated: false, uncertain: false,
                phase: phaseFor(parsed, mf.index), confidence: 0.90 });
        }
        SEX_F.lastIndex = 0;
        return out;
    }

    function extractVitals(text, parsed) {
        const out = [];
        for (const [vname, pat] of Object.entries(VITAL_PATS)) {
            const re = new RegExp(pat.source, pat.flags);
            let m;
            while ((m = re.exec(text)) !== null) {
                const attrs = { vital_type: vname };
                if (vname === "blood_pressure") {
                    attrs.systolic = parseInt(m[1], 10);
                    attrs.diastolic = parseInt(m[2], 10);
                    attrs.unit = "mmHg";
                } else {
                    attrs.value = parseFloat(m[1]);
                    attrs.unit = ({ heart_rate: "bpm", respiratory_rate: "/min",
                                    temperature_f: "F", spo2: "%" })[vname];
                }
                out.push({
                    kind: "Vital", text: m[0],
                    char_start: m.index, char_end: m.index + m[0].length,
                    attributes: attrs, codes: [],
                    negated: false, uncertain: false,
                    phase: phaseFor(parsed, m.index), confidence: 0.97,
                });
            }
        }
        return out;
    }

    function extractDurations(text, parsed) {
        const out = [];
        const wordToN = Object.assign({}, NUM_ONES, { ten: 10 });
        const re = new RegExp(DURATION_RE.source, DURATION_RE.flags);
        let m;
        while ((m = re.exec(text)) !== null) {
            const raw = m[1].toLowerCase();
            const n = /^\d+$/.test(raw) ? parseInt(raw, 10) : (wordToN[raw] || 0);
            const unit = m[2].toLowerCase();
            const days = n * ({ day:1, week:7, month:30, year:365 })[unit];
            out.push({
                kind: "Duration", text: m[0],
                char_start: m.index, char_end: m.index + m[0].length,
                attributes: { value: n, unit, approx_days: days }, codes: [],
                negated: false, uncertain: false,
                phase: phaseFor(parsed, m.index), confidence: 0.85,
            });
        }
        return out;
    }

    function extractExposures(text, parsed) {
        const out = [];
        for (const [exp, pat] of Object.entries(EXPOSURE_PATS)) {
            const re = new RegExp(pat.source, pat.flags);
            let m;
            while ((m = re.exec(text)) !== null) {
                const sStart = sentenceStart(parsed, m.index);
                out.push({
                    kind: "Exposure", text: m[0],
                    char_start: m.index, char_end: m.index + m[0].length,
                    attributes: { exposure_type: exp }, codes: [],
                    negated: isNegated(text, m.index, sStart),
                    uncertain: isHedged(text, m.index, sStart),
                    phase: phaseFor(parsed, m.index), confidence: 0.75,
                });
            }
        }
        return out;
    }

    function extractLexicon(text, parsed, lex, kind, codeKeys) {
        const out = [];
        const consumed = [];
        const phrases = Object.keys(lex).sort((a, b) => b.length - a.length);
        for (const phrase of phrases) {
            const re = new RegExp("\\b" + escapeRe(phrase) + "\\b", "gi");
            let m;
            while ((m = re.exec(text)) !== null) {
                if (consumed.some(([s, e]) => (s <= m.index && m.index < e) || (s < m.index + m[0].length && m.index + m[0].length <= e))) continue;
                consumed.push([m.index, m.index + m[0].length]);
                const entry = lex[phrase];
                const codes = [];
                for (const k of codeKeys) {
                    if (k === "snomed" && entry.snomed) codes.push({ system: "http://snomed.info/sct", code: entry.snomed, display: entry.display });
                    else if (k === "icd10" && entry.icd10) codes.push({ system: "http://hl7.org/fhir/sid/icd-10-cm", code: entry.icd10, display: entry.display });
                    else if (k === "loinc" && entry.loinc) codes.push({ system: "http://loinc.org", code: entry.loinc, display: entry.display });
                    else if (k === "rxnorm" && entry.rxnorm) codes.push({ system: "http://www.nlm.nih.gov/research/umls/rxnorm", code: entry.rxnorm, display: entry.display });
                }
                const sStart = sentenceStart(parsed, m.index);
                out.push({
                    kind, text: m[0],
                    char_start: m.index, char_end: m.index + m[0].length,
                    codes, attributes: { display: entry.display },
                    negated: isNegated(text, m.index, sStart),
                    uncertain: isHedged(text, m.index, sStart),
                    phase: phaseFor(parsed, m.index),
                    confidence: phrase.length > 6 ? 0.88 : 0.78,
                });
            }
        }
        return out;
    }

    function extractEntities(text, terms) {
        const lex = buildLexicons(terms);
        const parsed = parseDictation(text);
        const ents = []
            .concat(extractDemographics(text, parsed))
            .concat(extractVitals(text, parsed))
            .concat(extractDurations(text, parsed))
            .concat(extractExposures(text, parsed))
            .concat(extractLexicon(text, parsed, lex.cond, "Condition", ["snomed","icd10"]))
            .concat(extractLexicon(text, parsed, lex.sym,  "Symptom",   ["snomed","loinc"]))
            .concat(extractLexicon(text, parsed, lex.meds, "Medication", ["rxnorm"]));
        ents.sort((a, b) => a.char_start - b.char_start);
        // Cross-kind overlap resolution: drop a shorter entity fully contained
        // in a longer one (e.g. "fever" inside "valley fever"). Keep both when
        // they only partially overlap (rare).
        const byLen = ents.slice().sort((a, b) =>
            (b.char_end - b.char_start) - (a.char_end - a.char_start));
        const kept = [];
        for (const e of byLen) {
            const containedBy = kept.find(k =>
                k.char_start <= e.char_start && e.char_end <= k.char_end &&
                !(k.char_start === e.char_start && k.char_end === e.char_end));
            if (containedBy) continue;
            kept.push(e);
        }
        kept.sort((a, b) => a.char_start - b.char_start);
        return { parsed, entities: kept };
    }

    // ----------------------------------------------------------------------
    // FHIR builder (mirror of fhir_builder.py)
    // ----------------------------------------------------------------------
    function uuid() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, c => {
            const r = (Math.random() * 16) | 0;
            return (c === "x" ? r : (r & 0x3 | 0x8)).toString(16);
        });
    }
    function nowIso() { return new Date().toISOString(); }
    function provExt(e) {
        return [
            { url: "http://onehealthrecord.org/authorship",   valueString: "machine-authored" },
            { url: "http://onehealthrecord.org/confidence",   valueDecimal: Math.round(e.confidence * 1000) / 1000 },
            { url: "http://onehealthrecord.org/source-text",  valueString: e.text },
            { url: "http://onehealthrecord.org/source-span",  valueString: e.char_start + "," + e.char_end },
            { url: "http://onehealthrecord.org/source-phase", valueString: e.phase },
        ];
    }

    function buildBundle(entities, rawText) {
        const entries = [];
        // Patient from demographics.
        let age = null, gender = "unknown";
        for (const e of entities) if (e.kind === "Demographic") {
            if (e.attributes.age_years && age === null) age = e.attributes.age_years;
            if (e.attributes.gender && gender === "unknown") gender = e.attributes.gender;
        }
        const pid = uuid();
        const patient = { resourceType: "Patient", id: pid, gender };
        if (age) {
            const d = new Date(); d.setFullYear(d.getFullYear() - age);
            patient.birthDate = d.toISOString().substring(0, 10);
        }
        entries.push({ fullUrl: "urn:uuid:" + pid, resource: patient });
        const patientRef = "Patient/" + pid;

        for (const e of entities) {
            const id = uuid();
            if (e.kind === "Condition") {
                const cs = e.uncertain ? "provisional" : "active";
                const vs = e.uncertain ? "differential" : "confirmed";
                entries.push({ fullUrl: "urn:uuid:" + id, resource: {
                    resourceType: "Condition", id,
                    subject: { reference: patientRef },
                    code: { coding: e.codes, text: e.attributes.display },
                    clinicalStatus:     { coding: [{ system: "http://terminology.hl7.org/CodeSystem/condition-clinical",   code: cs }] },
                    verificationStatus: { coding: [{ system: "http://terminology.hl7.org/CodeSystem/condition-ver-status", code: vs }] },
                    recordedDate: nowIso(),
                    extension: provExt(e),
                }});
            } else if (e.kind === "Symptom") {
                entries.push({ fullUrl: "urn:uuid:" + id, resource: {
                    resourceType: "Observation", id, status: "final",
                    category: [{ coding: [{ system: "http://terminology.hl7.org/CodeSystem/observation-category", code: "exam" }] }],
                    code: { coding: e.codes, text: e.attributes.display },
                    subject: { reference: patientRef },
                    effectiveDateTime: nowIso(),
                    valueBoolean: !e.negated,
                    extension: provExt(e),
                }});
            } else if (e.kind === "Vital") {
                const vt = e.attributes.vital_type;
                const loinc = ({
                    blood_pressure:["85354-9","Blood pressure panel"],
                    heart_rate:["8867-4","Heart rate"],
                    respiratory_rate:["9279-1","Respiratory rate"],
                    temperature_f:["8310-5","Body temperature"],
                    spo2:["59408-5","Oxygen saturation"],
                })[vt];
                const obs = {
                    resourceType: "Observation", id, status: "final",
                    category: [{ coding: [{ system: "http://terminology.hl7.org/CodeSystem/observation-category", code: "vital-signs" }] }],
                    code: { coding: [{ system: "http://loinc.org", code: loinc[0], display: loinc[1] }] },
                    subject: { reference: patientRef },
                    effectiveDateTime: nowIso(),
                    extension: provExt(e),
                };
                if (vt === "blood_pressure") {
                    obs.component = [
                        { code: { coding: [{ system: "http://loinc.org", code: "8480-6", display: "Systolic BP" }] },
                          valueQuantity: { value: e.attributes.systolic, unit: "mmHg",
                                           system: "http://unitsofmeasure.org", code: "mm[Hg]" } },
                        { code: { coding: [{ system: "http://loinc.org", code: "8462-4", display: "Diastolic BP" }] },
                          valueQuantity: { value: e.attributes.diastolic, unit: "mmHg",
                                           system: "http://unitsofmeasure.org", code: "mm[Hg]" } },
                    ];
                } else {
                    obs.valueQuantity = { value: e.attributes.value, unit: e.attributes.unit,
                                          system: "http://unitsofmeasure.org", code: e.attributes.unit };
                }
                entries.push({ fullUrl: "urn:uuid:" + id, resource: obs });
            } else if (e.kind === "Exposure") {
                entries.push({ fullUrl: "urn:uuid:" + id, resource: {
                    resourceType: "Observation", id, status: "final",
                    category: [{ coding: [{ system: "http://terminology.hl7.org/CodeSystem/observation-category", code: "social-history" }] }],
                    code: { coding: [{ system: "http://onehealthrecord.org/exposure",
                                       code: e.attributes.exposure_type,
                                       display: e.attributes.exposure_type.replace(/_/g, " ") }] },
                    subject: { reference: patientRef },
                    effectiveDateTime: nowIso(),
                    valueBoolean: !e.negated,
                    extension: provExt(e),
                }});
            } else if (e.kind === "Medication") {
                entries.push({ fullUrl: "urn:uuid:" + id, resource: {
                    resourceType: "MedicationStatement", id, status: "active",
                    medicationCodeableConcept: { coding: e.codes, text: e.attributes.display },
                    subject: { reference: patientRef },
                    effectiveDateTime: nowIso(),
                    extension: provExt(e),
                }});
            }
        }

        const provId = uuid();
        entries.push({ fullUrl: "urn:uuid:" + provId, resource: {
            resourceType: "Provenance", id: provId,
            recorded: nowIso(),
            agent: [{ who: { display: "ONE-HealthRecord Machine Authorship Engine v0.1 (browser port)" } }],
            activity: { coding: [{ system: "http://onehealthrecord.org/activity", code: "machine-authored" }] },
            extension: [
                { url: "http://onehealthrecord.org/source-dictation", valueString: rawText.substring(0, 8000) },
                { url: "http://onehealthrecord.org/n-resources", valueInteger: entries.length + 1 },
            ],
        }});

        return {
            resourceType: "Bundle", id: uuid(), type: "collection",
            timestamp: nowIso(), entry: entries,
        };
    }

    // Public surface.
    window.ONE_HR_NLP = { parseDictation, extractEntities, buildBundle };
})();
