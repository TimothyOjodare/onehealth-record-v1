/* ============================================================================
 * Phase 8 — Environmental Surveillance dashboard.
 *
 * Renders five live data feeds from public AZ environmental data sources:
 *   1. EPA AirNow — PM2.5 + AQI per station, 30-day history
 *   2. NWS — active heat / dust / fire weather advisories
 *   3. ArboNET — mosquito + tick vector counts per trap, 90-day history
 *   4. USGS — plague-rodent surveillance, flea index per site, 60-day history
 *   5. AGFD — wildlife mortality reports
 *
 * Each feed shows a "Public data — synthetic for demo" attribution.
 * ========================================================================== */

(function () {
    'use strict';

    function renderEnvSurveillance(host) {
        if (!host) return;
        const data = window.ONE_HR_DATA || {};
        const feeds = data.environmental_feeds || null;
        if (!feeds) {
            host.innerHTML = '<div class="empty-state" style="padding: 30px; text-align: center;">Environmental feeds not in bundle.</div>';
            return;
        }
        host.innerHTML = `
            <div class="envsurv-banner">
                <div class="envsurv-banner-icon">🌎</div>
                <div>
                    <h3 style="margin: 0;">Live Arizona environmental health feeds</h3>
                    <p style="margin: 4px 0 0; color: var(--ink-2); font-size: 0.85rem;">
                        Public access · no login required. Feeds aggregated from EPA, NWS, ArboNET, USGS, and AGFD.
                        Critical for One Health early-warning: vector activity, wildlife mortality, air quality, and weather all drive infectious-disease risk in Arizona.
                    </p>
                </div>
            </div>

            <div class="envsurv-grid">
                <div class="envsurv-card envsurv-card-airnow">
                    <div class="envsurv-card-head">
                        <span class="envsurv-source-pill" style="background: #4A6F4D;">EPA AirNow</span>
                        <h3>Air Quality (PM₂.₅ + AQI)</h3>
                    </div>
                    <div id="envsurv-airnow"></div>
                </div>
                <div class="envsurv-card envsurv-card-nws">
                    <div class="envsurv-card-head">
                        <span class="envsurv-source-pill" style="background: #003B5C;">NWS</span>
                        <h3>Active weather advisories</h3>
                    </div>
                    <div id="envsurv-nws"></div>
                </div>
                <div class="envsurv-card envsurv-card-arbonet">
                    <div class="envsurv-card-head">
                        <span class="envsurv-source-pill" style="background: #AB0520;">ArboNET</span>
                        <h3>Vector surveillance (mosquito · tick)</h3>
                    </div>
                    <div id="envsurv-arbonet"></div>
                </div>
                <div class="envsurv-card envsurv-card-usgs">
                    <div class="envsurv-card-head">
                        <span class="envsurv-source-pill" style="background: #7C3F2C;">USGS</span>
                        <h3>Plague-rodent surveillance</h3>
                    </div>
                    <div id="envsurv-usgs"></div>
                </div>
                <div class="envsurv-card envsurv-card-agfd envsurv-card-wide">
                    <div class="envsurv-card-head">
                        <span class="envsurv-source-pill" style="background: #1B4332;">AGFD</span>
                        <h3>Wildlife mortality reports</h3>
                    </div>
                    <div id="envsurv-agfd"></div>
                </div>
            </div>`;
        _renderAirNow(feeds.epa_airnow || []);
        _renderNws(feeds.nws || {});
        _renderArboNet(feeds.arbonet || {});
        _renderUsgs(feeds.usgs_plague || {});
        _renderAgfd(feeds.agfd_wildlife || {});
    }

    function _aqiColor(aqi) {
        if (aqi <= 50) return "#00E400";   // green
        if (aqi <= 100) return "#FFFF00";  // yellow
        if (aqi <= 150) return "#FF7E00";  // orange
        if (aqi <= 200) return "#FF0000";  // red
        if (aqi <= 300) return "#8F3F97";  // purple
        return "#7E0023";                  // maroon
    }

    function _renderAirNow(stations) {
        const el = document.getElementById("envsurv-airnow");
        if (!el) return;
        // Sort by AQI desc to show worst air first
        const sorted = stations.slice().sort((a, b) => (b.latest_reading?.aqi || 0) - (a.latest_reading?.aqi || 0));
        el.innerHTML = `
            <p class="envsurv-blurb">14 EPA AirNow monitoring stations across Arizona. PM₂.₅ &gt; 35 µg/m³ correlates with respiratory ED visits and Coccidioides spore aerosolization risk.</p>
            <table class="audit-log-table envsurv-table">
                <thead><tr>
                    <th>Station</th><th>County</th><th>PM₂.₅ (µg/m³)</th><th>AQI</th><th>Category</th><th>Trend</th>
                </tr></thead>
                <tbody>${sorted.map(s => {
                    const r = s.latest_reading || {};
                    const trend = ({"rising": "↑", "falling": "↓", "stable": "→"})[s.trend] || "—";
                    const trendColor = ({"rising": "var(--cardinal)", "falling": "var(--clinical)", "stable": "var(--ink-3)"})[s.trend] || "var(--ink-3)";
                    return `<tr>
                        <td><strong>${escapeHtml(s.name)}</strong></td>
                        <td>${escapeHtml(s.county)}</td>
                        <td><code>${(r.pm25_ugm3 || 0).toFixed(1)}</code></td>
                        <td><span class="envsurv-aqi-pill" style="background: ${_aqiColor(r.aqi || 0)};">${r.aqi || 0}</span></td>
                        <td>${escapeHtml(r.category || "")}</td>
                        <td style="color: ${trendColor}; font-weight: 600;">${trend} ${escapeHtml(s.trend)}</td>
                    </tr>`;
                }).join("")}</tbody>
            </table>
            <p class="envsurv-cite">${escapeHtml(stations[0]?.data_source || "EPA AirNow")} · <em>${escapeHtml(stations[0]?.data_caveat || "")}</em></p>`;
    }

    function _renderNws(feed) {
        const el = document.getElementById("envsurv-nws");
        if (!el) return;
        const advs = feed.active_advisories || [];
        if (advs.length === 0) {
            el.innerHTML = '<div class="envsurv-empty">No active advisories.</div>';
            return;
        }
        const sevColor = (s) => ({Major: "var(--cardinal)", Moderate: "var(--amber)", Minor: "var(--clinical)"})[s] || "var(--ink-3)";
        el.innerHTML = `
            ${advs.map(a => `
                <div class="envsurv-advisory" style="border-left-color: ${sevColor(a.severity)};">
                    <div class="envsurv-advisory-head">
                        <strong>${escapeHtml(a.type)}</strong>
                        <span class="envsurv-advisory-sev" style="background: ${sevColor(a.severity)};">${escapeHtml(a.severity)}</span>
                    </div>
                    <p class="envsurv-advisory-headline">${escapeHtml(a.headline)}</p>
                    <p class="envsurv-advisory-areas"><strong>Areas:</strong> ${escapeHtml((a.areas || []).join(", "))}</p>
                    <p class="envsurv-advisory-detail">${escapeHtml(a.expected_temps_f || "")}</p>
                    <p class="envsurv-advisory-oh"><strong>One Health relevance:</strong> ${escapeHtml(a.one_health_relevance || "")}</p>
                </div>
            `).join("")}
            <p class="envsurv-cite">${escapeHtml(feed.data_source || "")} · <em>${escapeHtml(feed.data_caveat || "")}</em></p>`;
    }

    function _renderArboNet(feed) {
        const el = document.getElementById("envsurv-arbonet");
        if (!el) return;
        const traps = feed.traps || [];
        el.innerHTML = `
            <p class="envsurv-blurb">${traps.length} surveillance traps across Arizona counties. WNV-positive mosquito pools precede human West Nile cases by 2-6 weeks. The Pinal mosquito anomaly is the cluster signal driving the current alert.</p>
            <table class="audit-log-table envsurv-table">
                <thead><tr>
                    <th>Trap ID</th><th>Kind</th><th>County</th><th>Site</th><th>7-day avg</th><th>WNV+ pools</th><th>Anomaly?</th>
                </tr></thead>
                <tbody>${traps.map(t => `
                    <tr>
                        <td><code>${escapeHtml(t.id)}</code></td>
                        <td>${escapeHtml(t.kind)}</td>
                        <td>${escapeHtml(t.county)}</td>
                        <td>${escapeHtml(t.site)}</td>
                        <td><strong>${(t.avg_7d || 0).toFixed(1)}</strong></td>
                        <td>${t.wnv_positive_pools_7d > 0 ? `<span style="color: var(--cardinal); font-weight: 700;">${t.wnv_positive_pools_7d} +</span>` : "0"}</td>
                        <td>${t.is_anomaly ? '<span class="envsurv-anomaly-pill">⚠ ANOMALY</span>' : '—'}</td>
                    </tr>
                `).join("")}</tbody>
            </table>
            <p class="envsurv-cite">${escapeHtml(feed.data_source || "")} · <em>${escapeHtml(feed.data_caveat || "")}</em></p>`;
    }

    function _renderUsgs(feed) {
        const el = document.getElementById("envsurv-usgs");
        if (!el) return;
        const sites = feed.sites || [];
        const alertColor = (lvl) => ({ALERT: "var(--cardinal)", ELEVATED: "var(--amber)", MONITOR: "var(--clinical)", BASELINE: "var(--ink-3)"})[lvl] || "var(--ink-3)";
        el.innerHTML = `
            <p class="envsurv-blurb">${sites.length} plague-rodent surveillance sites in northern Arizona enzootic zones. Flea index &gt; 0.30 with Y. pestis confirmation triggers ADHS + AGFD coordination. Coyotes and prairie dogs are the primary sentinels.</p>
            <table class="audit-log-table envsurv-table">
                <thead><tr>
                    <th>Site</th><th>County</th><th>Host species</th><th>Flea index</th><th>Y. pestis</th><th>Alert level</th>
                </tr></thead>
                <tbody>${sites.map(s => `
                    <tr>
                        <td><strong>${escapeHtml(s.site)}</strong><br><small style="color: var(--ink-3);">${escapeHtml(s.id)}</small></td>
                        <td>${escapeHtml(s.county)}</td>
                        <td>${escapeHtml(s.host)}</td>
                        <td><code>${(s.latest_flea_index || 0).toFixed(3)}</code></td>
                        <td>${s.ypestis_status === 'positive' ? `<span style="color: var(--cardinal); font-weight: 700;">⚠ POSITIVE</span><br><small>last: ${escapeHtml(s.last_positive_date || '')}</small>` : '<span style="color: var(--clinical);">negative</span>'}</td>
                        <td><span class="envsurv-alert-pill" style="background: ${alertColor(s.alert_level)};">${escapeHtml(s.alert_level)}</span></td>
                    </tr>
                `).join("")}</tbody>
            </table>
            <p class="envsurv-cite">${escapeHtml(feed.data_source || "")} · <em>${escapeHtml(feed.data_caveat || "")}</em></p>`;
    }

    function _renderAgfd(feed) {
        const el = document.getElementById("envsurv-agfd");
        if (!el) return;
        const reports = feed.active_reports || [];
        el.innerHTML = `
            <p class="envsurv-blurb">${reports.length} active wildlife mortality reports under investigation. Plague-positive coyotes and prairie-dog die-offs in Apache-Sitgreaves cross-flagged to USGS. ADHS notified per multi-jurisdictional protocol.</p>
            <div class="envsurv-agfd-list">
                ${reports.map(r => {
                    const isAlert = (r.suspected_cause || "").toLowerCase().includes("plague")
                                  || (r.suspected_cause || "").toLowerCase().includes("west nile")
                                  || (r.suspected_cause || "").toLowerCase().includes("rabies");
                    return `
                    <div class="envsurv-agfd-card ${isAlert ? 'envsurv-agfd-alert' : ''}">
                        <div class="envsurv-agfd-head">
                            <strong>${escapeHtml(r.species)}</strong>
                            <span class="envsurv-agfd-meta">${r.n_dead} dead · ${escapeHtml(r.county)} · ${escapeHtml(r.discovered_date)}</span>
                        </div>
                        <p><strong>Suspected cause:</strong> ${escapeHtml(r.suspected_cause)}</p>
                        <p><strong>Lab status:</strong> ${escapeHtml(r.lab_status)}</p>
                        <p class="envsurv-advisory-oh"><strong>One Health relevance:</strong> ${escapeHtml(r.one_health_relevance)}</p>
                    </div>`;
                }).join("")}
            </div>
            <p class="envsurv-cite">${escapeHtml(feed.data_source || "")} · <em>${escapeHtml(feed.data_caveat || "")}</em></p>`;
    }

    function escapeHtml(s) {
        return String(s == null ? "" : s).replace(/[&<>"']/g,
            c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
    }

    window.OH_ENVSURV = { renderEnvSurveillance };
})();
