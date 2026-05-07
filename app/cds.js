/* ============================================================================
 * Phase 6 — Closed-loop CDS UI module.
 *
 * When a confirmed reportable disease is in scope (the patient has an
 * active condition matching one of the 14 One Health diseases), this
 * module renders a sticky CDS panel offering:
 *
 *   1. Pre-populated order set keyed to the disease (LOINC + CPT codes)
 *   2. One-click NNDSS report submission (human side, HL7 v2.5.1 ELR)
 *      OR one-click VSPS report submission (animal side, USDA APHIS)
 *   3. Patient handouts in 4 languages
 *   4. Alert state machine display (fired → acknowledged → ordered →
 *      resulted → reported → closed)
 *
 * The panel is rendered in the right column under the cross-species
 * pointer when a relevant condition is detected. State is held in
 * memory; in production it would persist as FHIR Task / Communication
 * resources scoped to the encounter.
 * ========================================================================== */

(function () {
    'use strict';

    // Order sets keyed to disease_id. Each line carries a real code:
    //   LOINC for labs, CPT for imaging/procedures, RxNorm for medications.
    const ORDER_SETS = {
        valley_fever: {
            display: "Coccidioidomycosis (Valley Fever) workup",
            orders: [
                { type: "lab",   code: "6435-2",   system: "LOINC", name: "Coccidioides antibody.IgM (CF/IgM)", priority: "stat", checked: true },
                { type: "lab",   code: "31698-7",  system: "LOINC", name: "Coccidioides antibody.IgG (EIA/IgG)", priority: "stat", checked: true },
                { type: "lab",   code: "58410-2",  system: "LOINC", name: "CBC with differential", priority: "routine", checked: true },
                { type: "lab",   code: "24323-8",  system: "LOINC", name: "Comprehensive metabolic panel (CMP)", priority: "routine", checked: true },
                { type: "imaging", code: "71046",  system: "CPT",   name: "Chest X-ray, 2 views", priority: "routine", checked: true },
                { type: "med",   code: "4452",     system: "RxNorm", name: "Fluconazole 200 mg PO BID × 6 months", priority: "outpatient", checked: false, note: "Hold pending serology" },
            ],
        },
        rmsf: {
            display: "Rocky Mountain Spotted Fever workup (suspect)",
            orders: [
                { type: "med",   code: "10395",    system: "RxNorm", name: "Doxycycline 100 mg PO BID — START EMPIRICALLY", priority: "stat", checked: true, note: "Do NOT wait for serology — RMSF mortality rises sharply after day 5 of illness." },
                { type: "lab",   code: "29445-6",  system: "LOINC", name: "R. rickettsii IgM antibody", priority: "stat", checked: true },
                { type: "lab",   code: "29446-4",  system: "LOINC", name: "R. rickettsii IgG antibody (acute)", priority: "stat", checked: true },
                { type: "lab",   code: "58410-2",  system: "LOINC", name: "CBC with differential — look for thrombocytopenia", priority: "stat", checked: true },
                { type: "lab",   code: "24323-8",  system: "LOINC", name: "CMP — look for hyponatremia, transaminitis", priority: "stat", checked: true },
            ],
        },
        plague: {
            display: "Plague (Yersinia pestis) workup",
            orders: [
                { type: "med",   code: "9533",     system: "RxNorm", name: "Streptomycin 1 g IM q12h × 10 days OR Gentamicin 5 mg/kg/day", priority: "stat", checked: true, note: "Alternative: Doxycycline 100 mg PO BID" },
                { type: "lab",   code: "5028-7",   system: "LOINC", name: "Y. pestis culture (blood × 2 + lymph node aspirate)", priority: "stat", checked: true, note: "BSL-3 — alert lab in advance" },
                { type: "lab",   code: "32717-7",  system: "LOINC", name: "Y. pestis F1 antigen rapid test", priority: "stat", checked: true },
                { type: "imaging", code: "71046",  system: "CPT",   name: "Chest X-ray — rule out pneumonic plague", priority: "stat", checked: true },
                { type: "isolation", code: "ISO",  system: "internal", name: "Droplet isolation — possible pneumonic transmission risk", priority: "stat", checked: true },
            ],
        },
        west_nile: {
            display: "West Nile Virus workup",
            orders: [
                { type: "lab",   code: "31200-6",  system: "LOINC", name: "WNV IgM antibody (serum + CSF if neuro)", priority: "stat", checked: true },
                { type: "lab",   code: "31201-4",  system: "LOINC", name: "WNV IgG antibody", priority: "stat", checked: true },
                { type: "lab",   code: "58410-2",  system: "LOINC", name: "CBC", priority: "routine", checked: true },
                { type: "imaging", code: "70551",  system: "CPT",   name: "MRI brain (if neurologic signs)", priority: "stat", checked: false, note: "Order if any focal neurologic deficit" },
            ],
        },
        ehrlichiosis: {
            display: "Ehrlichiosis workup",
            orders: [
                { type: "med",   code: "10395",    system: "RxNorm", name: "Doxycycline 100 mg PO BID × 7-14d — START EMPIRICALLY", priority: "stat", checked: true },
                { type: "lab",   code: "33013-0",  system: "LOINC", name: "Ehrlichia chaffeensis IgG IFA", priority: "stat", checked: true },
                { type: "lab",   code: "58410-2",  system: "LOINC", name: "CBC — look for leukopenia, thrombocytopenia", priority: "stat", checked: true },
                { type: "lab",   code: "24323-8",  system: "LOINC", name: "CMP — look for transaminitis", priority: "stat", checked: true },
            ],
        },
    };

    // Alert state machine — order is meaningful
    const STATES = ["fired", "acknowledged", "ordered", "resulted", "reported", "closed"];
    const STATE_LABELS = {
        fired:        "Fired (model-flagged)",
        acknowledged: "Acknowledged by clinician",
        ordered:      "Workup ordered",
        resulted:     "Lab results in",
        reported:     "Reported to ADHS / APHIS",
        closed:       "Closed",
    };

    // In-memory state for the demo. In production, persisted as FHIR Task.
    const ALERT_STATE = {};   // key: alert_id (or condition_id) → state

    function _getState(key) { return ALERT_STATE[key] || "fired"; }
    function _setState(key, s) { ALERT_STATE[key] = s; renderCDSPanel(window._OHR_LAST_CDS_CTX); }

    // Map common condition names → disease_id, used as a fallback when the
    // handcrafted household conditions don't carry _one_health.disease_id.
    const NAME_TO_DISEASE = [
        [/coccidioid|valley\s*fever/i, "valley_fever"],
        [/rocky\s*mountain|spotted\s*fever|rmsf/i, "rmsf"],
        [/plague|yersinia/i, "plague"],
        [/west\s*nile|wnv/i, "west_nile"],
        [/hantavirus|hps/i, "hantavirus"],
        [/ehrlichi/i, "ehrlichiosis"],
        [/leptospir/i, "leptospirosis"],
        [/q\s*fever|coxiella/i, "q_fever"],
    ];
    function _diseaseIdFromCondition(c) {
        const did = (c._one_health || {}).disease_id;
        if (did) return did;
        const text = ((c.code && c.code.text) || "") + " " + ((c.code && (c.code.coding || [])[0] && c.code.coding[0].display) || "");
        for (const [re, id] of NAME_TO_DISEASE) {
            if (re.test(text)) return id;
        }
        return null;
    }

    /**
     * Detect the disease in scope from a household + selected patient.
     * Returns { disease_id, condition, role } or null.
     */
    function _detectDisease(hh, p) {
        const conditions = hh.conditions || [];
        // Prefer conditions on the selected subject; if none, try any household condition
        const onSubject = conditions.filter(c => {
            const ref = (c.subject && c.subject.reference) || "";
            return ref === p.ref;
        });
        const pool = onSubject.length ? onSubject : conditions;
        for (const c of pool) {
            const did = _diseaseIdFromCondition(c);
            if (did && ORDER_SETS[did]) {
                return {
                    disease_id: did,
                    condition: c,
                    order_set: ORDER_SETS[did],
                };
            }
        }
        return null;
    }

    /**
     * Public render entry point. Called by app.js renderContext()
     * after the cross-species pointer is decided.
     *
     *   ctx = { hh, patient, isAnimal, sessionRole, container }
     */
    function renderCDSPanel(ctx) {
        if (!ctx) return;
        window._OHR_LAST_CDS_CTX = ctx;
        const { hh, patient, isAnimal, sessionRole, container } = ctx;
        if (!container) return;

        const detected = _detectDisease(hh, patient);
        if (!detected) {
            container.innerHTML = "";
            return;
        }

        const did = detected.disease_id;
        const os = detected.order_set;
        const condId = detected.condition.id || (did + "-" + (patient.ref || ""));
        const state = _getState(condId);
        const stateIdx = STATES.indexOf(state);

        // Disease metadata for the report panel
        const reportTarget = isAnimal
            ? "USDA APHIS VSPS + Arizona Department of Agriculture"
            : "Arizona Department of Health Services (NNDSS)";

        container.innerHTML = `
        <div class="cds-panel" style="margin-top: 14px;">
            <div class="cds-header">
                <span class="cds-title">CDS · ${escapeHtml(os.display)}</span>
                <span class="cds-disposition">closed-loop</span>
            </div>

            <div class="cds-state-machine">
                ${STATES.map((s, i) => `
                    <div class="cds-state ${i <= stateIdx ? 'reached' : 'pending'} ${i === stateIdx ? 'current' : ''}"
                         data-state="${s}">
                        <span class="cds-state-num">${i+1}</span>
                        <span class="cds-state-label">${escapeHtml(STATE_LABELS[s])}</span>
                    </div>
                `).join("")}
            </div>

            <div class="cds-section">
                <h4>Pre-populated order set</h4>
                <div class="cds-orders">
                    ${os.orders.map((o, i) => `
                        <label class="cds-order-row">
                            <input type="checkbox" ${o.checked ? 'checked' : ''} data-cds-order="${i}">
                            <div class="cds-order-body">
                                <div class="cds-order-name">${escapeHtml(o.name)}</div>
                                <div class="cds-order-meta">
                                    <span class="cds-order-type">${escapeHtml(o.type)}</span>
                                    <code>${escapeHtml(o.system)}:${escapeHtml(o.code)}</code>
                                    <span class="cds-order-priority cds-priority-${escapeHtml(o.priority)}">${escapeHtml(o.priority)}</span>
                                </div>
                                ${o.note ? `<div class="cds-order-note">${escapeHtml(o.note)}</div>` : ''}
                            </div>
                        </label>
                    `).join("")}
                </div>
                <button class="cds-action-btn cds-primary" data-cds-action="sign-orders">Sign and submit orders</button>
            </div>

            <div class="cds-section">
                <h4>One-click reportable disease push</h4>
                <p class="cds-section-blurb">
                    Confirmed reportable. Auto-generates <strong>${isAnimal ? 'USDA VS Form 1-7 / VSPS payload' : 'HL7 v2.5.1 ELR (NNDSS condition code)'}</strong>
                    and pushes to <strong>${escapeHtml(reportTarget)}</strong>. Reduces a 60-minute paper-based workflow to one click.
                </p>
                <div class="cds-action-row">
                    <button class="cds-action-btn cds-primary" data-cds-action="${isAnimal ? 'submit-vsps' : 'submit-nndss'}">
                        ${isAnimal ? 'Generate &amp; submit VSPS report' : 'Generate &amp; submit NNDSS ELR'}
                    </button>
                    <button class="cds-action-btn" data-cds-action="${isAnimal ? 'preview-vsps' : 'preview-nndss'}">Preview message</button>
                </div>
            </div>

            <div class="cds-section">
                <h4>Patient handouts</h4>
                <p class="cds-section-blurb">
                    Plain-language disease handouts auto-generated for the patient.
                </p>
                <div class="cds-action-row">
                    <button class="cds-handout-btn" data-cds-action="handout-en"  data-cds-disease="${did}">English (PDF)</button>
                    <button class="cds-handout-btn" data-cds-action="handout-es"  data-cds-disease="${did}">Español (PDF)</button>
                    <button class="cds-handout-btn cds-pending" data-cds-action="handout-nv"  data-cds-disease="${did}" title="Pending tribal-IRB-vetted translator">Diné Bizaad <span class="cds-pending-badge">pending</span></button>
                    <button class="cds-handout-btn cds-pending" data-cds-action="handout-apw" data-cds-disease="${did}" title="Pending tribal-IRB-vetted translator">Ndee Biyáti' <span class="cds-pending-badge">pending</span></button>
                </div>
            </div>

            <div class="cds-meta">
                <strong>Provenance:</strong> Order set scaffolded from CDC/IDSA guidelines for ${escapeHtml(os.display)}; clinician retains full override authority.
                <strong>Synthetic:</strong> Reportable submission goes to a stub endpoint, not real ADHS / APHIS infrastructure.
            </div>
        </div>`;

        // Wire actions
        container.querySelectorAll('[data-cds-action]').forEach(btn => {
            btn.addEventListener('click', e => {
                e.preventDefault();
                const action = btn.dataset.cdsAction;
                handleCDSAction(action, ctx, detected, condId);
            });
        });
    }

    function handleCDSAction(action, ctx, detected, condId) {
        if (action === "sign-orders") {
            _setState(condId, "ordered");
            _toast(`Orders signed and routed to lab/imaging. Workup in progress.`);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("cds_orders_signed", detected.disease_id);
        }
        else if (action === "submit-nndss" || action === "submit-vsps") {
            _setState(condId, "reported");
            const isVsps = action === "submit-vsps";
            const caseId = (isVsps ? "AZ-VS-" : "AZ-NNDSS-") +
                Math.random().toString(36).slice(2, 10).toUpperCase();
            _toast(`Case submitted. ${isVsps ? "USDA APHIS" : "ADHS NNDSS"} case ID: ${caseId}.`);
            if (window.OH_AUTH) window.OH_AUTH.auditLog(isVsps ? "cds_vsps_submitted" : "cds_nndss_submitted", detected.disease_id + ":" + caseId);
        }
        else if (action === "preview-nndss") {
            _showMessagePreview(detected, ctx, "nndss");
        }
        else if (action === "preview-vsps") {
            _showMessagePreview(detected, ctx, "vsps");
        }
        else if (action.startsWith("handout-")) {
            const lang = action.split("-")[1];
            const did = detected.disease_id;
            const url = "handouts/" + did + "_" + lang + ".pdf";
            if (lang === "en" || lang === "es") {
                window.open(url, "_blank");
            } else {
                _toast("Translation pending tribal-IRB-vetted translator. Template scaffolded; do not distribute until reviewed.");
            }
        }
    }

    function _toast(msg) {
        let t = document.getElementById("cds-toast");
        if (!t) {
            t = document.createElement("div");
            t.id = "cds-toast";
            t.className = "cds-toast";
            document.body.appendChild(t);
        }
        t.textContent = msg;
        t.classList.add("show");
        setTimeout(() => t.classList.remove("show"), 4500);
    }

    function _showMessagePreview(detected, ctx, kind) {
        // Build a representative HL7 ELR or VSPS JSON preview client-side.
        // The real generators (NNDSS HL7 v2.5.1 + VSPS JSON) live server-side
        // in src/cds/; this is a faithful shorter preview for the modal.
        const did = detected.disease_id;
        const cond = detected.condition;
        const patient = ctx.patient;
        const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
        const caseId = (kind === "vsps" ? "AZ-VS-" : "AZ-") + ts.slice(0, 8) + "-" + (patient.id || "0").slice(0, 8);

        const NNDSS_CODES = {
            valley_fever:  ["11020", "Coccidioidomycosis"],
            rmsf:          ["10250", "Spotted Fever Rickettsiosis"],
            plague:        ["10080", "Plague"],
            west_nile:     ["10056", "West Nile virus disease"],
            hantavirus:    ["11590", "Hantavirus pulmonary syndrome"],
            ehrlichiosis:  ["10075", "Ehrlichiosis/Anaplasmosis"],
            leptospirosis: ["10090", "Leptospirosis"],
            q_fever:       ["10260", "Q fever"],
        };
        const code = NNDSS_CODES[did] || ["00000", did];

        let body;
        if (kind === "nndss") {
            body = [
                "MSH|^~\\&|ONE-HealthRecord^2.16.840.1.113883.3.AZ-OHR^ISO|TMC^03D9999999^CLIA|ADHS-MEDSIS^2.16.840.1.113883.3.4321^ISO|ADHS^04^FIPS|" + ts + "||ORU^R01^ORU_R01|OHR-" + ts + "|P|2.5.1",
                "PID|1||" + (patient.id || "").slice(0, 16) + "^^^&2.16.840.1.113883.3.AZ-OHR&ISO^MR||" + escapeHtml(patient.last_name || "") + "^" + escapeHtml(patient.first_name || "") + "||" + (patient.dob || "").replace(/-/g, "") + "|" + (patient.gender || "U")[0].toUpperCase() + "|||^^^AZ^^USA",
                "ORC|RE|" + caseId + "^OHR|" + caseId + "^ADHS||CM|||" + ts,
                "OBR|1|" + caseId + "^OHR|" + caseId + "^ADHS|" + code[0] + "^" + code[1] + "^CDCNNDSS",
                "OBX|1|CWE|6435-2^Coccidioides antibody.IgM^LN||Positive||Negative|A|||F",
                "SPM|1|" + caseId + "-SPM^OHR||SER^Serum^HL70487",
                "NTE|1|L|Reportable: " + code[1] + ". Submitted via ONE-HealthRecord one-click reporting."
            ].join("\n");
        } else {
            const APHIS = {
                rmsf:           { name: "Rocky Mountain Spotted Fever (canine)", reportable: ["AZ-ADA"] },
                plague:         { name: "Plague (Yersinia pestis) — animal case", reportable: ["USDA-APHIS", "AZ-ADA", "ADHS-cross-species"] },
                west_nile:      { name: "West Nile virus disease — equine/avian", reportable: ["USDA-APHIS", "AZ-ADA", "ADHS-cross-species"] },
                ehrlichiosis:   { name: "Canine Ehrlichiosis", reportable: ["AZ-ADA"] },
                rabies:         { name: "Rabies — animal confirmed/suspect", reportable: ["USDA-APHIS", "AZ-ADA", "ADHS-cross-species"] },
            };
            const meta = APHIS[did] || { name: did, reportable: ["AZ-ADA"] };
            body = JSON.stringify({
                report_metadata: { case_id: caseId, submission_date: new Date().toISOString(), submitting_system: "ONE-HealthRecord" },
                disease: { common_name: meta.name, internal_disease_id: did },
                animal: { animal_id: patient.id, name: patient.first_name, household_id: ctx.hh.household_id },
                destinations: meta.reportable.map(r => ({ agency: r })),
                one_health_context: { cross_species_sentinel: true, sentinel_direction: "animal_to_human" },
            }, null, 2);
        }

        const m = document.createElement("div");
        m.className = "cds-modal-backdrop";
        m.innerHTML = `
            <div class="cds-modal">
                <div class="cds-modal-head">
                    <h3>${kind === "nndss" ? "HL7 v2.5.1 ELR — NNDSS push (preview)" : "USDA APHIS VSPS payload (preview)"}</h3>
                    <button class="cds-modal-close" type="button">&times;</button>
                </div>
                <div class="cds-modal-body">
                    <div class="cds-modal-meta">
                        Destination: <strong>${kind === "nndss" ? "ADHS-MEDSIS" : "USDA APHIS Region 7 + AZ Dept of Agriculture"}</strong> ·
                        Case ID: <code>${caseId}</code> ·
                        Format: <code>${kind === "nndss" ? "HL7 v2.5.1 ELR R-2" : "JSON (VS Form 1-7 equivalent)"}</code>
                    </div>
                    <pre class="cds-modal-pre">${escapeHtml(body)}</pre>
                </div>
                <div class="cds-modal-foot">
                    <span style="color: var(--ink-3); font-size:0.78rem;">Synthetic preview. Real submission requires production credentials.</span>
                    <button class="cds-action-btn cds-primary" type="button" data-close>Close</button>
                </div>
            </div>`;
        document.body.appendChild(m);
        m.querySelectorAll(".cds-modal-close, [data-close]").forEach(b => {
            b.addEventListener("click", () => m.remove());
        });
        m.addEventListener("click", e => { if (e.target === m) m.remove(); });
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g,
            c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
    }

    // Public surface
    window.OH_CDS = { renderCDSPanel };
})();
