/* ============================================================================
 * Phase 8 — Patient Intake module.
 *
 * Public surface:
 *   OH_INTAKE.renderRegistration(host)     — new patient registration form
 *   OH_INTAKE.renderTrackBoard(host)       — triage track board
 *   OH_INTAKE.getWaitingRoom()             — array of registered-but-not-seen patients
 *   OH_INTAKE.attachEncounterInput(host)   — voice / keyboard / template tabs
 *
 * In-memory state is held in OH_INTAKE._state. In production this would be
 * persisted as FHIR Encounter + Observation resources scoped to the visit.
 * ========================================================================== */

(function () {
    'use strict';

    const STATE = {
        registered: [],   // patients in waiting room
        triaged: [],      // patients post-triage (with vitals + CC + ESI)
    };

    // ---- eMPI duplicate-detection (uses Phase 6 manifest) -------------------
    function _runEmpiCheck(patientForm) {
        const data = window.ONE_HR_DATA || {};
        const hhContainer = data.households || {};
        const households = Array.isArray(hhContainer) ? hhContainer : (hhContainer.households || []);
        const matches = [];
        const lname = (patientForm.last_name || "").trim().toLowerCase();
        const fname = (patientForm.first_name || "").trim().toLowerCase();
        const dob = (patientForm.dob || "").trim();
        const street = (patientForm.address || "").trim().toLowerCase().slice(0, 14);

        if (!lname || !fname) return matches;

        for (const hh of households) {
            for (const h of (hh.humans || [])) {
                const nm = (h.name && h.name[0]) || {};
                const hLname = (nm.family || h.family || h.last_name || "").toLowerCase();
                const hFname = ((nm.given && nm.given[0]) || (h.given && h.given[0]) || h.first_name || "").toLowerCase();
                const hDob = h.birthDate || h.dob || "";
                const addrObj = (h.address && h.address[0]) || {};
                const hAddr = ((addrObj.line && addrObj.line[0]) || "").toLowerCase();
                if (!hLname || !hFname) continue;

                let score = 0;
                if (hLname === lname) score += 0.40;
                else if (hLname.startsWith(lname.slice(0, 4)) || lname.startsWith(hLname.slice(0, 4))) score += 0.18;

                if (hFname === fname) score += 0.30;
                else if (hFname.startsWith(fname.slice(0, 3)) || fname.startsWith(hFname.slice(0, 3))) score += 0.12;
                else if (hFname.startsWith(fname[0]) && fname.length === 1) score += 0.10;

                if (dob && hDob === dob) score += 0.25;

                if (street && hAddr.includes(street)) score += 0.15;

                if (score >= 0.50) {
                    matches.push({
                        patient_id: h.id,
                        name: (((nm.given && nm.given[0]) || "") + " " + (nm.family || "")).trim(),
                        dob: hDob,
                        household: hh.household_id,
                        site: (hh._owning_site || "Unknown site"),
                        score: Math.min(0.99, score),
                    });
                }
            }
        }
        matches.sort((a, b) => b.score - a.score);
        return matches.slice(0, 3);
    }

    // ---- New Patient Registration -------------------------------------------
    function renderRegistration(host) {
        if (!host) return;
        host.innerHTML = `
            <div class="intake-grid">
                <div class="intake-form-col">
                    <h3 class="intake-h">Patient demographics</h3>
                    <div class="intake-form" id="intake-form">
                        <div class="intake-row">
                            <label>First name <input type="text" id="reg-first" placeholder="Maria"></label>
                            <label>Last name <input type="text" id="reg-last" placeholder="Hernandez"></label>
                        </div>
                        <div class="intake-row">
                            <label>Date of birth <input type="date" id="reg-dob"></label>
                            <label>Sex
                                <select id="reg-sex">
                                    <option value="">—</option>
                                    <option value="female">Female</option>
                                    <option value="male">Male</option>
                                    <option value="other">Other / Non-binary</option>
                                    <option value="unknown">Unknown</option>
                                </select>
                            </label>
                        </div>
                        <div class="intake-row">
                            <label class="full">Street address <input type="text" id="reg-address" placeholder="2847 E Speedway Blvd"></label>
                        </div>
                        <div class="intake-row">
                            <label>City <input type="text" id="reg-city" placeholder="Tucson"></label>
                            <label>ZIP <input type="text" id="reg-zip" placeholder="85716"></label>
                        </div>
                        <div class="intake-row">
                            <label>Phone <input type="tel" id="reg-phone" placeholder="(520) 555-0123"></label>
                            <label>Insurance
                                <select id="reg-insurance">
                                    <option value="">—</option>
                                    <option>Medicare</option>
                                    <option>Medicaid (AHCCCS)</option>
                                    <option>BCBS Arizona</option>
                                    <option>UnitedHealthcare</option>
                                    <option>Aetna</option>
                                    <option>Cigna</option>
                                    <option>Self-pay</option>
                                    <option>IHS / 638</option>
                                </select>
                            </label>
                        </div>
                        <div class="intake-row">
                            <label class="full">Reason for visit (chief complaint) <input type="text" id="reg-cc" placeholder="Cough x 3 weeks, fatigue"></label>
                        </div>
                        <div class="intake-row">
                            <label>Household
                                <select id="reg-household">
                                    <option value="new">— Create new household —</option>
                                    <option disabled>──────────</option>
                                </select>
                            </label>
                            <label>Has tribal residency?
                                <select id="reg-tribal">
                                    <option value="false">No</option>
                                    <option value="true">Yes</option>
                                </select>
                            </label>
                        </div>
                        <div class="intake-row">
                            <label class="intake-consent">
                                <input type="checkbox" id="reg-consent" checked>
                                One Health consent: link to household for cross-species cluster signals
                                <span class="intake-consent-note">FHIR Consent resource — patient may revoke at any time</span>
                            </label>
                        </div>
                        <div class="intake-actions">
                            <button class="cds-action-btn" id="reg-empi">Run eMPI duplicate check</button>
                            <button class="cds-action-btn cds-primary" id="reg-submit">Register patient →</button>
                        </div>
                    </div>
                </div>
                <div class="intake-side-col">
                    <h3 class="intake-h">eMPI duplicate detection</h3>
                    <p class="intake-side-blurb">
                        On submit, the registrar's record is checked against the
                        <strong>federation manifest</strong> (13 partner sites) for
                        possible existing identities. This prevents the duplicate-MRN
                        problem that plagues real EHR systems.
                    </p>
                    <div id="reg-empi-results" class="intake-empi-results">
                        <div class="intake-empty">Fill in the form and click <em>Run eMPI duplicate check</em>.</div>
                    </div>
                </div>
            </div>`;

        // Populate household dropdown with a few sample households for convenience
        const data = window.ONE_HR_DATA || {};
        const sel = host.querySelector("#reg-household");
        if (sel) {
            const hhContainer = data.households || {};
            const allHh = Array.isArray(hhContainer) ? hhContainer : (hhContainer.households || []);
            const sample = allHh.slice(0, 30);
            for (const hh of sample) {
                const opt = document.createElement("option");
                opt.value = hh.household_id;
                opt.textContent = (hh.name || hh.household_id) + " — " + ((hh.county && hh.county.name) || "");
                sel.appendChild(opt);
            }
        }

        const formData = () => ({
            first_name: host.querySelector("#reg-first").value.trim(),
            last_name:  host.querySelector("#reg-last").value.trim(),
            dob:        host.querySelector("#reg-dob").value.trim(),
            sex:        host.querySelector("#reg-sex").value,
            address:    host.querySelector("#reg-address").value.trim(),
            city:       host.querySelector("#reg-city").value.trim(),
            zip:        host.querySelector("#reg-zip").value.trim(),
            phone:      host.querySelector("#reg-phone").value.trim(),
            insurance:  host.querySelector("#reg-insurance").value,
            cc:         host.querySelector("#reg-cc").value.trim(),
            household:  host.querySelector("#reg-household").value,
            tribal:     host.querySelector("#reg-tribal").value === "true",
            consent_one_health: host.querySelector("#reg-consent").checked,
        });

        host.querySelector("#reg-empi").addEventListener("click", () => {
            const f = formData();
            if (!f.first_name || !f.last_name) {
                _renderEmpi(host, [], "Please enter first and last name to run eMPI check.");
                return;
            }
            const matches = _runEmpiCheck(f);
            _renderEmpi(host, matches, null);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("empi_check", `${f.first_name} ${f.last_name}`);
        });

        host.querySelector("#reg-submit").addEventListener("click", () => {
            const f = formData();
            if (!f.first_name || !f.last_name || !f.dob) {
                alert("First name, last name, and date of birth are required.");
                return;
            }
            // Run eMPI check first
            const matches = _runEmpiCheck(f);
            if (matches.length > 0 && !host.dataset.duplicateAcknowledged) {
                _renderEmpi(host, matches, "⚠ Possible existing patient match — review before creating new record.");
                host.dataset.duplicateAcknowledged = "pending";
                host.querySelector("#reg-submit").textContent = "Confirm — create as new patient anyway";
                host.querySelector("#reg-submit").classList.add("cds-warn");
                return;
            }
            // Proceed
            _completeRegistration(f);
            host.dataset.duplicateAcknowledged = "";
            host.querySelector("#reg-submit").textContent = "Register patient →";
            host.querySelector("#reg-submit").classList.remove("cds-warn");
            _showRegistrationSuccess(host, f);
        });
    }

    function _renderEmpi(host, matches, message) {
        const el = host.querySelector("#reg-empi-results");
        if (!el) return;
        if (message && matches.length === 0) {
            el.innerHTML = `<div class="intake-empty">${escapeHtml(message)}</div>`;
            return;
        }
        if (matches.length === 0) {
            el.innerHTML = `
                <div class="intake-empi-clean">
                    <div class="intake-empi-icon">✓</div>
                    <strong>No existing patient match.</strong>
                    <p>The federation manifest has no record matching the supplied identifiers. Safe to create a new patient.</p>
                </div>`;
            return;
        }
        el.innerHTML = `
            ${message ? `<div class="intake-empi-warn">${escapeHtml(message)}</div>` : ''}
            <div class="intake-empi-list">
                ${matches.map(m => `
                    <div class="intake-empi-card">
                        <div class="intake-empi-card-head">
                            <strong>${escapeHtml(m.name)}</strong>
                            <span class="intake-empi-score">match score: ${(m.score * 100).toFixed(0)}%</span>
                        </div>
                        <div class="intake-empi-meta">
                            DOB: ${escapeHtml(m.dob)} ·
                            Household: <code>${escapeHtml(m.household)}</code> ·
                            Site: ${escapeHtml(m.site)}
                        </div>
                        <div class="intake-empi-meta" style="margin-top:6px;">
                            <strong>Action:</strong> Confirm with patient — is this them?
                            If yes, link to existing record (do not create new).
                        </div>
                    </div>`).join("")}
            </div>`;
    }

    function _completeRegistration(f) {
        const newPatient = {
            id: "p-new-" + Math.random().toString(36).slice(2, 10),
            family: f.last_name,
            given: [f.first_name],
            dob: f.dob,
            gender: f.sex,
            address: { city: f.city, postalCode: f.zip, line: [f.address] },
            phone: f.phone,
            insurance: f.insurance,
            chief_complaint: f.cc,
            household_id: f.household === "new" ? ("HH-NEW-" + Math.random().toString(36).slice(2, 8).toUpperCase()) : f.household,
            tribal: f.tribal,
            consent_one_health: f.consent_one_health,
            registered_at: new Date().toISOString(),
            triage_state: "waiting",
        };
        STATE.registered.push(newPatient);
        if (window.OH_AUTH) window.OH_AUTH.auditLog("patient_registered", newPatient.id);
        return newPatient;
    }

    function _showRegistrationSuccess(host, f) {
        host.innerHTML = `
            <div class="intake-success">
                <div class="intake-success-icon">✓</div>
                <h2>Patient registered.</h2>
                <p><strong>${escapeHtml(f.first_name + " " + f.last_name)}</strong> has been added to the waiting room. The triage nurse will see them on the track board.</p>
                <p class="intake-success-sub">FHIR <code>Patient</code> resource created. Household ID: <code>${escapeHtml(f.household === 'new' ? 'NEW-' + Math.random().toString(36).slice(2, 8).toUpperCase() : f.household)}</code>. Consent: <code>${f.consent_one_health ? 'active' : 'inactive'}</code>.</p>
                <div style="margin-top: 24px;">
                    <button class="cds-action-btn cds-primary" id="reg-another">Register another patient</button>
                    <button class="cds-action-btn" id="reg-trackboard">Go to triage track board →</button>
                </div>
            </div>`;
        host.querySelector("#reg-another").addEventListener("click", () => renderRegistration(host));
        host.querySelector("#reg-trackboard").addEventListener("click", () => {
            // Activate the trackboard view in the intake hub
            const btn = document.querySelector('button[data-view="trackboard"]');
            if (btn) btn.click();
        });
    }

    // ---- Triage Track Board -------------------------------------------------
    function renderTrackBoard(host) {
        if (!host) return;
        const all = _allPatientsOnBoard();
        host.innerHTML = `
            <div class="trackboard-summary">
                ${_summaryCard("Waiting", all.filter(p => p.triage_state === "waiting").length, "var(--amber)")}
                ${_summaryCard("In triage", all.filter(p => p.triage_state === "in_triage").length, "var(--cardinal)")}
                ${_summaryCard("Ready for clinician", all.filter(p => p.triage_state === "ready").length, "var(--clinical)")}
                ${_summaryCard("With clinician", all.filter(p => p.triage_state === "with_clinician").length, "var(--navy)")}
            </div>
            <div class="trackboard-blurb">
                Triage nurses see all patients in the waiting room and current triage queue.
                Click <em>Triage</em> on any patient to capture vitals, chief complaint, and ESI acuity.
                Once triaged, the patient becomes visible to the assigned clinician's encounter screen with the captured triage data pre-loaded.
            </div>
            <table class="audit-log-table trackboard-table">
                <thead><tr>
                    <th>Patient</th><th>DOB</th><th>Reason for visit</th>
                    <th>Status</th><th>Wait time</th><th>Actions</th>
                </tr></thead>
                <tbody>${all.length === 0
                    ? '<tr><td colspan="6" class="intake-empty">No patients in the queue. Register a new patient to begin.</td></tr>'
                    : all.map(p => _trackboardRow(p)).join("")}
                </tbody>
            </table>`;

        host.querySelectorAll("[data-tri-action]").forEach(b => {
            b.addEventListener("click", () => _handleTrackboardAction(b.dataset.triAction, b.dataset.patientId, host));
        });
    }

    function _summaryCard(label, n, color) {
        return `<div class="trackboard-summary-card" style="--accent: ${color};">
            <div class="trackboard-summary-num">${n}</div>
            <div class="trackboard-summary-label">${escapeHtml(label)}</div>
        </div>`;
    }

    function _allPatientsOnBoard() {
        // Combine registered + triaged; dedup by id
        const seen = new Set();
        const out = [];
        for (const arr of [STATE.registered, STATE.triaged]) {
            for (const p of arr) {
                if (seen.has(p.id)) continue;
                seen.add(p.id);
                out.push(p);
            }
        }
        // If no real registrations yet, seed a couple of demo patients
        if (out.length === 0) {
            const demoNow = new Date();
            return [
                { id: "demo-1", given: ["Sandra"], family: "Mendez", dob: "1962-04-19", chief_complaint: "Persistent cough × 4 weeks, low-grade fever",
                    triage_state: "waiting", registered_at: new Date(demoNow - 28*60*1000).toISOString() },
                { id: "demo-2", given: ["Daniel"], family: "Park", dob: "1989-11-03", chief_complaint: "Tick bite 5 days ago, now headache + fever",
                    triage_state: "in_triage", registered_at: new Date(demoNow - 14*60*1000).toISOString() },
                { id: "demo-3", given: ["Aisha"], family: "Begay", dob: "1975-08-22", chief_complaint: "Annual physical",
                    triage_state: "ready", registered_at: new Date(demoNow - 6*60*1000).toISOString(),
                    triage: { vitals: { bp: "126/78", hr: 72, temp_f: 98.4, spo2: 98 }, esi: 4, cc: "Annual physical" } },
                { id: "demo-4", given: ["Carlos"], family: "Hernandez", dob: "1971-09-12", chief_complaint: "Fatigue, mild cough — wife recently dx'd Valley Fever",
                    triage_state: "ready", registered_at: new Date(demoNow - 41*60*1000).toISOString(),
                    triage: { vitals: { bp: "132/84", hr: 78, temp_f: 99.1, spo2: 97 }, esi: 3, cc: "Fatigue + r/o cocci (household exposure)" } },
            ];
        }
        return out;
    }

    function _waitTime(registeredAt) {
        const ms = Date.now() - new Date(registeredAt).getTime();
        const min = Math.floor(ms / 60000);
        if (min < 60) return `${min}m`;
        return `${Math.floor(min/60)}h ${min%60}m`;
    }

    function _trackboardRow(p) {
        const name = ((p.given || [""])[0] + " " + (p.family || "")).trim();
        const stateLabel = ({
            waiting: "Waiting",
            in_triage: "In triage",
            ready: "Ready for clinician",
            with_clinician: "With clinician",
            discharged: "Discharged",
        })[p.triage_state] || p.triage_state;
        const stateColor = ({
            waiting: "var(--amber)", in_triage: "var(--cardinal)",
            ready: "var(--clinical)", with_clinician: "var(--navy)",
        })[p.triage_state] || "var(--ink-3)";

        const actions = [];
        if (p.triage_state === "waiting") {
            actions.push(`<button class="cds-action-btn" data-tri-action="start-triage" data-patient-id="${p.id}">Start triage</button>`);
        } else if (p.triage_state === "in_triage") {
            actions.push(`<button class="cds-action-btn cds-primary" data-tri-action="open-triage-form" data-patient-id="${p.id}">Open triage form</button>`);
        } else if (p.triage_state === "ready") {
            actions.push(`<button class="cds-action-btn" data-tri-action="hand-off" data-patient-id="${p.id}">Hand off to clinician →</button>`);
        }
        return `<tr>
            <td><strong>${escapeHtml(name)}</strong>${p.triage?.esi ? `<span class="esi-pill esi-${p.triage.esi}">ESI ${p.triage.esi}</span>` : ''}</td>
            <td>${escapeHtml(p.dob || '')}</td>
            <td>${escapeHtml(p.chief_complaint || p.triage?.cc || '')}</td>
            <td><span class="trackboard-state" style="color: ${stateColor};">● ${escapeHtml(stateLabel)}</span></td>
            <td><code>${escapeHtml(_waitTime(p.registered_at))}</code></td>
            <td>${actions.join(" ")}</td>
        </tr>`;
    }

    function _handleTrackboardAction(action, patientId, host) {
        const all = _allPatientsOnBoard();
        const p = all.find(x => x.id === patientId);
        if (!p) return;
        if (action === "start-triage") {
            p.triage_state = "in_triage";
            renderTrackBoard(host);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("triage_start", patientId);
        } else if (action === "open-triage-form") {
            _openTriageForm(p, host);
        } else if (action === "hand-off") {
            p.triage_state = "with_clinician";
            renderTrackBoard(host);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("triage_handoff_to_clinician", patientId);
        }
    }

    function _openTriageForm(p, host) {
        const modal = document.createElement("div");
        modal.className = "cds-modal-backdrop";
        modal.innerHTML = `
            <div class="cds-modal" style="max-width: 760px;">
                <div class="cds-modal-head">
                    <h3>Triage · ${escapeHtml((p.given || [""])[0] + " " + (p.family || ""))}</h3>
                    <button class="cds-modal-close" type="button">&times;</button>
                </div>
                <div class="cds-modal-body">
                    <p class="intake-side-blurb">DOB: <strong>${escapeHtml(p.dob || "")}</strong> · Reason: <strong>${escapeHtml(p.chief_complaint || "")}</strong></p>
                    <h4 style="margin-top: 14px;">Vital signs</h4>
                    <div class="intake-row">
                        <label>BP <input type="text" id="tri-bp" placeholder="120/80"></label>
                        <label>HR <input type="text" id="tri-hr" placeholder="72"></label>
                        <label>RR <input type="text" id="tri-rr" placeholder="16"></label>
                    </div>
                    <div class="intake-row">
                        <label>Temp °F <input type="text" id="tri-temp" placeholder="98.6"></label>
                        <label>SpO₂ <input type="text" id="tri-spo2" placeholder="98"></label>
                        <label>Pain (0-10) <input type="text" id="tri-pain" placeholder="2"></label>
                    </div>
                    <h4 style="margin-top: 14px;">Chief complaint (refined)</h4>
                    <textarea id="tri-cc" class="encounter-textarea" placeholder="Refine the reason for visit, capture pertinent history, allergies, current medications..." style="min-height: 80px;">${escapeHtml(p.chief_complaint || "")}</textarea>
                    <h4 style="margin-top: 14px;">ESI acuity (Emergency Severity Index)</h4>
                    <div class="esi-grid">
                        <label class="esi-radio esi-1"><input type="radio" name="tri-esi" value="1"><span>1 — Resuscitation</span><small>life-threatening; immediate physician needed</small></label>
                        <label class="esi-radio esi-2"><input type="radio" name="tri-esi" value="2"><span>2 — Emergent</span><small>high risk of deterioration; rooms next</small></label>
                        <label class="esi-radio esi-3"><input type="radio" name="tri-esi" value="3" checked><span>3 — Urgent</span><small>multiple resources needed; standard pace</small></label>
                        <label class="esi-radio esi-4"><input type="radio" name="tri-esi" value="4"><span>4 — Less urgent</span><small>one resource needed</small></label>
                        <label class="esi-radio esi-5"><input type="radio" name="tri-esi" value="5"><span>5 — Non-urgent</span><small>no resources needed</small></label>
                    </div>
                </div>
                <div class="cds-modal-foot">
                    <span class="oh-report-foot-meta">Triage RN signs the chart on submit.</span>
                    <div style="display:flex; gap: 10px;">
                        <button class="cds-action-btn" data-close>Cancel</button>
                        <button class="cds-action-btn cds-primary" id="tri-save">Save triage &amp; mark ready →</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(modal);
        modal.querySelectorAll(".cds-modal-close, [data-close]").forEach(b => b.addEventListener("click", () => modal.remove()));
        modal.querySelector("#tri-save").addEventListener("click", () => {
            const esi = (modal.querySelector('input[name="tri-esi"]:checked') || {}).value || "3";
            p.triage = {
                vitals: {
                    bp: modal.querySelector("#tri-bp").value || "",
                    hr: modal.querySelector("#tri-hr").value || "",
                    rr: modal.querySelector("#tri-rr").value || "",
                    temp_f: modal.querySelector("#tri-temp").value || "",
                    spo2: modal.querySelector("#tri-spo2").value || "",
                    pain: modal.querySelector("#tri-pain").value || "",
                },
                cc: modal.querySelector("#tri-cc").value || p.chief_complaint || "",
                esi: parseInt(esi, 10),
                at: new Date().toISOString(),
            };
            p.triage_state = "ready";
            modal.remove();
            renderTrackBoard(host);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("triage_complete", `${p.id} ESI=${esi}`);
        });
    }

    function getWaitingRoom() { return _allPatientsOnBoard(); }

    // ---- Encounter input panel (voice / keyboard / template) -----------------
    function attachEncounterInput(host, options) {
        if (!host) return;
        options = options || {};
        const targetTextareaId = options.targetTextareaId || "dictation-input";
        host.innerHTML = `
            <div class="enc-input-tabs">
                <button class="enc-input-tab active" data-mode="voice">🎤 Voice (push to record)</button>
                <button class="enc-input-tab" data-mode="keyboard">⌨️ Keyboard</button>
                <button class="enc-input-tab" data-mode="template">📋 Template</button>
            </div>

            <div class="enc-input-pane enc-pane-voice active">
                <div class="enc-voice-status" id="enc-voice-status">Ready. Click below to start dictating.</div>
                <button class="enc-voice-btn" id="enc-voice-btn">
                    <span class="enc-voice-icon">🎤</span>
                    <span class="enc-voice-label">Push to record</span>
                </button>
                <div class="enc-voice-hint">
                    Hold the button while speaking. Releases on click again. Real-time transcription via Web Speech API.
                    <em>Production: this would route to Nuance Dragon Medical One or AWS HealthScribe for medical-grade ASR.</em>
                </div>
                <div class="enc-voice-transcript" id="enc-voice-transcript"></div>
                <div class="enc-voice-actions">
                    <button class="cds-action-btn" id="enc-voice-clear">Clear</button>
                    <button class="cds-action-btn cds-primary" id="enc-voice-send">Send to encounter →</button>
                </div>
            </div>

            <div class="enc-input-pane enc-pane-keyboard">
                <p class="intake-side-blurb">Type or paste your encounter note. Same dictation engine processes the text.</p>
                <textarea class="encounter-textarea" id="enc-keyboard-text" placeholder="Begin typing your encounter note..."></textarea>
                <div class="enc-voice-actions">
                    <button class="cds-action-btn" id="enc-keyboard-clear">Clear</button>
                    <button class="cds-action-btn cds-primary" id="enc-keyboard-send">Send to encounter →</button>
                </div>
            </div>

            <div class="enc-input-pane enc-pane-template">
                <p class="intake-side-blurb">Pick a template — pre-fills structured boilerplate. Useful for follow-ups, annual physicals, common presentations.</p>
                <select id="enc-template-select" class="enc-template-select">
                    <option value="">— Choose template —</option>
                    <option value="annual_physical">Annual physical (adult)</option>
                    <option value="acute_resp">Acute respiratory complaint</option>
                    <option value="follow_up">Follow-up visit</option>
                    <option value="vet_wellness">Vet wellness exam (companion animal)</option>
                    <option value="cocci_workup">Coccidioidomycosis workup</option>
                </select>
                <textarea class="encounter-textarea" id="enc-template-text" placeholder="Template will appear here..."></textarea>
                <div class="enc-voice-actions">
                    <button class="cds-action-btn cds-primary" id="enc-template-send">Send to encounter →</button>
                </div>
            </div>`;

        // Wire mode switching
        host.querySelectorAll(".enc-input-tab").forEach(tab => {
            tab.addEventListener("click", () => {
                host.querySelectorAll(".enc-input-tab").forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                host.querySelectorAll(".enc-input-pane").forEach(p => p.classList.remove("active"));
                const mode = tab.dataset.mode;
                host.querySelector(".enc-pane-" + mode).classList.add("active");
            });
        });

        // Voice / Web Speech API
        _wireVoiceInput(host, targetTextareaId);

        // Keyboard
        host.querySelector("#enc-keyboard-clear").addEventListener("click", () => {
            host.querySelector("#enc-keyboard-text").value = "";
        });
        host.querySelector("#enc-keyboard-send").addEventListener("click", () => {
            const text = host.querySelector("#enc-keyboard-text").value;
            _sendToEncounter(text, targetTextareaId);
        });

        // Templates
        host.querySelector("#enc-template-select").addEventListener("change", e => {
            const tmpl = TEMPLATES[e.target.value] || "";
            host.querySelector("#enc-template-text").value = tmpl;
        });
        host.querySelector("#enc-template-send").addEventListener("click", () => {
            const text = host.querySelector("#enc-template-text").value;
            _sendToEncounter(text, targetTextareaId);
        });
    }

    const TEMPLATES = {
        annual_physical: `Annual physical examination.

CC: Annual wellness visit.
HPI: [age]-year-old [sex] presents for routine annual physical.  Reports overall well-being.  Reviews systems unremarkable.

PMH: [chronic conditions or none].
Allergies: [NKDA].
Medications: [list].
SH: [tobacco/alcohol/exercise].
FH: [pertinent].

VS: BP __/__, HR __, RR __, T __°F, SpO₂ __%.

PE:
General: well-appearing, in NAD.
HEENT: [normocephalic, atraumatic; PERRLA].
Neck: [supple, no LAD].
CV: [RRR, no MRG].
Lungs: [CTAB].
Abd: [soft, NT/ND, +BS].
Extremities: [no edema].

A/P:
1. Continue current health-maintenance schedule.
2. [age-appropriate screenings].
3. Follow up in 1 year.`,
        acute_resp: `CC: Cough.

HPI: [age]-year-old [sex] presents with __ days of productive/non-productive cough.  Associated symptoms include __.  Denies fever / shortness of breath / chest pain / hemoptysis.  Sick contacts: __.

PMH: __.
SH: tobacco use __.
Travel/exposure: __.

VS: BP __/__, HR __, RR __, T __°F, SpO₂ __%.

PE:
General: __.
HEENT: __.
Lungs: __.

A/P:
1. Acute cough — likely __.
2. [imaging or labs].
3. [treatment].
4. Return precautions reviewed.`,
        follow_up: `Follow-up visit.

CC: Follow-up for __.

Interval history: __.
Adherence: __.
Side effects: __.

VS: BP __/__, HR __, RR __, T __°F, SpO₂ __%.

PE: focused.

A/P:
1. __ — [improved / stable / worsened].  [adjust plan].
2. Follow up in __ weeks.`,
        vet_wellness: `Wellness exam — [species, breed, age, sex/altered, weight kg].

History: presents for routine wellness.  Owner reports no concerns / minor concerns of __.
Diet: __.  Activity: __.  Vaccination status: __.  Parasite prevention: __.

PE:
General: BAR, BCS __/9.
HEENT: __.
Cardiovascular: __.
Respiratory: __.
Abdominal palp: __.
Musculoskeletal: __.
Skin/coat: __.

Plan:
1. Routine vaccinations [DAPP, lepto, Bordetella, rabies] as indicated.
2. Heartworm prevention [refill / start].
3. Tick prevention.
4. Annual fecal.
5. Recheck in 1 year.`,
        cocci_workup: `CC: ___ weeks of cough, fatigue, ___.

HPI: [age]-year-old [sex] from [Pima/Pinal/Maricopa] county, presents with prolonged cough and constitutional symptoms.  History of dust exposure: ___.  Pets at home: ___.

Differential includes coccidioidomycosis given AZ residence + duration of symptoms.

VS: BP __/__, HR __, RR __, T __°F, SpO₂ __%.

PE:
General: __.
Lungs: __.
Skin: [erythema nodosum?].
Joints: [arthralgia?].

A/P:
1. Probable coccidioidomycosis — order Coccidioides IgM/IgG serology, CBC, CMP, chest X-ray.
2. Hold antifungals pending serology unless severe presentation.
3. Patient counseled on natural history of valley fever (slow recovery, 6-12 months).
4. Reportable to ADHS within 1 working day per R9-6-202.
5. Follow up in 1 week to review serology.`,
    };

    function _wireVoiceInput(host, targetTextareaId) {
        const btn = host.querySelector("#enc-voice-btn");
        const status = host.querySelector("#enc-voice-status");
        const transcriptEl = host.querySelector("#enc-voice-transcript");
        const clearBtn = host.querySelector("#enc-voice-clear");
        const sendBtn = host.querySelector("#enc-voice-send");

        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            status.textContent = "Web Speech API not available in this browser. Switch to Keyboard or Template input. (Production: clinical-grade ASR via Nuance Dragon Medical One.)";
            btn.disabled = true;
            btn.classList.add("disabled");
            return;
        }

        const recog = new SR();
        recog.continuous = true;
        recog.interimResults = true;
        recog.lang = "en-US";

        let listening = false;
        let finalText = "";
        let interimText = "";

        recog.onresult = ev => {
            let interim = "";
            for (let i = ev.resultIndex; i < ev.results.length; i++) {
                const r = ev.results[i];
                if (r.isFinal) finalText += r[0].transcript + " ";
                else interim += r[0].transcript;
            }
            interimText = interim;
            transcriptEl.innerHTML = `${escapeHtml(finalText)}<em style="color: var(--ink-3);">${escapeHtml(interim)}</em>`;
        };
        recog.onerror = ev => { status.textContent = "Speech recognition error: " + ev.error; };
        recog.onend = () => {
            if (listening) {
                // restart for continuous listening
                try { recog.start(); } catch (_) {}
            }
        };

        btn.addEventListener("click", () => {
            if (!listening) {
                listening = true;
                try { recog.start(); } catch (_) {}
                btn.classList.add("recording");
                status.textContent = "● Recording... (click again to stop)";
                btn.querySelector(".enc-voice-label").textContent = "Stop recording";
            } else {
                listening = false;
                try { recog.stop(); } catch (_) {}
                btn.classList.remove("recording");
                status.textContent = "Recording stopped. Review transcript below.";
                btn.querySelector(".enc-voice-label").textContent = "Push to record";
            }
        });

        clearBtn.addEventListener("click", () => {
            finalText = "";
            interimText = "";
            transcriptEl.innerHTML = "";
        });
        sendBtn.addEventListener("click", () => {
            _sendToEncounter(finalText, targetTextareaId);
        });
    }

    function _sendToEncounter(text, targetTextareaId) {
        const target = document.getElementById(targetTextareaId);
        if (!target) {
            alert("Encounter dictation target not found.");
            return;
        }
        target.value = text;
        // Trigger any existing input handler
        target.dispatchEvent(new Event("input", { bubbles: true }));
        // Visually flash the target so the user sees it received
        target.classList.add("encounter-textarea-flash");
        setTimeout(() => target.classList.remove("encounter-textarea-flash"), 1200);
        // Scroll into view
        target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g,
            c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
    }

    window.OH_INTAKE = {
        renderRegistration,
        renderTrackBoard,
        getWaitingRoom,
        attachEncounterInput,
        _state: STATE,
    };
})();
