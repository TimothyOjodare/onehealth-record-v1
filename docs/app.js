/* ============================================================================
   ONE-HealthRecord — Application logic
   ----------------------------------------------------------------------------
   Bootstrapping, tab control, and the four primary views:
     1. Live encounter (dictation → entities → FHIR)
     2. One Health map (Leaflet)
     3. Knowledge graph (D3 force)
     4. Sentinel alerts (alerts + D3 chart)
     5. Architecture (inline SVG)
   ========================================================================== */

(function () {
    "use strict";
    const DATA = window.ONE_HR_DATA;
    const NLP = window.ONE_HR_NLP;
    const TERMS = DATA.terminologies;

    // Demo dictations baked in — used by the scenario buttons.
    // Phase 4.1 — each scenario is now tagged with the provider whose panel
    // owns the patient. Off-panel scenarios are hidden in the Live Encounter
    // toolbar based on the logged-in user's identity.
    const SCENARIO_OWNERS = {
        // Clinician scenarios → physician
        hernandez: { provider: "phys-reyes",    patient_kind: "human", patient_label: "Maria Hernandez" },
        johnson:   { provider: "phys-reyes",    patient_kind: "human", patient_label: "Tom Johnson" },
        williams:  { provider: "phys-okafor",   patient_kind: "human", patient_label: "Robert Williams" },
        begay:     { provider: "phys-yazzie",   patient_kind: "human", patient_label: "Sarah Begay" },
        ramirez:   { provider: "phys-anderson", patient_kind: "human", patient_label: "Roberto Ramirez" },
        becker:    { provider: "phys-anderson", patient_kind: "human", patient_label: "James Becker" },
        nguyen:    { provider: "phys-patel",    patient_kind: "human", patient_label: "Lan Nguyen" },
        sanchez:   { provider: "phys-reyes",    patient_kind: "human", patient_label: "Carlos Sanchez" },
        esrd:      { provider: "phys-patel",    patient_kind: "human", patient_label: "ESRD volume overload (general)" },
        // Veterinarian scenarios → vet
        vet_rocco:   { provider: "vet-cho",    patient_kind: "animal", patient_label: "Rocco (dog)" },
        vet_bella:   { provider: "vet-kim",    patient_kind: "animal", patient_label: "Bella (dog)" },
        vet_shadow:  { provider: "vet-becker", patient_kind: "animal", patient_label: "Shadow (cat)" },
        vet_trigger: { provider: "vet-becker", patient_kind: "animal", patient_label: "Trigger (horse)" },
        vet_mango:   { provider: "vet-kim",    patient_kind: "animal", patient_label: "Mango (bird)" },
        vet_buddy:   { provider: "vet-cho",    patient_kind: "animal", patient_label: "Buddy (dog)" },
    };

    const SCENARIOS = {
        hernandez: (
            "Fifty-two-year-old female, lives in Tucson, presenting with progressive cough times two weeks, " +
            "low-grade fever, and increasing fatigue. " +
            "She reports significant exposure to wind-blown soil dust during recent yard work, and the " +
            "family dog Rocco was just diagnosed with valley fever by their veterinarian last week. " +
            "On examination, Temp 100.8 F, HR 96, RR 18, SpO2 95% on room air. " +
            "Mild crackles auscultated in the right middle lobe. No skin rash. " +
            "Assessment: probable coccidioidomycosis given household animal index case and high-endemicity residence. " +
            "Plan: order Coccidioides serology, start fluconazole 200 mg twice daily, follow up in two weeks."
        ),
        johnson: (
            "Forty-seven-year-old male, lives in Florence in Pinal County, presents today with abrupt-onset fever, " +
            "headache, and a developing maculopapular rash that started on his wrists and ankles. " +
            "Symptoms began three days ago. " +
            "He was hiking five days ago and removed an attached tick the next morning. " +
            "Family dog Bella was diagnosed with ehrlichiosis eight days ago. " +
            "On examination, Temp 102.4 F, BP 124/78, HR 108, RR 18, SpO2 97% on room air. " +
            "Diffuse petechial rash involving palms and soles. " +
            "Assessment: high suspicion for Rocky Mountain spotted fever. " +
            "Plan: empiric doxycycline 100 mg twice daily, draw RMSF serology, monitor for progression."
        ),
        williams: (
            "Sixty-eight-year-old male, rural Maricopa County, presents with abrupt-onset fever, severe myalgia, " +
            "and progressive shortness of breath times three days. " +
            "Patient and his wife recently cleaned out a detached garage with heavy rodent infestation, ten days ago, " +
            "without respiratory protection. " +
            "On examination, Temp 102.8 F, BP 96/58, HR 124, RR 28, SpO2 87% on room air. " +
            "Bilateral crackles, no rash. " +
            "Assessment: hantavirus pulmonary syndrome must be considered given exposure history and presentation. " +
            "Plan: emergent admission to ICU, hantavirus IgM serology, supportive care, public health notification."
        ),
        esrd: (
            "Fifty-six-year-old male, known hypertensive and diabetic with end-stage renal disease on " +
            "maintenance hemodialysis, presenting with shortness of breath times one week and bilateral " +
            "leg swelling times one month. He missed his last two dialysis sessions. " +
            "On examination, BP 168/94, HR 102, RR 22, SpO2 91% on room air. " +
            "Bilateral basilar crackles on auscultation. No fever, no cough. " +
            "Assessment: acute fluid overload secondary to missed dialysis. " +
            "Plan: emergent dialysis, admit, cardiology consult."
        ),
        begay: (
            "Thirty-eight-year-old female, lives near St. Johns in Apache County, presents with abrupt-onset " +
            "fever, severe headache, and a tender swollen lump in the right groin times two days. " +
            "Her outdoor cat Shadow was diagnosed with plague at the veterinary clinic four days ago. " +
            "The cat has been hunting and consuming ground squirrels around their home. " +
            "On examination, Temp 103.6 F, BP 102/64, HR 124, RR 22, SpO2 95% on room air. " +
            "Tender right inguinal bubo measuring approximately three centimeters. No skin rash. " +
            "Assessment: high suspicion for bubonic plague — Class A reportable disease. " +
            "Plan: empiric streptomycin one gram IM twice daily, isolate, draw plague serology, " +
            "notify Arizona Department of Health Services and CDC immediately, household contact prophylaxis."
        ),
        ramirez: (
            "Fifty-nine-year-old male, lives near Bisbee in Cochise County, presents with five days of severe headache, " +
            "high fever, and progressive confusion. Family reports he has been less responsive over the past 24 hours. " +
            "Patient has known hypertension on lisinopril. " +
            "Property has standing water from the recent monsoon and the family horse Trigger was diagnosed " +
            "with West Nile virus by their veterinarian twelve days ago. " +
            "On examination, Temp 102.2 F, BP 158/92, HR 96, RR 18, SpO2 94% on room air. " +
            "Mild neck stiffness, oriented to person only. No rash. " +
            "Assessment: probable West Nile encephalitis given shared vector exposure with confirmed equine case. " +
            "Plan: admit, lumbar puncture, West Nile IgM serology on serum and CSF, supportive care, public health notification."
        ),
        becker: (
            "Forty-four-year-old male, runs a small goat dairy near Patagonia in Santa Cruz County, presents with " +
            "two weeks of dry cough, intermittent fever, and significant fatigue. " +
            "Three of his goats had spontaneous abortions over the past three weeks and the placental tissues " +
            "tested positive for Coxiella burnetii. He assisted with the deliveries without personal protective equipment. " +
            "On examination, Temp 101.4 F, BP 118/72, HR 88, RR 18, SpO2 96% on room air. " +
            "Mild crackles in the right lower lobe, no rash. " +
            "Assessment: Q fever with pneumonic presentation — classic occupational exposure. " +
            "Plan: empiric doxycycline 100 mg twice daily for two weeks, draw Q fever phase I and phase II antibodies, " +
            "chest X-ray, public health notification, follow up in two weeks."
        ),
        nguyen: (
            "Thirty-four-year-old female, lives in central Phoenix, presents with five days of high fever, severe headache, " +
            "and a dry non-productive cough. Pet African Grey parrot Mango has been listless and fluffed-up for two weeks " +
            "and was diagnosed with Chlamydia psittaci by her avian veterinarian. " +
            "On examination, Temp 102.8 F, BP 124/78, HR 104, RR 20, SpO2 94% on room air. " +
            "Mild crackles right base, no rash. " +
            "Assessment: probable psittacosis given direct bird exposure with confirmed avian index case. " +
            "Plan: empiric doxycycline 100 mg twice daily for ten days, chest X-ray, draw psittacosis serology, " +
            "public health notification."
        ),
        sanchez: (
            "Fifty-one-year-old male, lives near Florence in Pinal County, avid hunter, presents with " +
            "abrupt-onset fever, severe fatigue, and a painful swollen lump in his right armpit. " +
            "He field-dressed several wild rabbits eight days ago without gloves; one of the rabbits appeared sick. " +
            "He also has a non-healing skin ulcer on his right index finger at the dressing site. " +
            "On examination, Temp 102.6 F, BP 116/76, HR 108, RR 18, SpO2 97% on room air. " +
            "Tender right axillary lymphadenopathy approximately two centimeters; punched-out ulcer with raised border on right index finger. " +
            "Assessment: ulceroglandular tularemia given classic exposure history and presentation. " +
            "Plan: empiric streptomycin one gram IM twice daily, draw Francisella tularensis serology, " +
            "wound culture, public health notification."
        ),
        // Veterinarian scenarios
        vet_rocco: (
            "Patient Rocco, five-year-old male neutered Labrador Retriever, presented for two weeks of " +
            "decreased activity, reduced appetite, and intermittent dry cough. " +
            "Owner reports the dog frequently digs in dirt around the property in Tucson. " +
            "On examination, Temperature 102.6 F, Heart rate 110, Respiratory rate 32. " +
            "Mild crackles on thoracic auscultation in the right cranial lung field, body condition score 5/9. " +
            "Assessment: Coccidioidomycosis confirmed on Coccidioides serology. " +
            "Plan: fluconazole 5 milligram per kilogram orally twice daily for six months minimum, recheck in four weeks."
        ),
        vet_bella: (
            "Patient Bella, four-year-old female spayed German Shepherd, presented for one week of lethargy and inappetence. " +
            "Owner reports multiple ticks removed from the dog in the past month, lives in Florence Pinal County. " +
            "On examination, Temperature 103.4 F, Heart rate 120, mild generalized lymphadenopathy. " +
            "CBC reveals thrombocytopenia, platelets 88,000. " +
            "Assessment: Ehrlichiosis confirmed on SNAP 4Dx Plus. " +
            "Plan: doxycycline 5 milligram per kilogram orally twice daily for 28 days, recheck CBC in two weeks."
        ),
        vet_shadow: (
            "Patient Shadow, three-year-old female spayed Domestic Shorthair, presented for two days of high fever, " +
            "severely enlarged submandibular lymph node, and inappetence. " +
            "Owner reports cat is outdoor-access and frequently hunts ground squirrels in Apache County. " +
            "On examination, Temperature 105.2 F, Heart rate 220, severely enlarged tender submandibular lymph node. " +
            "Bubo aspirate Gram stain shows bipolar bacilli consistent with Yersinia pestis. " +
            "Assessment: feline plague — high zoonotic risk to household. " +
            "Plan: gentamicin 5 milligram per kilogram intramuscularly daily, isolate, owner counseled re household exposure, " +
            "Arizona Department of Health Services notified."
        ),
        vet_trigger: (
            "Patient Trigger, twelve-year-old male neutered Quarter Horse, presented for three days of progressive " +
            "ataxia, weakness, and muscle fasciculations. Property has standing water after recent monsoon rains. " +
            "On examination, Temperature 101.8 F, Heart rate 44, Respiratory rate 16. " +
            "Marked hindlimb ataxia with stumbling, muscle tremors of the face and shoulders, mentation depressed. " +
            "Assessment: West Nile virus encephalomyelitis confirmed on IgM capture ELISA. " +
            "Plan: supportive care with anti-inflammatories, owner counseled regarding mosquito control and " +
            "household human exposure risk, public health notification."
        ),
        vet_mango: (
            "Patient Mango, eight-year-old male African Grey Parrot, presented for two weeks of lethargy, " +
            "ruffled feathers, decreased vocalization, and green watery droppings. " +
            "Owner is a 34-year-old female who handles the bird daily. " +
            "On examination, weight 412 grams down from 478 grams, severely fluffed appearance, mild dyspnea. " +
            "Choanal swab PCR positive for Chlamydia psittaci. " +
            "Assessment: psittacosis — high zoonotic risk to household. " +
            "Plan: doxycycline 25 milligram per kilogram orally daily for 45 days, isolate from other birds, " +
            "owner strongly advised to seek medical evaluation given direct exposure."
        ),
        vet_buddy: (
            "Patient Buddy, six-year-old male neutered Mixed Breed dog, presented six days ago after attack " +
            "by a skunk in the yard. The skunk subsequently tested positive for rabies at the state lab. " +
            "Dog is current on rabies vaccination, last booster eight months ago. " +
            "On examination, multiple bite wounds on muzzle and neck, healing well, no neurologic signs, " +
            "Temperature 101.4 F, Heart rate 100, behavior bright alert and responsive. " +
            "Assessment: rabies exposure in vaccinated dog — currently in 45-day strict observation period per ADHS protocol. " +
            "Plan: post-exposure rabies booster administered today, strict confinement at home, " +
            "owner counseled, recheck and observation update in two weeks."
        ),
        clear: ""
    };

    // ----------------------------------------------------------------------
    // Tab switching
    // ----------------------------------------------------------------------
    const VIEW_INIT = {};
    const VIEW_RERENDER = {};   // Always-fire handlers (re-renderable views)
    function activateTab(viewName) {
        document.querySelectorAll(".tab").forEach(b =>
            b.classList.toggle("active", b.dataset.view === viewName));
        document.querySelectorAll(".view").forEach(v =>
            v.classList.toggle("active", v.id === "view-" + viewName));
        if (VIEW_INIT[viewName]) { VIEW_INIT[viewName](); VIEW_INIT[viewName] = null; }
        if (VIEW_RERENDER[viewName]) { VIEW_RERENDER[viewName](); }
        // Map needs a size invalidate if it was hidden when initialized.
        if (viewName === "map" && window._leafletMap) {
            setTimeout(() => window._leafletMap.invalidateSize(), 100);
        }
    }
    document.querySelectorAll(".tab").forEach(btn =>
        btn.addEventListener("click", () => activateTab(btn.dataset.view)));

    // ----------------------------------------------------------------------
    // Hub switching (Phase 3 — Clinical Workspace vs Public Health Console)
    // Each hub exposes only a subset of tabs. The active hub determines
    // which tab strip is visible and which is the default landing tab.
    // ----------------------------------------------------------------------
    const HUB_DEFAULTS = {
        "clinical":      "encounter",
        "public-health": "map",
        "intake":        "register",
        "envsurv":       "envsurv",
    };
    function activateHub(hubName) {
        document.querySelectorAll(".oh-hub-btn").forEach(b =>
            b.classList.toggle("active", b.dataset.hub === hubName));
        document.querySelectorAll("[data-hub-tabs]").forEach(strip =>
            strip.classList.toggle("active", strip.dataset.hubTabs === hubName));
        // Activate the default tab for the hub
        const defaultView = HUB_DEFAULTS[hubName];
        if (defaultView) activateTab(defaultView);
    }
    document.querySelectorAll(".oh-hub-btn").forEach(btn =>
        btn.addEventListener("click", () => activateHub(btn.dataset.hub)));

    // ======================================================================
    // PHASE 4 — Role-based access control: login, audit, gating, redaction
    // ======================================================================
    const SESSION_KEY = "onehr.session";
    const AUDIT_KEY   = "onehr.audit_log";
    const AUDIT_MAX   = 500;

    // Hub permissions per role:
    //   physician + veterinarian -> only Clinical Workspace
    //   public_health           -> only Public Health Console
    const ROLE_HUBS = {
        "physician":             ["clinical", "intake", "envsurv"],
        "veterinarian":          ["clinical", "intake", "envsurv"],
        "registrar":             ["intake", "envsurv"],
        "triage_nurse":          ["intake", "envsurv"],
        "vet_tech":              ["intake", "envsurv"],
        "discharge_coordinator": ["clinical", "envsurv"],
        "lab_tech":              ["clinical", "envsurv"],
        "administrator":         ["clinical", "envsurv"],
        "public_health":         ["public-health", "envsurv"],
        "environmental_public":  ["envsurv"],
    };
    const ROLE_DEFAULT_HUB = {
        "physician":             "clinical",
        "veterinarian":          "clinical",
        "registrar":             "intake",
        "triage_nurse":          "intake",
        "vet_tech":              "intake",
        "discharge_coordinator": "clinical",
        "lab_tech":              "clinical",
        "administrator":         "clinical",
        "public_health":         "public-health",
        "environmental_public":  "envsurv",
    };

    let SESSION = null; // { user_id, role, name, facility } or null

    function loadSession() {
        try {
            const raw = localStorage.getItem(SESSION_KEY);
            if (!raw) return null;
            const s = JSON.parse(raw);
            if (s && s.user_id && s.role) return s;
        } catch (_) {}
        return null;
    }

    function saveSession(s) {
        SESSION = s;
        try { localStorage.setItem(SESSION_KEY, JSON.stringify(s)); } catch (_) {}
    }

    function clearSession() {
        SESSION = null;
        try { localStorage.removeItem(SESSION_KEY); } catch (_) {}
    }

    // Audit log -- append, cap at AUDIT_MAX
    function auditLog(action, target) {
        const entry = {
            timestamp: new Date().toISOString(),
            user_id:   (SESSION && SESSION.user_id) || "anonymous",
            role:      (SESSION && SESSION.role) || "unauthenticated",
            action:    action,
            target:    target || "",
        };
        let log = [];
        try {
            log = JSON.parse(localStorage.getItem(AUDIT_KEY) || "[]");
            if (!Array.isArray(log)) log = [];
        } catch (_) { log = []; }
        log.push(entry);
        if (log.length > AUDIT_MAX) log = log.slice(-AUDIT_MAX);
        try { localStorage.setItem(AUDIT_KEY, JSON.stringify(log)); } catch (_) {}
        return entry;
    }

    function readAuditLog() {
        try {
            const log = JSON.parse(localStorage.getItem(AUDIT_KEY) || "[]");
            return Array.isArray(log) ? log : [];
        } catch (_) { return []; }
    }

    // Wrap activateTab and activateHub to audit-log
    // Phase 4 — also enforce role-based view permissions at the activation point
    const ROLE_VIEWS = {
        "physician":             ["encounter", "workspace", "register", "trackboard", "envsurv"],
        "veterinarian":          ["encounter", "workspace", "register", "trackboard", "envsurv"],
        "registrar":             ["register", "trackboard", "envsurv"],
        "triage_nurse":          ["register", "trackboard", "envsurv"],
        "vet_tech":              ["register", "trackboard", "envsurv"],
        "discharge_coordinator": ["encounter", "workspace", "envsurv"],
        "lab_tech":              ["encounter", "workspace", "envsurv"],
        "administrator":         ["encounter", "workspace", "envsurv"],
        "public_health":         ["map", "graph", "surveillance", "evaluation", "risk", "modelcard", "envsurv"],
        "environmental_public":  ["envsurv"],
    };
    const _activateTab = activateTab;
    activateTab = function (viewName) {
        if (SESSION) {
            const allowed = ROLE_VIEWS[SESSION.role] || [];
            if (allowed.indexOf(viewName) < 0) {
                auditLog("view_access_denied", viewName);
                return; // reject silently — UI buttons for these views are already hidden
            }
            auditLog("tab_view", viewName);
        }
        return _activateTab(viewName);
    };
    const _activateHub = activateHub;
    activateHub = function (hubName) {
        // Block unauthorized hub access
        if (SESSION) {
            const allowed = ROLE_HUBS[SESSION.role] || [];
            if (allowed.indexOf(hubName) < 0) {
                auditLog("hub_access_denied", hubName);
                return;
            }
            auditLog("hub_view", hubName);
        }
        return _activateHub(hubName);
    };

    // ----- Login UI rendering (Phase 8 — multi-stage domain flow) -----

    // Hospital + vet metadata (logos + branding colors)
    const INSTITUTION_BRANDING = {
        "tmc":         { color: "#003B5C", accent: "#FBB040", logo_text: "TMC", subtitle: "Tucson Medical Center" },
        "banner-phx":  { color: "#E37222", accent: "#003B5C", logo_text: "B",   subtitle: "Banner Health · Phoenix" },
        "banner-mesa": { color: "#E37222", accent: "#003B5C", logo_text: "B",   subtitle: "Banner Health · Mesa" },
        "honorhealth": { color: "#003B5C", accent: "#A6192E", logo_text: "HH",  subtitle: "HonorHealth Scottsdale" },
        "ihs-white":   { color: "#0F62A0", accent: "#FFFFFF", logo_text: "IHS", subtitle: "IHS Whiteriver Service Unit" },
        "naz":         { color: "#1B4332", accent: "#FBB040", logo_text: "NAZ", subtitle: "Northern AZ Healthcare" },
        "vet-pinal":   { color: "#0C234B", accent: "#AB0520", logo_text: "PMV", subtitle: "Pinal Mixed-Practice Vet" },
        "vet-tucson":  { color: "#1A7A89", accent: "#0C234B", logo_text: "TCV", subtitle: "Tucson Companion-Animal Vet" },
        "vet-cochise": { color: "#A6192E", accent: "#1B4332", logo_text: "CLA", subtitle: "Cochise Large-Animal Vet" },
        "vet-phx":     { color: "#0C234B", accent: "#1A7A89", logo_text: "PCA", subtitle: "Phoenix Companion-Animal Vet" },
        "adhs":        { color: "#AB0520", accent: "#0C234B", logo_text: "ADHS",subtitle: "Arizona Dept of Health Services" },
        "tribal":      { color: "#7C3F2C", accent: "#D89F2E", logo_text: "ATHA",subtitle: "Apache Tribal Health Authority" },
        "aphis":       { color: "#1B4332", accent: "#FFFFFF", logo_text: "VS",  subtitle: "USDA APHIS Veterinary Services" },
        "cdc":         { color: "#003B5C", accent: "#AB0520", logo_text: "CDC", subtitle: "CDC NNDSS (federal partner)" },
    };

    const PUBLIC_HEALTH_AGENCIES = [
        { id: "adhs",   name: "Arizona Department of Health Services", description: "State human-disease surveillance authority. Manages NNDSS reporting, MEDSIS database, and outbreak response." },
        { id: "tribal", name: "Apache Tribal Health Authority",        description: "Tribal-IRB-governed health surveillance for Apache reservations. Tribal sovereignty preserved over individual record access." },
        { id: "aphis",  name: "USDA APHIS Veterinary Services",        description: "Federal animal-disease authority. Manages VSPS reporting and federal-reportable animal-disease response." },
        { id: "cdc",    name: "CDC NNDSS",                              description: "Federal human-disease surveillance. Receives forwarded reports from state authorities; read-only role in this MVP." },
    ];

    const ROLE_LABELS = {
        physician:              { icon: "🩺", label: "Physician",       color: "#0C234B" },
        veterinarian:           { icon: "🐾", label: "Veterinarian",    color: "#1A7A89" },
        registrar:              { icon: "📋", label: "Registrar",       color: "#7C3F2C" },
        triage_nurse:           { icon: "🩹", label: "Triage Nurse",    color: "#AB0520" },
        vet_tech:               { icon: "🩹", label: "Vet Tech",        color: "#AB0520" },
        discharge_coordinator:  { icon: "📤", label: "Discharge",       color: "#4A6F4D" },
        lab_tech:               { icon: "🧪", label: "Lab Tech",        color: "#5C2A8B" },
        administrator:          { icon: "⚙️", label: "Administrator",   color: "#374151" },
        public_health:          { icon: "🏛️", label: "Public Health",   color: "#003B5C" },
    };

    let LOGIN_STAGE = "domain";
    let LOGIN_SUBDOMAIN = "human";
    let LOGIN_INSTITUTION = null;

    function renderLoginScreen() {
        const providers = (DATA && DATA.providers) || null;
        if (!providers) {
            console.error("providers.json not in bundle; login disabled");
            return;
        }

        // Stage 1: Domain cards click handlers
        document.querySelectorAll('.domain-card').forEach(card => {
            card.addEventListener('click', () => {
                const dom = card.dataset.domain;
                if (dom === 'environmental') {
                    // No login — go straight into env surveillance view
                    saveSession({
                        user_id: "anonymous-public",
                        role: "environmental_public",
                        name: "Public visitor",
                        facility: "Environmental Surveillance (public access)",
                    });
                    auditLog("login_public_environmental", "no auth");
                    enterApp();
                    setTimeout(() => activateTab("envsurv"), 100);
                    return;
                }
                showLoginStage(dom);
            });
        });

        // Stage 2 sub-tab handlers (human / animal)
        document.querySelectorAll('.login-subtab').forEach(t => {
            t.addEventListener('click', () => {
                document.querySelectorAll('.login-subtab').forEach(x => x.classList.remove('active'));
                t.classList.add('active');
                LOGIN_SUBDOMAIN = t.dataset.subdomain;
                renderInstitutionGrid();
            });
        });

        // Back buttons
        document.querySelectorAll('.login-back').forEach(b => {
            b.addEventListener('click', () => showLoginStage(b.dataset.back));
        });

        renderInstitutionGrid();
        renderAgencyGrid();
    }

    function showLoginStage(stage) {
        LOGIN_STAGE = stage;
        document.querySelectorAll('.login-stage').forEach(s => {
            s.classList.toggle('active', s.id === ('login-stage-' + stage));
        });
    }

    function renderInstitutionGrid() {
        const providers = (DATA && DATA.providers) || {};
        const facilities = providers.facilities || {};
        const list = LOGIN_SUBDOMAIN === "human" ? (facilities.hospitals || []) : (facilities.vets || []);
        const grid = document.getElementById('login-institutions');
        if (!grid) return;
        grid.innerHTML = list.map(f => {
            const b = INSTITUTION_BRANDING[f.id] || {};
            const nStaff = countStaffAt(f.id);
            return `
                <button class="institution-card" data-institution="${f.id}" data-kind="${LOGIN_SUBDOMAIN}" style="--inst-color: ${b.color}; --inst-accent: ${b.accent};">
                    <div class="institution-logo">${escapeHtml(b.logo_text || f.name.slice(0,3))}</div>
                    <h3>${escapeHtml(f.name)}</h3>
                    <p class="institution-city">${escapeHtml(f.city || "")}</p>
                    <p class="institution-staff-count">${nStaff} staff member${nStaff === 1 ? "" : "s"}</p>
                </button>`;
        }).join("");
        grid.querySelectorAll('.institution-card').forEach(c => {
            c.addEventListener('click', () => {
                LOGIN_INSTITUTION = { id: c.dataset.institution, kind: c.dataset.kind };
                renderInstitutionLogin();
                showLoginStage('institution');
            });
        });
    }

    function renderAgencyGrid() {
        const grid = document.getElementById('login-agencies');
        if (!grid) return;
        grid.innerHTML = PUBLIC_HEALTH_AGENCIES.map(a => {
            const b = INSTITUTION_BRANDING[a.id] || {};
            const nStaff = countAgencyStaff(a.id);
            return `
                <button class="institution-card" data-agency="${a.id}" style="--inst-color: ${b.color}; --inst-accent: ${b.accent};">
                    <div class="institution-logo">${escapeHtml(b.logo_text || a.id.toUpperCase())}</div>
                    <h3>${escapeHtml(a.name)}</h3>
                    <p class="institution-desc">${escapeHtml(a.description)}</p>
                    <p class="institution-staff-count">${nStaff} staff member${nStaff === 1 ? "" : "s"}</p>
                </button>`;
        }).join("");
        grid.querySelectorAll('.institution-card').forEach(c => {
            c.addEventListener('click', () => {
                LOGIN_INSTITUTION = { id: c.dataset.agency, kind: 'agency' };
                renderInstitutionLogin();
                showLoginStage('institution');
            });
        });
    }

    function countStaffAt(facId) {
        const p = (DATA && DATA.providers) || {};
        const all = [
            ...(p.physicians || []), ...(p.veterinarians || []),
            ...(p.registrars || []), ...(p.triage_nurses || []), ...(p.vet_techs || []),
            ...(p.discharge_coordinators || []), ...(p.lab_techs || []), ...(p.administrators || []),
        ];
        return all.filter(s => s.facility_id === facId || s.facility === _facNameFromId(facId)).length;
    }

    function countAgencyStaff(agencyId) {
        const p = (DATA && DATA.providers) || {};
        return (p.public_health || []).filter(s => _matchesAgency(s, agencyId)).length;
    }
    function _matchesAgency(s, agencyId) {
        const agency = (s.agency || s.facility || "").toLowerCase();
        if (agencyId === 'adhs') return /arizona dept|adhs|department of health/.test(agency);
        if (agencyId === 'tribal') return /tribal|apache/.test(agency);
        if (agencyId === 'aphis') return /aphis|usda/.test(agency);
        if (agencyId === 'cdc') return /cdc|nndss/.test(agency);
        return false;
    }

    function _facNameFromId(facId) {
        const p = (DATA && DATA.providers) || {};
        const all = [...(p.facilities?.hospitals || []), ...(p.facilities?.vets || [])];
        const f = all.find(x => x.id === facId);
        return f ? f.name : "";
    }

    function renderInstitutionLogin() {
        if (!LOGIN_INSTITUTION) return;
        const card = document.getElementById('login-institution-card');
        if (!card) return;
        const inst = LOGIN_INSTITUTION;
        const branding = INSTITUTION_BRANDING[inst.id] || { color: '#0C234B', accent: '#AB0520', logo_text: '?' };
        const facName = (inst.kind === 'agency')
            ? (PUBLIC_HEALTH_AGENCIES.find(a => a.id === inst.id) || {}).name
            : _facNameFromId(inst.id);
        const back = (inst.kind === 'agency') ? 'public_health' : 'healthcare';

        // What roles are available at this institution?
        let availableRoles = [];
        if (inst.kind === 'human') {
            availableRoles = ['physician', 'registrar', 'triage_nurse', 'discharge_coordinator', 'lab_tech', 'administrator'];
        } else if (inst.kind === 'animal') {
            availableRoles = ['veterinarian', 'registrar', 'vet_tech', 'administrator'];
        } else if (inst.kind === 'agency') {
            availableRoles = ['public_health'];
        }

        // For each role, find the staff at this institution
        const staffByRole = {};
        for (const role of availableRoles) {
            staffByRole[role] = _staffForRoleAtInstitution(role, inst);
        }

        card.style.setProperty('--inst-color', branding.color);
        card.style.setProperty('--inst-accent', branding.accent);
        card.innerHTML = `
            <div class="login-institution-header">
                <button class="login-back" data-back="${back}">← Back</button>
                <div class="login-institution-brand">
                    <div class="login-institution-logo">${escapeHtml(branding.logo_text)}</div>
                    <div>
                        <h2>${escapeHtml(facName || inst.id)}</h2>
                        <p class="login-institution-subtitle">${escapeHtml(branding.subtitle || '')}</p>
                    </div>
                </div>
            </div>
            <p class="login-institution-prompt">Sign in as:</p>
            <div class="login-role-grid">
                ${availableRoles.map(role => {
                    const r = ROLE_LABELS[role] || { icon: '?', label: role, color: '#374151' };
                    const staff = staffByRole[role] || [];
                    return `
                    <div class="login-role-tile" data-role="${role}">
                        <div class="role-tile-head" style="--role-color: ${r.color};">
                            <span class="role-tile-icon">${r.icon}</span>
                            <span class="role-tile-label">${escapeHtml(r.label)}</span>
                            <span class="role-tile-count">${staff.length}</span>
                        </div>
                        <div class="role-tile-staff">
                            ${staff.length === 0
                                ? '<div class="role-tile-empty">No staff at this institution.</div>'
                                : staff.map(s => `
                                    <button class="role-staff-btn" data-staff-id="${escapeHtml(s.id)}" data-role="${role}">
                                        <span class="staff-name">${escapeHtml(s.name)}</span>
                                        <span class="staff-title">${escapeHtml(s.title || s.specialty || r.label)}</span>
                                    </button>`).join("")}
                        </div>
                    </div>`;
                }).join("")}
            </div>
            <p class="login-disclaimer" style="margin-top: 18px;"><strong>Demo only.</strong> Production: SMART-on-FHIR with institution-specific identity provider.</p>`;

        // Wire back button
        card.querySelector('.login-back').addEventListener('click', () => showLoginStage(back));

        // Wire staff buttons
        card.querySelectorAll('.role-staff-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const staffId = btn.dataset.staffId;
                const role = btn.dataset.role;
                const staff = staffByRole[role].find(s => s.id === staffId);
                if (!staff) return;
                const session = {
                    user_id:  staff.id,
                    role:     role,
                    name:     staff.name,
                    facility: staff.facility || facName,
                    facility_id: inst.id,
                    facility_kind: inst.kind,
                    title:    staff.title || "",
                    specialty: staff.specialty || "",
                    credentials: staff.credentials || "",
                };
                saveSession(session);
                auditLog("login", staff.id);
                enterApp();
            });
        });
    }

    function _staffForRoleAtInstitution(role, inst) {
        const p = (DATA && DATA.providers) || {};
        const lookup = {
            physician:              p.physicians || [],
            veterinarian:           p.veterinarians || [],
            registrar:              p.registrars || [],
            triage_nurse:           p.triage_nurses || [],
            vet_tech:               p.vet_techs || [],
            discharge_coordinator:  p.discharge_coordinators || [],
            lab_tech:               p.lab_techs || [],
            administrator:          p.administrators || [],
            public_health:          p.public_health || [],
        };
        const candidates = lookup[role] || [];
        if (inst.kind === 'agency') {
            return candidates.filter(s => _matchesAgency(s, inst.id));
        } else {
            return candidates.filter(s =>
                s.facility_id === inst.id || s.facility === _facNameFromId(inst.id));
        }
    }

    function showLogin() {
        const overlay = document.getElementById("login-overlay");
        const root    = document.getElementById("app-root");
        if (overlay) overlay.style.display = "flex";
        if (root)    root.hidden = true;
    }

    function hideLogin() {
        const overlay = document.getElementById("login-overlay");
        const root    = document.getElementById("app-root");
        if (overlay) overlay.style.display = "none";
        if (root)    root.hidden = false;
    }

    function applyRoleGating() {
        if (!SESSION) return;
        const allowed = ROLE_HUBS[SESSION.role] || [];
        // Hide hub buttons the user can't access
        document.querySelectorAll(".oh-hub-btn").forEach(btn => {
            const hub = btn.dataset.hub;
            const allow = allowed.indexOf(hub) >= 0;
            btn.hidden = !allow;
        });
        // Display session info in header
        const roleEl = document.getElementById("session-role");
        const nameEl = document.getElementById("session-name");
        const facEl  = document.getElementById("session-fac");
        if (roleEl) {
            roleEl.textContent = ({
                "physician":             "Physician",
                "veterinarian":          "Veterinarian",
                "registrar":             "Registrar",
                "triage_nurse":          "Triage Nurse",
                "vet_tech":              "Vet Tech",
                "discharge_coordinator": "Discharge",
                "lab_tech":              "Lab Tech",
                "administrator":         "Administrator",
                "public_health":         "Public Health",
                "environmental_public":  "Public Visitor",
            })[SESSION.role] || SESSION.role;
            roleEl.className = "session-role role-" + SESSION.role;
        }
        if (nameEl) nameEl.textContent = SESSION.name;
        if (facEl)  facEl.textContent  = "· " + SESSION.facility;

        // Hide scenario toolbars for the wrong audience
        document.querySelectorAll("[data-scenarios-for]").forEach(row => {
            const audience = row.dataset.scenariosFor;
            if (SESSION.role === "physician" && audience === "veterinarian") row.style.display = "none";
            else if (SESSION.role === "veterinarian" && audience === "clinician") row.style.display = "none";
            else row.style.display = "";
        });

        // Phase 4.1 — hide off-panel scenario buttons within the visible toolbar.
        // A clinician sees only scenarios whose patient is on their own panel.
        document.querySelectorAll(".scenario-btn[data-scenario]").forEach(btn => {
            const sname = btn.dataset.scenario;
            if (sname === "clear") { btn.hidden = false; return; }   // always visible
            const owner = SCENARIO_OWNERS[sname];
            if (!owner) { btn.hidden = false; return; }              // unmapped → leave visible
            const onPanel = (owner.provider === SESSION.user_id);
            // Public-health users don't reach Live Encounter at all (gated upstream);
            // for clinicians and vets, gate on provider ownership.
            btn.hidden = !onPanel;
        });
        // Show a small note if any off-panel scenarios are hidden, so the user
        // knows the gating is real and isn't a UI bug.
        const visibleClinScenarios = Array.from(document.querySelectorAll('[data-scenarios-for="clinician"] .scenario-btn[data-scenario]:not([data-scenario="clear"])'))
            .filter(b => !b.hidden).length;
        const visibleVetScenarios  = Array.from(document.querySelectorAll('[data-scenarios-for="veterinarian"] .scenario-btn[data-scenario]:not([data-scenario="clear"])'))
            .filter(b => !b.hidden).length;
        const totalClin = 9, totalVet = 6;
        const ensureNote = (rowSelector, visible, total) => {
            const row = document.querySelector(rowSelector);
            if (!row) return;
            // Remove any prior note
            const prior = row.querySelector(".off-panel-note");
            if (prior) prior.remove();
            const hidden = total - visible;
            if (hidden > 0 && (SESSION.role === "physician" || SESSION.role === "veterinarian")) {
                const note = document.createElement("span");
                note.className = "off-panel-note";
                note.textContent = `· ${hidden} additional scenario${hidden === 1 ? "" : "s"} on other panels (not shown)`;
                row.appendChild(note);
            }
        };
        ensureNote('[data-scenarios-for="clinician"]', visibleClinScenarios, totalClin);
        ensureNote('[data-scenarios-for="veterinarian"]', visibleVetScenarios, totalVet);
    }

    function enterApp() {
        applyRoleGating();
        hideLogin();
        // Land on the user's default hub
        const defaultHub = ROLE_DEFAULT_HUB[SESSION.role] || "clinical";
        _activateHub(defaultHub); // direct call to bypass audit (we already logged login)
        // Phase 8: attach encounter input panel (voice / keyboard / template)
        setTimeout(() => {
            const host = document.getElementById("encounter-input-host");
            if (host && window.OH_INTAKE && SESSION && (SESSION.role === "physician" || SESSION.role === "veterinarian")) {
                window.OH_INTAKE.attachEncounterInput(host, { targetTextareaId: "dictation" });
            }
        }, 200);
    }

    // Sign out handler
    const signoutBtn = document.getElementById("signout-btn");
    if (signoutBtn) {
        signoutBtn.addEventListener("click", () => {
            auditLog("signout", SESSION ? SESSION.user_id : "");
            clearSession();
            location.reload();
        });
    }

    // Boot: check for existing session, otherwise render login
    renderLoginScreen();
    SESSION = loadSession();
    if (SESSION) {
        applyRoleGating();
        hideLogin();
    } else {
        showLogin();
    }

    // ======================================================================
    // PHASE 4 — Patient-list filtering + cross-species pointer redaction
    // ======================================================================
    function getPanelPatientIds() {
        // Return the set of patient IDs the logged-in clinician is authorized to see.
        if (!SESSION || !DATA || !DATA.providers) return null;
        const panels = (DATA.providers.panels || {});
        if (SESSION.role === "physician") {
            return (panels.physicians || {})[SESSION.user_id] || [];
        } else if (SESSION.role === "veterinarian") {
            return (panels.veterinarians || {})[SESSION.user_id] || [];
        }
        return null;
    }

    function getAuthorizedPatientKind() {
        if (!SESSION) return null;
        if (SESSION.role === "physician") return "human";
        if (SESSION.role === "veterinarian") return "animal";
        return null;
    }

    // Compute the set of households where a cross-species cluster signal exists.
    // Uses the existing alerts data (already in the bundle).
    function getHouseholdsWithCrossSpeciesSignal() {
        const set = new Set();
        const alerts = (DATA && DATA.alerts && DATA.alerts.alerts) || [];
        alerts.forEach(a => {
            const kind = (a.kind || a.alert_type || a.type || "").toUpperCase();
            if (kind === "CROSS_SPECIES_CLUSTER" || kind === "PROPHYLACTIC_HOUSEHOLD" ||
                kind.indexOf("CROSS_SPECIES") >= 0 || kind.indexOf("CLUSTER") >= 0) {
                if (a.household_id) set.add(a.household_id);
                if (Array.isArray(a.households)) a.households.forEach(h => set.add(h));
            }
        });
        return set;
    }

    // Get the disease class for a household's cross-species cluster, if any.
    function getCrossSpeciesDiseaseClass(householdId) {
        const alerts = (DATA && DATA.alerts && DATA.alerts.alerts) || [];
        for (const a of alerts) {
            if (a.household_id !== householdId) continue;
            const kind = (a.kind || a.alert_type || a.type || "").toUpperCase();
            if (kind !== "CROSS_SPECIES_CLUSTER" && kind !== "PROPHYLACTIC_HOUSEHOLD" &&
                kind.indexOf("CROSS_SPECIES") < 0 && kind.indexOf("CLUSTER") < 0) continue;
            return a.disease_display || a.disease_class || a.disease ||
                   (a.evidence && a.evidence.disease) ||
                   (a.findings && a.findings.disease) || null;
        }
        return null;
    }

    // Render the 3-tier cross-species pointer panel for a clinician/vet view.
    // Returns an HTML string, or empty if no signal.
    function renderCrossSpeciesPointer(householdId) {
        if (!SESSION) return "";
        if (SESSION.role !== "physician" && SESSION.role !== "veterinarian") return "";
        const xspSet = getHouseholdsWithCrossSpeciesSignal();
        if (!xspSet.has(householdId)) return "";

        const otherSpeciesText = SESSION.role === "physician"
            ? "An animal or animals"
            : "A human or humans";
        const diseaseClass = getCrossSpeciesDiseaseClass(householdId);

        return `
            <div class="cross-species-pointer">
                <h4>Model · One Health pointer</h4>
                <div class="csp-tier">
                    <strong>Tier 1.</strong> This household — or the community from which the patient is from — has a model-flagged cross-species risk signal. See the Public Health Console (or contact ADHS) for cluster-level detail.
                </div>
                <div class="csp-tier">
                    <strong>Tier 2.</strong> ${otherSpeciesText} in this household or community has a related condition.
                </div>
                <div class="csp-tier">
                    <strong>Tier 3 (disease class):</strong>
                    ${diseaseClass ? `<span class="csp-disease-class">${escapeHtml(diseaseClass)}</span>` : `<span class="csp-disease-class">cluster signal</span>`}
                    — name and species withheld by access policy.
                </div>
                <div class="csp-source">
                    Provenance: <code>model_pointer</code> (not raw_record). Generated by the cross-species cluster detector. Underlying record is not accessible to your role.
                </div>
            </div>
        `;
    }

    // Expose Phase 4 helpers on a namespace so existing renderers can call them
    window.OH_AUTH = {
        getPanelPatientIds,
        getAuthorizedPatientKind,
        renderCrossSpeciesPointer,
        getSession: () => SESSION,
        auditLog,
        readAuditLog,
    };

    // ======================================================================
    // VIEW 1 — Live encounter
    // ======================================================================
    const dictEl = document.getElementById("dictation");
    const highlightEl = document.getElementById("highlighted");
    const fhirListEl = document.getElementById("fhir-list");
    const mResources = document.getElementById("m-resources");
    const mConditions = document.getElementById("m-conditions");
    const mObservations = document.getElementById("m-observations");
    const mConfidence = document.getElementById("m-confidence");

    function renderHighlighted(rawText, entities) {
        if (!rawText.trim()) { highlightEl.innerHTML = '<span style="color:var(--ink-4)">Type or paste a dictation to see live entity extraction…</span>'; return; }
        // Build the highlighted text by walking entities sorted by start.
        // Resolve overlaps: keep longer / earlier entity, drop overlapping ones.
        const sorted = entities.slice().sort((a, b) => a.char_start - b.char_start || (b.char_end - b.char_start) - (a.char_end - a.char_start));
        const accepted = [];
        for (const e of sorted) {
            if (accepted.some(a => !(e.char_end <= a.char_start || e.char_start >= a.char_end))) continue;
            accepted.push(e);
        }
        accepted.sort((a, b) => a.char_start - b.char_start);

        let cursor = 0;
        const parts = [];
        for (const e of accepted) {
            if (e.char_start > cursor) parts.push(escapeHtml(rawText.substring(cursor, e.char_start)));
            const flagClasses = [];
            if (e.negated) flagClasses.push("negated");
            if (e.uncertain) flagClasses.push("uncertain");
            const codes = (e.codes || []).map(c => c.code).join(", ");
            const tip = e.kind + (codes ? " · " + codes : "") + (e.attributes && e.attributes.display ? " · " + e.attributes.display : "")
                       + " · phase=" + e.phase + " · conf=" + e.confidence.toFixed(2)
                       + (e.negated ? " · NEGATED" : "") + (e.uncertain ? " · HEDGED" : "");
            parts.push(
                '<span class="ent ' + flagClasses.join(" ") + '" data-kind="' + e.kind + '" title="' + escapeHtml(tip) + '">' +
                escapeHtml(rawText.substring(e.char_start, e.char_end)) +
                '</span>'
            );
            cursor = e.char_end;
        }
        if (cursor < rawText.length) parts.push(escapeHtml(rawText.substring(cursor)));
        highlightEl.innerHTML = parts.join("");
    }
    function escapeHtml(s) { return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }

    function renderFhir(bundle) {
        if (!bundle || !bundle.entry || !bundle.entry.length) {
            mResources.textContent = "0"; mConditions.textContent = "0";
            mObservations.textContent = "0"; mConfidence.textContent = "—";
            fhirListEl.innerHTML = '<div class="empty-state">FHIR bundle will appear here as you dictate.</div>';
            return;
        }
        const counts = {};
        let confSum = 0, confN = 0;
        for (const e of bundle.entry) {
            const rt = e.resource.resourceType;
            counts[rt] = (counts[rt] || 0) + 1;
            for (const ext of (e.resource.extension || [])) {
                if (ext.url === "http://onehealthrecord.org/confidence") {
                    confSum += ext.valueDecimal; confN++;
                }
            }
        }
        mResources.textContent = bundle.entry.length;
        mConditions.textContent = counts.Condition || 0;
        mObservations.textContent = counts.Observation || 0;
        mConfidence.textContent = confN ? (confSum / confN).toFixed(2) : "—";

        const cards = bundle.entry.map(e => fhirCard(e.resource)).join("");
        fhirListEl.innerHTML = cards;
    }
    function fhirCard(r) {
        const rt = r.resourceType;
        let title = "", codes = "", conf = "";
        if (rt === "Patient") {
            title = (r.gender || "?") + ", born " + (r.birthDate || "?");
        } else if (rt === "Condition") {
            title = (r.code && r.code.text) || "(no display)";
            codes = (r.code && r.code.coding || []).map(c => `${c.system.split('/').pop()}:${c.code}`).join(" · ");
            const cs = r.clinicalStatus && r.clinicalStatus.coding && r.clinicalStatus.coding[0].code;
            if (cs === "provisional") title += "  ◇ provisional";
        } else if (rt === "Observation") {
            title = (r.code && r.code.text) || (r.code && r.code.coding && r.code.coding[0] && r.code.coding[0].display) || "(observation)";
            if (r.valueQuantity) title += " — " + r.valueQuantity.value + " " + r.valueQuantity.unit;
            if (r.valueBoolean === false) title += " — NEGATIVE";
            if (r.component) title += " — " + r.component.map(c => c.valueQuantity.value).join(" / ");
            codes = (r.code && r.code.coding || []).map(c => `${c.system.split('/').pop()}:${c.code}`).join(" · ");
        } else if (rt === "MedicationStatement") {
            title = (r.medicationCodeableConcept && r.medicationCodeableConcept.text) || "(medication)";
            codes = (r.medicationCodeableConcept && r.medicationCodeableConcept.coding || []).map(c => `${c.system.split('/').pop()}:${c.code}`).join(" · ");
        } else if (rt === "Provenance") {
            title = "Machine-authored bundle (engine v0.1)";
            codes = (r.activity && r.activity.coding && r.activity.coding[0] && r.activity.coding[0].code) || "";
        }
        for (const ext of (r.extension || [])) {
            if (ext.url === "http://onehealthrecord.org/confidence") {
                const c = ext.valueDecimal;
                conf = `<span class="conf ${c < 0.7 ? "low" : ""}">${c.toFixed(2)}</span>`;
            }
        }
        return `<div class="fhir-card" data-rt="${rt}">
            <div class="rt">${rt}</div>
            <div class="title">${escapeHtml(title)}${conf}</div>
            ${codes ? `<div class="codes">${escapeHtml(codes)}</div>` : ""}
        </div>`;
    }

    function runDictationPipeline() {
        const text = dictEl.value;
        if (!text.trim()) {
            renderHighlighted("", []);
            renderFhir(null);
            return;
        }
        const { parsed, entities } = NLP.extractEntities(text, TERMS);
        renderHighlighted(text, entities);
        const bundle = NLP.buildBundle(entities, text);
        renderFhir(bundle);
    }

    // Debounced input handler.
    let dictTimer = null;
    dictEl.addEventListener("input", () => {
        clearTimeout(dictTimer);
        dictTimer = setTimeout(runDictationPipeline, 120);
    });

    // Scenario buttons.
    document.querySelectorAll(".scenario-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            dictEl.value = SCENARIOS[btn.dataset.scenario] || "";
            runDictationPipeline();
            dictEl.scrollTop = 0;
        });
    });

    // Initialize with the headline scenario.
    dictEl.value = SCENARIOS.hernandez;
    runDictationPipeline();

    // ======================================================================
    // VIEW 2 — Map
    // ======================================================================
    VIEW_INIT.map = function () {
        const map = L.map("map", { zoomControl: true, scrollWheelZoom: false }).setView([34.0, -111.7], 6);
        window._leafletMap = map;

        // Subtle Carto Voyager-style basemap (free, no API key).
        L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
            attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
            maxZoom: 12, minZoom: 5, subdomains: "abcd",
        }).addTo(map);

        // County circles tinted by Coccidioides endemicity, sized by EPA EQI deviation.
        const endemicColor = { high: "#AB0520", moderate: "#C8553D", low: "#3F6B47" };
        for (const c of DATA.counties.counties) {
            const radius = 12000 + Math.abs(c.epa_eqi) * 18000;
            L.circle([c.lat, c.lon], {
                radius,
                color: endemicColor[c.cocci_endemic] || "#A8B5A8",
                weight: 1.2, opacity: 0.65,
                fillColor: endemicColor[c.cocci_endemic] || "#A8B5A8",
                fillOpacity: 0.12,
            }).bindPopup(
                `<div class="popup-title">${c.name} County</div>
                 <div class="popup-row"><b>FIPS:</b> ${c.fips}</div>
                 <div class="popup-row"><b>EPA EQI:</b> ${c.epa_eqi.toFixed(2)} ${c.epa_eqi < 0 ? "(better)" : "(worse)"}</div>
                 <div class="popup-row"><b>Coccidioides endemicity:</b> ${c.cocci_endemic}</div>
                 <div class="popup-row"><b>Population:</b> ${c.population.toLocaleString()}</div>`
            ).addTo(map);
        }

        // Build alert lookup by household_id and by county.
        const hhSeverity = {};
        const countyAlerts = {};
        for (const a of DATA.alerts.alerts) {
            if (a.household_id) {
                if (!hhSeverity[a.household_id] || sevRank(a.severity) > sevRank(hhSeverity[a.household_id])) {
                    hhSeverity[a.household_id] = a.severity;
                }
            }
            if (a.geography && a.geography.county_fips) {
                (countyAlerts[a.geography.county_fips] ||= []).push(a);
            }
        }

        // Household markers
        for (const hh of DATA.households.households) {
            const sev = hhSeverity[hh.household_id] || "healthy";
            const cls = sev;
            const icon = L.divIcon({
                className: "hh-marker " + cls,
                html: hh.animals.length ? "🐾" : "👥",
                iconSize: [28, 28], iconAnchor: [14, 14],
            });
            // Jitter a tiny bit so multiple households in the same county don't stack.
            const jitter = (Math.random() - 0.5) * 0.18;
            const m = L.marker([hh.county.lat + jitter, hh.county.lon + jitter * 1.4], { icon });
            const memberLines = []
                .concat(hh.humans.map(p => `${p.name[0].given[0]} ${p.name[0].family} (${p.gender})`))
                .concat(hh.animals.map(a => `${a.name} — ${a.species.code} (${a.breed})`));
            const conditionLines = hh.conditions.map(c => `<span style="color:var(--ua-cardinal)">●</span> ${c.code.text}`);
            m.bindPopup(
                `<div class="popup-title">${hh.name} household</div>
                 <div class="popup-row"><b>${hh.county.name} Co.</b> · ${hh.household_id}</div>
                 <div class="popup-row" style="margin-top:6px;"><b>Members:</b><br>${memberLines.join("<br>")}</div>
                 ${conditionLines.length ? `<div class="popup-row" style="margin-top:6px;"><b>Active dx:</b><br>${conditionLines.join("<br>")}</div>` : ""}
                 ${sev !== "healthy" ? `<div class="popup-row" style="margin-top:6px;color:var(--ua-cardinal)"><b>Active alert:</b> ${sev.toUpperCase()}</div>` : ""}`
            );
            m.addTo(map);
        }

        // Cross-species cluster arc — Hernandez household: draw a line between the
        // owner and the dog over the household location. (Symbolic — emphasizes the linkage.)
        const xspecies = DATA.alerts.alerts.filter(a => a.kind === "CROSS_SPECIES_CLUSTER");
        for (const a of xspecies) {
            if (!a.geography || !a.geography.lat) continue;
            const c = [a.geography.lat, a.geography.lon];
            // Animated pulsing circle marking the cluster.
            const pulse = L.circleMarker(c, {
                radius: 24, color: "#AB0520", weight: 3, opacity: 0.8,
                fillColor: "#AB0520", fillOpacity: 0,
                className: "cluster-pulse",
            }).addTo(map);
        }
    };

    function sevRank(s) { return ({ info: 1, watch: 2, action: 3 })[s] || 0; }

    // Add small CSS for the pulse animation.
    const styleAdd = document.createElement("style");
    styleAdd.textContent = `
        .cluster-pulse { animation: clusterPulse 1.6s ease-out infinite; }
        @keyframes clusterPulse {
            0%   { stroke-width: 3; r: 14; opacity: 0.95; }
            100% { stroke-width: 0; r: 38; opacity: 0; }
        }`;
    document.head.appendChild(styleAdd);

    // ======================================================================
    // VIEW 3 — Knowledge graph (D3 force)
    // ======================================================================
    VIEW_INIT.graph = function () {
        // Always wire the search bar first, even if d3 fails to load
        try { _wireKgSearch(null, null, null, 0, 0); } catch (e) { console.warn("KG search wiring:", e); }
        try {
        const svg = d3.select("#graph-svg");
        const bb = svg.node().getBoundingClientRect();
        const W = bb.width, H = bb.height || 640;
        svg.attr("viewBox", `0 0 ${W} ${H}`);

        const root = svg.append("g").attr("class", "graph-root");
        svg.call(d3.zoom().scaleExtent([0.3, 3]).on("zoom", e => root.attr("transform", e.transform)));

        const kg = DATA.knowledge_graph;
        const nodes = kg.nodes.map(n => Object.assign({}, n));
        const links = kg.links.map(l => Object.assign({}, l));

        const COLOR = {
            Person: "#0C234B", Animal: "#3F6B47", Household: "#C8553D",
            County: "#A8B5A8", Disease: "#AB0520", Condition: "#1F4D7A",
            Environment: "#8B6F47", Exposure: "#D89F2E",
        };
        const SIZE = { Person: 7, Animal: 7, Household: 11, County: 13, Disease: 12, Condition: 7, Environment: 6, Exposure: 5 };

        const sim = d3.forceSimulation(nodes)
            .force("link", d3.forceLink(links).id(d => d.id).distance(d => d.kind === "LIVES_IN" ? 38 : 80).strength(0.9))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(W / 2, H / 2))
            .force("collide", d3.forceCollide().radius(d => (SIZE[d.type] || 5) + 6));

        const link = root.append("g").attr("class", "links")
            .selectAll("line").data(links).join("line")
            .attr("class", d => "link" + (d.kind === "SAME_DISEASE_AS" ? " cross-species" : ""))
            .attr("stroke-width", d => d.kind === "INSTANCE_OF" ? 1.8 : 1);

        const node = root.append("g").attr("class", "nodes")
            .selectAll("g").data(nodes).join("g")
            .call(d3.drag()
                .on("start", (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
                .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
                .on("end",  (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));
        node.append("circle")
            .attr("r", d => SIZE[d.type] || 5)
            .attr("fill", d => COLOR[d.type] || "#999")
            .attr("stroke", "var(--bg-raised)")
            .attr("stroke-width", 2);
        node.append("title").text(d => `${d.type}: ${d.label || d.id}`);
        node.filter(d => d.type === "Household" || d.type === "County" || d.type === "Disease")
            .append("text")
            .attr("class", d => "node-label" + (d.type === "Household" ? " hh" : ""))
            .attr("x", d => (SIZE[d.type] || 5) + 4)
            .attr("y", 3)
            .text(d => d.label || d.id);

        sim.on("tick", () => {
            link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
            node.attr("transform", d => `translate(${d.x},${d.y})`);
        });

        // Phase 8 — Knowledge graph patient identity search (re-wire with d3 nodes)
        _wireKgSearch(svg, node, nodes, W, H);
        } catch (e) {
            console.warn("Graph view d3 init failed; search bar still wired:", e);
        }
    };

    // Phase 8 — KG search (extracted so it works even if d3 fails to load)
    function _wireKgSearch(svg, node, nodes, W, H) {
        const searchBtn = document.getElementById("kg-search-btn");
        const clearBtn = document.getElementById("kg-search-clear");
        const resultPanel = document.getElementById("kg-search-result");
        if (!searchBtn || !resultPanel) return;

        function _matchPatient(name, dob, address) {
            const data = window.ONE_HR_DATA || {};
            // households can be an envelope {_metadata, households: [...]} or a direct array
            const hhContainer = data.households || {};
            const households = Array.isArray(hhContainer) ? hhContainer : (hhContainer.households || []);
            const nameQuery = (name || "").trim().toLowerCase();
            const dobQuery = (dob || "").trim();
            const addrQuery = (address || "").trim().toLowerCase();
            const matches = [];
            for (const hh of households) {
                for (const h of (hh.humans || [])) {
                    const nm = (h.name && h.name[0]) || {};
                    const family = (nm.family || h.family || h.last_name || "").toLowerCase();
                    const given = ((nm.given && nm.given[0]) || (h.given && h.given[0]) || h.first_name || "").toLowerCase();
                    const fullName = (given + " " + family).trim();
                    const hDob = h.birthDate || h.dob || "";
                    const addrObj = (h.address && h.address[0]) || {};
                    const addrLine = ((addrObj.line && addrObj.line[0]) || "").toLowerCase();
                    const city = (addrObj.city || "").toLowerCase();

                    let score = 0;
                    let matched = false;
                    if (nameQuery) {
                        if (fullName.includes(nameQuery) || family.includes(nameQuery) || given.includes(nameQuery)) {
                            score += 0.5; matched = true;
                        } else continue;
                    } else {
                        matched = true;
                    }
                    if (dobQuery) {
                        if (hDob === dobQuery) score += 0.4;
                        else if (nameQuery) score -= 0.3;
                    }
                    if (addrQuery) {
                        if ((addrLine + " " + city).includes(addrQuery)) score += 0.2;
                        else if ((hh.county?.name || "").toLowerCase().includes(addrQuery)) score += 0.15;
                    }
                    if (matched && score > 0) {
                        matches.push({
                            patient_id: h.id,
                            name: (((nm.given && nm.given[0]) || "") + " " + (nm.family || "")).trim(),
                            dob: hDob,
                            household: hh.household_id,
                            address: ((addrObj.line && addrObj.line[0]) || "(synthetic)") + ", " + (addrObj.city || hh.county?.name || ""),
                            county: hh.county?.name || "",
                            score: Math.min(0.99, score),
                        });
                    }
                }
            }
            matches.sort((a, b) => b.score - a.score);
            return matches.slice(0, 5);
        }

        function _highlightNode(patientId) {
            if (!node || !nodes) return false;
            const targetNode = nodes.find(n => n.id === patientId);
            if (!targetNode) return false;
            try {
                node.selectAll("circle").classed("kg-pulse", false);
                node.filter(d => d.id === patientId).select("circle").classed("kg-pulse", true);
                if (window.d3 && svg) {
                    const transform = window.d3.zoomIdentity.translate(W/2 - targetNode.x * 1.6, H/2 - targetNode.y * 1.6).scale(1.6);
                    svg.transition().duration(800).call(window.d3.zoom().transform, transform);
                }
                setTimeout(() => { try { node.selectAll("circle").classed("kg-pulse", false); } catch(_) {} }, 4000);
            } catch (e) { console.warn("KG highlight error:", e); }
            return true;
        }

        searchBtn.addEventListener("click", () => {
            const name = document.getElementById("kg-search-name").value;
            const dob = document.getElementById("kg-search-dob").value;
            const address = document.getElementById("kg-search-address").value;
            if (!name && !dob && !address) {
                resultPanel.innerHTML = '<div class="kg-search-empty">Enter at least one identifier (name, DOB, or address) to search.</div>';
                resultPanel.hidden = false;
                return;
            }
            const matches = _matchPatient(name, dob, address);
            if (window.OH_AUTH) window.OH_AUTH.auditLog("kg_patient_search", `${name||'-'} | ${dob||'-'} | ${address||'-'}`);
            if (matches.length === 0) {
                resultPanel.innerHTML = '<div class="kg-search-empty">No patient found matching those identifiers.</div>';
                resultPanel.hidden = false;
                return;
            }
            resultPanel.innerHTML = `
                <div class="kg-search-result-head">
                    <strong>${matches.length} match${matches.length === 1 ? '' : 'es'}</strong> — read the identifiers aloud to confirm:
                </div>
                ${matches.map(m => `
                    <div class="kg-result-card" data-patient-id="${escapeHtml(m.patient_id)}">
                        <div class="kg-result-head">
                            <strong>${escapeHtml(m.name)}</strong>
                            <span class="kg-result-score">${(m.score * 100).toFixed(0)}% match</span>
                        </div>
                        <div class="kg-result-row"><strong>DOB:</strong> ${escapeHtml(m.dob)}</div>
                        <div class="kg-result-row"><strong>Address:</strong> ${escapeHtml(m.address)}</div>
                        <div class="kg-result-row"><strong>Household:</strong> <code>${escapeHtml(m.household)}</code></div>
                        <button class="cds-action-btn cds-primary kg-result-locate" data-patient-id="${escapeHtml(m.patient_id)}">Locate in graph &amp; verify →</button>
                    </div>
                `).join("")}`;
            resultPanel.hidden = false;
            resultPanel.querySelectorAll(".kg-result-locate").forEach(b => {
                b.addEventListener("click", () => {
                    const found = _highlightNode(b.dataset.patientId);
                    if (!found) {
                        const card = b.closest(".kg-result-card");
                        const note = document.createElement("div");
                        note.className = "kg-result-row";
                        note.style.color = "var(--ink-3)";
                        note.style.fontStyle = "italic";
                        note.textContent = "(Patient not currently rendered in graph view — verified via search match only.)";
                        card.appendChild(note);
                    }
                });
            });
        });
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                document.getElementById("kg-search-name").value = "";
                document.getElementById("kg-search-dob").value = "";
                document.getElementById("kg-search-address").value = "";
                resultPanel.hidden = true;
                try { node.selectAll("circle").classed("kg-pulse", false); } catch(_) {}
            });
        }
    }

    // ======================================================================
    // VIEW 4 — Surveillance
    // ======================================================================
    VIEW_INIT.surveillance = function () {
        const list = document.getElementById("alert-list");
        const detail = document.getElementById("alert-detail");
        const alerts = DATA.alerts.alerts;

        list.innerHTML = alerts.map((a, i) => `
            <div class="alert-card ${a.severity}" data-i="${i}">
                <div class="head">
                    <span class="kind">${a.kind.replace(/_/g, " ")}</span>
                    <span class="sev-pill">${a.severity}</span>
                </div>
                <div class="title">${escapeHtml(a.title)}</div>
                <div class="summary">${escapeHtml(a.summary)}</div>
                <div class="meta">conf ${a.confidence.toFixed(2)} · ${a.geography.county_name || ""} · ${a.alert_id}</div>
            </div>`).join("");

        function show(i) {
            list.querySelectorAll(".alert-card").forEach(c => c.classList.toggle("selected", c.dataset.i === String(i)));
            const a = alerts[i];
            const ev = a.evidence || {};
            const evGrid = Object.entries(ev).filter(([k,v]) => typeof v !== "object" || v === null)
                .map(([k, v]) => `<div class="ev-item"><div class="l">${k.replace(/_/g, " ")}</div><div class="v">${escapeHtml(String(v))}</div></div>`).join("");
            detail.innerHTML = `
                <h3>${escapeHtml(a.title)}</h3>
                <p style="color:var(--ink-3); font-size:0.78rem; letter-spacing:0.08em; text-transform:uppercase; margin-top:6px;">
                  ${a.kind.replace(/_/g, " ")} · severity ${a.severity} · confidence ${a.confidence.toFixed(2)}
                </p>
                <div class="rationale">${escapeHtml(a.rationale)}</div>
                ${evGrid ? `<h4 style="margin-top:12px;">Evidence</h4><div class="ev-grid">${evGrid}</div>` : ""}
                ${(a.dp_noised_count !== null && a.dp_noised_count !== undefined) ? `
                <div class="dp-disclosure">
                    <strong>Differential privacy:</strong> aggregate count released at ε = 1.0 with the Laplace mechanism.
                    True count: <strong>${ev.month_count !== undefined ? ev.month_count : (ev.recent_4wk_total !== undefined ? ev.recent_4wk_total : "—")}</strong>
                    · DP-released count: <strong>${a.dp_noised_count}</strong>.
                    For surveillance dashboards visible beyond the originating clinic, only the noised value is exposed.
                </div>` : ""}
                ${a.kind === "VECTOR_ANOMALY" ? `<svg id="surv-chart"></svg>` : ""}
                ${a.kind === "SENTINEL_CASE" ? `<svg id="surv-chart"></svg>` : ""}
            `;
            // Render chart for time-series alerts.
            if (a.kind === "VECTOR_ANOMALY") drawVectorChart(a);
            if (a.kind === "SENTINEL_CASE") drawIncidenceChart(a);
        }
        list.addEventListener("click", e => {
            const card = e.target.closest(".alert-card");
            if (card) show(parseInt(card.dataset.i, 10));
        });
        if (alerts.length) show(0);
    };

    function drawVectorChart(a) {
        const fips = a.geography.county_fips;
        const series = DATA.surveillance.vector_surveillance
            .filter(r => r.county_fips === fips)
            .sort((p, q) => p.year - q.year || p.week - q.week);
        if (series.length < 2) return;
        const svg = d3.select("#surv-chart");
        const W = svg.node().getBoundingClientRect().width;
        const H = 240, M = { top: 18, right: 18, bottom: 28, left: 40 };
        svg.attr("viewBox", `0 0 ${W} ${H}`);
        const x = d3.scaleLinear().domain([0, series.length - 1]).range([M.left, W - M.right]);
        const y = d3.scaleLinear().domain([0, d3.max(series, d => d.tick_count) * 1.1]).range([H - M.bottom, M.top]);
        const line = d3.line().x((_, i) => x(i)).y(d => y(d.tick_count)).curve(d3.curveMonotoneX);
        const area = d3.area().x((_, i) => x(i)).y0(H - M.bottom).y1(d => y(d.tick_count)).curve(d3.curveMonotoneX);

        const baseline = a.evidence.baseline_mean;
        svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.bottom})`).call(d3.axisBottom(x).ticks(8).tickFormat(i => series[Math.round(i)] ? `W${series[Math.round(i)].week}` : ""));
        svg.append("g").attr("class", "axis").attr("transform", `translate(${M.left},0)`).call(d3.axisLeft(y).ticks(5));
        svg.append("path").attr("class", "data-area").datum(series).attr("d", area);
        svg.append("path").attr("class", "data-line").datum(series).attr("d", line);
        svg.append("line").attr("class", "baseline-line")
           .attr("x1", M.left).attr("x2", W - M.right)
           .attr("y1", y(baseline)).attr("y2", y(baseline));
        svg.append("text").attr("x", W - M.right - 6).attr("y", y(baseline) - 4)
           .attr("text-anchor", "end").attr("font-size", "10px").attr("fill", "var(--ink-3)")
           .text(`baseline ≈ ${baseline.toFixed(0)}`);
        // Anomaly window markers (last 4 points).
        svg.append("g").selectAll("circle")
            .data(series.slice(-4)).join("circle")
            .attr("class", "anomaly-marker")
            .attr("cx", (_, i) => x(series.length - 4 + i))
            .attr("cy", d => y(d.tick_count))
            .attr("r", 4);
    }

    function drawIncidenceChart(a) {
        const fips = a.geography.county_fips;
        const snomed = a.disease_snomed;
        const series = DATA.surveillance.adhs_disease_counts
            .filter(r => r.county_fips === fips && r.condition_snomed === snomed)
            .sort((p, q) => p.year - q.year || p.month - q.month);
        if (series.length < 2) return;
        const svg = d3.select("#surv-chart");
        const W = svg.node().getBoundingClientRect().width;
        const H = 240, M = { top: 18, right: 18, bottom: 28, left: 40 };
        svg.attr("viewBox", `0 0 ${W} ${H}`);
        const x = d3.scaleLinear().domain([0, series.length - 1]).range([M.left, W - M.right]);
        const y = d3.scaleLinear().domain([0, d3.max(series, d => d.case_count) * 1.15 + 1]).range([H - M.bottom, M.top]);
        const line = d3.line().x((_, i) => x(i)).y(d => y(d.case_count)).curve(d3.curveMonotoneX);
        const area = d3.area().x((_, i) => x(i)).y0(H - M.bottom).y1(d => y(d.case_count)).curve(d3.curveMonotoneX);
        const baseline = a.evidence.baseline_mean;

        svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.bottom})`).call(d3.axisBottom(x).ticks(8).tickFormat(i => series[Math.round(i)] ? `${series[Math.round(i)].year}-${String(series[Math.round(i)].month).padStart(2,"0")}` : ""));
        svg.append("g").attr("class", "axis").attr("transform", `translate(${M.left},0)`).call(d3.axisLeft(y).ticks(5));
        svg.append("path").attr("class", "data-area").datum(series).attr("d", area);
        svg.append("path").attr("class", "data-line").datum(series).attr("d", line);
        svg.append("line").attr("class", "baseline-line")
            .attr("x1", M.left).attr("x2", W - M.right)
            .attr("y1", y(baseline)).attr("y2", y(baseline));
        svg.append("text").attr("x", W - M.right - 6).attr("y", y(baseline) - 4)
            .attr("text-anchor", "end").attr("font-size", "10px").attr("fill", "var(--ink-3)")
            .text(`baseline ≈ ${baseline.toFixed(1)}`);
        const last = series[series.length - 1];
        svg.append("circle")
            .attr("class", "anomaly-marker")
            .attr("cx", x(series.length - 1))
            .attr("cy", y(last.case_count))
            .attr("r", 5);
    }

    // ======================================================================
    // VIEW 5 — Architecture
    // ======================================================================
    VIEW_INIT.architecture = function () {
        const host = document.getElementById("arch-svg-host");
        host.innerHTML = `
        <svg viewBox="0 0 980 460" xmlns="http://www.w3.org/2000/svg" style="font-family: var(--font-body); font-size: 12px;">
          <defs>
            <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="strokeWidth" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#3A3F4B" />
            </marker>
            <filter id="neo">
              <feGaussianBlur stdDeviation="2.5" />
            </filter>
          </defs>

          <!-- Lane labels -->
          <text x="20" y="35" font-family="var(--font-display)" font-size="12" font-style="italic" fill="#6E6960">INPUT</text>
          <text x="270" y="35" font-family="var(--font-display)" font-size="12" font-style="italic" fill="#6E6960">MACHINE AUTHORSHIP</text>
          <text x="540" y="35" font-family="var(--font-display)" font-size="12" font-style="italic" fill="#6E6960">KNOWLEDGE</text>
          <text x="780" y="35" font-family="var(--font-display)" font-size="12" font-style="italic" fill="#6E6960">PUBLIC HEALTH</text>

          <!-- Input column -->
          <rect x="20"  y="65" width="200" height="64"  rx="14" fill="#FAF5E9" stroke="#D4CCB8" stroke-width="1"/>
          <text x="120" y="92"  text-anchor="middle" font-weight="600" fill="#0C234B">Clinician dictation</text>
          <text x="120" y="112" text-anchor="middle" font-size="11" fill="#6E6960">audio · text · structured</text>

          <rect x="20"  y="155" width="200" height="64" rx="14" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="120" y="182" text-anchor="middle" font-weight="600" fill="#0C234B">Veterinary record</text>
          <text x="120" y="202" text-anchor="middle" font-size="11" fill="#6E6960">VetCompass · in-clinic</text>

          <rect x="20"  y="245" width="200" height="64" rx="14" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="120" y="272" text-anchor="middle" font-weight="600" fill="#0C234B">Environmental data</text>
          <text x="120" y="292" text-anchor="middle" font-size="11" fill="#6E6960">EPA EQI · ADHS · vectors</text>

          <!-- Authorship column -->
          <rect x="260" y="65" width="220" height="244" rx="18" fill="#F4EEE0" stroke="#AB0520" stroke-width="1.4" stroke-dasharray="4 3"/>
          <text x="370" y="88" text-anchor="middle" font-weight="600" fill="#AB0520">Machine Authorship Engine</text>

          <rect x="278" y="105" width="184" height="44" rx="10" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="370" y="132" text-anchor="middle" font-size="12">Phase segmentation</text>

          <rect x="278" y="158" width="184" height="44" rx="10" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="370" y="180" text-anchor="middle" font-size="12">Entity extraction</text>
          <text x="370" y="194" text-anchor="middle" font-size="10" fill="#6E6960">+ negation / hedge</text>

          <rect x="278" y="211" width="184" height="44" rx="10" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="370" y="233" text-anchor="middle" font-size="12">FHIR R4 builder</text>
          <text x="370" y="247" text-anchor="middle" font-size="10" fill="#6E6960">+ provenance · confidence</text>

          <text x="370" y="290" text-anchor="middle" font-size="10" font-style="italic" fill="#6E6960">production: BioClinicalBERT</text>

          <!-- Knowledge column -->
          <rect x="520" y="65" width="220" height="120" rx="14" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="630" y="92" text-anchor="middle" font-weight="600" fill="#0C234B">FHIR data store</text>
          <text x="630" y="112" text-anchor="middle" font-size="11" fill="#6E6960">Patient · Animal · Condition</text>
          <text x="630" y="128" text-anchor="middle" font-size="11" fill="#6E6960">Observation · Provenance</text>
          <text x="630" y="160" text-anchor="middle" font-size="10" font-style="italic" fill="#6E6960">SMART-on-FHIR API</text>

          <rect x="520" y="200" width="220" height="109" rx="14" fill="#FAF5E9" stroke="#3F6B47" stroke-width="1.4"/>
          <text x="630" y="226" text-anchor="middle" font-weight="600" fill="#3F6B47">One Health knowledge graph</text>
          <text x="630" y="246" text-anchor="middle" font-size="11" fill="#6E6960">Person ↔ Animal ↔ Disease</text>
          <text x="630" y="262" text-anchor="middle" font-size="11" fill="#6E6960">cross-species via SNOMED root</text>
          <text x="630" y="290" text-anchor="middle" font-size="10" font-style="italic" fill="#6E6960">production: Neo4j + GNN</text>

          <!-- Public health column -->
          <rect x="780" y="65"  width="180" height="74" rx="14" fill="#FAF5E9" stroke="#AB0520"/>
          <text x="870" y="92"  text-anchor="middle" font-weight="600" fill="#AB0520">Sentinel detectors</text>
          <text x="870" y="110" text-anchor="middle" font-size="10" fill="#6E6960">cross-species · vector</text>
          <text x="870" y="124" text-anchor="middle" font-size="10" fill="#6E6960">env-amplified · spike</text>

          <rect x="780" y="160" width="180" height="64" rx="14" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="870" y="186" text-anchor="middle" font-weight="600" fill="#0C234B">Differential privacy</text>
          <text x="870" y="206" text-anchor="middle" font-size="10" fill="#6E6960">Laplace mechanism · ε=1.0</text>

          <rect x="780" y="245" width="180" height="64" rx="14" fill="#FAF5E9" stroke="#D4CCB8"/>
          <text x="870" y="271" text-anchor="middle" font-weight="600" fill="#0C234B">Clinician + ADHS dashboards</text>
          <text x="870" y="290" text-anchor="middle" font-size="10" fill="#6E6960">map · graph · alerts</text>

          <!-- Arrows -->
          <line x1="222" y1="97"  x2="278" y2="127" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="222" y1="187" x2="278" y2="180" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="222" y1="277" x2="538" y2="247" stroke="#3A3F4B" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#ar)"/>

          <line x1="464" y1="190" x2="520" y2="125" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="630" y1="186" x2="630" y2="200" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>

          <line x1="742" y1="125" x2="780" y2="100" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="742" y1="255" x2="780" y2="190" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>

          <line x1="870" y1="139" x2="870" y2="158" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>
          <line x1="870" y1="225" x2="870" y2="244" stroke="#3A3F4B" stroke-width="1.5" marker-end="url(#ar)"/>

          <!-- Caption -->
          <text x="490" y="445" text-anchor="middle" font-size="11" font-style="italic" fill="#6E6960">
            Every machine-authored resource carries a source-text span, source-phase, confidence score, and engine version
          </text>
        </svg>`;
    };

    // ======================================================================
    // VIEW — Patient Intake (Phase 8): Registration + Triage Track Board
    // ======================================================================
    VIEW_INIT.register = function () {
        const host = document.getElementById("register-host");
        if (host && window.OH_INTAKE) window.OH_INTAKE.renderRegistration(host);
    };
    VIEW_RERENDER.trackboard = function () {
        const host = document.getElementById("trackboard-host");
        if (host && window.OH_INTAKE) window.OH_INTAKE.renderTrackBoard(host);
    };
    VIEW_RERENDER.envsurv = function () {
        const host = document.getElementById("envsurv-host");
        if (host && window.OH_ENVSURV) window.OH_ENVSURV.renderEnvSurveillance(host);
    };

    // ======================================================================
    // VIEW 2 — Provider Workspace (clinician + veterinarian view)
    // ======================================================================
    VIEW_INIT.workspace = function () {
        // Phase 4 — defense in depth: PH users have no patient panel
        const session = window.OH_AUTH ? window.OH_AUTH.getSession() : null;
        if (session && session.role === "public_health") {
            const v = document.getElementById("view-workspace");
            if (v) {
                v.innerHTML = `
                    <div class="panel">
                        <div class="panel-head">
                            <h2><small>Access policy</small>Provider Workspace not available for Public Health users</h2>
                        </div>
                        <div style="padding: 24px; font-size: 0.9rem; color: var(--ink-2); line-height: 1.6;">
                            Public-health users see aggregate, household-level surveillance signals only.
                            Individual primary records are not accessible from this role, even for accountable households.
                            Please use the One Health Map, Sentinel Alerts, or Risk Model views instead.
                        </div>
                    </div>`;
            }
            return;
        }
        const allHouseholds = DATA.households.households;
        const allEncounters = (DATA.encounters && DATA.encounters.encounters) || [];
        const allAlerts = DATA.alerts.alerts || [];

        // Phase 4 — restrict patient list to the logged-in clinician's panel
        const panelIds = window.OH_AUTH ? window.OH_AUTH.getPanelPatientIds() : null;
        const authKind = window.OH_AUTH ? window.OH_AUTH.getAuthorizedPatientKind() : null;
        const panelSet = panelIds ? new Set(panelIds) : null;

        // Build flat patient list — humans + animals
        const patients = [];
        for (const hh of allHouseholds) {
            for (const p of hh.humans) {
                // Phase 4 — physicians: only humans on their panel
                if (session && session.role === "veterinarian") continue;
                if (session && session.role === "physician" && panelSet && !panelSet.has(p.id)) continue;
                patients.push({
                    kind: "Person",
                    id: p.id,
                    label: p.name[0].given[0] + " " + p.name[0].family,
                    role: "clinician",
                    ref: "Patient/" + p.id,
                    household: hh,
                    raw: p,
                    icon: "👤",
                    sub: p.gender + " · b. " + p.birthDate.substring(0, 4) + " · " + hh.county.name
                });
            }
            for (const a of hh.animals) {
                // Phase 4 — vets: only animals on their panel
                if (session && session.role === "physician") continue;
                if (session && session.role === "veterinarian" && panelSet && !panelSet.has(a.id)) continue;
                patients.push({
                    kind: "Animal",
                    id: a.id,
                    label: a.name + " (" + a.species.code + ")",
                    role: "vet",
                    ref: "AnimalPatient/" + a.id,
                    household: hh,
                    raw: a,
                    icon: ({"dog":"🐕","cat":"🐈","horse":"🐎","bird":"🦜","goat":"🐐","rabbit":"🐇","reptile":"🦎"}[a.species.code] || "🐾"),
                    sub: a.breed + " · " + (a.sex || "?") + " · " + hh.county.name
                });
            }
        }

        // Patients with alerts get a dot
        const alertedHouseholds = new Set(allAlerts.map(a => a.household_id).filter(Boolean));

        const listEl = document.getElementById("ws-patient-list");
        const detailEl = document.getElementById("ws-detail");
        const ctxEl = document.getElementById("ws-context");
        const searchEl = document.getElementById("ws-search");
        const roleEl = document.getElementById("ws-role");

        let selectedPatient = null;

        function renderList() {
            const q = (searchEl.value || "").trim().toLowerCase();
            const role = roleEl.value;
            // Sort: alerted households first, then by name
            const filtered = patients.filter(p => {
                if (role === "clinician" && p.kind !== "Person") return false;
                if (role === "vet" && p.kind !== "Animal") return false;
                if (!q) return true;
                return (p.label.toLowerCase().includes(q) ||
                        p.household.name.toLowerCase().includes(q) ||
                        p.household.county.name.toLowerCase().includes(q) ||
                        (p.household.conditions || []).some(c => c.code.text.toLowerCase().includes(q)));
            }).sort((a, b) => {
                const aa = alertedHouseholds.has(a.household.household_id) ? 0 : 1;
                const bb = alertedHouseholds.has(b.household.household_id) ? 0 : 1;
                if (aa !== bb) return aa - bb;
                return a.label.localeCompare(b.label);
            });

            // Limit to first 80 visible to keep DOM responsive
            const visible = filtered.slice(0, 80);
            const truncated = filtered.length > visible.length;

            listEl.innerHTML = visible.map(p => {
                const hasAlert = alertedHouseholds.has(p.household.household_id);
                const sel = (selectedPatient && selectedPatient.id === p.id) ? "selected" : "";
                return `<div class="patient-row ${sel}" data-pid="${p.id}">
                    <span class="icon">${p.icon}</span>
                    <div class="info">
                        <div class="name">${escapeHtml(p.label)}</div>
                        <div class="meta">${escapeHtml(p.sub)}</div>
                    </div>
                    ${hasAlert ? '<span class="alert-dot" title="Active One Health alert"></span>' : ""}
                </div>`;
            }).join("") +
            (truncated ? `<div style="padding:10px; font-size:0.78rem; color:var(--ink-3); text-align:center;">+ ${filtered.length - visible.length} more — refine search</div>` : "");

            listEl.querySelectorAll(".patient-row").forEach(row => {
                row.addEventListener("click", () => {
                    const pid = row.dataset.pid;
                    selectedPatient = patients.find(p => p.id === pid);
                    try { renderDetail(); } catch (e) { console.error("renderDetail:", e); }
                    try { renderContext(); } catch (e) { console.error("renderContext:", e); }
                    renderList();  // update selection styling
                    if (window.OH_AUTH && selectedPatient) {
                        window.OH_AUTH.auditLog("patient_select", selectedPatient.id);
                    }
                });
            });
        }

        function renderDetail() {
            if (!selectedPatient) {
                detailEl.innerHTML = '<div class="empty-state">Select a patient from the list to view their chart.</div>';
                return;
            }
            const p = selectedPatient;
            const enc = allEncounters.filter(e => e.subject.reference === p.ref).sort((a, b) => b.period.start.localeCompare(a.period.start));
            const isAnimal = p.kind === "Animal";
            const chronic = isAnimal ? [] : (p.raw.chronic_conditions || []);
            const activeConditions = (p.household.conditions || []).filter(c => c.subject.reference === p.ref);
            const meds = new Set();
            for (const e of enc) {
                for (const m of (e.medications_recorded || [])) meds.add(m);
            }

            // Demographics
            let dem = "";
            if (isAnimal) {
                const age = (new Date()).getFullYear() - parseInt(p.raw.birthDate.substring(0,4), 10);
                dem = p.raw.species.display + " · " + p.raw.breed + " · " + (p.raw.sex || "?") + " · " + age + "y old · " + p.household.county.seat + ", AZ";
            } else {
                const age = (new Date()).getFullYear() - parseInt(p.raw.birthDate.substring(0,4), 10);
                dem = age + "y · " + p.raw.gender + " · " + p.household.county.seat + ", AZ";
            }

            const chronicHtml = chronic.length
                ? '<div class="pt-chronic-list">' + chronic.map(c => `<span class="pt-chip condition">${escapeHtml(c)}</span>`).join("") + '</div>'
                : '<div style="font-size:0.85rem; color:var(--ink-3);">None on record.</div>';

            const activeHtml = activeConditions.length
                ? '<div class="pt-condition-list">' + activeConditions.map(c => {
                    const onset = (c.onsetDateTime || c.recordedDate || "").substring(0, 10);
                    const conf = (c.extension || []).find(x => x.url.endsWith("confidence"));
                    const oh = (c.extension || []).find(x => x.url.endsWith("one-health-relevant"));
                    // Phase 7 — reportable badge + Report-this-case button
                    let reportBtn = '';
                    if (window.OH_REPORT) {
                        const r = window.OH_REPORT.findReportable(c);
                        if (r) {
                            const isAnimalC = (c.subject?.reference || "").startsWith("AnimalPatient/");
                            const meta = isAnimalC ? (r.animal_reporting || {}) : (r.human_reporting || {});
                            if (meta.is_reportable) {
                                const cid = c.id || ("cond-" + Math.random().toString(36).slice(2, 8));
                                if (!c.id) c.id = cid;
                                const state = window.OH_REPORT.getReportState(cid);
                                if (state === "submitted") {
                                    reportBtn = `<button class="oh-report-button oh-report-button-reported" disabled>✓ Reported</button>`;
                                } else {
                                    reportBtn = `<button class="oh-report-button" data-reportable-cond="${escapeHtml(cid)}"><span class="oh-icon-bolt">⚡</span> Report this case</button>`;
                                }
                            }
                        }
                    }
                    return `<span class="pt-chip condition" title="onset ${onset}${conf ? ' · conf '+conf.valueDecimal.toFixed(2) : ''}">${escapeHtml(c.code.text)}${oh && oh.valueBoolean ? ' 🌍' : ''} <small style="color:var(--ink-3);font-family:var(--font-mono);">${onset}</small></span>${reportBtn}`;
                }).join("") + '</div>'
                : '<div style="font-size:0.85rem; color:var(--ink-3);">No active acute or zoonotic conditions on record.</div>';

            const medsHtml = meds.size
                ? '<div class="pt-medication-list">' + Array.from(meds).map(m => `<span class="pt-chip medication">${escapeHtml(m)}</span>`).join("") + '</div>'
                : '<div style="font-size:0.85rem; color:var(--ink-3);">No active medications on record.</div>';

            const encHtml = enc.length
                ? '<div class="encounter-timeline">' + enc.slice(0, 12).map(e => {
                    const v = e.vitals || {};
                    const vitParts = [];
                    if (v.bp)    vitParts.push("BP " + v.bp);
                    if (v.hr)    vitParts.push("HR " + v.hr);
                    if (v.rr)    vitParts.push("RR " + v.rr);
                    if (v.temp_f) vitParts.push("T " + v.temp_f + "°F");
                    if (v.spo2)  vitParts.push("SpO2 " + v.spo2 + "%");
                    if (v.glucose_mg_dl) vitParts.push("Gluc " + v.glucose_mg_dl);
                    if (v.weight_kg) vitParts.push("Wt " + v.weight_kg + "kg");
                    if (v.weight_g) vitParts.push("Wt " + v.weight_g + "g");
                    return `<div class="encounter" data-provider="${escapeHtml(e.provider)}">
                        <div class="row">
                            <span class="date">${e.period.start.substring(0,10)}</span>
                            <span class="provider">${escapeHtml(e.provider)}</span>
                        </div>
                        <div class="cc">${escapeHtml(e.chief_complaint)}</div>
                        <div class="narrative">${escapeHtml(e.narrative)}</div>
                        ${vitParts.length ? '<div class="vitals">' + vitParts.map(escapeHtml).join(" · ") + '</div>' : ''}
                    </div>`;
                }).join("") + '</div>' +
                (enc.length > 12 ? `<div style="font-size:0.78rem; color:var(--ink-3); padding:8px 0;">${enc.length - 12} earlier encounter(s) not shown.</div>` : '')
                : '<div style="font-size:0.85rem; color:var(--ink-3);">No prior encounters in this record.</div>';

            detailEl.innerHTML = `
                <div class="pt-header">
                    <div>
                        <div class="pt-name">${escapeHtml(p.label)}</div>
                        <div class="pt-demographics">${escapeHtml(dem)}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.74rem; color:var(--ink-3); text-transform:uppercase; letter-spacing:0.12em;">Household</div>
                        <div style="font-family:var(--font-mono); font-size:0.86rem; color:var(--ink-1);">${escapeHtml(p.household.name)}</div>
                        <div style="font-family:var(--font-mono); font-size:0.74rem; color:var(--ink-3);">${escapeHtml(p.household.household_id)}</div>
                    </div>
                </div>

                <div class="pt-section">
                    <h4>Active acute / zoonotic conditions</h4>
                    ${activeHtml}
                </div>

                <div class="pt-section">
                    <h4>${isAnimal ? 'Persistent conditions' : 'Chronic conditions'}</h4>
                    ${chronicHtml}
                </div>

                <div class="pt-section">
                    <h4>Active medications (from encounter history)</h4>
                    ${medsHtml}
                </div>

                ${(!isAnimal && enc.some(e => e.vitals && e.vitals.bp)) ? `
                <div class="pt-section">
                    <h4>Blood pressure trend (last ${Math.min(enc.length, 24)} encounters)</h4>
                    <svg id="vitals-trend"></svg>
                </div>` : ''}

                <div class="pt-section">
                    <h4>Encounter timeline (most recent first)</h4>
                    ${encHtml}
                </div>
            `;

            // Vitals trend chart
            if (!isAnimal && document.getElementById("vitals-trend")) {
                try { drawVitalsTrend(enc); } catch (e) { console.warn("drawVitalsTrend skipped:", e); }
            }

            // Phase 7 — wire "Report this case" buttons
            document.querySelectorAll('[data-reportable-cond]').forEach(btn => {
                btn.addEventListener('click', e => {
                    e.preventDefault();
                    e.stopPropagation();
                    const cid = btn.dataset.reportableCond;
                    const cond = (p.household.conditions || []).find(c => c.id === cid);
                    if (!cond || !window.OH_REPORT) return;
                    const isAnimalC = (cond.subject?.reference || "").startsWith("AnimalPatient/");
                    const session = window.OH_AUTH ? window.OH_AUTH.getSession() : {};
                    const patientLite = isAnimalC ? {
                        id: p.raw.id, first_name: p.raw.name, last_name: "",
                        dob: p.raw.dob || "", gender: p.raw.sex || "U",
                    } : {
                        id: p.raw.id,
                        first_name: ((p.raw.name && p.raw.name[0] && p.raw.name[0].given) || [""])[0],
                        last_name:  ((p.raw.name && p.raw.name[0] && p.raw.name[0].family) || ""),
                        dob: p.raw.birthDate || "",
                        gender: p.raw.gender || "U",
                    };
                    window.OH_REPORT.openReportPanel(cond, {
                        hh: p.household,
                        isAnimal: isAnimalC,
                        patient: patientLite,
                        species: isAnimalC ? ((p.raw.species || {}).display || "") : "",
                        household_id: p.household.household_id,
                        provider: { name: session.display_name || session.user_id || "Unknown clinician" },
                        facility: { id: session.facility || "TMC", name: session.facility || "Tucson Medical Center" },
                    });
                });
            });
        }

        function drawVitalsTrend(encounters) {
            const svg = d3.select("#vitals-trend");
            svg.selectAll("*").remove();
            const data = encounters.filter(e => e.vitals && e.vitals.bp).slice(0, 24).reverse().map(e => {
                const [sys, dia] = e.vitals.bp.split("/").map(s => parseInt(s, 10));
                return { date: new Date(e.period.start), sys, dia };
            });
            if (!data.length) return;
            const W = svg.node().getBoundingClientRect().width || 600;
            const H = 200;
            const margin = { top: 12, right: 12, bottom: 28, left: 38 };
            svg.attr("width", W).attr("height", H);
            const xs = d3.scaleTime().domain(d3.extent(data, d => d.date)).range([margin.left, W - margin.right]);
            const ys = d3.scaleLinear().domain([60, 200]).range([H - margin.bottom, margin.top]);
            const lineSys = d3.line().x(d => xs(d.date)).y(d => ys(d.sys));
            const lineDia = d3.line().x(d => xs(d.date)).y(d => ys(d.dia));
            const css = getComputedStyle(document.documentElement);
            const cardinal = css.getPropertyValue("--ua-cardinal").trim() || "#AB0520";
            const navy = css.getPropertyValue("--ua-navy").trim() || "#0C234B";
            const ink4 = css.getPropertyValue("--ink-4").trim() || "#D4CFC2";
            // Normal-range band 90-140 / 60-90
            svg.append("rect").attr("x", margin.left).attr("y", ys(140))
               .attr("width", W - margin.left - margin.right).attr("height", ys(90) - ys(140))
               .attr("fill", "rgba(63,107,71,0.07)");
            svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - margin.bottom})`)
               .call(d3.axisBottom(xs).ticks(5).tickFormat(d3.timeFormat("%b '%y")));
            svg.append("g").attr("class", "axis").attr("transform", `translate(${margin.left},0)`)
               .call(d3.axisLeft(ys).ticks(5));
            svg.append("path").datum(data).attr("d", lineSys).attr("fill", "none").attr("stroke", cardinal).attr("stroke-width", 1.6);
            svg.append("path").datum(data).attr("d", lineDia).attr("fill", "none").attr("stroke", navy).attr("stroke-width", 1.6).attr("stroke-dasharray", "3,2");
            svg.selectAll(".dot-sys").data(data).enter().append("circle").attr("class", "dot-sys")
               .attr("cx", d => xs(d.date)).attr("cy", d => ys(d.sys)).attr("r", 2.6).attr("fill", cardinal);
            svg.selectAll(".dot-dia").data(data).enter().append("circle").attr("class", "dot-dia")
               .attr("cx", d => xs(d.date)).attr("cy", d => ys(d.dia)).attr("r", 2.4).attr("fill", navy);
        }

        function renderContext() {
            if (!selectedPatient) { ctxEl.innerHTML = ""; return; }
            const p = selectedPatient;
            const hh = p.household;
            const sessionRole = (window.OH_AUTH && window.OH_AUTH.getSession() && window.OH_AUTH.getSession().role) || null;

            // Other household members — Phase 4 — redact cross-species
            const others = [];
            // Phase 4.1 — for cross-clinician privacy, household members on a
            // *different* clinician's panel are not shown by name; we surface
            // a count of "household members on other panels" so the clinician
            // knows there are people in the household but cannot identify them.
            const panelIds = window.OH_AUTH ? window.OH_AUTH.getPanelPatientIds() : null;
            const panelSet = panelIds ? new Set(panelIds) : null;
            let othersOffPanel = 0;
            const hasOtherSpecies = (sessionRole === "physician" && (hh.animals || []).length > 0) ||
                                     (sessionRole === "veterinarian" && (hh.humans || []).length > 0);
            for (const h of hh.humans) {
                if ("Patient/" + h.id === p.ref) continue;
                if (sessionRole === "veterinarian") continue; // vets don't see humans
                // Phase 4.1 — only show humans who are on THIS physician's panel
                if (sessionRole === "physician" && panelSet && !panelSet.has(h.id)) {
                    othersOffPanel++;
                    continue;
                }
                others.push({
                    icon: "👤",
                    label: h.name[0].given[0] + " " + h.name[0].family,
                    flagged: false
                });
            }
            for (const a of hh.animals) {
                if ("AnimalPatient/" + a.id === p.ref) continue;
                if (sessionRole === "physician") continue; // physicians don't see animals
                // Phase 4.1 — only show animals on THIS vet's panel
                if (sessionRole === "veterinarian" && panelSet && !panelSet.has(a.id)) {
                    othersOffPanel++;
                    continue;
                }
                others.push({
                    icon: ({"dog":"🐕","cat":"🐈","horse":"🐎","bird":"🦜","goat":"🐐","rabbit":"🐇","reptile":"🦎"}[a.species.code] || "🐾"),
                    label: a.name + " (" + a.species.code + ")",
                    flagged: false
                });
            }
            // Mark anyone with active condition as flagged
            for (const c of (hh.conditions || [])) {
                others.forEach(o => {
                    if (c.subject.reference.endsWith(o.label.split(" ")[0]) || c.subject.reference.includes(o.label.split(" ")[0])) o.flagged = true;
                });
            }

            // Relevant alerts for this household — Phase 4 — redact cross-species details
            // Alerts that name animals/humans of the protected species are summarized
            // via the model pointer rather than shown verbatim.
            const isCrossSpeciesAlert = (a) => {
                const k = ((a.kind || a.alert_type || a.type || "") + " " + (a.title || "")).toUpperCase();
                return k.indexOf("CROSS_SPECIES") >= 0 || k.indexOf("CROSS-SPECIES") >= 0 ||
                       k.indexOf("CLUSTER") >= 0 || k.indexOf("PROPHYLACTIC_HOUSEHOLD") >= 0;
            };
            const allHHAlerts = allAlerts.filter(a => a.household_id === hh.household_id);
            const visibleHHAlerts = allHHAlerts.filter(a => !isCrossSpeciesAlert(a) || sessionRole === "public_health");
            // Plus county-level (vector / RMSF / WNV anomalies in this county)
            const countyAlerts = allAlerts.filter(a =>
                !a.household_id &&
                a.evidence && (a.evidence.county_fips === hh.county.fips || (a.title || "").toLowerCase().includes(hh.county.name.toLowerCase()))
            );

            // ADHS county trends
            const surv = (DATA.surveillance.surveillance && DATA.surveillance.surveillance.adhs_reportable_counts) || [];
            const countyRows = surv.filter(r => r.county_fips === hh.county.fips);
            const lastWeek = countyRows.length ? countyRows[countyRows.length - 1].iso_week : "";
            const counts = {};
            for (const r of countyRows.slice(-8)) {
                counts[r.disease] = (counts[r.disease] || 0) + r.count;
            }

            const alertHtml = (visibleHHAlerts.concat(countyAlerts).slice(0, 6)).map(a => {
                const cls = a.disposition === "action" ? "action" : "watch";
                return `<div class="ctx-alert ${cls}">
                    <div class="title">${escapeHtml(a.title)}</div>
                    <div class="meta">${escapeHtml(a.kind)} · conf ${a.confidence.toFixed(2)} · ${escapeHtml(a.disposition)}</div>
                </div>`;
            }).join("") || '<div style="font-size:0.82rem; color:var(--ink-3);">No active alerts for this household.</div>';

            // Phase 6 — consent gating: if the household declined cross-species
            // linkage, replace the model pointer with a consent-declined notice.
            // The household graph itself remains intact for single-species clinical care.
            const consentRecord = ((DATA.consents && DATA.consents.consents) || [])
                .find(c => c.patient && c.patient.reference === ("Group/" + hh.household_id));
            const consentDeclined = consentRecord && consentRecord.status === "inactive";

            // Phase 4 — model pointer panel (replaces redacted cross-species detail)
            // Phase 6 — gated by consent
            let modelPointerHtml = "";
            if (consentDeclined && hasOtherSpecies) {
                modelPointerHtml = `
                <div class="cross-species-pointer consent-declined">
                    <div class="cs-header">
                        <span class="cs-title">CONSENT · CROSS-SPECIES LINKAGE</span>
                    </div>
                    <div class="cs-tier consent-deny">
                        <strong>Consent declined.</strong> This household has declined the
                        One Health cross-species linkage option at intake. The system
                        respects this decision: cross-species cluster signals are
                        suppressed, and the household graph treats human and animal
                        records as separate compartments.
                    </div>
                    <div class="cs-prov" style="margin-top:10px;">
                        Provenance: <code>Consent</code> resource <code>${escapeHtml(consentRecord.id || "")}</code>,
                        status <code>${escapeHtml(consentRecord.status)}</code>, decision date
                        ${escapeHtml((consentRecord.dateTime || "").slice(0, 10))}.
                        Single-species clinical care continues unaffected.
                        Aggregate public-health surveillance (county and ZIP level) continues unaffected.
                    </div>
                </div>`;
            } else if (window.OH_AUTH && hasOtherSpecies) {
                modelPointerHtml = window.OH_AUTH.renderCrossSpeciesPointer(hh.household_id);
            }

            // Phase 6 — fire a federation fan-out for this household so the wire
            // log fills as the user navigates. Fire-and-forget; we do not block
            // the render on the result.
            if (window.OH_FED && hh.household_id) {
                try { window.OH_FED.fhirFetchHousehold(hh.household_id); }
                catch (e) { /* ignore */ }
            }

            const countyHtml = `
                <div class="ctx-county-card">
                    <div style="font-weight:600; color:var(--ink-1); margin-bottom:8px;">${escapeHtml(hh.county.name)} Co.</div>
                    <div class="stat"><span>EPA EQI</span><span class="v">${hh.county.epa_eqi.toFixed(2)}</span></div>
                    <div class="stat"><span>Cocci endemicity</span><span class="v">${escapeHtml(hh.county.cocci_endemic)}</span></div>
                    ${Object.keys(counts).length ? `<hr style="border:none; border-top:1px dashed var(--ink-4); margin: 8px 0;">
                        <div style="font-size:0.74rem; color:var(--ink-3); text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;">Last 8 weeks (ADHS)</div>
                        ${Object.entries(counts).slice(0, 5).map(([d, n]) => `<div class="stat"><span>${escapeHtml(d)}</span><span class="v">${n}</span></div>`).join("")}` : ""}
                </div>`;

            // Build household-member section label depending on role
            const householdLabel = sessionRole === "physician"   ? `Household members on your panel (${others.length})` :
                                    sessionRole === "veterinarian" ? `Household animals on your panel (${others.length})` :
                                    `Household members (${others.length})`;
            const offPanelNote = othersOffPanel > 0
                ? `<div class="off-panel-household-note">${othersOffPanel} additional household member${othersOffPanel === 1 ? "" : "s"} on other clinicians' panels — names withheld pending consent.</div>`
                : "";

            ctxEl.innerHTML = `
                ${modelPointerHtml}
                <div id="cds-panel-host"></div>
                <div class="ctx-section">
                    <h4>One Health alerts</h4>
                    ${alertHtml}
                </div>
                <div class="ctx-section">
                    <h4>${householdLabel}</h4>
                    ${others.length ? others.slice(0, 12).map(o =>
                        `<div class="ctx-household-member">
                            <span class="icon">${o.icon}</span>
                            <span class="label">${escapeHtml(o.label)}</span>
                            ${o.flagged ? '<span class="badge">case</span>' : ''}
                        </div>`).join("") : '<div style="font-size:0.82rem; color:var(--ink-3);">No other members visible to your role.</div>'}
                    ${offPanelNote}
                </div>
                <div class="ctx-section">
                    <h4>County context</h4>
                    ${countyHtml}
                </div>
            `;

            // Phase 6 — render CDS panel if a relevant condition is in scope
            // and consent is granted (or the patient/household has no animals,
            // since single-species CDS doesn't require cross-species consent).
            if (window.OH_CDS && !consentDeclined) {
                const cdsHost = document.getElementById("cds-panel-host");
                const isAnimalLocal = (p.kind === "Animal") || (p.ref || "").startsWith("AnimalPatient/");
                if (cdsHost) {
                    const patientLite = {
                        ref: p.ref,
                        id: p.id || (p.ref || "").split("/").pop(),
                        first_name: isAnimalLocal ? (p.name || "") : ((p.given || []).join(" ") || (p.name || "").split(" ")[0] || ""),
                        last_name:  isAnimalLocal ? "" : ((p.family || "") || (p.name || "").split(" ").slice(1).join(" ")),
                        dob: p.dob || "",
                        gender: p.gender || "",
                    };
                    window.OH_CDS.renderCDSPanel({
                        hh, patient: patientLite, isAnimal: isAnimalLocal, sessionRole, container: cdsHost
                    });
                }
            }
        }

        searchEl.addEventListener("input", () => renderList());
        roleEl.addEventListener("change", () => renderList());

        // Phase 4 — when a physician or vet is logged in, force role and hide selector
        if (session && session.role === "physician") {
            roleEl.value = "clinician";
            roleEl.disabled = true;
            const wrap = roleEl.closest(".filter-pill") || roleEl.parentElement;
            if (wrap) wrap.style.display = "none";
        } else if (session && session.role === "veterinarian") {
            roleEl.value = "vet";
            roleEl.disabled = true;
            const wrap = roleEl.closest(".filter-pill") || roleEl.parentElement;
            if (wrap) wrap.style.display = "none";
        }

        // Pre-select first patient on the user's panel (or Maria for the un-logged demo)
        selectedPatient = patients.find(p => p.label.startsWith("Maria Hernandez")) || patients[0];
        renderList();
        try { renderDetail(); } catch (e) { console.error("renderDetail (init):", e); }
        try { renderContext(); } catch (e) { console.error("renderContext (init):", e); }
    };

    // ======================================================================
    // VIEW 6 — Evaluation
    // ======================================================================
    VIEW_INIT.evaluation = function () {
        // Look for evaluation.json in the data bundle, else use a fallback dataset
        const ev = (DATA.evaluation && DATA.evaluation.results) || (window.ONE_HR_EVAL || null);
        const summaryEl = document.getElementById("eval-summary");
        const tableEl = document.getElementById("eval-table");
        const runtimeEl = document.getElementById("eval-runtime");
        const confEl = document.getElementById("eval-confusion");

        if (!ev) {
            summaryEl.innerHTML = '<div class="empty-state">Evaluation data not yet loaded. Run <code>python -m src.evaluation.run_eval</code> first.</div>';
            return;
        }

        // Summary cards
        summaryEl.innerHTML = `
            <div class="card"><div class="v">${(ev.overall.precision * 100).toFixed(1)}%</div><div class="l">Precision</div></div>
            <div class="card"><div class="v">${(ev.overall.recall * 100).toFixed(1)}%</div><div class="l">Recall</div></div>
            <div class="card"><div class="v">${(ev.overall.f1 * 100).toFixed(1)}%</div><div class="l">F1 score</div></div>
            <div class="card"><div class="v">${ev.overall.n_gold}</div><div class="l">Gold-standard entities</div></div>
        `;

        // Per-kind table
        const rows = ev.per_kind.map(k => {
            const fScore = k.f1;
            const cls = fScore >= 0.85 ? "score-good" : fScore >= 0.70 ? "score-mid" : "score-low";
            return `<tr>
                <td>${escapeHtml(k.kind)}</td>
                <td>${k.support}</td>
                <td>${k.tp}</td>
                <td>${k.fp}</td>
                <td>${k.fn}</td>
                <td>${(k.precision * 100).toFixed(1)}%</td>
                <td>${(k.recall * 100).toFixed(1)}%</td>
                <td class="${cls}">${(k.f1 * 100).toFixed(1)}%</td>
            </tr>`;
        }).join("");
        tableEl.innerHTML = `<table class="eval-table">
            <thead><tr><th>Entity kind</th><th>Support</th><th>TP</th><th>FP</th><th>FN</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>`;

        // Calibration chart
        drawCalibration(ev.calibration);

        // Runtime
        runtimeEl.innerHTML = ev.runtime.map(r => `
            <div class="card">
                <div class="v">${r.median_ms.toFixed(1)}<small style="font-size:0.55em; color:var(--ink-3);"> ms</small></div>
                <div class="l">${escapeHtml(r.stage)}</div>
                <div class="d">p95 ${r.p95_ms.toFixed(1)}ms · n=${r.n}</div>
            </div>
        `).join("");

        // Confusion examples
        confEl.innerHTML = `
            <div class="card">
                <h4>Most common false positives</h4>
                <ul>${ev.errors.top_fp.map(e => `<li><code>${escapeHtml(e.text)}</code> tagged as <strong>${escapeHtml(e.kind)}</strong> (n=${e.n})</li>`).join("")}</ul>
            </div>
            <div class="card">
                <h4>Most common false negatives</h4>
                <ul>${ev.errors.top_fn.map(e => `<li>Missed <strong>${escapeHtml(e.kind)}</strong>: <code>${escapeHtml(e.text)}</code> (n=${e.n})</li>`).join("")}</ul>
            </div>
        `;
    };

    function drawCalibration(bins) {
        const svg = d3.select("#eval-calibration");
        svg.selectAll("*").remove();
        const W = svg.node().getBoundingClientRect().width || 600;
        const H = 240;
        const m = { top: 14, right: 14, bottom: 32, left: 40 };
        svg.attr("width", W).attr("height", H);
        const xs = d3.scaleLinear().domain([0, 1]).range([m.left, W - m.right]);
        const ys = d3.scaleLinear().domain([0, 1]).range([H - m.bottom, m.top]);

        // Diagonal
        svg.append("line").attr("class", "diag-line")
           .attr("x1", xs(0)).attr("y1", ys(0)).attr("x2", xs(1)).attr("y2", ys(1));

        // Axes
        svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.bottom})`)
           .call(d3.axisBottom(xs).ticks(5).tickFormat(d3.format(".1f")))
           .append("text").attr("x", (W) / 2).attr("y", 26).attr("fill", "currentColor").text("Predicted confidence");
        svg.append("g").attr("class", "axis").attr("transform", `translate(${m.left},0)`)
           .call(d3.axisLeft(ys).ticks(5).tickFormat(d3.format(".1f")))
           .append("text").attr("transform", "rotate(-90)").attr("x", -H/2).attr("y", -28).attr("fill", "currentColor").text("Actual accuracy");

        // Observed line
        const valid = (bins || []).filter(b => b.n > 0);
        const line = d3.line().x(d => xs(d.bin_mid)).y(d => ys(d.observed_accuracy));
        svg.append("path").datum(valid).attr("class", "obs-line").attr("d", line);
        svg.selectAll(".obs-dot").data(valid).enter().append("circle")
           .attr("class", "obs-dot")
           .attr("cx", d => xs(d.bin_mid)).attr("cy", d => ys(d.observed_accuracy))
           .attr("r", d => Math.min(8, 2 + Math.sqrt(d.n)));
    }

    // ======================================================================
    // HAND-BACK UI — low-confidence extraction review
    // Persists user decisions to localStorage so the demo "remembers"
    // ======================================================================
    const HANDBACK_KEY_PREFIX = "one-hr-handback:";
    const LOWCONF_THRESHOLD = 0.75;

    function _handbackKey(text, ent) {
        // Stable per-(text, span, kind) key
        const slug = (text || "").substring(0, 64).replace(/\W+/g, "_");
        return HANDBACK_KEY_PREFIX + slug + ":" + ent.char_start + "-" + ent.char_end + ":" + ent.kind;
    }

    function _loadDecision(text, ent) {
        try { return localStorage.getItem(_handbackKey(text, ent)); } catch (e) { return null; }
    }
    function _saveDecision(text, ent, decision) {
        try { localStorage.setItem(_handbackKey(text, ent), decision); } catch (e) {}
    }

    function applyHandbackOverlay() {
        const text = dictEl.value;
        if (!text.trim()) return;
        const allEnts = highlightEl.querySelectorAll("span.ent");
        let lowConfCount = 0;
        let pendingCount = 0;
        const lastResult = NLP.extractEntities(text, TERMS);
        const entsByPos = new Map();
        for (const e of lastResult.entities) {
            entsByPos.set(e.char_start + ":" + e.char_end, e);
        }
        // Walk DOM spans and find their underlying entity by reading back the displayed text positions
        const nodes = Array.from(allEnts);
        let cursor = 0;
        const dictText = text;
        let dictIdx = 0;
        nodes.forEach((node, i) => {
            // Find the entity whose char_start matches this node's text
            const t = node.textContent;
            // Search for it in the dict text starting from dictIdx
            const found = dictText.indexOf(t, dictIdx);
            if (found < 0) return;
            const start = found;
            const end = found + t.length;
            dictIdx = end;
            const ent = entsByPos.get(start + ":" + end);
            if (!ent) return;
            if (ent.confidence < LOWCONF_THRESHOLD) {
                lowConfCount++;
                const decision = _loadDecision(text, ent);
                if (decision === "confirm") node.classList.add("confirmed");
                else if (decision === "reject") node.classList.add("rejected");
                else { node.classList.add("lowconf"); pendingCount++; }
                node.dataset.entStart = ent.char_start;
                node.dataset.entEnd = ent.char_end;
                node.dataset.entKind = ent.kind;
                node.style.cursor = "pointer";
                if (!node.dataset.handbackBound) {
                    node.dataset.handbackBound = "1";
                    node.addEventListener("click", (ev) => {
                        ev.stopPropagation();
                        showHandbackPopup(node, ent, text);
                    });
                }
            }
        });

        // Banner
        let banner = document.getElementById("handback-banner");
        if (lowConfCount === 0) {
            if (banner) banner.remove();
            return;
        }
        if (!banner) {
            banner = document.createElement("div");
            banner.id = "handback-banner";
            banner.className = "handback-banner";
            highlightEl.parentNode.insertBefore(banner, highlightEl);
        }
        banner.innerHTML = `
            <div class="text">
                ⚠️ <strong>${pendingCount} of ${lowConfCount}</strong> low-confidence extractions need review before this bundle is committed.
                Click any highlighted item below to confirm, reject, or edit.
            </div>
            <button id="handback-accept-all">Accept all remaining</button>
        `;
        document.getElementById("handback-accept-all").onclick = () => {
            highlightEl.querySelectorAll("span.ent.lowconf").forEach(node => {
                const ent = {
                    char_start: parseInt(node.dataset.entStart, 10),
                    char_end: parseInt(node.dataset.entEnd, 10),
                    kind: node.dataset.entKind
                };
                _saveDecision(text, ent, "confirm");
                node.classList.remove("lowconf");
                node.classList.add("confirmed");
            });
            applyHandbackOverlay();
        };
    }

    function showHandbackPopup(anchor, ent, text) {
        document.querySelectorAll(".handback-popup").forEach(p => p.remove());
        const rect = anchor.getBoundingClientRect();
        const pop = document.createElement("div");
        pop.className = "handback-popup";
        pop.style.top = (window.scrollY + rect.bottom + 8) + "px";
        pop.style.left = Math.max(12, window.scrollX + rect.left - 12) + "px";
        const codes = (ent.codes || []).map(c => c.code).join(", ") || "(none)";
        pop.innerHTML = `
            <div class="title">Review extraction</div>
            <div class="meta">
                "${escapeHtml(anchor.textContent)}" · ${escapeHtml(ent.kind)}<br>
                codes: ${escapeHtml(codes)} · confidence: ${ent.confidence.toFixed(2)}
            </div>
            <div class="actions">
                <button class="btn-confirm">Confirm</button>
                <button class="btn-reject">Reject</button>
                <button class="btn-cancel">Cancel</button>
            </div>
        `;
        document.body.appendChild(pop);
        pop.querySelector(".btn-confirm").onclick = () => {
            _saveDecision(text, ent, "confirm");
            pop.remove();
            applyHandbackOverlay();
        };
        pop.querySelector(".btn-reject").onclick = () => {
            _saveDecision(text, ent, "reject");
            pop.remove();
            applyHandbackOverlay();
        };
        pop.querySelector(".btn-cancel").onclick = () => pop.remove();
        // Auto-dismiss on outside click
        setTimeout(() => {
            const off = (e) => {
                if (!pop.contains(e.target)) { pop.remove(); document.removeEventListener("click", off); }
            };
            document.addEventListener("click", off);
        }, 50);
    }

    // Hook hand-back into the existing pipeline
    const _origRun = runDictationPipeline;
    runDictationPipeline = function () {
        _origRun();
        setTimeout(applyHandbackOverlay, 50);
    };
    // Re-apply on initial load
    setTimeout(applyHandbackOverlay, 200);

    // ======================================================================
    // VIEW — Risk Model (predictive ML, XAI, contact tracing, LLM benchmark)
    // ======================================================================
    VIEW_INIT.risk = function () {
        // Sub-tab switching within the Risk Model panel
        document.querySelectorAll(".sub-tab").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".sub-tab").forEach(b => b.classList.toggle("active", b === btn));
                document.querySelectorAll(".rsub").forEach(v => v.classList.toggle("active", v.id === "rsub-" + btn.dataset.rsub));
            });
        });

        // Each sub-renderer is wrapped so a failure in one doesn't break the others
        try { renderRiskModels(); } catch (e) { console.error("renderRiskModels failed:", e); }
        try { renderRiskExplainability(); } catch (e) { console.error("renderRiskExplainability failed:", e); }
        try { renderRiskPublicHealth(); } catch (e) { console.error("renderRiskPublicHealth failed:", e); }
        try { renderRiskLLM(); } catch (e) { console.error("renderRiskLLM failed:", e); }
    };

    // ---- Sub-view 1: AI metrics (3-model bake-off + ROC + calibration) ----
    function renderRiskModels() {
        const ev = DATA.ml_evaluation;
        if (!ev) {
            document.getElementById("risk-model-summary").innerHTML =
                '<div class="empty-state">ML evaluation not yet bundled.</div>';
            return;
        }

        const models = ev.models;
        const md = ev._metadata;

        // Headline cards: ROC-AUC for each model + dataset summary
        const order = ["logistic_regression", "random_forest", "gradient_boosting"];
        const summaryEl = document.getElementById("risk-model-summary");
        summaryEl.innerHTML = `
            <div class="card"><div class="v">${md.n_encounters}</div><div class="l">Encounters (n)</div></div>
            <div class="card"><div class="v">${(md.prevalence * 100).toFixed(1)}%</div><div class="l">Cluster prevalence</div></div>
            ${order.map(m => `
                <div class="card">
                    <div class="v">${models[m].overall.roc_auc.toFixed(3)}</div>
                    <div class="l">${m.replace("_", " ").replace("_", " ")}</div>
                    <div class="d">ROC-AUC · 5-fold CV</div>
                </div>
            `).join("")}
        `;

        // Detailed comparison table
        const tableRows = order.map(m => {
            const o = models[m].overall;
            const cls = o.f1_at_50 >= 0.5 ? "score-good" : o.f1_at_50 >= 0.3 ? "score-mid" : "score-low";
            return `<tr>
                <td><strong>${m.replace("_", " ").replace("_", " ")}</strong></td>
                <td>${o.roc_auc.toFixed(3)}</td>
                <td>${o.pr_auc.toFixed(3)}</td>
                <td>${o.brier.toFixed(4)}</td>
                <td>${(o.precision_at_50 * 100).toFixed(1)}%</td>
                <td>${(o.recall_at_50 * 100).toFixed(1)}%</td>
                <td class="${cls}">${(o.f1_at_50 * 100).toFixed(1)}%</td>
            </tr>`;
        }).join("");

        document.getElementById("risk-model-table").innerHTML = `<table class="eval-table">
            <thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>Precision@0.5</th><th>Recall@0.5</th><th>F1@0.5</th></tr></thead>
            <tbody>${tableRows}</tbody>
        </table>`;

        // ROC curves overlay
        drawRiskROC(ev);

        // Calibration of gradient boosting
        drawRiskCalibration(ev.models.gradient_boosting.calibration);
    }

    function drawRiskROC(ev) {
        const svg = d3.select("#risk-roc-curves");
        svg.selectAll("*").remove();
        const W = svg.node().getBoundingClientRect().width || 700;
        const H = 320;
        svg.attr("viewBox", `0 0 ${W} ${H}`);
        const M = { top: 14, right: 130, bottom: 40, left: 50 };

        const x = d3.scaleLinear().domain([0, 1]).range([M.left, W - M.right]);
        const y = d3.scaleLinear().domain([0, 1]).range([H - M.bottom, M.top]);

        // Diagonal reference
        svg.append("line")
            .attr("x1", x(0)).attr("y1", y(0)).attr("x2", x(1)).attr("y2", y(1))
            .attr("stroke", "#888").attr("stroke-dasharray", "3,3").attr("stroke-width", 1).attr("opacity", 0.5);

        const colors = { logistic_regression: "#5b9", random_forest: "#d72", gradient_boosting: "#48a" };
        const order = ["logistic_regression", "random_forest", "gradient_boosting"];

        order.forEach((m, idx) => {
            const r = ev.models[m].roc_curve;
            const points = r.fpr.map((f, i) => [f, r.tpr[i]]);
            const line = d3.line().x(d => x(d[0])).y(d => y(d[1])).curve(d3.curveStepAfter);
            svg.append("path")
                .attr("d", line(points))
                .attr("fill", "none")
                .attr("stroke", colors[m])
                .attr("stroke-width", 2);

            // Legend
            const lx = W - M.right + 12;
            const ly = M.top + 14 + idx * 20;
            svg.append("rect").attr("x", lx).attr("y", ly - 8).attr("width", 12).attr("height", 12).attr("fill", colors[m]);
            svg.append("text").attr("x", lx + 18).attr("y", ly + 2).attr("font-size", "0.78rem").attr("fill", "var(--ink-2)").text(`${m.replace("_", " ").replace("_", " ")} (${ev.models[m].overall.roc_auc.toFixed(2)})`);
        });

        // Axes
        svg.append("g").attr("transform", `translate(0,${H - M.bottom})`)
            .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format(".1f")));
        svg.append("g").attr("transform", `translate(${M.left},0)`)
            .call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".1f")));
        svg.append("text").attr("x", W / 2).attr("y", H - 6)
            .attr("text-anchor", "middle").attr("font-size", "0.78rem").attr("fill", "var(--ink-3)")
            .text("False positive rate");
        svg.append("text").attr("transform", `translate(15,${H/2}) rotate(-90)`)
            .attr("text-anchor", "middle").attr("font-size", "0.78rem").attr("fill", "var(--ink-3)")
            .text("True positive rate");
    }

    function drawRiskCalibration(bins) {
        const svg = d3.select("#risk-calibration");
        svg.selectAll("*").remove();
        const W = svg.node().getBoundingClientRect().width || 700;
        const H = 240;
        svg.attr("viewBox", `0 0 ${W} ${H}`);
        const M = { top: 14, right: 14, bottom: 32, left: 50 };
        const x = d3.scaleLinear().domain([0, 1]).range([M.left, W - M.right]);
        const y = d3.scaleLinear().domain([0, 1]).range([H - M.bottom, M.top]);

        // Diagonal
        svg.append("line").attr("x1", x(0)).attr("y1", y(0)).attr("x2", x(1)).attr("y2", y(1))
            .attr("stroke", "#888").attr("stroke-dasharray", "3,3").attr("opacity", 0.5);

        const points = bins.map(b => [b.mean_pred, b.mean_actual]).filter(p => isFinite(p[0]) && isFinite(p[1]));
        if (points.length > 0) {
            const line = d3.line().x(d => x(d[0])).y(d => y(d[1]));
            svg.append("path").attr("d", line(points)).attr("fill", "none").attr("stroke", "var(--accent)").attr("stroke-width", 2);
            svg.selectAll("circle").data(points).join("circle")
                .attr("cx", d => x(d[0])).attr("cy", d => y(d[1])).attr("r", 4).attr("fill", "var(--accent)");
        }
        svg.append("g").attr("transform", `translate(0,${H - M.bottom})`).call(d3.axisBottom(x).ticks(5));
        svg.append("g").attr("transform", `translate(${M.left},0)`).call(d3.axisLeft(y).ticks(5));
        svg.append("text").attr("x", W / 2).attr("y", H - 4).attr("text-anchor", "middle").attr("font-size", "0.75rem").attr("fill", "var(--ink-3)").text("Mean predicted probability");
        svg.append("text").attr("transform", `translate(14,${H/2}) rotate(-90)`).attr("text-anchor", "middle").attr("font-size", "0.75rem").attr("fill", "var(--ink-3)").text("Empirical positive rate");
    }

    // ---- Sub-view 2: Explainability (SHAP global + per-patient + tree) ----
    function renderRiskExplainability() {
        const ex = DATA.explanations;
        if (!ex) {
            document.getElementById("risk-shap-global").innerHTML =
                '<div class="empty-state">Explanations not yet bundled.</div>';
            return;
        }

        // Global SHAP - top 12
        const top = ex.global_shap_importance.slice(0, 12);
        const maxV = top[0].importance;
        document.getElementById("risk-shap-global").innerHTML = top.map(f => `
            <div class="shap-bar-row">
                <div class="label">${escapeHtml(f.label)}</div>
                <div class="bar" style="width: ${(f.importance / maxV * 100).toFixed(1)}%"></div>
                <div class="val">${f.importance.toFixed(3)}</div>
            </div>
        `).join("");

        // Per-patient explanation - household selector
        const toolbar = document.getElementById("risk-shap-household-toolbar");
        toolbar.innerHTML = '<strong style="margin-right:6px; color:var(--ink-3); font-size:0.75rem; text-transform:uppercase; letter-spacing:0.12em; align-self:center;">Household:</strong>';
        ex.per_patient_explanations.forEach((p, i) => {
            const btn = document.createElement("button");
            btn.className = "scenario-btn" + (i === 0 ? " primary" : "");
            const hhName = p.household_id.split("-").pop().replace(/^\d+$/, p.household_id);
            const counties = (DATA.households && DATA.households.households) ?
                (DATA.households.households.find(h => h.household_id === p.household_id) || {}).name : "";
            btn.textContent = `${counties || p.household_id.slice(-5)} (P=${p.predicted_proba.toFixed(2)})`;
            btn.dataset.hid = p.household_id;
            btn.addEventListener("click", () => {
                document.querySelectorAll("#risk-shap-household-toolbar button").forEach(b => b.classList.remove("primary"));
                btn.classList.add("primary");
                renderRiskPerPatient(p);
            });
            toolbar.appendChild(btn);
        });
        renderRiskPerPatient(ex.per_patient_explanations[0]);

        // Permutation importance - top 10
        const perm = ex.permutation_importance.slice(0, 10).filter(f => f.importance > 0);
        const permMax = perm[0] ? perm[0].importance : 1;
        document.getElementById("risk-perm-importance").innerHTML = perm.map(f => `
            <div class="shap-bar-row">
                <div class="label">${escapeHtml(f.label)}</div>
                <div class="bar" style="width: ${(f.importance / permMax * 100).toFixed(1)}%"></div>
                <div class="val">${f.importance.toFixed(3)} ± ${f.std.toFixed(3)}</div>
            </div>
        `).join("");

        // Decision tree rules
        const dtRules = (DATA.ml_evaluation && DATA.ml_evaluation._metadata && DATA.ml_evaluation._metadata.decision_tree_rules) || "(decision tree rules not available)";
        document.getElementById("risk-tree-rules").textContent = dtRules;
    }

    function renderRiskPerPatient(p) {
        if (!p) return;
        const hh = DATA.households.households.find(h => h.household_id === p.household_id);
        const hhName = hh ? hh.name : p.household_id;
        const county = hh && hh.county ? hh.county.name : "";

        const contributions = p.top_contributions;
        const maxAbs = Math.max(...contributions.map(c => Math.abs(c.shap)));

        let html = `
            <div class="shap-patient-header">
                <h4>${escapeHtml(hhName)} — ${escapeHtml(county)} County</h4>
                <div>
                    <span class="proba">P = ${p.predicted_proba.toFixed(3)}</span>
                    <span style="margin-left: 12px; color: var(--ink-3); font-size: 0.78rem;">label: ${p.actual_label === 1 ? "<strong style='color:#d04;'>positive</strong>" : "<strong style='color:#2a7;'>negative</strong>"}</span>
                </div>
            </div>
            <div style="font-size: 0.78rem; color: var(--ink-3); margin-bottom: 10px;">
                Base value: ${p.base_value.toFixed(3)} → Final prediction: ${p.predicted_proba.toFixed(3)}
            </div>
        `;

        contributions.forEach(c => {
            const isPos = c.shap > 0;
            const widthPct = (Math.abs(c.shap) / maxAbs * 50).toFixed(1);
            const offset = isPos ? 50 : (50 - widthPct);
            html += `
                <div class="shap-waterfall-row">
                    <div class="feature-name">${escapeHtml(c.label)}</div>
                    <div class="feature-value">${c.value !== null && c.value !== undefined ? (typeof c.value === "number" ? c.value.toFixed(2) : c.value) : ""}</div>
                    <div class="shap-bar-container">
                        <div class="shap-bar-fill ${isPos ? "pos" : "neg"}"
                             style="left: ${offset}%; width: ${widthPct}%;"></div>
                    </div>
                    <div class="shap-val ${isPos ? "pos" : "neg"}">${isPos ? "+" : ""}${c.shap.toFixed(3)}</div>
                </div>
            `;
        });
        document.getElementById("risk-shap-patient").innerHTML = html;
    }

    // ---- Sub-view 3: PH metrics (contact tracing, lead time, equity) ----
    function renderRiskPublicHealth() {
        const ct = DATA.contact_tracing;
        const lt = DATA.lead_time;
        const eq = DATA.equity;

        // Contact tracing
        if (ct && ct.evaluation) {
            const e = ct.evaluation;
            document.getElementById("risk-ct-summary").innerHTML = `
                <div class="card"><div class="v">${e.n_indices_traced}</div><div class="l">Index cases traced</div></div>
                <div class="card"><div class="v">${e.total_contacts_traced}</div><div class="l">Contacts surfaced</div></div>
                <div class="card"><div class="v">${e.tier1_contacts_total}</div><div class="l">Tier 1 (household)</div></div>
                <div class="card"><div class="v">${e.tier2_contacts_total}</div><div class="l">Tier 2 (shared exposure)</div></div>
                <div class="card"><div class="v">${e.post_index_secondaries_total}</div><div class="l">Post-index secondaries</div></div>
                <div class="card"><div class="v">${e.pre_index_positives_uncatchable}</div><div class="l">Pre-index (uncatchable)</div></div>
            `;

            const trows = e.by_threshold.map(b => `
                <tr>
                    <td>${b.risk_threshold.toFixed(2)}</td>
                    <td>${b.flagged_total}</td>
                    <td>${b.tp}</td>
                    <td>${b.fp}</td>
                    <td>${b.fn}</td>
                    <td>${(b.sensitivity * 100).toFixed(1)}%</td>
                    <td>${(b.precision * 100).toFixed(1)}%</td>
                    <td>${(b.f1 * 100).toFixed(1)}%</td>
                    <td>${b.mean_lead_time_days != null ? b.mean_lead_time_days.toFixed(1) + "d" : "—"}</td>
                </tr>
            `).join("");
            document.getElementById("risk-ct-threshold-table").innerHTML = `<table class="eval-table">
                <thead><tr><th>Threshold</th><th>Flagged</th><th>TP</th><th>FP</th><th>FN</th><th>Sensitivity</th><th>Precision</th><th>F1</th><th>Lead time</th></tr></thead>
                <tbody>${trows}</tbody>
            </table>`;

            const irows = e.per_index.map(p => `
                <tr>
                    <td><strong>${p.household_id}</strong></td>
                    <td>${p.index_date}</td>
                    <td>${p.n_contacts_total}</td>
                    <td>${p.tier1_count}</td>
                    <td>${p.tier2_count}</td>
                    <td>${p.tier3_count}</td>
                    <td>${p["n_flagged_at_0.20"]}</td>
                    <td>${p.n_secondaries_total}</td>
                    <td>${p["n_secondaries_caught_at_0.20"]}</td>
                    <td>${p.n_pre_index_positives_uncatchable}</td>
                </tr>
            `).join("");
            document.getElementById("risk-ct-per-index").innerHTML = `<table class="eval-table">
                <thead><tr><th>Index household</th><th>Index date</th><th>Total</th><th>T1</th><th>T2</th><th>T3</th><th>Flagged@0.20</th><th>Secondaries</th><th>Caught</th><th>Pre-index</th></tr></thead>
                <tbody>${irows}</tbody>
            </table>`;
        }

        // Lead time
        if (lt && lt.summary) {
            const s = lt.summary;
            document.getElementById("risk-leadtime-summary").innerHTML = `
                <div class="card"><div class="v">${s.n_with_positive_lead}/${s.n_scenarios}</div><div class="l">Scenarios with lead time</div></div>
                <div class="card"><div class="v">${s.mean_lead_days.toFixed(1)}d</div><div class="l">Mean lead time</div></div>
                <div class="card"><div class="v">${s.max_lead_days}d</div><div class="l">Max lead</div></div>
                <div class="card"><div class="v">0d</div><div class="l">Baseline (ArboNET-eq.)</div></div>
            `;
            const lrows = lt.per_scenario.map(s => `
                <tr>
                    <td><strong>${s.household_id}</strong></td>
                    <td>${escapeHtml(s.household_name || "")}</td>
                    <td>${escapeHtml(s.county || "")}</td>
                    <td>${escapeHtml(s.disease)}</td>
                    <td>${s.confirmation_date}</td>
                    <td><strong>${s.best_lead_days}d</strong></td>
                    <td>${s.best_signal ? escapeHtml(s.best_signal.signal) : "—"}</td>
                </tr>
            `).join("");
            document.getElementById("risk-leadtime-table").innerHTML = `<table class="eval-table">
                <thead><tr><th>HH</th><th>Family</th><th>County</th><th>Disease</th><th>Confirmation</th><th>Lead time</th><th>Signal source</th></tr></thead>
                <tbody>${lrows}</tbody>
            </table>`;
        }

        // Equity
        if (eq && eq.model_performance_by_stratum) {
            const eqWrap = document.getElementById("risk-equity");
            const dims = eq.model_performance_by_stratum;
            const dimLabels = {
                "rural_urban": "Rural vs urban",
                "tribal_status": "Tribal vs non-tribal",
                "species": "Species",
                "size_stratum": "County size"
            };
            const cards = Object.keys(dims).map(dim => {
                const rows = dims[dim].map(r => {
                    const aucs = r.roc_auc != null ? r.roc_auc.toFixed(3) : "n/a";
                    const prs = r.pr_auc != null ? r.pr_auc.toFixed(3) : "n/a";
                    return `<div class="row">
                        <div class="stratum">${escapeHtml(r.stratum)} <span style="font-size:0.7rem; color: var(--ink-3);">(n=${r.n}, +${r.n_positive})</span></div>
                        <div class="metric">${aucs}</div>
                        <div class="metric">${prs}</div>
                    </div>`;
                }).join("");
                return `<div class="card">
                    <h4>${escapeHtml(dimLabels[dim] || dim)}</h4>
                    <div class="row" style="font-weight:600; color:var(--ink-3); border-bottom: 1px solid var(--border);">
                        <div></div><div class="metric">ROC-AUC</div><div class="metric">PR-AUC</div>
                    </div>
                    ${rows}
                </div>`;
            }).join("");
            eqWrap.innerHTML = `<div class="equity-strata">${cards}</div>`;
        }
    }

    // ---- Sub-view 4: LLM benchmark (Rule vs Claude Haiku 4.5) ----
    function renderRiskLLM() {
        const b = DATA.llm_benchmark;
        if (!b) {
            document.getElementById("risk-llm-headline").innerHTML =
                '<div class="empty-state">LLM benchmark not yet bundled.</div>';
            return;
        }
        const h = b.head_to_head;
        document.getElementById("risk-llm-headline").innerHTML = `
            <div class="llm-headline">
                <div class="card rule">
                    <h4>Rule-based extractor</h4>
                    <div class="stat-row"><span>Precision</span><span class="v">${(h.rule_based.precision * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>Recall</span><span class="v">${(h.rule_based.recall * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>F1</span><span class="v">${(h.rule_based.f1 * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>Latency</span><span class="v">${h.rule_based.latency_ms.toFixed(1)} ms</span></div>
                    <div class="stat-row"><span>Cost</span><span class="v">$${h.rule_based.cost_per_dictation_usd.toFixed(4)}</span></div>
                </div>
                <div class="card llm">
                    <h4>${escapeHtml(b._metadata.model)}</h4>
                    <div class="stat-row"><span>Precision</span><span class="v">${(h.llm_haiku.precision * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>Recall</span><span class="v">${(h.llm_haiku.recall * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>F1</span><span class="v">${(h.llm_haiku.f1 * 100).toFixed(1)}%</span></div>
                    <div class="stat-row"><span>Latency</span><span class="v">${h.llm_haiku.latency_ms.toFixed(0)} ms</span></div>
                    <div class="stat-row"><span>Cost</span><span class="v">$${h.llm_haiku.cost_per_dictation_usd.toFixed(4)}</span></div>
                </div>
            </div>
        `;

        // Per-kind metrics
        const krows = Object.keys(b.llm_per_kind).map(k => {
            const v = b.llm_per_kind[k];
            return `<tr>
                <td><strong>${escapeHtml(k)}</strong></td>
                <td>${v.support}</td>
                <td>${(v.precision * 100).toFixed(1)}%</td>
                <td>${(v.recall * 100).toFixed(1)}%</td>
                <td>${(v.f1 * 100).toFixed(1)}%</td>
            </tr>`;
        }).join("");
        document.getElementById("risk-llm-perkind").innerHTML = `<table class="eval-table">
            <thead><tr><th>Entity kind</th><th>Support</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead>
            <tbody>${krows}</tbody>
        </table>`;

        // Tradeoff cards
        document.getElementById("risk-llm-tradeoff").innerHTML = `
            <div class="card">
                <h4>When to prefer rules</h4>
                <ul>
                    <li>Determinism required (audit trail)</li>
                    <li>Latency budget &lt; 50 ms (real-time triage)</li>
                    <li>Zero per-call cost at scale</li>
                    <li>Air-gapped or offline environments</li>
                </ul>
            </div>
            <div class="card">
                <h4>When to prefer LLM</h4>
                <ul>
                    <li>Novel surface forms / phrasing variation</li>
                    <li>Long-tail vocabulary not in dictionary</li>
                    <li>Complex negation / hedging patterns</li>
                    <li>Few annotated examples for fine-tuning</li>
                </ul>
            </div>
        `;

        // is_simulated caveat
        if (b._metadata && b._metadata.is_simulated) {
            document.getElementById("risk-llm-caveat").innerHTML = `
                <div class="caveat-banner">
                    <strong>Note:</strong> These LLM numbers are <strong>projected</strong> from
                    published Haiku 4.5 clinical-NER benchmarks (calibrated, deterministic seed=42),
                    not from a live API run. To produce real numbers from your environment,
                    run <code>ANTHROPIC_API_KEY=... python src/ml/llm_benchmark.py</code>.
                    Cost ≈ $0.05 for the full 25-dictation evaluation.
                </div>
            `;
        }
    }



    // Activate map first hidden — its init runs only when the tab is opened.
    // ======================================================================
    // VIEW — Model Card (Phase 3 — replaces Architecture)
    // ======================================================================
    VIEW_INIT.modelcard = function () {
        // Phase 4.1 — Audit log sub-tab is restricted to public-health users
        const session = window.OH_AUTH ? window.OH_AUTH.getSession() : null;
        const auditTabBtn = document.querySelector('.sub-tab[data-mcsub="audit"]');
        if (auditTabBtn) {
            auditTabBtn.hidden = !(session && session.role === "public_health");
        }

        // Sub-tab switching
        document.querySelectorAll(".sub-tab[data-mcsub]").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".sub-tab[data-mcsub]").forEach(b =>
                    b.classList.toggle("active", b === btn));
                document.querySelectorAll(".mcsub").forEach(v =>
                    v.classList.toggle("active", v.id === "mcsub-" + btn.dataset.mcsub));
                if (btn.dataset.mcsub === "audit") renderModelCardAudit();
                if (btn.dataset.mcsub === "federation") renderModelCardFederation();
            });
        });

        // Wire the "Clear audit log" button
        const clearBtn = document.getElementById("mc-audit-clear");
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                try { localStorage.removeItem(AUDIT_KEY); } catch (_) {}
                if (window.OH_AUTH) window.OH_AUTH.auditLog("audit_cleared", "");
                renderModelCardAudit();
            });
        }

        // Render live metrics in Section 4 from ml_evaluation
        try { renderModelCardMetrics(); } catch (e) { console.error("MC metrics:", e); }
        // Render federated-learning simulation summary
        try { renderModelCardFederated(); } catch (e) { console.error("MC FL:", e); }
        // Render initial federation overview
        try { renderModelCardFederation(); } catch (e) { console.error("MC fed:", e); }
        // Render initial audit log (in case the user navigates straight there)
        try { renderModelCardAudit(); } catch (e) { console.error("MC audit:", e); }
    };

    // ---- Federation sub-tab (Phase 6) -----------------------------------
    function renderModelCardFederation() {
        if (!window.OH_FED) return;
        const counters = window.OH_FED.getFederationCounters();
        const sites = window.OH_FED.getSiteStats();

        const cEl = document.getElementById("mc-fed-counters");
        if (cEl) {
            cEl.innerHTML = `
                <div class="metric-card"><div class="metric-num">${counters.n_sites}</div><div class="metric-label">PARTNER SITES</div></div>
                <div class="metric-card"><div class="metric-num">${counters.n_hospital_systems}</div><div class="metric-label">HOSPITAL SYSTEMS</div></div>
                <div class="metric-card"><div class="metric-num">${counters.n_vet_clinics}</div><div class="metric-label">VET NETWORKS</div></div>
                <div class="metric-card"><div class="metric-num">${counters.n_public_health}</div><div class="metric-label">PUBLIC HEALTH</div></div>
                <div class="metric-card"><div class="metric-num">${counters.total_patients.toLocaleString()}</div><div class="metric-label">HUMANS (FEDERATED)</div></div>
                <div class="metric-card"><div class="metric-num">${counters.total_animals.toLocaleString()}</div><div class="metric-label">ANIMALS (FEDERATED)</div></div>
            `;
        }
        const sEl = document.getElementById("mc-fed-sites");
        if (sEl) {
            sEl.innerHTML = `
                <table class="audit-log-table">
                    <thead><tr>
                        <th>Site</th><th>Kind</th><th>Vendor</th><th>FHIR</th>
                        <th style="text-align:right;">Humans</th><th style="text-align:right;">Animals</th><th style="text-align:right;">Encounters</th>
                        <th>Endpoint</th><th>Health</th>
                    </tr></thead>
                    <tbody>${sites.map(s => `
                        <tr>
                            <td><strong>${escapeHtml(s.facility)}</strong></td>
                            <td>${s.kind.replace(/_/g, ' ')}</td>
                            <td>${escapeHtml(s.vendor)}</td>
                            <td><code style="font-size:0.78rem;">${escapeHtml(s.fhir_version)}</code></td>
                            <td style="text-align:right;">${(s.n_patients || 0).toLocaleString()}</td>
                            <td style="text-align:right;">${(s.n_animal_patients || 0).toLocaleString()}</td>
                            <td style="text-align:right;">${(s.n_encounters || 0).toLocaleString()}</td>
                            <td><code style="font-size:0.72rem;">${escapeHtml(s.endpoint)}</code></td>
                            <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#4A6F4D;"></span> green</td>
                        </tr>`).join("")}</tbody>
                </table>`;
        }
        renderWireLog();

        // Wire up trigger / clear buttons
        const trig = document.getElementById("mc-fed-trigger");
        if (trig && !trig.dataset.bound) {
            trig.dataset.bound = "1";
            trig.addEventListener("click", async () => {
                const pulse = document.getElementById("mc-fed-pulse");
                if (pulse) pulse.textContent = "Querying federation for the Hernandez household (HH-AZ-PIMA-001) …";
                try {
                    await window.OH_FED.fhirFetchHousehold("HH-AZ-PIMA-001");
                    if (pulse) pulse.textContent = "Done — see wire log.";
                    setTimeout(() => { if (pulse) pulse.textContent = ""; }, 4000);
                } catch (e) {
                    if (pulse) pulse.textContent = "Error: " + e.message;
                }
            });
        }
        const clr = document.getElementById("mc-fed-clear");
        if (clr && !clr.dataset.bound) {
            clr.dataset.bound = "1";
            clr.addEventListener("click", () => {
                window.OH_FED.clearWireLog();
                renderWireLog();
            });
        }

        // Subscribe to live wire-log updates (only register once per session)
        if (!window._OHR_WIRE_LISTENER) {
            window._OHR_WIRE_LISTENER = true;
            window.OH_FED.onWireEntry(() => renderWireLog());
        }
    }

    function renderWireLog() {
        const el = document.getElementById("mc-fed-wirelog");
        if (!el || !window.OH_FED) return;
        const log = window.OH_FED.getWireLog();
        if (!log.length) {
            el.innerHTML = `<div class="empty-state" style="padding:14px 18px; color:var(--ink-3); font-size:0.85rem;">No cross-site fetches yet. Click <em>Trigger sample federation query</em> above, or open Provider Workspace and select a multi-site household.</div>`;
            return;
        }
        el.innerHTML = `
            <table class="audit-log-table">
                <thead><tr>
                    <th>Timestamp</th><th>Source</th><th>Target</th><th>Resource</th>
                    <th>Query</th><th style="text-align:right;">Latency</th><th style="text-align:right;">Results</th><th>Status</th>
                </tr></thead>
                <tbody>${log.slice(0, 80).map(e => {
                    if (!e) return "";
                    const queryStr = Object.entries(e.query || {}).map(([k, v]) => `${k}=${String(v).slice(0, 24)}`).join(", ") || "—";
                    const statusColor = e.ok ? "var(--grn)" : "var(--cardinal)";
                    return `<tr>
                        <td><code style="font-size:0.78rem;">${escapeHtml(e.ts || "")}</code></td>
                        <td>${escapeHtml(e.source || "")}</td>
                        <td><strong>${escapeHtml(e.target || e.target_id || "")}</strong></td>
                        <td><code>${escapeHtml(e.resource || "")}</code></td>
                        <td style="font-size:0.78rem; color:var(--ink-3);">${escapeHtml(queryStr)}</td>
                        <td style="text-align:right;"><code>${e.latency_ms || 0}ms</code></td>
                        <td style="text-align:right;">${e.n_results ?? 0}</td>
                        <td style="color:${statusColor};"><strong>${e.status || ""} ${e.ok ? "OK" : ""}</strong></td>
                    </tr>`;
                }).join("")}</tbody>
            </table>`;
    }

    function renderModelCardAudit() {
        // Phase 4.1 — defense in depth: renderer refuses for non-PH users
        const session = window.OH_AUTH ? window.OH_AUTH.getSession() : null;
        const tblEl     = document.getElementById("mc-audit-table");
        const summaryEl = document.getElementById("mc-audit-summary");
        if (!session || session.role !== "public_health") {
            if (summaryEl) summaryEl.innerHTML = "";
            if (tblEl) tblEl.innerHTML = `
                <div class="empty-state" style="border-left: 4px solid var(--amber); padding: 14px 18px; background: rgba(216,159,46,0.05);">
                    <strong>Access policy.</strong> The audit log is restricted to public-health users (ADHS, tribal health, USDA APHIS) — the roles with audit responsibility for the One Health surveillance system. Clinicians and veterinarians cannot view system-wide audit events; their own actions are still recorded and retained for SOC review.
                </div>`;
            const clearBtn = document.getElementById("mc-audit-clear");
            if (clearBtn) clearBtn.style.display = "none";
            return;
        }
        const clearBtn = document.getElementById("mc-audit-clear");
        if (clearBtn) clearBtn.style.display = "";

        const log = window.OH_AUTH ? window.OH_AUTH.readAuditLog() : [];
        if (summaryEl) {
            // Compute basic stats
            const counts = {};
            const users  = new Set();
            log.forEach(e => {
                counts[e.action] = (counts[e.action] || 0) + 1;
                if (e.user_id) users.add(e.user_id);
            });
            const sessionsCount = counts.login || 0;
            const navCount      = (counts.tab_view || 0) + (counts.hub_view || 0);
            const denials       = counts.hub_access_denied || 0;
            summaryEl.innerHTML = `
                <div class="card"><div class="v">${log.length}</div><div class="l">Total events</div></div>
                <div class="card"><div class="v">${sessionsCount}</div><div class="l">Logins</div></div>
                <div class="card"><div class="v">${navCount}</div><div class="l">Navigation events</div></div>
                <div class="card"><div class="v">${denials}</div><div class="l">Access denials</div></div>
                <div class="card"><div class="v">${users.size}</div><div class="l">Distinct users</div></div>
            `;
        }
        if (tblEl) {
            if (!log.length) {
                tblEl.innerHTML = '<div class="empty-state">No audit events recorded yet. (Log starts on first login.)</div>';
                return;
            }
            // Show latest first (max 100)
            const reversed = log.slice().reverse().slice(0, 100);
            const rows = reversed.map(e => {
                const ts = e.timestamp ? e.timestamp.replace("T", " ").replace(/\.\d+Z$/, "Z") : "";
                const actionClass = "action-" + (e.action || "").split("_")[0];
                return `<tr>
                    <td class="timestamp">${escapeHtml(ts)}</td>
                    <td><code>${escapeHtml(e.user_id || "")}</code></td>
                    <td>${escapeHtml(e.role || "")}</td>
                    <td class="${actionClass}"><strong>${escapeHtml(e.action || "")}</strong></td>
                    <td><code>${escapeHtml(e.target || "")}</code></td>
                </tr>`;
            }).join("");
            tblEl.innerHTML = `<table class="audit-log-table">
                <thead><tr><th>Timestamp</th><th>User</th><th>Role</th><th>Action</th><th>Target</th></tr></thead>
                <tbody>${rows}</tbody></table>
                ${log.length > 100 ? `<div style="font-size: 0.78rem; color: var(--ink-3); margin-top: 8px; text-align: right;">Showing latest 100 of ${log.length} events</div>` : ""}
            `;
        }
    }

    function renderModelCardMetrics() {
        const ev = DATA.ml_evaluation;
        if (!ev) {
            const el = document.getElementById("mc-metrics-headline");
            if (el) el.innerHTML = '<div class="empty-state">ML evaluation not yet bundled.</div>';
            return;
        }
        const md = ev._metadata, m = ev.models;
        const headline = document.getElementById("mc-metrics-headline");
        if (headline) {
            headline.innerHTML = `
                <div class="card"><div class="v">${md.n_encounters}</div><div class="l">Encounters (n)</div></div>
                <div class="card"><div class="v">${(md.prevalence * 100).toFixed(1)}%</div><div class="l">Cluster prevalence</div></div>
                <div class="card"><div class="v">${m.gradient_boosting.overall.roc_auc.toFixed(3)}</div><div class="l">GB ROC-AUC</div><div class="d">5-fold CV</div></div>
                <div class="card"><div class="v">${m.gradient_boosting.overall.brier.toFixed(4)}</div><div class="l">GB Brier (calib)</div></div>
                <div class="card"><div class="v">${(m.gradient_boosting.overall.f1_at_50 * 100).toFixed(1)}%</div><div class="l">GB F1 @ 0.5</div></div>
            `;
        }
        const order = ["logistic_regression", "random_forest", "gradient_boosting"];
        const tbl = document.getElementById("mc-metrics-table");
        if (tbl) {
            tbl.innerHTML = `<table class="eval-table">
                <thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th><th>Brier</th><th>P@0.5</th><th>R@0.5</th><th>F1@0.5</th></tr></thead>
                <tbody>${order.map(name => {
                    const o = m[name].overall;
                    return `<tr><td><strong>${name.replace(/_/g, " ")}</strong></td>
                        <td>${o.roc_auc.toFixed(3)}</td><td>${o.pr_auc.toFixed(3)}</td>
                        <td>${o.brier.toFixed(4)}</td><td>${(o.precision_at_50*100).toFixed(1)}%</td>
                        <td>${(o.recall_at_50*100).toFixed(1)}%</td>
                        <td><strong>${(o.f1_at_50*100).toFixed(1)}%</strong></td></tr>`;
                }).join("")}</tbody></table>`;
        }

        // Equity disaggregation (mirrors Risk Model tab but in MC context)
        const eq = DATA.equity;
        const eqEl = document.getElementById("mc-equity-table");
        if (eq && eqEl && eq.model_performance_by_stratum) {
            const dims = eq.model_performance_by_stratum;
            const rows = [];
            for (const dim of Object.keys(dims)) {
                for (const r of dims[dim]) {
                    const auc = r.roc_auc != null ? r.roc_auc.toFixed(3) : "—";
                    const pr = r.pr_auc != null ? r.pr_auc.toFixed(3) : "—";
                    rows.push(`<tr><td>${dim.replace(/_/g, " ")}</td>
                        <td>${escapeHtml(r.stratum)}</td><td>${r.n}</td><td>${r.n_positive}</td>
                        <td>${auc}</td><td>${pr}</td></tr>`);
                }
            }
            eqEl.innerHTML = `<table class="eval-table">
                <thead><tr><th>Dimension</th><th>Stratum</th><th>n</th><th>n positive</th><th>ROC-AUC</th><th>PR-AUC</th></tr></thead>
                <tbody>${rows.join("")}</tbody></table>`;
        }
    }

    function renderModelCardFederated() {
        const fl = DATA.federated;
        const summary = document.getElementById("mc-fl-summary");
        const tbl = document.getElementById("mc-fl-table");
        if (!fl || !fl.summary) {
            if (summary) summary.innerHTML = '<div class="empty-state">Run <code>python src/ml/federated_simulation.py</code> to populate.</div>';
            return;
        }
        const s = fl.summary;
        if (summary) {
            summary.innerHTML = `
                <div class="card"><div class="v">${s.n_sites}</div><div class="l">Simulated sites</div></div>
                <div class="card"><div class="v">${s.n_rounds}</div><div class="l">FedAvg rounds</div></div>
                <div class="card"><div class="v">${s.federated_auc.toFixed(3)}</div><div class="l">Federated ROC-AUC</div></div>
                <div class="card"><div class="v">${s.centralized_auc.toFixed(3)}</div><div class="l">Centralized (reference)</div></div>
                <div class="card"><div class="v">${(s.auc_gap >= 0 ? "+" : "")}${s.auc_gap.toFixed(3)}</div><div class="l">Federated − centralized</div></div>
            `;
        }
        if (tbl) {
            const rows = (fl.per_site || []).map(r => `
                <tr><td><strong>${escapeHtml(r.site_id)}</strong></td>
                    <td>${escapeHtml(r.site_type)}</td>
                    <td>${r.n_train}</td><td>${r.n_pos}</td>
                    <td>${r.local_auc.toFixed(3)}</td>
                    <td>${r.federated_auc.toFixed(3)}</td>
                    <td>${(r.federated_auc - r.local_auc >= 0 ? "+" : "") + (r.federated_auc - r.local_auc).toFixed(3)}</td></tr>
            `).join("");
            tbl.innerHTML = `<table class="eval-table">
                <thead><tr><th>Site</th><th>Type</th><th>n train</th><th>n positive</th><th>Local AUC</th><th>Federated AUC</th><th>Δ from federation</th></tr></thead>
                <tbody>${rows}</tbody></table>`;
        }
    }

    activateTab("encounter");
})();
