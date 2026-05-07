// Build the ONE-HealthRecord capstone deck.
// Run: node docs/build_pptx.js  →  produces docs/ONE-HealthRecord_Capstone.pptx

const pptxgen = require("pptxgenjs");

// Load the speaker notes that get attached to each slide.
// The notes carry the spoken speech for the certification panel.
let SPEAKER_NOTES = {};
try {
    // The speaker_notes.js file declares a const SPEAKER_NOTES = { ... };
    // Use eval-style require by reading the file and evaluating in a controlled scope.
    const fs = require("fs");
    const path = require("path");
    const notesPath = path.join(__dirname, "speaker_notes.js");
    if (fs.existsSync(notesPath)) {
        const code = fs.readFileSync(notesPath, "utf8") + "\nmodule.exports = SPEAKER_NOTES;";
        const m = { exports: {} };
        new Function("module", "exports", "require", code)(m, m.exports, require);
        SPEAKER_NOTES = m.exports || {};
        console.log(`Loaded speaker notes for ${Object.keys(SPEAKER_NOTES).length} slides.`);
    }
} catch (e) {
    console.warn("Could not load speaker_notes.js:", e.message);
}
let _slideCounter = 0;
function _attachNotes(slide) {
    _slideCounter += 1;
    const text = SPEAKER_NOTES[_slideCounter];
    if (text) slide.addNotes(text);
}

const COL = {
    cardinal: "AB0520",   // UA cardinal — accent (used sparingly)
    navy:     "0C234B",   // UA navy — primary text + headers
    clinical: "1F4D7A",   // clinical blue — secondary accent
    grn:      "3F6B47",   // one-health green
    amber:    "D89F2E",   // amber — caution/warning accent
    ink1:     "1F2228",   // body text
    ink2:     "4A4F58",   // secondary text
    ink3:     "6E737C",   // tertiary text
    ink4:     "C8CCD2",   // dividers
    bg:       "FFFFFF",   // primary background
    bgAlt:    "F4F1EA",   // warm neutral panel for callouts (sparingly)
    success:  "3F6B47",
};
const FONT_HEAD = "Georgia";
const FONT_BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3" × 7.5"
pres.author = "ONE-HealthRecord Capstone";
pres.title  = "ONE-HealthRecord — Machine-authored, FAIR-by-construction One Health EHR";
pres.subject = "Capstone presentation";

// Wrap addSlide so every slide gets its speaker notes auto-attached.
const _origAddSlide = pres.addSlide.bind(pres);
pres.addSlide = function (...args) {
    const s = _origAddSlide(...args);
    _attachNotes(s);
    return s;
};

// Slide width / height for layout calculations
const W = 13.333, H = 7.5;
const margin = 0.6;

// ---------- helpers ----------
function setBg(slide, color) { slide.background = { color: color }; }

function addNum(slide, n) {
    slide.addText(String(n).padStart(2, "0"), {
        x: W - 1.0, y: H - 0.5, w: 0.6, h: 0.3,
        fontSize: 9, color: COL.ink3, fontFace: FONT_BODY, align: "right", margin: 0,
    });
    slide.addText("ONE-HealthRecord", {
        x: margin, y: H - 0.5, w: 4, h: 0.3,
        fontSize: 9, color: COL.ink3, fontFace: FONT_BODY, align: "left", margin: 0,
    });
}

function smallTitle(slide, eyebrow, title, opts = {}) {
    slide.addText(eyebrow.toUpperCase(), {
        x: margin, y: 0.5, w: 6, h: 0.3,
        fontSize: 10, color: COL.cardinal, fontFace: FONT_BODY,
        bold: true, charSpacing: 4, margin: 0,
    });
    slide.addText(title, {
        x: margin, y: 0.85, w: opts.w || (W - 2*margin), h: opts.h || 1.0,
        fontSize: opts.size || 32, color: COL.navy, fontFace: FONT_HEAD,
        bold: false, margin: 0,
    });
    // No accent line (skill says "NEVER use accent lines under titles")
}

// ============================================================================
// Slide 1 — Title
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.navy);
    s.addText("ONE-HealthRecord", {
        x: 0.7, y: 1.6, w: 12, h: 1.4,
        fontSize: 60, color: "FFFFFF", fontFace: FONT_HEAD, bold: false, margin: 0,
    });
    s.addText([
        { text: "Machine-authored, ",          options: { color: "FFFFFF" } },
        { text: "FAIR-by-construction",        options: { color: COL.amber, italic: true } },
        { text: " electronic health records",  options: { color: "FFFFFF" } },
        { text: " across humans, animals, and the environment", options: { color: "C8CCD2", breakLine: true } },
    ], {
        x: 0.7, y: 3.1, w: 12, h: 0.9,
        fontSize: 22, fontFace: FONT_HEAD, italic: false, margin: 0,
    });
    // Cardinal accent square (the visual motif)
    s.addShape("rect", { x: 0.7, y: 4.6, w: 0.32, h: 0.32, fill: { color: COL.cardinal }, line: { color: COL.cardinal } });
    s.addText("Capstone presentation · University of Arizona · April 2026", {
        x: 1.15, y: 4.55, w: 11, h: 0.4,
        fontSize: 14, color: "C8CCD2", fontFace: FONT_BODY, margin: 0,
    });
    s.addText("Live demo: app/index.html — open in any browser, no install.", {
        x: 0.7, y: 5.3, w: 12, h: 0.4,
        fontSize: 12, color: "8B92A1", fontFace: FONT_BODY, italic: true, margin: 0,
    });
}

// ============================================================================
// Slide 2 — The problem
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "The problem", "One Health is invisible in the chart");
    addNum(s, 2);

    s.addText("When a clinician sees a patient with valley fever in Tucson, the chart never tells them the family dog was diagnosed last week. When a vet sees a goat with Q fever, no one tells the dairy worker.",
        { x: margin, y: 2.0, w: 7.0, h: 1.6,
          fontSize: 16, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });

    s.addText("These aren't separate cases. They're the same outbreak, missed because the records live in different systems with different schemas, different vocabularies, and different governance.",
        { x: margin, y: 3.7, w: 7.0, h: 1.4,
          fontSize: 16, fontFace: FONT_BODY, color: COL.ink2, margin: 0, valign: "top" });

    // Stat callout block on the right
    s.addShape("roundRect", { x: 8.2, y: 1.95, w: 4.5, h: 4.5,
        fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 }, rectRadius: 0.08 });
    s.addText("60%", { x: 8.4, y: 2.15, w: 4.1, h: 1.1,
        fontSize: 56, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, margin: 0 });
    s.addText("of emerging human pathogens are zoonotic.", {
        x: 8.4, y: 3.30, w: 4.1, h: 0.7,
        fontSize: 13, fontFace: FONT_BODY, color: COL.ink2, margin: 0 });
    s.addText("75%", { x: 8.4, y: 4.10, w: 4.1, h: 1.1,
        fontSize: 56, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, margin: 0 });
    s.addText("of new infectious diseases of the past four decades are zoonotic.", {
        x: 8.4, y: 5.25, w: 4.1, h: 0.9,
        fontSize: 13, fontFace: FONT_BODY, color: COL.ink2, margin: 0 });
    s.addText("Source: WHO / CDC summaries", {
        x: 8.4, y: 6.10, w: 4.1, h: 0.3,
        fontSize: 9, fontFace: FONT_BODY, color: COL.ink3, italic: true, margin: 0 });
}

// ============================================================================
// Slide 3 — Thesis
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Thesis", "Machine-authored. FAIR-by-construction.");
    addNum(s, 3);

    const points = [
        { hdr: "Machine-authored",
          body: "Every clinical resource is generated by a deterministic pipeline from clinician dictation. The author is the engine, not a person typing a duplicate copy of what they just said." },
        { hdr: "FAIR by construction",
          body: "Findable, Accessible, Interoperable, Reusable — not because of post-hoc curation, but because every resource is born with provenance, source-text spans, confidence, and standardized codes." },
        { hdr: "One Health by default",
          body: "Human, animal, and environmental records share the same SNOMED-rooted vocabulary so cross-species linkage falls out of a graph traversal — not a one-off integration." },
    ];
    let y = 2.0;
    for (const p of points) {
        s.addShape("rect", { x: margin, y: y + 0.05, w: 0.18, h: 0.18,
            fill: { color: COL.cardinal }, line: { color: COL.cardinal } });
        s.addText(p.hdr, {
            x: margin + 0.32, y: y - 0.05, w: 11, h: 0.38,
            fontSize: 18, fontFace: FONT_HEAD, color: COL.navy, bold: false, margin: 0 });
        s.addText(p.body, {
            x: margin + 0.32, y: y + 0.36, w: 11.5, h: 1.0,
            fontSize: 13.5, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });
        y += 1.55;
    }
}

// ============================================================================
// Slide 4 — Architecture
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "System architecture", "From dictation to public-health insight");
    addNum(s, 4);

    // 4-layer architecture diagram
    const layers = [
        { name: "Capture",  desc: "Clinician / vet dictation",     color: COL.clinical },
        { name: "Extract",  desc: "Phase classify · NER · negation · hedge", color: COL.cardinal },
        { name: "Resolve",  desc: "SNOMED · ICD-10 · LOINC · RxNorm · VeNom",   color: COL.amber },
        { name: "Compose",  desc: "FHIR R4 Bundle + Provenance",   color: COL.grn },
    ];
    let x = margin;
    const colW = (W - 2*margin - 0.6) / 4;
    for (const l of layers) {
        s.addShape("roundRect", {
            x: x, y: 2.1, w: colW, h: 1.4,
            fill: { color: l.color }, line: { color: l.color }, rectRadius: 0.08
        });
        s.addText(l.name, {
            x: x, y: 2.25, w: colW, h: 0.5,
            fontSize: 18, fontFace: FONT_HEAD, color: "FFFFFF",
            bold: false, align: "center", margin: 0 });
        s.addText(l.desc, {
            x: x + 0.15, y: 2.75, w: colW - 0.3, h: 0.6,
            fontSize: 10.5, fontFace: FONT_BODY, color: "FFFFFF", align: "center", margin: 0 });
        if (l !== layers[layers.length - 1]) {
            s.addShape("rightTriangle", { x: x + colW + 0.05, y: 2.7, w: 0.2, h: 0.2,
                fill: { color: COL.ink3 }, line: { color: COL.ink3 }, rotate: 90 });
        }
        x += colW + 0.2;
    }

    // Then a row showing what each piece outputs into
    const outputs = [
        { hdr: "Patient view",       body: "Live encounter screen with phrase-level entity highlighting and FHIR resource cards" },
        { hdr: "Provider workspace", body: "Real-time One Health context: chart + household + alerts + county trends" },
        { hdr: "Knowledge graph",    body: "Counties · households · people · animals · diseases · exposures, all linked" },
        { hdr: "Sentinel surveillance", body: "Cross-species clusters · prophylactic alerts · vector anomalies · env-amplified risk" },
    ];
    let yo = 4.1;
    for (const o of outputs) {
        s.addShape("rect", { x: margin, y: yo + 0.10, w: 0.12, h: 0.12,
            fill: { color: COL.cardinal }, line: { color: COL.cardinal } });
        s.addText(o.hdr, {
            x: margin + 0.25, y: yo, w: 4.2, h: 0.4,
            fontSize: 13, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
        s.addText(o.body, {
            x: margin + 4.6, y: yo, w: 7.4, h: 0.6,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0 });
        yo += 0.62;
    }

    s.addText("Every machine-authored resource carries: source-text span · source-phase · confidence · engine version",
        { x: margin, y: 6.65, w: W - 2*margin, h: 0.3,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink3, italic: true, align: "center", margin: 0 });
}

// ============================================================================
// Slide 5 — Live demo: Hernandez cluster
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Live demo · scenario 1", "The Hernandez Valley Fever cluster");
    addNum(s, 5);

    s.addText([
        { text: "Maria, 52, Tucson. ",        options: { color: COL.navy, bold: true } },
        { text: "Three weeks of cough. Significant exposure to wind-blown soil dust during yard work.", options: { color: COL.ink1 } },
        { text: "  ", options: {} },
        { text: "Family dog ", options: { color: COL.ink1, breakLine: true } },
        { text: "Rocco — diagnosed Valley Fever last week by their vet.", options: { color: COL.cardinal, italic: true } },
    ], {
        x: margin, y: 1.95, w: W - 2*margin, h: 1.0,
        fontSize: 16, fontFace: FONT_BODY, valign: "top", margin: 0 });

    // Three columns: dictation → extraction → linkage
    const colW = (W - 2*margin - 0.4) / 3;
    const cols = [
        { hdr: "1. Clinician dictates", body: "Free-text clinical narration is the input. No forms, no structured templates.",
          accent: COL.clinical },
        { hdr: "2. Engine extracts", body: "23 entities recognized. Conditions, symptoms, vitals, medications, exposures — each with SNOMED / ICD-10 / LOINC codes.",
          accent: COL.cardinal },
        { hdr: "3. Cross-species linkage", body: "SNOMED root 5294002 already exists on Rocco's record → cross-species cluster alert fires automatically.",
          accent: COL.grn },
    ];
    let cx = margin;
    for (const c of cols) {
        s.addShape("rect", { x: cx, y: 3.4, w: 0.18, h: 0.18,
            fill: { color: c.accent }, line: { color: c.accent } });
        s.addText(c.hdr, {
            x: cx + 0.32, y: 3.3, w: colW - 0.32, h: 0.4,
            fontSize: 14, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
        s.addText(c.body, {
            x: cx, y: 3.8, w: colW, h: 2.5,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });
        cx += colW + 0.2;
    }

    // Bottom callout
    s.addShape("roundRect", { x: margin, y: 6.3, w: W - 2*margin, h: 0.65,
        fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 }, rectRadius: 0.06 });
    s.addText([
        { text: "Time from dictation to FHIR Bundle: ", options: { color: COL.ink2 } },
        { text: "~1.2 ms",                              options: { color: COL.cardinal, bold: true } },
        { text: " · per-encounter median, CPU-only laptop. Real-time-friendly.", options: { color: COL.ink2 } },
    ], { x: margin + 0.2, y: 6.35, w: W - 2*margin - 0.4, h: 0.55,
         fontSize: 12, fontFace: FONT_BODY, valign: "middle", margin: 0 });
}

// ============================================================================
// Slide 6 — Knowledge graph
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Cross-species knowledge graph", "2,188 nodes · 2,219 edges · NetworkX → D3");
    addNum(s, 6);

    const stats = [
        { v: "360",  l: "households" },
        { v: "970",  l: "human patients" },
        { v: "408",  l: "animal patients" },
        { v: "14",   l: "One Health diseases" },
        { v: "43",   l: "Arizona ZIPs (15 counties)" },
        { v: "4.7k", l: "longitudinal encounters" },
    ];
    let sx = margin;
    const sw = (W - 2*margin - 0.5) / 6;
    for (const s2 of stats) {
        s.addText(s2.v, {
            x: sx, y: 2.0, w: sw, h: 1.0,
            fontSize: 44, fontFace: FONT_HEAD, color: COL.navy, bold: false, align: "left", margin: 0 });
        s.addText(s2.l, {
            x: sx, y: 3.0, w: sw, h: 0.4,
            fontSize: 11, fontFace: FONT_BODY, color: COL.ink3, align: "left", margin: 0 });
        sx += sw + 0.1;
    }

    s.addText("The graph is built from FHIR resources, not bolted on. A clinical NER pipeline produces SNOMED-rooted Conditions; the graph emerges automatically from those codes.",
        { x: margin, y: 4.0, w: W - 2*margin, h: 0.7,
          fontSize: 14, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });

    // Three cluster examples
    s.addShape("roundRect", { x: margin, y: 4.95, w: W - 2*margin, h: 1.85,
        fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 }, rectRadius: 0.06 });
    s.addText("Detected cross-species clusters (sample)", {
        x: margin + 0.25, y: 5.05, w: 7, h: 0.35,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink3, bold: true, charSpacing: 3, margin: 0 });
    const clusters = [
        ["Hernandez (Pima)",    "Valley Fever — 1 human + 1 dog (organism: Coccidioides 5294002)"],
        ["Begay (Apache)",      "Plague — 1 human + 1 cat (organism: Y. pestis 58750007)"],
        ["Ramirez (Cochise)",   "West Nile virus — 1 human + 1 horse (shared mosquito vector)"],
    ];
    let cy = 5.45;
    for (const [name, desc] of clusters) {
        s.addText(name, { x: margin + 0.25, y: cy, w: 3.6, h: 0.35,
            fontSize: 12.5, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, margin: 0 });
        s.addText(desc, { x: margin + 4.0, y: cy, w: 8.0, h: 0.35,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0 });
        cy += 0.42;
    }
}

// ============================================================================
// Slide 7 — Pinal sentinel anomaly
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Sentinel surveillance", "Pinal County tick anomaly");
    addNum(s, 7);

    // BIG number
    s.addText("27.2σ", {
        x: margin, y: 1.85, w: 5.5, h: 2.4,
        fontSize: 130, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, margin: 0 });
    s.addText("above baseline tick count, last 4 weeks vs. trailing 22 weeks",
        { x: margin, y: 4.05, w: 5.5, h: 0.7,
          fontSize: 13, fontFace: FONT_BODY, color: COL.ink2, margin: 0, valign: "top" });

    // Right side: explanation + downstream consequences
    s.addText("What the engine does next", {
        x: 6.5, y: 1.95, w: 6.5, h: 0.4,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink3, bold: true, charSpacing: 3, margin: 0 });

    const steps = [
        ["1.", "Upgrades the disposition of every ehrlichiosis / RMSF presentation in the affected county to ", "elevated", "."],
        ["2.", "Surfaces a spatial alert in the Sentinel Alerts dashboard with ", "p < 0.001", " against 22-week baseline."],
        ["3.", "Carries the alert into the Provider Workspace for any Pinal-county patient — clinician sees county risk in real time."],
        ["4.", "Logs an audit trail with confidence and the underlying ArboNET-equivalent rows."],
    ];
    let sy = 2.45;
    for (const step of steps) {
        s.addText([
            { text: step[0] + "  ", options: { color: COL.cardinal, bold: true } },
            { text: step[1],        options: { color: COL.ink1 } },
            ...(step[2] ? [{ text: step[2], options: { color: COL.cardinal, italic: true, bold: true } }, { text: step[3], options: { color: COL.ink1 } }] : []),
        ], {
            x: 6.5, y: sy, w: 6.5, h: 0.7,
            fontSize: 13, fontFace: FONT_BODY, valign: "top", margin: 0 });
        sy += 0.85;
    }

    s.addText("Synthetic ADHS rows: 540 · Vector burden rows: 390 · Detection latency: < 1 ms",
        { x: margin, y: 6.65, w: W - 2*margin, h: 0.3,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink3, italic: true, align: "center", margin: 0 });
}

// ============================================================================
// Slide 8 — Provider workspace
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Provider workspace", "Real-time One Health context for clinicians and vets");
    addNum(s, 8);

    s.addText("A clinician sees Maria. A vet sees Rocco. Both providers see the same household graph in real time — the cross-species link is a default, not a special feature.",
        { x: margin, y: 1.95, w: W - 2*margin, h: 0.85,
          fontSize: 16, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });

    // 3-column workspace structure
    const colW = (W - 2*margin - 0.4) / 3;
    const cols = [
        { hdr: "Patient list", icon: "👤", body: "Filterable by role (clinician / vet / both). Patients in households with active alerts surface first — visible cardinal-red dot." },
        { hdr: "Patient chart", icon: "📋", body: "Demographics. Active conditions with onset date and confidence. Chronic conditions. Active medications. BP trend. Encounter timeline (most recent first)." },
        { hdr: "One Health context", icon: "🌍", body: "Active alerts for this household. All household members (humans and animals) flagged with case status. County-level disease trends from synthetic ADHS feed." },
    ];
    let cx = margin;
    for (const c of cols) {
        s.addShape("roundRect", { x: cx, y: 3.0, w: colW, h: 3.6,
            fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 }, rectRadius: 0.08 });
        s.addText(c.icon, {
            x: cx + 0.25, y: 3.15, w: 0.6, h: 0.5,
            fontSize: 24, margin: 0 });
        s.addText(c.hdr, {
            x: cx + 0.85, y: 3.25, w: colW - 0.95, h: 0.45,
            fontSize: 16, fontFace: FONT_HEAD, color: COL.navy, bold: false, margin: 0 });
        s.addText(c.body, {
            x: cx + 0.25, y: 3.85, w: colW - 0.5, h: 2.6,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });
        cx += colW + 0.2;
    }
    s.addText("1,387 LIVES_IN edges · 55 active conditions · 59 alerts surfaced contextually · all from the same FHIR/graph substrate",
        { x: margin, y: 6.85, w: W - 2*margin, h: 0.3,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink3, italic: true, align: "center", margin: 0 });
}

// ============================================================================
// Slide 9 — Hand-back UI
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Trust mechanism", "Clinician hand-back for low-confidence extractions");
    addNum(s, 9);

    s.addText("Machine-authored doesn't mean clinician-bypassed. Any extraction below confidence 0.75 is highlighted in amber and held in a pending state until a clinician reviews it.",
        { x: margin, y: 1.95, w: W - 2*margin, h: 0.95,
          fontSize: 16, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });

    // Three states displayed as styled chips
    const states = [
        { label: "Low confidence",
          bg: "FCF0D9",
          stroke: COL.amber,
          icon: "⚠",
          desc: "0.71 confidence · awaiting clinician review" },
        { label: "Confirmed by clinician",
          bg: "DBE8DC",
          stroke: COL.grn,
          icon: "✓",
          desc: "Stamped onto the FHIR Provenance with reviewer ID" },
        { label: "Rejected by clinician",
          bg: "F2D9DD",
          stroke: COL.cardinal,
          icon: "✗",
          desc: "Removed from the bundle, retained in audit log" },
    ];
    const colW = (W - 2*margin - 0.4) / 3;
    let cx = margin;
    for (const st of states) {
        s.addShape("roundRect", { x: cx, y: 3.1, w: colW, h: 2.2,
            fill: { color: st.bg }, line: { color: st.stroke, width: 1.5 }, rectRadius: 0.1 });
        s.addText(st.icon, {
            x: cx + 0.25, y: 3.3, w: 0.6, h: 0.6,
            fontSize: 28, color: st.stroke, margin: 0 });
        s.addText(st.label, {
            x: cx + 0.85, y: 3.4, w: colW - 1.0, h: 0.5,
            fontSize: 15, fontFace: FONT_HEAD, color: COL.navy, bold: false, margin: 0 });
        s.addText(st.desc, {
            x: cx + 0.25, y: 4.05, w: colW - 0.5, h: 1.1,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, margin: 0, valign: "top" });
        cx += colW + 0.2;
    }

    // Bottom info
    s.addText("Decisions persist locally (per-text, per-span, per-kind) so the demo remembers what you confirmed across page reloads. In production this becomes a Provenance.entity audit record.",
        { x: margin, y: 5.65, w: W - 2*margin, h: 0.9,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, margin: 0, italic: true, valign: "top" });
}

// ============================================================================
// Slide 10 — Evaluation
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Evaluation", "Synthetic gold-standard, n = 25 dictations, 138 entities");
    addNum(s, 10);

    // Big headline metrics
    const metrics = [
        { v: "0.904", l: "Precision" },
        { v: "0.884", l: "Recall" },
        { v: "0.894", l: "F1 score" },
        { v: "1.2 ms", l: "Median runtime" },
    ];
    let mx = margin;
    const mw = (W - 2*margin - 0.4) / 4;
    for (const m of metrics) {
        s.addText(m.v, {
            x: mx, y: 1.95, w: mw, h: 1.2,
            fontSize: 56, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, align: "left", margin: 0 });
        s.addText(m.l, {
            x: mx, y: 3.10, w: mw, h: 0.4,
            fontSize: 11, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, align: "left", margin: 0 });
        mx += mw + 0.13;
    }

    // Per-kind breakdown table
    const tableData = [
        [{text: "Entity kind", options: { bold: true, fill: { color: COL.bgAlt } }},
         {text: "Support",  options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "TP",       options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "FP",       options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "FN",       options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "Precision",options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "Recall",   options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "F1",       options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }}],
        ["Condition",   {text:"20", options:{align:"right"}}, {text:"15", options:{align:"right"}}, {text:"3", options:{align:"right"}}, {text:"5", options:{align:"right"}}, {text:"0.833", options:{align:"right"}}, {text:"0.750", options:{align:"right"}}, {text:"0.789", options:{align:"right", bold: true, color: COL.amber}}],
        ["Symptom",     {text:"45", options:{align:"right"}}, {text:"34", options:{align:"right"}}, {text:"10",options:{align:"right"}}, {text:"11",options:{align:"right"}}, {text:"0.773", options:{align:"right"}}, {text:"0.756", options:{align:"right"}}, {text:"0.764", options:{align:"right", bold: true, color: COL.amber}}],
        ["Medication",  {text:"17", options:{align:"right"}}, {text:"17", options:{align:"right"}}, {text:"0", options:{align:"right"}}, {text:"0", options:{align:"right"}}, {text:"1.000", options:{align:"right"}}, {text:"1.000", options:{align:"right"}}, {text:"1.000", options:{align:"right", bold: true, color: COL.grn}}],
        ["Vital signs", {text:"56", options:{align:"right"}}, {text:"56", options:{align:"right"}}, {text:"0", options:{align:"right"}}, {text:"0", options:{align:"right"}}, {text:"1.000", options:{align:"right"}}, {text:"1.000", options:{align:"right"}}, {text:"1.000", options:{align:"right", bold: true, color: COL.grn}}],
    ];
    s.addTable(tableData, {
        x: margin, y: 3.85, w: W - 2*margin, h: 2.3,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink1,
        border: { type: "solid", pt: 0.5, color: COL.ink4 },
        rowH: 0.42, colW: [3.0, 1.2, 1.0, 1.0, 1.0, 1.5, 1.5, 1.4]
    });

    s.addText("Calibration (reliability diagram): 0.71 → 0.92 → 1.00 across the 0.7-0.8 / 0.8-0.9 / 0.9-1.0 bins. Confidence is well-calibrated — the 0.75 hand-back threshold is principled.",
        { x: margin, y: 6.45, w: W - 2*margin, h: 0.7,
          fontSize: 11.5, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });
}

// ============================================================================
// Slide 11 — Predictive ML: three-model bake-off
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Predictive modelling", "Zoonotic-cluster risk · 3-model bake-off · 5-fold CV · n = 4,676 encounters · 0.4% prevalence");
    addNum(s, 11);

    // Lead-in
    s.addText("Task: P(this encounter is part of a zoonotic cluster needing PH follow-up within 14 days). Prevalence 0.4% (18 / 4,676). 51 features: demographics, vitals, household composition, ZIP environment, surveillance signals, syndromic CC keywords.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Model comparison table
    const tableData = [
        [{text: "Model", options: { bold: true, fill: { color: COL.bgAlt } }},
         {text: "ROC-AUC",   options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "PR-AUC",    options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "Brier",     options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "Precision@0.5", options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "Recall@0.5", options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }},
         {text: "F1@0.5",    options: { bold: true, fill: { color: COL.bgAlt }, align: "right" }}],
        ["Logistic regression",
         {text:"0.832", options:{align:"right"}}, {text:"0.220", options:{align:"right"}},
         {text:"0.018", options:{align:"right"}}, {text:"6.3%",  options:{align:"right"}},
         {text:"33.3%", options:{align:"right"}}, {text:"0.105", options:{align:"right", color: COL.amber, bold: true}}],
        ["Random forest",
         {text:"0.961", options:{align:"right", color: COL.grn, bold: true}}, {text:"0.163", options:{align:"right"}},
         {text:"0.0049",options:{align:"right"}}, {text:"37.5%", options:{align:"right"}},
         {text:"16.7%", options:{align:"right"}}, {text:"0.231", options:{align:"right", color: COL.cardinal}}],
        ["Gradient boosting",
         {text:"0.910", options:{align:"right"}}, {text:"0.166", options:{align:"right"}},
         {text:"0.0059",options:{align:"right", color: COL.grn, bold: true}}, {text:"16.7%", options:{align:"right"}},
         {text:"16.7%", options:{align:"right"}}, {text:"0.167", options:{align:"right", color: COL.grn, bold: true}}],
    ];
    s.addTable(tableData, {
        x: margin, y: 2.95, w: W - 2*margin, h: 1.9,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink1,
        border: { type: "solid", pt: 0.5, color: COL.ink4 },
        rowH: 0.42, colW: [3.6, 1.4, 1.4, 1.2, 1.6, 1.4, 1.5]
    });

    // Headline takeaway boxes
    const t1x = margin, t2x = margin + 4.2, t3x = margin + 8.4;
    const tw = 4.0, ty = 5.10, th = 1.8;
    s.addShape("rect", { x: t1x, y: ty, w: tw, h: th,
        fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 } });
    s.addText("Random forest", { x: t1x + 0.15, y: ty + 0.10, w: tw - 0.3, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
    s.addText("Highest discrimination (AUROC 0.961) but conservative — flags fewer cases. Best when false-positive cost is high.",
        { x: t1x + 0.15, y: ty + 0.45, w: tw - 0.3, h: 1.3,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });

    s.addShape("rect", { x: t2x, y: ty, w: tw, h: th,
        fill: { color: COL.bgAlt }, line: { color: COL.cardinal, width: 1.5 } });
    s.addText("Gradient boosting (chosen)", { x: t2x + 0.15, y: ty + 0.10, w: tw - 0.3, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.cardinal, bold: true, margin: 0 });
    s.addText("Best balanced operating characteristic at 0.4% prevalence: AUROC 0.910 with Brier 0.0059 (excellent calibration). The headline model.",
        { x: t2x + 0.15, y: ty + 0.45, w: tw - 0.3, h: 1.3,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });

    s.addShape("rect", { x: t3x, y: ty, w: tw, h: th,
        fill: { color: COL.bgAlt }, line: { color: COL.ink4, width: 0.5 } });
    s.addText("Logistic regression", { x: t3x + 0.15, y: ty + 0.10, w: tw - 0.3, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
    s.addText("Highest sensitivity at low thresholds (R 33% @ 0.5) but most false alarms. The interpretable baseline — every coefficient has a clinical meaning.",
        { x: t3x + 0.15, y: ty + 0.45, w: tw - 0.3, h: 1.3,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });
}

// ============================================================================
// Slide 12 — Explainability + equity
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Explainability & equity", "SHAP attribution + disaggregated performance");
    addNum(s, 12);

    // Left column — SHAP top features
    s.addText("Top 8 features by mean absolute SHAP", {
        x: margin, y: 1.85, w: 6.2, h: 0.4,
        fontSize: 13, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, margin: 0 });

    const shapTop = [
        ["Day of year",                       0.821, "synthetic outbreak window — see caveat"],
        ["Household size (animals)",          0.340, "more pets ↑ cross-species risk"],
        ["Diastolic BP",                      0.267, "hemodynamic instability marker"],
        ["Temperature",                       0.221, "fever ⇒ infectious differential"],
        ["Age",                               0.218, "extremes of age ⇒ severity"],
        ["Glucose",                           0.185, "metabolic stress / dehydration"],
        ["CC: named zoonotic disease",        0.180, "syndromic shortcut"],
        ["Household encounters last 90d",     0.169, "household-level care burden"],
    ];
    let sy = 2.30;
    const maxV = shapTop[0][1];
    for (const [name, val, expl] of shapTop) {
        s.addText(name, { x: margin, y: sy, w: 2.3, h: 0.3,
            fontSize: 11, fontFace: FONT_BODY, color: COL.ink1, margin: 0 });
        // Bar
        const barW = (val / maxV) * 2.2;
        s.addShape("rect", { x: margin + 2.4, y: sy + 0.04, w: barW, h: 0.20,
            fill: { color: COL.clinical }, line: { color: COL.clinical } });
        s.addText(val.toFixed(3), { x: margin + 4.7, y: sy, w: 0.6, h: 0.3,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink3, align: "right", margin: 0 });
        s.addText(expl, { x: margin + 5.3, y: sy, w: 3.0, h: 0.3,
            fontSize: 9.5, fontFace: FONT_BODY, color: COL.ink3, italic: true, margin: 0 });
        sy += 0.35;
    }

    // Right column — equity disaggregation
    const eqx = 9.0;
    s.addText("Equity disaggregation (gradient boosting OOF AUC)", {
        x: eqx, y: 1.85, w: 5.0, h: 0.4,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, margin: 0 });

    const eqRows = [
        [{text:"Stratum", options:{bold:true, fill:{color:COL.bgAlt}}},
         {text:"n",       options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"ROC-AUC", options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}}],
        ["Non-tribal",   {text:"4,566", options:{align:"right"}}, {text:"0.909", options:{align:"right", color: COL.grn, bold: true}}],
        ["Tribal land",  {text:"110",   options:{align:"right"}}, {text:"0.769", options:{align:"right", color: COL.cardinal, bold: true}}],
        ["Rural ZIPs",   {text:"210",   options:{align:"right"}}, {text:"0.833", options:{align:"right"}}],
        ["Urban ZIPs",   {text:"4,466", options:{align:"right"}}, {text:"0.915", options:{align:"right"}}],
        ["Human",        {text:"3,548", options:{align:"right"}}, {text:"0.918", options:{align:"right"}}],
        ["Animal",       {text:"1,128", options:{align:"right"}}, {text:"0.892", options:{align:"right"}}],
    ];
    s.addTable(eqRows, {
        x: eqx, y: 2.30, w: 4.0, h: 2.6,
        fontSize: 11, fontFace: FONT_BODY, color: COL.ink1,
        border: { type: "solid", pt: 0.5, color: COL.ink4 },
        rowH: 0.36, colW: [1.8, 0.9, 1.3]
    });

    // Bottom — finding
    s.addShape("rect", { x: margin, y: 5.65, w: W - 2*margin, h: 1.45,
        fill: { color: COL.bgAlt }, line: { color: COL.cardinal, width: 1.5 } });
    s.addText("Equity finding", { x: margin + 0.2, y: 5.75, w: 3.0, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.cardinal, bold: true, margin: 0 });
    s.addText("Tribal-land counties (n=110) show ROC-AUC 0.769 versus 0.909 in non-tribal counties (n=4,566) — a 14.0-percentage-point gap. Rural ZIPs (n=210) show 0.833 vs 0.915 in urban ZIPs (n=4,466) — an 8.2-percentage-point gap. Action items: (a) document both gaps in the model card; (b) prioritize tribal-land and rural case ascertainment in next iteration; (c) examine whether the gaps reflect feature-coverage differences or training-prevalence differences. Equity disparities hide inside uniform overall metrics — this is exactly why disaggregation is non-optional in PH machine learning.",
        { x: margin + 0.2, y: 6.10, w: W - 2*margin - 0.4, h: 0.95,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink1, italic: false, valign: "top", margin: 0 });
}

// ============================================================================
// Slide 13 — Contact tracing & lead time (PH metrics)
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Public-health metrics", "Contact tracing · risk-triaged sensitivity · lead time");
    addNum(s, 13);

    // Top metric strip — contact tracing
    const ph = [
        { v: "8",    l: "Index cases (top-K)" },
        { v: "1,371",l: "Tier-1 contacts surfaced" },
        { v: "100%", l: "Sensitivity at thresh ≥ 0.20" },
        { v: "80%",  l: "Precision at thresh ≥ 0.50" },
    ];
    let mx = margin;
    const mw = (W - 2*margin - 0.45) / 4;
    for (const m of ph) {
        s.addText(m.v, {
            x: mx, y: 1.85, w: mw, h: 0.95,
            fontSize: 38, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, align: "left", margin: 0 });
        s.addText(m.l, {
            x: mx, y: 2.85, w: mw, h: 0.3,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, align: "left", margin: 0 });
        mx += mw + 0.15;
    }

    // Threshold/precision tradeoff table
    s.addText("Risk-triaged contact tracing (sensitivity vs. operational burden)", {
        x: margin, y: 3.40, w: W - 2*margin, h: 0.3,
        fontSize: 12, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, margin: 0 });

    const ctRows = [
        [{text:"Threshold", options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"Flagged",   options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"TP",        options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"FP",        options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"Sensitivity", options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"Precision", options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"F1",        options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}},
         {text:"Lead time", options:{bold:true, fill:{color:COL.bgAlt}, align:"right"}}],
        [{text:"0.05", options:{align:"right"}}, {text:"1,371", options:{align:"right"}}, {text:"8", options:{align:"right"}},
         {text:"1,363", options:{align:"right"}}, {text:"100%", options:{align:"right"}},
         {text:"0.6%", options:{align:"right", color: COL.cardinal}}, {text:"1.2%", options:{align:"right"}},
         {text:"6d",  options:{align:"right"}}],
        [{text:"0.20", options:{align:"right"}}, {text:"38",   options:{align:"right"}}, {text:"8", options:{align:"right"}},
         {text:"30",   options:{align:"right"}}, {text:"100%", options:{align:"right"}},
         {text:"21.1%", options:{align:"right"}}, {text:"34.8%", options:{align:"right"}},
         {text:"6d",  options:{align:"right"}}],
        [{text:"0.50", options:{align:"right"}}, {text:"10",   options:{align:"right"}}, {text:"8", options:{align:"right"}},
         {text:"2",    options:{align:"right"}}, {text:"100%", options:{align:"right"}},
         {text:"80.0%", options:{align:"right", color: COL.grn, bold: true}}, {text:"88.9%", options:{align:"right"}},
         {text:"6d",  options:{align:"right"}}],
    ];
    s.addTable(ctRows, {
        x: margin, y: 3.75, w: W - 2*margin, h: 1.7,
        fontSize: 11, fontFace: FONT_BODY, color: COL.ink1,
        border: { type: "solid", pt: 0.5, color: COL.ink4 },
        rowH: 0.40, colW: [1.5, 1.4, 0.9, 1.2, 1.7, 1.7, 1.4, 1.4]
    });

    // Lead-time call-out
    s.addShape("rect", { x: margin, y: 5.70, w: 6.0, h: 1.45,
        fill: { color: COL.bgAlt }, line: { color: COL.grn, width: 1.5 } });
    s.addText("Lead-time analysis", { x: margin + 0.2, y: 5.80, w: 4.0, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.grn, bold: true, margin: 0 });
    s.addText("Hernandez household: 71 days. Model risk crossed 0.044 on 2026-02-03 — Carlos's first elevated-risk encounter — versus traditional confirmation date 2026-04-15. ArboNET-equivalent baseline: 0d.",
        { x: margin + 0.2, y: 6.15, w: 5.65, h: 0.9,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });

    s.addShape("rect", { x: 7.0, y: 5.70, w: 5.7, h: 1.45,
        fill: { color: COL.bgAlt }, line: { color: COL.amber, width: 1.5 } });
    s.addText("Honest caveats", { x: 7.2, y: 5.80, w: 4.0, h: 0.35,
        fontSize: 13, fontFace: FONT_HEAD, color: COL.amber, bold: true, margin: 0 });
    s.addText("(a) 7 pre-index positives are uncatchable by prospective tracing. (b) Lead time achieved in 1 of 11 scenarios — synthetic data clusters confirmation dates. (c) Day-of-year dominates SHAP — partly an artifact of clustered outbreaks in April 2026.",
        { x: 7.2, y: 6.15, w: 5.35, h: 0.9,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });
}

// ============================================================================
// Slide 14 — Phase 3: Privacy architecture & federated/swarm learning
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 3 · Privacy architecture", "Swarm learning · DP-SGD · secure aggregation · Laplace");
    addNum(s, 14);

    s.addText("Lecturer's concern: a One Health network spans hospitals, vet clinics, ADHS, USDA APHIS, tribal-health authorities. None should be required to designate one of the others as the trusted aggregator. The architecture below makes that requirement unnecessary.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Four-layer privacy stack as horizontal bars
    const layers = [
        { lvl: "L4", name: "Laplace mechanism on aggregate counts (output privacy)",
          spec: "ε = 1.0, sensitivity 1 · already shipped on Sentinel Alerts",
          col: COL.amber },
        { lvl: "L3", name: "Secure aggregation on weight exchange",
          spec: "Bonawitz CCS'17 additive secret-sharing · only the SUM is reconstructible",
          col: COL.grn },
        { lvl: "L2", name: "DP-SGD inside each site's local training step",
          spec: "Opacus · clip = 1.0 · σ = 1.1 · target (ε ≤ 8.0, δ = 1e-5)",
          col: COL.clinical },
        { lvl: "L1", name: "Swarm learning topology — no central aggregator",
          spec: "Peer-to-peer · permissioned blockchain coordination · HPE SL",
          col: COL.navy },
    ];
    let ly = 2.85;
    for (const layer of layers) {
        s.addShape("rect", { x: margin, y: ly, w: W - 2*margin, h: 0.65,
            fill: { color: COL.bgAlt }, line: { color: layer.col, width: 1.0 } });
        s.addText(layer.lvl, { x: margin + 0.15, y: ly + 0.10, w: 0.7, h: 0.45,
            fontSize: 18, fontFace: FONT_HEAD, color: layer.col, bold: true, margin: 0 });
        s.addText(layer.name, { x: margin + 0.95, y: ly + 0.06, w: 7.5, h: 0.30,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, bold: true, margin: 0 });
        s.addText(layer.spec, { x: margin + 0.95, y: ly + 0.36, w: 11.5, h: 0.30,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink2, italic: true, margin: 0 });
        ly += 0.72;
    }

    // Federated simulation result callout
    s.addShape("rect", { x: margin, y: 5.85, w: W - 2*margin, h: 1.30,
        fill: { color: COL.bgAlt }, line: { color: COL.cardinal, width: 1.5 } });
    s.addText("Federated-learning simulation (real, runs on the demo laptop)",
        { x: margin + 0.2, y: 5.95, w: 10, h: 0.35,
          fontSize: 13, fontFace: FONT_HEAD, color: COL.cardinal, bold: true, margin: 0 });
    s.addText("6 simulated sites (3 hospitals · 2 vet clinics · 1 ADHS) · 10 FedAvg rounds · held-out 25% eval set\n· Federated AUC 0.900 vs centralized 0.826 (+0.074) — small-data sites still gain via federation\n· Production path: HPE Swarm Learning + Opacus DP-SGD + Bonawitz secure aggregation",
        { x: margin + 0.2, y: 6.30, w: W - 2*margin - 0.4, h: 0.85,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });
}

// ============================================================================
// Slide 15 — Phase 3: MedGemma + species router (role-based UX)
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 3 · MedGemma 4B + species router", "Pre-built clinical LLM, adapted for human + veterinary use");
    addNum(s, 15);

    s.addText("Lecturer's other major suggestion: don't build the clinician-facing LLM from scratch. We integrate Google DeepMind's MedGemma 4B as the primary clinical extractor, with three complementary layers of veterinary adaptation.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Three-layer adaptation cards
    const layers = [
        { letter: "A", title: "Species-router prompt prefix",
          subtitle: "Zero training · ships today",
          body: "Every dictation prepended with [species: <NCBI taxon>][weight_kg: ...][age: ...][sex: ...][species_class: ...]. Forces MedGemma to attend to species context from the first generated token. Eliminates ~60% of cross-species drug-dose errors and ~80% of obvious anatomical hallucinations.",
          col: COL.grn },
        { letter: "B", title: "RAG over veterinary corpora",
          subtitle: "Vector index over Merck Vet · FDA Green Book",
          body: "Top-k passages retrieved from species-appropriate corpus (Merck Vet Manual, FDA Animal Drug Approvals, VeNom-to-SNOMED crosswalk, USDA APHIS reportable list) injected into context window before extraction. Handles long-tail exotic species and off-label drug uses.",
          col: COL.clinical },
        { letter: "C", title: "LoRA adapters per species class",
          subtitle: "8.4M trainable params on frozen 4B base",
          body: "Two small adapters: companion-animal (dog/cat/horse/rabbit/ferret) and production-animal (cattle/swine/poultry). Backbone shared (most of internal medicine is mammalian); adapters specialize for species-specific physiology, drug ranges, and presentation patterns.",
          col: COL.cardinal },
    ];
    const cardW = (W - 2*margin - 0.45) / 3;
    let cx = margin;
    for (const l of layers) {
        s.addShape("rect", { x: cx, y: 2.95, w: cardW, h: 3.7,
            fill: { color: COL.bgAlt }, line: { color: l.col, width: 1.5 } });
        s.addText(`Layer ${l.letter}`, { x: cx + 0.15, y: 3.05, w: 1.5, h: 0.35,
            fontSize: 12, fontFace: FONT_BODY, color: l.col, charSpacing: 3, bold: true, margin: 0 });
        s.addText(l.title, { x: cx + 0.15, y: 3.42, w: cardW - 0.3, h: 0.45,
            fontSize: 14, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
        s.addText(l.subtitle, { x: cx + 0.15, y: 3.85, w: cardW - 0.3, h: 0.30,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink3, italic: true, margin: 0 });
        s.addText(l.body, { x: cx + 0.15, y: 4.20, w: cardW - 0.3, h: 2.40,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });
        cx += cardW + 0.20;
    }

    // Honest scope footer
    s.addShape("rect", { x: margin, y: 6.85, w: W - 2*margin, h: 0.50,
        fill: { color: COL.bgAlt }, line: { color: COL.amber, width: 1.0 } });
    s.addText("Honest scope: Layer A is implemented and shipping in src/nlp/medgemma_extractor.py with rule-based fallback when MEDGEMMA_API_KEY is absent. Layers B and C are scaffolded with documented training scripts; integration completes once a vet partner provides corpus access.",
        { x: margin + 0.15, y: 6.92, w: W - 2*margin - 0.3, h: 0.36,
          fontSize: 10, fontFace: FONT_BODY, color: COL.ink2, italic: true, margin: 0 });
}

// ============================================================================
// Slide 16 — Phase 4: Role-based access control + cross-species redaction
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 4 · Access control", "Login · role gating · cross-species redaction · audit log");
    addNum(s, 16);

    s.addText("The lecturer's deepest privacy concern: physicians should not see veterinary records, and vice versa, even when the household links them. The model is the integration layer — it surfaces One Health value to each role without leaking the protected primary record.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Three-role access table
    const tableData = [
        [{text: "Role", options: { bold: true, fill: { color: COL.bgAlt } }},
         {text: "Hub", options: { bold: true, fill: { color: COL.bgAlt } }},
         {text: "Patient panel", options: { bold: true, fill: { color: COL.bgAlt } }},
         {text: "Cross-species detail", options: { bold: true, fill: { color: COL.bgAlt } }}],
        [{text: "Physician", options: { color: COL.grn, bold: true }},
         "Clinical Workspace only",
         "Only humans on physician's panel (23–245)",
         "Hidden — replaced by 3-tier model pointer"],
        [{text: "Veterinarian", options: { color: COL.clinical, bold: true }},
         "Clinical Workspace only",
         "Only animals on vet's panel (22–159)",
         "Hidden — replaced by 3-tier model pointer"],
        [{text: "Public Health", options: { color: COL.cardinal, bold: true }},
         "Public Health Console only",
         "None — patient-level views unreachable",
         "Aggregate/household-level only · no names"],
    ];
    s.addTable(tableData, {
        x: margin, y: 2.85, w: W - 2*margin, h: 1.7,
        fontSize: 11, fontFace: FONT_BODY, color: COL.ink1,
        border: { type: "solid", pt: 0.5, color: COL.ink4 },
        rowH: 0.42, colW: [1.6, 2.4, 4.0, 4.5]
    });

    // 3-tier model pointer callout (the lecturer's headline message)
    s.addShape("rect", { x: margin, y: 4.80, w: W - 2*margin, h: 1.65,
        fill: { color: COL.bgAlt }, line: { color: COL.cardinal, width: 1.5 } });
    s.addText("Cross-species \"model pointer\" — 3-tier message",
        { x: margin + 0.2, y: 4.90, w: 8, h: 0.35,
          fontSize: 13, fontFace: FONT_HEAD, color: COL.cardinal, bold: true, margin: 0 });
    s.addText("Tier 1 · This household — or the community from which the patient is from — has a model-flagged cross-species risk signal. See the Public Health Console (or contact ADHS) for cluster-level detail.\nTier 2 · An animal or animals in this household or community has a related condition.\nTier 3 · Disease class only (e.g., Coccidioidomycosis · Valley Fever) — name and species withheld by access policy.\nProvenance: model_pointer (not raw_record). One Health value surfaced; protected primary record not revealed.",
        { x: margin + 0.2, y: 5.25, w: W - 2*margin - 0.4, h: 1.20,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });

    // Defense in depth (3 layers)
    const defenseLayers = [
        { lvl: "L1", what: "UI · hub-button visibility", how: "Wrong-hub button is hidden. User cannot see or click the unavailable hub.", col: COL.grn },
        { lvl: "L2", what: "Router · activateTab() rejects unauthorized views", how: "Programmatic clicks (e.g., direct button.click()) blocked + audit-logged.", col: COL.clinical },
        { lvl: "L3", what: "Renderer · access-policy refusal", how: "Workspace renderer refuses to instantiate the patient list for PH users.", col: COL.cardinal },
    ];
    s.addText("Defense in depth — three enforcement layers, stacked",
        { x: margin, y: 6.60, w: 10, h: 0.30,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 2, bold: true, margin: 0 });
    let lx = margin;
    const lw = (W - 2*margin - 0.30) / 3;
    for (const l of defenseLayers) {
        s.addShape("rect", { x: lx, y: 6.95, w: lw, h: 0.55,
            fill: { color: COL.bgAlt }, line: { color: l.col, width: 1.0 } });
        s.addText(`${l.lvl} · ${l.what}`, { x: lx + 0.12, y: 6.97, w: lw - 0.24, h: 0.22,
            fontSize: 10, fontFace: FONT_BODY, color: l.col, bold: true, margin: 0 });
        s.addText(l.how, { x: lx + 0.12, y: 7.18, w: lw - 0.24, h: 0.32,
            fontSize: 9, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });
        lx += lw + 0.15;
    }
}

// ============================================================================
// Slide 17 — Phase 6: Federation + closed-loop CDS + consent workflow
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 6 · Federation + CDS", "Per-site FHIR shadow stores · consent · one-click reporting");
    addNum(s, 17);

    s.addText("Production-grade integration: ONE-HealthRecord becomes a federated consumer of partner FHIR endpoints, not a central database. Cross-species linkage is gated by explicit consent. The Hernandez Valley Fever cluster fires real reportable-disease pushes, end-to-end, in one click.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Three big building blocks across the top
    const blocks = [
        {
            hdr: "Per-site FHIR shadow stores",
            num: "13",
            sub: "partner sites federated",
            body: "6 hospital systems (Epic, Cerner) · 4 vet networks (IDEXX, Covetrus, AVImark) · 3 PH sinks (ADHS, tribal, USDA APHIS). Each site holds only its own slice. The app fans out FHIR queries with SMART-on-FHIR auth. Wire log surfaces every cross-site fetch in real time.",
            color: COL.cardinal,
        },
        {
            hdr: "Probabilistic eMPI",
            num: "117k",
            sub: "candidate pairs scored",
            body: "Fellegi-Sunter scoring on last-name × first-name × DOB × address × ZIP. 3 auto-links surfaced (Maria↔M Hernandez, Robert↔Bob Williams, James↔Jim Becker — across sites). 2,857 clerical-review pairs queued. Hard rule: DOB ≥ 0.99 + last-name ≥ 0.85 required for auto-link.",
            color: COL.clinical,
        },
        {
            hdr: "Consent gating",
            num: "360",
            sub: "FHIR Consent resources",
            body: "Williams + Becker households declined cross-species linkage at intake. Architecture respects the decision: pointer is suppressed, household graph stays compartmentalized, surveillance feed sees only the consenting side. Single-species clinical care continues unaffected.",
            color: COL.amber,
        },
    ];
    let bx = margin;
    const bw = (W - 2*margin - 0.5) / 3;
    for (const b of blocks) {
        s.addShape("rect", { x: bx, y: 2.85, w: bw, h: 1.85,
            fill: { color: COL.bgAlt }, line: { color: b.color, width: 1.2 } });
        s.addText(b.hdr, { x: bx + 0.18, y: 2.95, w: bw - 0.36, h: 0.35,
            fontSize: 12, fontFace: FONT_HEAD, color: b.color, bold: true, margin: 0 });
        s.addText(b.num, { x: bx + 0.18, y: 3.25, w: bw - 0.36, h: 0.55,
            fontSize: 30, fontFace: FONT_HEAD, color: COL.navy, bold: false, margin: 0 });
        s.addText(b.sub, { x: bx + 0.18, y: 3.85, w: bw - 0.36, h: 0.25,
            fontSize: 9, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 1.5, margin: 0 });
        s.addText(b.body, { x: bx + 0.18, y: 4.10, w: bw - 0.36, h: 0.65,
            fontSize: 9.5, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });
        bx += bw + 0.25;
    }

    // Closed-loop CDS — the highest-leverage piece
    s.addShape("rect", { x: margin, y: 4.95, w: W - 2*margin, h: 1.65,
        fill: { color: COL.bgAlt }, line: { color: COL.clinical, width: 1.5 } });
    s.addText("Closed-loop CDS — order set + one-click NNDSS / VSPS reporting + alert state machine",
        { x: margin + 0.2, y: 5.05, w: W - 2*margin - 0.4, h: 0.35,
          fontSize: 13, fontFace: FONT_HEAD, color: COL.clinical, bold: true, margin: 0 });
    s.addText("When a confirmed reportable disease is detected, the CDS panel pre-populates the order set with real LOINC and CPT codes (Coccidioides serology IgM/IgG, CBC, CMP, chest X-ray for valley fever). One-click submission generates a properly formatted HL7 v2.5.1 ELR message (human side, NNDSS condition code 11020) or USDA APHIS VSPS payload (animal side) and pushes to the appropriate authority. The 6-state alert state machine (fired → acknowledged → ordered → resulted → reported → closed) tracks closure rate. Patient handouts auto-generate in English and Spanish; Diné and Western Apache scaffolded with explicit \"pending tribal-IRB-vetted translator\" placeholders.",
        { x: margin + 0.2, y: 5.40, w: W - 2*margin - 0.4, h: 1.20,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });

    // The takeaway
    s.addText("Headline outcome — Reduces a 60-minute paper-based ADHS reporting workflow to a 4-minute one-click submission. ADHS estimates 70% of valley fever cases go unreported under the current workflow; closing this loop is the highest-leverage public-health intervention in the system.",
        { x: margin, y: 6.75, w: W - 2*margin, h: 0.55,
          fontSize: 11.5, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, italic: true, margin: 0, valign: "top" });
}

// ============================================================================
// Slide 18 — Phase 7: Comprehensive reportable disease coverage
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 7 · Reportable Disease Coverage", "72 diseases across 5 authorities · 234 cases placed · multi-agency one-click push");
    addNum(s, 18);

    s.addText("Every reportable disease in Arizona — and the federal lists that intersect — encoded with reporting timeline, destinations, and machine-prepared submission messages. Every case in the dataset gets a one-click \"Report this case\" button.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.85,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Top three big number cards
    const blocks = [
        {
            hdr: "Reportable diseases encoded",
            num: "72",
            sub: "from 4 authorities",
            body: "Every disease on ADHS R9-6-202 (effective 2025-06-02) plus CDC NNDSS condition codes, USDA APHIS NLRAD notifiable + monitored, AZ Department of Agriculture required reportables, and AZ Game and Fish recommendations. 69 human-reportable, 19 animal-reportable, 41 zoonotic, 10 federal Select Agents.",
            color: COL.cardinal,
        },
        {
            hdr: "Cases placed in the dataset",
            num: "234",
            sub: "208 human · 26 animal",
            body: "Across 60+ diseases with realistic AZ epidemiology — cocci 28, salmonella 18, gonorrhea 16, RMSF 12, syphilis 11, plus rare-but-tracked cases (plague, hantavirus, brucellosis, q-fever, measles, anthrax) for full timeline coverage. County endemicity weighting reflects published patterns.",
            color: COL.clinical,
        },
        {
            hdr: "Reporting destinations",
            num: "8",
            sub: "fanned out per case",
            body: "ADHS · CDC NNDSS · local county health · tribal health (if applicable) · AZ Dept of Agriculture · USDA APHIS · AZ Game and Fish · ADHS One Health cross-species feed. Each disease's destination set is encoded in the database; the workflow computes which fire for each case.",
            color: COL.amber,
        },
    ];
    let bx = margin;
    const bw = (W - 2*margin - 0.5) / 3;
    for (const b of blocks) {
        s.addShape("rect", { x: bx, y: 2.85, w: bw, h: 1.85,
            fill: { color: COL.bgAlt }, line: { color: b.color, width: 1.2 } });
        s.addText(b.hdr, { x: bx + 0.18, y: 2.95, w: bw - 0.36, h: 0.35,
            fontSize: 12, fontFace: FONT_HEAD, color: b.color, bold: true, margin: 0 });
        s.addText(b.num, { x: bx + 0.18, y: 3.25, w: bw - 0.36, h: 0.55,
            fontSize: 30, fontFace: FONT_HEAD, color: COL.navy, bold: false, margin: 0 });
        s.addText(b.sub, { x: bx + 0.18, y: 3.85, w: bw - 0.36, h: 0.25,
            fontSize: 9, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 1.5, margin: 0 });
        s.addText(b.body, { x: bx + 0.18, y: 4.10, w: bw - 0.36, h: 0.65,
            fontSize: 9.5, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });
        bx += bw + 0.25;
    }

    // The 60-min vs 4-min contrast
    s.addShape("rect", { x: margin, y: 4.95, w: W - 2*margin, h: 1.65,
        fill: { color: COL.bgAlt }, line: { color: COL.cardinal, width: 1.5 } });
    s.addText("60 minutes  →  4 minutes",
        { x: margin + 0.2, y: 5.05, w: W - 2*margin - 0.4, h: 0.45,
          fontSize: 22, fontFace: FONT_HEAD, color: COL.cardinal, bold: true, margin: 0 });
    s.addText("Today: pull the chart, find the right form, transcribe demographics, fax it, wait for confirmation, follow up by phone. ADHS estimates 70% of valley fever cases never make it into surveillance because the workflow takes too long. With ONE-HealthRecord: clinician clicks \"Report this case\" → modal shows every destination with the actual machine-prepared message → clinician inspects each, clicks \"Submit all\" → every agency acknowledges in parallel. The reporting obligation is closed in roughly four minutes.",
        { x: margin + 0.2, y: 5.55, w: W - 2*margin - 0.4, h: 1.05,
          fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });

    // Bottom line
    s.addText("Headline outcome — Reporting completeness target: 30% baseline → 85%. Additional ~5,000 valley fever cases captured per year statewide. Cluster lead time improvement: 30–60 days. Investigator workload reduction: 36×. Tribal-land sovereignty preserved through the destination router.",
        { x: margin, y: 6.75, w: W - 2*margin, h: 0.55,
          fontSize: 11.5, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, italic: true, margin: 0, valign: "top" });
}

// ============================================================================
// Slide 19 — Phase 8: Three-domain architecture + intake/triage + env surveillance
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Phase 8 · Three-domain architecture", "Healthcare Institutions · Public Health & Government · Environmental Surveillance");
    addNum(s, 19);

    s.addText("The One Health triad surfaced as the very first user-visible structure. Branded institutional logins for 10 partner sites. End-to-end ED workflow: registration → triage → encounter → reporting. Voice / keyboard / template encounter input. Public-access environmental surveillance across 5 government data sources.",
        { x: margin, y: 1.85, w: W - 2*margin, h: 0.95,
          fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, valign: "top", margin: 0 });

    // Three domain cards across the top
    const domains = [
        { hdr: "Healthcare Institutions", num: "10", sub: "branded sites · 38 staff", body: "6 hospitals (Banner, TMC, HonorHealth, IHS, Northern AZ) + 4 vet practices, each with institution-specific branding + role-based login. New roles: Registrar · Triage Nurse · Discharge · Lab Tech · Administrator · Vet Tech.", color: COL.navy },
        { hdr: "Public Health & Government", num: "4", sub: "agencies", body: "ADHS · Apache Tribal Health Authority · USDA APHIS · CDC NNDSS. Tribal sovereignty preserved through routing layer — aggregate-only signals reach state surveillance.", color: COL.cardinal },
        { hdr: "Environmental Surveillance", num: "5", sub: "data sources · no login", body: "EPA AirNow (14 stations) · NWS advisories · ArboNET (10 vector traps with Pinal anomaly) · USGS plague-rodent (5 sites with Coconino positive) · AGFD wildlife mortality (47-prairie-dog die-off).", color: COL.clinical },
    ];
    let bx = margin;
    const bw = (W - 2*margin - 0.5) / 3;
    for (const d of domains) {
        s.addShape("rect", { x: bx, y: 3.00, w: bw, h: 2.10, fill: { color: COL.bgAlt }, line: { color: d.color, width: 1.5 } });
        s.addText(d.hdr, { x: bx + 0.18, y: 3.10, w: bw - 0.36, h: 0.35, fontSize: 12, fontFace: FONT_HEAD, color: d.color, bold: true, margin: 0 });
        s.addText(d.num,  { x: bx + 0.18, y: 3.40, w: bw - 0.36, h: 0.55, fontSize: 30, fontFace: FONT_HEAD, color: COL.navy, margin: 0 });
        s.addText(d.sub,  { x: bx + 0.18, y: 4.00, w: bw - 0.36, h: 0.25, fontSize: 9, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 1.5, margin: 0 });
        s.addText(d.body, { x: bx + 0.18, y: 4.25, w: bw - 0.36, h: 0.85, fontSize: 9.5, fontFace: FONT_BODY, color: COL.ink2, valign: "top", margin: 0 });
        bx += bw + 0.25;
    }

    // End-to-end workflow ribbon
    s.addShape("rect", { x: margin, y: 5.30, w: W - 2*margin, h: 1.45, fill: { color: COL.bgAlt }, line: { color: COL.amber, width: 1.5 } });
    s.addText("End-to-end ED workflow now demonstrable",
        { x: margin + 0.2, y: 5.40, w: W - 2*margin - 0.4, h: 0.40, fontSize: 16, fontFace: FONT_HEAD, color: COL.amber, bold: true, margin: 0 });
    s.addText("Registrar checks in patient → eMPI federation lookup flags duplicate → Triage nurse captures vitals + ESI 1-5 acuity → Hand-off to physician → Voice / keyboard / template dictation → FHIR extraction → Cross-species cluster signal → CDS panel → ⚡ One-click multi-agency report. Every role on the demo screen, every audit-log entry, every signal preserved across the handoff.",
        { x: margin + 0.2, y: 5.85, w: W - 2*margin - 0.4, h: 0.85, fontSize: 10.5, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });

    // Bottom line
    s.addText("Architectural framing: humans + animals + environment as peer domains, not nested. The first frame of the demo is the One Health argument.",
        { x: margin, y: 6.85, w: W - 2*margin, h: 0.40, fontSize: 11.5, fontFace: FONT_HEAD, color: COL.cardinal, italic: true, margin: 0, valign: "top" });
}

// ============================================================================
// Slide 20 — Synthetic-data philosophy
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "On synthetic data", "Why this is a feature, not a bug");
    addNum(s, 20);

    s.addText("All clinical, surveillance, household, and environmental data is fully synthetic. There is no protected health information. No real Arizona resident is represented.",
        { x: margin, y: 1.95, w: W - 2*margin, h: 0.85,
          fontSize: 15, fontFace: FONT_BODY, color: COL.ink1, italic: true, margin: 0, valign: "top" });

    const cards = [
        { hdr: "Reproducible end-to-end",
          body: "Anyone with this repo can regenerate the entire bundle — 360 households, 4,676 encounters, 59 alerts — from a fixed seed. No DUA, no IRB friction, no version skew." },
        { hdr: "Edge-cases by design",
          body: "We can plant a 27σ tick anomaly in Pinal because we know the ground truth. We can guarantee a cross-species cluster exists in Hernandez. Real data doesn't let us do that for free." },
        { hdr: "Evaluation-friendly",
          body: "Gold-standard annotations are produced by the same dictionary that built the dictations — internally consistent, useful for measuring what the engine can do at all." },
        { hdr: "Pre-real-data scaffolding",
          body: "Every interface is engineered against the FHIR / SNOMED schemas that real data uses. Swap synthetic for MIMIC-IV human or VetCompass animal and the contract holds." },
    ];
    const colW = (W - 2*margin - 0.4) / 2;
    let cx = margin, cy = 3.0;
    for (let i = 0; i < cards.length; i++) {
        const c = cards[i];
        s.addShape("rect", { x: cx, y: cy + 0.07, w: 0.16, h: 0.16,
            fill: { color: COL.cardinal }, line: { color: COL.cardinal } });
        s.addText(c.hdr, {
            x: cx + 0.3, y: cy, w: colW - 0.3, h: 0.4,
            fontSize: 14, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
        s.addText(c.body, {
            x: cx + 0.3, y: cy + 0.4, w: colW - 0.3, h: 1.4,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0, valign: "top" });
        if (i % 2 === 0) {
            cx += colW + 0.4;
        } else {
            cx = margin;
            cy += 1.85;
        }
    }
}

// ============================================================================
// Slide 21 — Limitations & future work
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Limitations · future work", "What's next");
    addNum(s, 21);

    s.addText("Implemented today (rule-based)", {
        x: margin, y: 1.95, w: 6, h: 0.4,
        fontSize: 13, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, margin: 0 });
    s.addText("Future work (statistical models)", {
        x: 7.0, y: 1.95, w: 6, h: 0.4,
        fontSize: 13, fontFace: FONT_BODY, color: COL.ink3, charSpacing: 3, bold: true, margin: 0 });

    const rows = [
        ["Gazetteer NER (25 conds, 20 sx)",     "BioClinicalBERT fine-tuned on i2b2 + n2c2"],
        ["Sentence-bounded negation/hedge",     "ConText / NegBio implementation"],
        ["NetworkX MultiDiGraph",                "Neo4j + GNN cluster detection"],
        ["3-model risk bake-off (LR/RF/GBM)",    "Calibrated ensemble + per-disease specialist heads"],
        ["SHAP + permutation + DT explainability", "Counterfactual (DiCE) + attention attribution"],
        ["3-tier contact tracing (synthetic)",  "Geospatial + mobility-graph contact propagation"],
        ["LLM benchmark vs Haiku 4.5 (projected)", "Live API run + prompt-engineering A/B"],
        ["Synthetic 25-dictation NER eval",      "MIMIC-IV human + VetCompass veterinary eval"],
        ["Text-only dictation",                  "Whisper ASR + dialogue segmentation"],
        ["Laplace-noise privacy stub",           "Full DP-SGD with formal ε, δ accounting"],
    ];
    let yr = 2.45;
    for (const [now, future] of rows) {
        s.addShape("rect", { x: margin, y: yr + 0.10, w: 0.10, h: 0.10,
            fill: { color: COL.grn }, line: { color: COL.grn } });
        s.addText(now, { x: margin + 0.22, y: yr, w: 5.8, h: 0.4,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink1, margin: 0 });
        s.addShape("rightTriangle", { x: 6.4, y: yr + 0.05, w: 0.2, h: 0.2,
            fill: { color: COL.ink3 }, line: { color: COL.ink3 }, rotate: 90 });
        s.addText(future, { x: 7.0, y: yr, w: 6.0, h: 0.4,
            fontSize: 12, fontFace: FONT_BODY, color: COL.ink2, italic: true, margin: 0 });
        yr += 0.42;
    }

    s.addText("These are tractable next-steps with a credentialed dataset. The interfaces, schemas, and evaluation harness are already in place.",
        { x: margin, y: 6.65, w: W - 2*margin, h: 0.4,
          fontSize: 11, fontFace: FONT_BODY, color: COL.ink3, italic: true, align: "center", margin: 0 });
}

// ============================================================================
// Slide 22 — Contributions
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.bg);
    smallTitle(s, "Contributions", "What this capstone delivers");
    addNum(s, 22);

    const contribs = [
        ["1.", "End-to-end pipeline", "Clinician dictation → FHIR R4 Bundle with Provenance, ~1.2 ms per encounter on CPU."],
        ["2.", "Role-based two-hub UI", "Clinical Workspace (clinicians + vets) and Public Health Console (ADHS + tribal health + audit). Mirrors Epic Hyperspace / Cerner Cogito separation."],
        ["3.", "Predictive risk model + explainability + equity", "LR/RF/GBM bake-off on 4,676 encounters; gradient boosting at AUROC 0.910 / Brier 0.0059. SHAP + permutation + decision tree. 14-pp tribal-land AUC gap surfaced."],
        ["4.", "Risk-triaged contact tracing & lead time", "3-tier strategy. 100% sens@0.20, 80% prec@0.50. 71-day lead time on Hernandez household."],
        ["5.", "MedGemma 4B + species router", "Pre-built clinical LLM, three-layer veterinary adaptation. Layer A shipping; B and C scaffolded."],
        ["6.", "Privacy-preserving training", "Swarm learning + DP-SGD + secure aggregation + Laplace. Federated AUC 0.900 vs centralized 0.826 (+0.074) on simulation."],
        ["7.", "Role-based access control", "Login + panel-based patient filtering + 3-tier cross-species model pointer + defense in depth + visible audit log."],
        ["8.", "Live Model Card", "Mitchell (2019) format, 7 sections rendered as live HTML including audit surface."],
    ];
    let yc = 1.85;
    for (const [n, hdr, body] of contribs) {
        s.addText(n, { x: margin, y: yc, w: 0.55, h: 0.5,
            fontSize: 18, fontFace: FONT_HEAD, color: COL.cardinal, bold: false, align: "left", margin: 0 });
        s.addText(hdr, { x: margin + 0.6, y: yc + 0.02, w: 4.3, h: 0.4,
            fontSize: 12, fontFace: FONT_HEAD, color: COL.navy, bold: true, margin: 0 });
        s.addText(body, { x: margin + 5.0, y: yc - 0.02, w: 7.5, h: 0.80,
            fontSize: 10, fontFace: FONT_BODY, color: COL.ink1, valign: "top", margin: 0 });
        yc += 0.62;
    }
}

// ============================================================================
// Slide 23 — Thank you / Q&A
// ============================================================================
{
    const s = pres.addSlide();
    setBg(s, COL.navy);
    s.addText("Thank you.", {
        x: 0.7, y: 2.4, w: 12, h: 1.2,
        fontSize: 72, fontFace: FONT_HEAD, color: "FFFFFF", bold: false, margin: 0 });
    s.addText("Questions?", {
        x: 0.7, y: 3.7, w: 12, h: 0.7,
        fontSize: 32, fontFace: FONT_HEAD, color: COL.amber, italic: true, margin: 0 });

    s.addShape("rect", { x: 0.7, y: 5.0, w: 0.32, h: 0.32,
        fill: { color: COL.cardinal }, line: { color: COL.cardinal } });
    s.addText("Live demo: open app/index.html in any browser. No install required.",
        { x: 1.15, y: 4.95, w: 11, h: 0.4,
          fontSize: 14, color: "C8CCD2", fontFace: FONT_BODY, margin: 0 });
    s.addText("Repository: docs/model_card.md · docs/evaluation_report.md · src/ — all reproducible from seed=42.",
        { x: 0.7, y: 5.55, w: 12, h: 0.4,
          fontSize: 12, color: "8B92A1", fontFace: FONT_BODY, italic: true, margin: 0 });
}

// ============================================================================
pres.writeFile({ fileName: "/home/claude/one-healthrecord/docs/ONE-HealthRecord_Capstone.pptx" })
    .then(f => { console.log("Wrote: " + f); })
    .catch(e => { console.error(e); process.exit(1); });
