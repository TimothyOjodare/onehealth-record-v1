/* ============================================================================
 * Phase 6 — Federation client.
 *
 * Provides a small "FHIR fetcher" surface that simulates cross-site network
 * calls. Each call:
 *   1. Logs to a global ring buffer (the wire log) with source, target,
 *      latency, and outcome.
 *   2. Returns the matching resources from the relevant in-memory shadow
 *      store after a small synthetic delay.
 *   3. Notifies any registered listeners so the Federation Network sub-tab
 *      can render the live wire log.
 *
 * In production:
 *   - fhirFetch() would make a real HTTPS call to the partner site's FHIR
 *     server with a SMART-on-FHIR bearer token.
 *   - The wire log would feed the SOC audit pipeline.
 *   - Latency, retry, and circuit-breaker logic would replace the synthetic
 *     latency model below.
 * ========================================================================== */

(function () {
    'use strict';

    const WIRE_LOG_MAX = 200;
    const wireLog = [];
    const listeners = new Set();

    // Synthetic latency model — vet sites are slower (less mature infra),
    // tribal sites have variable connectivity, ADHS is a shared public
    // service so latency varies with load.
    const LATENCY_MS = {
        hospital_system: { min: 45,  max: 180 },
        vet_clinic:      { min: 80,  max: 320 },
        public_health:   { min: 110, max: 480 },
    };

    function _now() { return new Date().toISOString().replace('T', ' ').slice(0, 19) + 'Z'; }

    function _logEntry(entry) {
        wireLog.unshift(entry);
        if (wireLog.length > WIRE_LOG_MAX) wireLog.length = WIRE_LOG_MAX;
        listeners.forEach(fn => { try { fn(entry); } catch (e) { /* ignore listener errors */ } });
    }

    function _delay(kind) {
        const range = LATENCY_MS[kind] || LATENCY_MS.hospital_system;
        const ms = Math.floor(range.min + Math.random() * (range.max - range.min));
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // The shadow stores and federation manifest are bundled into ONE_HR_DATA
    // by the bundler. Look them up at call time.
    function _shadow(siteId) {
        const stores = (window.ONE_HR_DATA && window.ONE_HR_DATA.shadow_stores) || {};
        return stores[siteId] || null;
    }
    function _manifest() {
        return (window.ONE_HR_DATA && window.ONE_HR_DATA.federation_manifest) || null;
    }
    function _siteMeta(siteId) {
        const m = _manifest();
        if (!m) return null;
        return (m.sites || []).find(s => s.id === siteId) || null;
    }

    /**
     * fhirFetch(siteId, resourceType, query)
     *   Simulates a FHIR query against a partner site.
     *
     *   resourceType: "Patient" | "AnimalPatient" | "Encounter" | "Condition"
     *   query:        { id?, subject?, household_id? }
     *
     *   Returns: { ok, resources, latency_ms, status, source_site, target_site, queried_at }
     */
    async function fhirFetch(siteId, resourceType, query) {
        query = query || {};
        const start = performance.now();
        const targetSite = _siteMeta(siteId);
        const targetKind = targetSite ? targetSite.kind : 'hospital_system';
        const sourceSite = (window.OH_AUTH && window.OH_AUTH.getSession())
            ? (window.OH_AUTH.getSession().facility || 'app')
            : 'app';

        // Synthetic latency
        await _delay(targetKind);
        const latency = Math.round(performance.now() - start);

        const store = _shadow(siteId);
        if (!store) {
            const entry = {
                ts: _now(), source: sourceSite, target: targetSite ? targetSite.facility : siteId,
                target_id: siteId, resource: resourceType, query,
                status: 404, ok: false, latency_ms: latency, n_results: 0,
                note: 'Site not in federation manifest',
            };
            _logEntry(entry);
            return { ok: false, resources: [], ...entry };
        }

        // Match resources within the store
        let pool = [];
        if (resourceType === 'Patient')          pool = store.patients || [];
        else if (resourceType === 'AnimalPatient') pool = store.animal_patients || [];
        else if (resourceType === 'Encounter')   pool = store.encounters || [];
        else if (resourceType === 'Condition')   pool = store.conditions || [];
        else pool = [];

        let results = pool;
        if (query.id) {
            results = results.filter(r => r.id === query.id);
        }
        if (query.subject) {
            // subject is a reference like "Patient/abc-123" or just an id
            const refSuffix = query.subject.includes('/') ? query.subject : query.subject;
            results = results.filter(r => {
                const subjRef = (r.subject && r.subject.reference) || '';
                return subjRef.endsWith(refSuffix) || subjRef === refSuffix;
            });
        }
        if (query.household_id) {
            // household_refs only meaningful at the Patient/AnimalPatient layer
            results = results.filter(r => {
                const ext = (r._provenance && r._provenance.household_id) ||
                             (r.extension && (r.extension.find(e => e.url === 'household-id') || {}).valueString) ||
                             null;
                if (ext) return ext === query.household_id;
                // Fallback: find via household_refs in store
                return (store.household_refs || []).indexOf(query.household_id) >= 0;
            });
        }

        const entry = {
            ts: _now(),
            source: sourceSite,
            target: targetSite ? targetSite.facility : siteId,
            target_id: siteId,
            resource: resourceType,
            query,
            status: 200,
            ok: true,
            latency_ms: latency,
            n_results: results.length,
        };
        _logEntry(entry);
        return { ok: true, resources: results, ...entry };
    }

    /**
     * fhirFetchHousehold(householdId)
     *   Convenience: fan out across all sites the household participates in
     *   and return a merged view. This is the canonical "load Maria
     *   Hernandez's household" call.
     */
    async function fhirFetchHousehold(householdId) {
        const m = _manifest();
        if (!m) return { ok: false, error: 'No federation manifest', resources: [] };
        const hhEntry = (m.household_index || []).find(h => h.household_id === householdId);
        if (!hhEntry) return { ok: false, error: 'Household not in manifest', resources: [] };

        const calls = [];
        for (const siteId of hhEntry.participating_sites) {
            calls.push(fhirFetch(siteId, 'Patient', { household_id: householdId }));
            calls.push(fhirFetch(siteId, 'AnimalPatient', { household_id: householdId }));
        }
        const results = await Promise.all(calls);
        const merged = { humans: [], animals: [], wire_calls: results };
        for (const r of results) {
            if (!r.ok) continue;
            if (r.resource === 'Patient') merged.humans.push(...r.resources);
            else if (r.resource === 'AnimalPatient') merged.animals.push(...r.resources);
        }
        return { ok: true, ...merged };
    }

    // Listener registration for the wire-log UI
    function onWireEntry(fn) { listeners.add(fn); return () => listeners.delete(fn); }
    function getWireLog() { return wireLog.slice(); }
    function clearWireLog() { wireLog.length = 0; listeners.forEach(fn => fn(null)); }

    // Per-site stats for the topology view
    function getSiteStats() {
        const m = _manifest();
        if (!m) return [];
        return (m.sites || []).map(s => {
            const store = _shadow(s.id) || {};
            const meta = store._metadata || {};
            return {
                ...s,
                n_patients:        meta.n_patients || 0,
                n_animal_patients: meta.n_animal_patients || 0,
                n_encounters:      meta.n_encounters || 0,
                n_conditions:      meta.n_conditions || 0,
                health: 'green',  // synthetic — all sites green for the demo
            };
        });
    }

    // Aggregate counters for the federation health bar
    function getFederationCounters() {
        const stats = getSiteStats();
        return {
            n_sites:              stats.length,
            n_hospital_systems:   stats.filter(s => s.kind === 'hospital_system').length,
            n_vet_clinics:        stats.filter(s => s.kind === 'vet_clinic').length,
            n_public_health:      stats.filter(s => s.kind === 'public_health').length,
            total_patients:       stats.reduce((a, s) => a + (s.n_patients || 0), 0),
            total_animals:        stats.reduce((a, s) => a + (s.n_animal_patients || 0), 0),
            total_encounters:     stats.reduce((a, s) => a + (s.n_encounters || 0), 0),
            n_calls_logged:       wireLog.length,
        };
    }

    // Public surface
    window.OH_FED = {
        fhirFetch,
        fhirFetchHousehold,
        onWireEntry,
        getWireLog,
        clearWireLog,
        getSiteStats,
        getFederationCounters,
    };
})();
