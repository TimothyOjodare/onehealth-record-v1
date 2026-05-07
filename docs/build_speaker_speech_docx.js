/* Build the SPEAKER_SPEECH.docx — every slide's speech, formatted for podium reading. */

const fs = require('fs');
const path = require('path');
const {
    Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel,
    PageBreak, BorderStyle, Header, Footer, PageNumber, LineRuleType,
    ShadingType, LevelFormat
} = require('docx');

// Load the speaker notes
const notesPath = path.join(__dirname, "speaker_notes.js");
const code = fs.readFileSync(notesPath, "utf8") + "\nmodule.exports = SPEAKER_NOTES;";
const m = { exports: {} };
new Function("module", "exports", "require", code)(m, m.exports, require);
const NOTES = m.exports;

// Slide titles for the section headers
const SLIDE_TITLES = {
    1:  ["Title", "ONE-HealthRecord · Capstone presentation"],
    2:  ["The problem", "One Health is invisible in the chart"],
    3:  ["Thesis", "Machine-authored. FAIR-by-construction."],
    4:  ["System architecture", "From dictation to public-health insight"],
    5:  ["Live demo · scenario 1", "The Hernandez Valley Fever cluster"],
    6:  ["Cross-species knowledge graph", "2,188 nodes · 2,219 edges"],
    7:  ["Sentinel surveillance", "Pinal County tick anomaly"],
    8:  ["Provider workspace", "Real-time One Health context for clinicians and vets"],
    9:  ["Trust mechanism", "Clinician hand-back for low-confidence extractions"],
    10: ["Evaluation", "Synthetic gold-standard, n = 25 dictations, 138 entities"],
    11: ["Predictive modelling", "Zoonotic-cluster risk · 3-model bake-off"],
    12: ["Explainability & equity", "SHAP attribution + disaggregated performance"],
    13: ["Public-health metrics", "Contact tracing · risk-triaged sensitivity · lead time"],
    14: ["Phase 3 · Privacy architecture", "Swarm learning · DP-SGD · secure aggregation"],
    15: ["Phase 3 · MedGemma + species router", "Pre-built clinical LLM, adapted for human + veterinary"],
    16: ["Phase 4 · Access control", "Login · role gating · cross-species redaction · audit log"],
    17: ["Phase 6 · Federation + CDS", "Per-site FHIR shadow stores · consent · one-click reporting"],
    18: ["Phase 7 · Reportable Disease Coverage", "72 diseases across 5 authorities · 234 cases · multi-agency push"],
    19: ["Phase 8 · Three-domain architecture", "Healthcare · Public Health · Environmental Surveillance"],
    20: ["On synthetic data", "Why this is a feature, not a bug"],
    21: ["Limitations · future work", "What's next"],
    22: ["Contributions", "What this capstone delivers"],
    23: ["Thank you / Q & A", ""],
};

// Inline parser for **bold** and *italic*
function inline(text, baseStyle = {}) {
    const runs = [];
    let i = 0;
    while (i < text.length) {
        if (text[i] === '*' && text[i+1] === '*') {
            const end = text.indexOf('**', i + 2);
            if (end === -1) { runs.push(new TextRun({text: cleanText(text.slice(i)), ...baseStyle})); break; }
            runs.push(new TextRun({text: cleanText(text.slice(i + 2, end)), bold: true, ...baseStyle}));
            i = end + 2;
        } else if (text[i] === '*') {
            // single asterisk — italic span
            const end = text.indexOf('*', i + 1);
            if (end === -1) {
                // unmatched lone asterisk — treat as literal
                runs.push(new TextRun({text: cleanText(text.slice(i)), ...baseStyle}));
                break;
            }
            runs.push(new TextRun({text: cleanText(text.slice(i + 1, end)), italics: true, ...baseStyle}));
            i = end + 1;
        } else {
            const next = text.indexOf('*', i);
            const stop = next === -1 ? text.length : next;
            runs.push(new TextRun({text: cleanText(text.slice(i, stop)), ...baseStyle}));
            i = stop;
        }
    }
    return runs;
}

function cleanText(s) {
    return s
        .replace(/'/g, '\u2019')
        .replace(/(\s|^)"/g, '$1\u201C')
        .replace(/"/g, '\u201D')
        .replace(/--/g, '\u2014');
}

// A spoken-paragraph: 13pt Garamond, 1.5 line spacing, generous margins
function speech(text) {
    return new Paragraph({
        children: inline(text, { size: 26, font: "Garamond" }),  // 13pt
        spacing: { line: 380, lineRule: LineRuleType.AUTO, after: 240 },
    });
}

// Slide section title
function slideHeading(num, title, subtitle) {
    const out = [];
    out.push(new Paragraph({
        children: [new TextRun({
            text: `SLIDE ${num} OF 23`, bold: true, size: 18, color: "AB0520",
        })],
        spacing: { after: 60 },
    }));
    out.push(new Paragraph({
        children: [new TextRun({
            text: title, bold: true, size: 36, color: "0C234B", font: "Garamond",
        })],
        spacing: { after: 60 },
    }));
    if (subtitle) {
        out.push(new Paragraph({
            children: [new TextRun({
                text: subtitle, italics: true, size: 22, color: "4A4F58", font: "Garamond",
            })],
            spacing: { after: 200 },
        }));
    }
    out.push(new Paragraph({
        children: [new TextRun("")],
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "AB0520", space: 8 } },
        spacing: { after: 240 },
    }));
    return out;
}

// Build the document
const children = [];

// Cover page
children.push(new Paragraph({
    children: [new TextRun({ text: "SPEAKER SPEECH", bold: true, size: 18, color: "AB0520" })],
    spacing: { after: 60 },
}));
children.push(new Paragraph({
    children: [new TextRun({
        text: "ONE-HealthRecord", bold: true, size: 56, color: "0C234B", font: "Garamond",
    })],
    spacing: { after: 60 },
}));
children.push(new Paragraph({
    children: [new TextRun({
        text: "Capstone certification presentation · 23 slides · ~25 minutes spoken",
        italics: true, size: 26, color: "4A4F58", font: "Garamond",
    })],
    spacing: { after: 280 },
}));

// Usage notes
children.push(new Paragraph({
    children: [new TextRun({
        text: "How to use this document",
        bold: true, size: 30, color: "0C234B", font: "Garamond",
    })],
    spacing: { after: 120 },
}));

const usageNotes = [
    "Read at presentation pace — roughly 130 words per minute. The full speech, spoken at this pace, runs about 25 minutes. Combined with the 6:30 OPENING_PITCH read at the start, the full session lands at approximately 32 minutes, leaving generous time for the panel\u2019s questions.",
    "Each slide\u2019s speech is on its own page, with the slide number and title printed at the top. Place this document on the lectern. Click forward through the deck. Read each speech as the slide is on screen.",
    "Where the speech says \u201C[your name]\u201D in slide 1, fill in your name. Where it says \u201C[morning/afternoon]\u201D, choose the appropriate time of day. There are no other placeholders.",
    "Bold text is for emphasis \u2014 land those phrases with a slight pause and lower volume. Italic text indicates names of people, papers, and proper nouns. Em-dashes mark natural breath points.",
    "Speaker notes are also embedded directly in the .pptx file. If you present from PowerPoint or Keynote in Presenter Mode, you will see the same speech on your laptop screen while the panel sees only the slide. This Word document is the printed backup, in case the laptop fails.",
    "If you lose your place, the safest re-entry points are the slide titles. Pause, look down, find the slide, find the speech, resume. The panel will not penalize a brief pause; they will penalize unprepared improvisation.",
];

usageNotes.forEach(note => {
    children.push(new Paragraph({
        children: inline(note, { size: 22, font: "Garamond" }),
        spacing: { line: 320, lineRule: LineRuleType.AUTO, after: 140 },
    }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// One page per slide
for (let i = 1; i <= 23; i++) {
    const [title, subtitle] = SLIDE_TITLES[i] || ["", ""];
    const speech_text = NOTES[i] || "";

    slideHeading(i, title, subtitle).forEach(p => children.push(p));

    // Split the speech into paragraphs (speaker notes are written with \n\n separators)
    const paragraphs = speech_text.split(/\n\s*\n/).filter(p => p.trim());
    paragraphs.forEach(para => {
        // Each paragraph: collapse internal newlines to spaces for prose flow
        const collapsed = para.replace(/\s*\n\s*/g, " ").trim();
        children.push(speech(collapsed));
    });

    if (i < 23) children.push(new Paragraph({ children: [new PageBreak()] }));
}

// Build document
const doc = new Document({
    creator: "ONE-HealthRecord",
    title: "Speaker Speech \u2014 ONE-HealthRecord Capstone",
    description: "Certification panel presentation, 23 slides, ~25 minutes spoken.",
    styles: {
        default: {
            document: { run: { font: "Garamond", size: 26 } },
        },
    },
    sections: [{
        properties: {
            page: {
                size: { width: 12240, height: 15840 },               // US Letter
                margin: { top: 1440, right: 1620, bottom: 1440, left: 1620 },
            },
        },
        headers: {
            default: new Header({
                children: [new Paragraph({
                    children: [new TextRun({
                        text: "ONE-HealthRecord  \u00B7  Speaker Speech  \u00B7  Capstone Presentation",
                        size: 18, color: "AB0520",
                    })],
                    alignment: AlignmentType.RIGHT,
                })],
            }),
        },
        footers: {
            default: new Footer({
                children: [new Paragraph({
                    children: [
                        new TextRun({ text: "Page ", size: 18, color: "888888" }),
                        new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" }),
                        new TextRun({ text: " of ", size: 18, color: "888888" }),
                        new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: "888888" }),
                    ],
                    alignment: AlignmentType.CENTER,
                })],
            }),
        },
        children,
    }],
});

Packer.toBuffer(doc).then(buf => {
    const out = path.join(__dirname, 'SPEAKER_SPEECH.docx');
    fs.writeFileSync(out, buf);
    console.log("Wrote:", out, `(${(buf.length/1024).toFixed(1)} KB)`);
});
