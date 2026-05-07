/* ============================================================================
 * Phase 7 — Multi-agency reportable-disease push.
 *
 * Public surface:
 *   OH_REPORT.findReportable(condition)    → reportability metadata or null
 *   OH_REPORT.findReportablesForPatient(patient_ref, hh) → array of conditions
 *   OH_REPORT.openReportPanel(condition, ctx)             → opens modal
 *
 * What the panel shows:
 *   - Disease name + reporting timeline (immediate / one-day / five-day)
 *   - Destinations list — every agency that needs this case, with the form/
 *     format each one expects
 *   - Per-agency message preview tabs — clinician can tap each to inspect
 *     the actual generated message before submission
 *   - "Edit before sending" toggle on non-immediate cases
 *   - "Submit all" button — fires every destination in parallel; shows
 *     per-agency acknowledgement receipts on return
 *
 * Once the cases is reported, we mark it on the in-memory state so the
 * "Report this case" badge changes to a "Reported" pill.
 * ========================================================================== */

(function () {
    'use strict';

    // Per-condition state machine (in-memory only for the demo; in production
    // these would be FHIR Task resources persisted at each destination).
    //   key = condition_id, value = "unreported" | "submitted" | "ack_received"
    const REPORT_STATE = {};

    // Agency contact metadata — used to build the destination cards
    const AGENCIES = {
        adhs: {
            name: "Arizona Department of Health Services",
            short_name: "ADHS",
            endpoint: "https://surveillance.adhs.az.example/r4/$nndss-elr",
            format: "HL7 v2.5.1 ELR R-2",
            phone: "602-364-3676",
            description: "State-level human reportable disease registry. Forwards to CDC NNDSS automatically.",
        },
        cdc_nndss: {
            name: "CDC National Notifiable Diseases Surveillance System",
            short_name: "CDC NNDSS",
            endpoint: "https://nndss.cdc.gov/r4/$case-notification",
            format: "HL7 v2.5.1 ELR (forwarded by ADHS)",
            phone: "—",
            description: "Federal surveillance. Receives forwarded reports from state authorities.",
        },
        local_health_dept: {
            name: "Local County Health Department (case investigation)",
            short_name: "Local Health",
            endpoint: "Routed by ADHS based on patient county-of-residence",
            format: "Case-investigation queue entry",
            phone: "varies by county",
            description: "Performs contact tracing, household outreach, public-health response.",
        },
        tribal_if_applicable: {
            name: "Tribal Health Authority (if applicable)",
            short_name: "Tribal Health",
            endpoint: "Routed if patient resides on tribal land",
            format: "Tribal-IRB-approved case notification",
            phone: "varies by reservation",
            description: "Routed only if patient resides on tribal land. Tribal sovereignty preserved.",
        },
        ada: {
            name: "Arizona Department of Agriculture, State Veterinarian's Office",
            short_name: "AZ Dept of Ag",
            endpoint: "https://reportable.azda.az.example/v1/animal-disease",
            format: "ADA-AD-101 JSON (replacing fax + email)",
            phone: "602-542-4293",
            description: "State animal-disease authority. Required reportable per AZ Admin Code R3-2-402.",
        },
        aphis: {
            name: "USDA APHIS Veterinary Services",
            short_name: "USDA APHIS",
            endpoint: "https://vsps.aphis.usda.example/r4/$report-disease",
            format: "VS Form 1-7 / VSPS JSON equivalent",
            phone: "866-536-7593 (FAD Hotline)",
            description: "Federal animal-health authority. Required for federal-reportable animal diseases.",
        },
        agfd: {
            name: "Arizona Game and Fish Department",
            short_name: "AZ Game & Fish",
            endpoint: "https://reportable.azgfd.az.example/v1/wildlife-disease",
            format: "AGFD wildlife-disease report",
            phone: "623-236-7351",
            description: "Wildlife disease (e.g., plague in rodents, rabies in skunks/bats).",
        },
        adhs_cross_species: {
            name: "ADHS Cross-Species Surveillance Feed",
            short_name: "ADHS One Health",
            endpoint: "https://surveillance.adhs.az.example/r4/$cross-species-zoonotic",
            format: "ONE-HealthRecord cross-species sentinel notification",
            phone: "602-364-3676",
            description: "Real-time notification that an animal sentinel signal has fired in this county. Drives upstream PH response.",
        },
    };

    const TIMELINE_LABEL = {
        immediate: "IMMEDIATE — within 24 hours",
        one_working_day: "ONE WORKING DAY",
        five_working_days: "FIVE WORKING DAYS",
        outbreak_24h: "OUTBREAK — within 24 hours",
        notifiable_24h: "NOTIFIABLE — within 24 hours",
        monitored_30d: "MONITORED — within 30 days",
    };
    const TIMELINE_COLOR = {
        immediate:        "var(--cardinal)",
        outbreak_24h:     "var(--cardinal)",
        notifiable_24h:   "var(--cardinal)",
        one_working_day:  "var(--amber)",
        five_working_days:"var(--clinical)",
        monitored_30d:    "var(--ink-3)",
    };

    function _getDB() {
        return (window.ONE_HR_DATA && window.ONE_HR_DATA.reportable_diseases_db) || null;
    }

    function findReportable(condition) {
        if (!condition) return null;
        // Prefer the embedded _reportable extension placed by the case generator
        if (condition._reportable && condition._reportable.disease_id) {
            const db = _getDB();
            if (db) {
                const d = db.diseases.find(x => x.disease_id === condition._reportable.disease_id);
                if (d) return d;
            }
            // Fall back to the embedded metadata
            const r = condition._reportable;
            return {
                disease_id: r.disease_id,
                common_name: r.common_name || condition.code?.text,
                human_reporting: r.human_reporting,
                animal_reporting: r.animal_reporting,
                is_zoonotic: r.is_zoonotic,
                applies_to: ["human", "animal"],
            };
        }
        // Otherwise scan by SNOMED-CT or text
        const db = _getDB();
        if (!db) return null;
        const sct = (condition.code?.coding || []).find(c => c.system?.includes("snomed"));
        const text = (condition.code?.text || "").toLowerCase();
        for (const d of db.diseases) {
            if (sct && d.snomed_ct === sct.code) return d;
            if (text && d.common_name.toLowerCase().includes(text.slice(0, 14))) return d;
        }
        return null;
    }

    function findReportablesForPatient(patient_ref, hh) {
        if (!hh || !hh.conditions) return [];
        const out = [];
        for (const c of hh.conditions) {
            const ref = c.subject?.reference;
            if (ref !== patient_ref) continue;
            const r = findReportable(c);
            if (!r) continue;
            const isAnimal = ref.startsWith("AnimalPatient/");
            const reportingMeta = isAnimal ? r.animal_reporting : r.human_reporting;
            if (!reportingMeta || !reportingMeta.is_reportable) continue;
            out.push({ condition: c, disease: r, isAnimal });
        }
        return out;
    }

    /**
     * Build the destination list for a condition based on the disease's
     * reporting metadata and the patient's residency.
     */
    function _destinationsForCase(disease, isAnimal, hh) {
        const meta = isAnimal ? (disease.animal_reporting || {}) : (disease.human_reporting || {});
        const dests = (meta.destinations || []).slice();
        // Filter "tribal_if_applicable" by household residency
        const onTribal = (hh?.county?.is_tribal || hh?.environment?.tribal_land || false);
        return dests.map(id => {
            const ag = AGENCIES[id];
            const isApplicable = (id !== "tribal_if_applicable") || onTribal;
            return { id, agency: ag, applicable: isApplicable };
        }).filter(d => d.applicable);
    }

    /**
     * Generate a per-agency message preview. Uses the same shape as the
     * server-side generators in src/cds/.
     */
    function _generateMessage(destId, disease, condition, ctx) {
        const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
        const patient = ctx.patient || {};
        const facility = ctx.facility || {};
        const provider = ctx.provider || {};
        const caseId = (ctx.isAnimal ? "AZ-VS-" : "AZ-") + ts.slice(0, 8) + "-" + ((patient.id || "0").slice(0, 8));

        const code = (disease.human_reporting?.nndss_condition_code) || "00000";
        const sct = disease.snomed_ct || "";

        if (destId === "adhs" || destId === "cdc_nndss" || destId === "local_health_dept" || destId === "tribal_if_applicable") {
            // HL7 v2.5.1 ELR
            return [
                "MSH|^~\\&|ONE-HealthRecord^2.16.840.1.113883.3.AZ-OHR^ISO|" + (facility.id || "TMC") + "^03D9999999^CLIA|" +
                    (destId === "adhs" ? "ADHS-MEDSIS^2.16.840.1.113883.3.4321^ISO|ADHS^04^FIPS" :
                     destId === "cdc_nndss" ? "CDC-NNDSS^2.16.840.1.114222.4.10.3^ISO|CDC^USA^ISO" :
                     destId === "tribal_if_applicable" ? "TRIBAL-HEALTH^TBD^TRIBAL|TRIBAL^TBD^TRIBAL" :
                     "LOCAL-HEALTH-DEPT^TBD^LOCAL|LHD^TBD^LOCAL") +
                    "|" + ts + "||ORU^R01^ORU_R01|OHR-" + ts + "|P|2.5.1",
                "PID|1||" + (patient.id || "").slice(0, 16) + "^^^&2.16.840.1.113883.3.AZ-OHR&ISO^MR||" +
                    (patient.last_name || "") + "^" + (patient.first_name || "") + "||" +
                    (patient.dob || "").replace(/-/g, "") + "|" + ((patient.gender || "U")[0] || "U").toUpperCase() +
                    "|||^^^AZ^^USA",
                "ORC|RE|" + caseId + "^OHR|" + caseId + "^ADHS||CM|||" + ts,
                "OBR|1|" + caseId + "^OHR|" + caseId + "^ADHS|" + code + "^" + (disease.common_name || "") + "^CDCNNDSS",
                "OBX|1|CWE|" + sct + "^" + (disease.common_name || "") + "^SCT||confirmed||negative|A|||F",
                "SPM|1|" + caseId + "-SPM^OHR||SER^Serum^HL70487",
                "NTE|1|L|Reportable: " + (disease.common_name || "") +
                    ". Submitted via ONE-HealthRecord one-click reporting. " +
                    "Reporting class: " + ((disease.human_reporting?.adhs_timeline) || "") + "."
            ].join("\n");
        }
        if (destId === "ada" || destId === "aphis" || destId === "agfd") {
            // VSPS / VS Form 1-7 JSON equivalent
            return JSON.stringify({
                report_metadata: {
                    case_id: caseId,
                    submission_date: new Date().toISOString(),
                    submitting_system: "ONE-HealthRecord",
                    submission_method: "REST POST application/json",
                },
                disease: {
                    common_name: disease.common_name,
                    internal_disease_id: disease.disease_id,
                    icd10: disease.icd10,
                    snomed_ct: disease.snomed_ct,
                    is_federal_reportable: disease.animal_reporting?.aphis_notifiable || false,
                    is_az_state_reportable: disease.animal_reporting?.ada_required || false,
                },
                animal: {
                    animal_id: patient.id,
                    name: patient.first_name,
                    species: ctx.species || "",
                    household_id: ctx.household_id || "",
                    premises_id: ctx.premises_id || "AZ-PREM-SYNTHETIC",
                },
                veterinarian: { name: provider.name || "", license_number: "AZ-VET-SYNTHETIC", license_state: "AZ" },
                destination_agency: AGENCIES[destId]?.name || destId,
                clinical_information: { case_status: "confirmed", outcome: "under_treatment" },
            }, null, 2);
        }
        if (destId === "adhs_cross_species") {
            return JSON.stringify({
                notification_type: "ONE Health cross-species sentinel signal",
                case_id: caseId,
                disease: { common_name: disease.common_name, internal_disease_id: disease.disease_id },
                sentinel_kind: ctx.isAnimal ? "animal-side index case" : "human-side index case",
                household_id: ctx.household_id || "",
                rationale: "Sentinel signal generated under Arizona's One Health Surveillance Program. ADHS will be notified via parallel cross-species notification feed for any potential cross-species prophylactic or surveillance action.",
            }, null, 2);
        }
        return "(no preview generator for destination: " + destId + ")";
    }

    /**
     * Open the multi-agency report panel as a modal.
     */
    function openReportPanel(condition, ctx) {
        const disease = findReportable(condition);
        if (!disease) {
            console.warn("openReportPanel: condition is not reportable", condition);
            return;
        }
        ctx = ctx || {};
        const isAnimal = ctx.isAnimal === undefined
            ? (condition.subject?.reference || "").startsWith("AnimalPatient/")
            : ctx.isAnimal;
        const hh = ctx.hh || null;

        const dests = _destinationsForCase(disease, isAnimal, hh);
        const meta = isAnimal ? (disease.animal_reporting || {}) : (disease.human_reporting || {});
        const timeline = meta.adhs_timeline ||
            (meta.aphis_notifiable ? "notifiable_24h" : (meta.aphis_monitored ? "monitored_30d" : "five_working_days"));
        const condId = condition.id || "cond-" + Math.random().toString(36).slice(2, 10);

        // Initial state — pre-build all messages once so tab switching is instant
        const messages = {};
        for (const d of dests) {
            messages[d.id] = _generateMessage(d.id, disease, condition, { ...ctx, isAnimal });
        }

        let activeTab = dests[0]?.id || null;

        const m = document.createElement("div");
        m.className = "cds-modal-backdrop oh-report-modal-backdrop";
        m.innerHTML = `
            <div class="cds-modal oh-report-modal">
                <div class="cds-modal-head oh-report-head">
                    <div>
                        <span class="oh-report-flag">REPORT THIS CASE</span>
                        <h3 style="margin: 4px 0 0;">${escapeHtml(disease.common_name)}</h3>
                        <div class="oh-report-meta">
                            <span class="oh-report-timeline" style="background: ${TIMELINE_COLOR[timeline] || 'var(--ink-3)'};">${escapeHtml(TIMELINE_LABEL[timeline] || timeline)}</span>
                            ${disease.icd10 ? `<code>ICD-10 ${escapeHtml(disease.icd10)}</code>` : ''}
                            ${disease.snomed_ct ? `<code>SNOMED ${escapeHtml(disease.snomed_ct)}</code>` : ''}
                            ${meta.nndss_condition_code ? `<code>NNDSS ${escapeHtml(meta.nndss_condition_code)}</code>` : ''}
                            ${disease.is_zoonotic ? '<span class="oh-pill">zoonotic</span>' : ''}
                            ${disease.is_select_agent ? '<span class="oh-pill oh-pill-cardinal">SELECT AGENT</span>' : ''}
                        </div>
                    </div>
                    <button class="cds-modal-close" type="button" aria-label="Close">&times;</button>
                </div>
                <div class="cds-modal-body oh-report-body">
                    <div class="oh-report-intro">
                        Auto-generated from the patient encounter. The destinations below
                        are determined by the disease's reportability metadata and
                        the patient's residency. Review each message before submission.
                        Future versions will support automatic submission once the model is fully trained;
                        for now, <strong>clinician review is required</strong> for every case.
                    </div>
                    <div class="oh-report-grid">
                        <div class="oh-dest-list">
                            <h4>Destinations (${dests.length})</h4>
                            ${dests.map(d => `
                                <button class="oh-dest-tab" data-dest="${d.id}" ${d.id === activeTab ? 'data-active="1"' : ''}>
                                    <div class="oh-dest-name">${escapeHtml(d.agency.short_name)}</div>
                                    <div class="oh-dest-format">${escapeHtml(d.agency.format)}</div>
                                </button>
                            `).join("")}
                        </div>
                        <div class="oh-dest-detail" id="oh-report-detail">
                            ${_renderTab(dests, activeTab, messages, AGENCIES)}
                        </div>
                    </div>
                </div>
                <div class="cds-modal-foot oh-report-foot">
                    <span class="oh-report-foot-meta">
                        Auto-prepared at ${new Date().toLocaleString()}.
                        Synthetic destinations — real submission would require production credentials.
                    </span>
                    <div style="display:flex; gap:10px;">
                        <button class="cds-action-btn" type="button" data-close>Cancel</button>
                        <button class="cds-action-btn cds-primary" type="button" id="oh-report-submit">Submit all (${dests.length}) →</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(m);

        // Tab wiring
        m.querySelectorAll(".oh-dest-tab").forEach(btn => {
            btn.addEventListener("click", () => {
                activeTab = btn.dataset.dest;
                m.querySelectorAll(".oh-dest-tab").forEach(b => b.removeAttribute("data-active"));
                btn.setAttribute("data-active", "1");
                m.querySelector("#oh-report-detail").innerHTML = _renderTab(dests, activeTab, messages, AGENCIES);
            });
        });

        // Close handlers
        m.querySelectorAll(".cds-modal-close, [data-close]").forEach(b =>
            b.addEventListener("click", () => m.remove()));
        m.addEventListener("click", e => { if (e.target === m) m.remove(); });

        // Submit
        m.querySelector("#oh-report-submit").addEventListener("click", () => {
            REPORT_STATE[condId] = "submitted";
            // Build a fake ack from each destination
            const acks = dests.map(d => ({
                destination: d.id,
                agency_name: d.agency.short_name,
                ack_id: "ACK-" + Math.random().toString(36).slice(2, 10).toUpperCase(),
                received_at: new Date().toISOString(),
                status: "received_for_investigation",
            }));
            REPORT_STATE[condId + "_acks"] = acks;
            if (window.OH_AUTH) {
                window.OH_AUTH.auditLog("reportable_case_submitted",
                    disease.disease_id + " → " + dests.map(d => d.id).join(","));
            }
            _showSuccessPanel(m, dests, acks);
        });
    }

    function _renderTab(dests, activeId, messages, AGENCIES) {
        const d = dests.find(x => x.id === activeId);
        if (!d) return "";
        const msg = messages[activeId] || "";
        return `
            <div class="oh-dest-card">
                <div class="oh-dest-card-head">
                    <h4>${escapeHtml(d.agency.name)}</h4>
                    <div class="oh-dest-desc">${escapeHtml(d.agency.description)}</div>
                </div>
                <div class="oh-dest-stats">
                    <div><strong>Format</strong><br>${escapeHtml(d.agency.format)}</div>
                    <div><strong>Endpoint</strong><br><code>${escapeHtml(d.agency.endpoint)}</code></div>
                    <div><strong>Phone</strong><br>${escapeHtml(d.agency.phone)}</div>
                </div>
                <div class="oh-dest-msg-label">Pre-generated message preview <span style="color: var(--ink-3); font-style: italic;">(read-only in this MVP; production allows clinician edit before submission)</span></div>
                <pre class="cds-modal-pre">${escapeHtml(msg)}</pre>
            </div>`;
    }

    function _showSuccessPanel(m, dests, acks) {
        const body = m.querySelector(".oh-report-body");
        body.innerHTML = `
            <div class="oh-report-success">
                <div class="oh-success-icon">✓</div>
                <h2>Reported.</h2>
                <p>Submitted to ${dests.length} destinations in parallel. Below are the per-agency acknowledgements.</p>
                <table class="audit-log-table" style="margin-top: 18px;">
                    <thead><tr><th>Agency</th><th>Acknowledgement ID</th><th>Received at</th><th>Status</th></tr></thead>
                    <tbody>
                        ${acks.map(a => `<tr>
                            <td><strong>${escapeHtml(a.agency_name)}</strong></td>
                            <td><code>${escapeHtml(a.ack_id)}</code></td>
                            <td>${escapeHtml(a.received_at)}</td>
                            <td><span style="color: var(--clinical); font-weight: 600;">✓ ${escapeHtml(a.status.replace(/_/g, " "))}</span></td>
                        </tr>`).join("")}
                    </tbody>
                </table>
                <p style="margin-top: 18px; color: var(--ink-3); font-style: italic;">
                    Workflow time: ~4 minutes (vs. 60+ minutes for traditional fax/phone reporting).
                    Each agency will route to its own case-investigation team. The clinician's responsibility is complete.
                </p>
            </div>`;
        m.querySelector(".oh-report-foot").innerHTML = `
            <span class="oh-report-foot-meta">Reportable case fully closed.</span>
            <button class="cds-action-btn cds-primary" type="button" data-close>Close</button>`;
        m.querySelectorAll("[data-close]").forEach(b => b.addEventListener("click", () => m.remove()));
    }

    function getReportState(condId) { return REPORT_STATE[condId] || "unreported"; }
    function getReportAcks(condId)  { return REPORT_STATE[condId + "_acks"] || []; }

    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g,
            c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
    }

    window.OH_REPORT = {
        findReportable,
        findReportablesForPatient,
        openReportPanel,
        getReportState,
        getReportAcks,
    };
})();
