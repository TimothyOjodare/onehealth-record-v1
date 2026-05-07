# Hosting Guide

The demo is a single-folder static site (`app/`) — no build step, no server, no environment variables. Three free hosting options, in order of how fast you can get a public URL.

---

## Option 1 — Netlify Drop (zero configuration, ~60 seconds)

The fastest path. No account required for a quick share, but a free account makes the URL persistent.

1. Open [https://app.netlify.com/drop](https://app.netlify.com/drop) in your browser.
2. Drag the entire `app/` folder onto the drop zone.
3. Netlify gives you a URL like `https://lucky-meerkat-93f12a.netlify.app/`. Done.

**Persistence.** Without an account, the deployment expires after a few hours. To keep it:

- Sign up for a free Netlify account (GitHub login works).
- After dropping, click "Claim this site" while the success page is still visible.
- The site becomes permanent and gets a friendlier subdomain you can pick yourself, e.g. `one-healthrecord.netlify.app`.

**Custom domain.** Netlify gives you free HTTPS on any custom domain you own. Settings → Domains.

**Cost.** Free tier covers 100 GB bandwidth per month. The demo is ~2 MB, so you'd need ~50,000 monthly visitors to come close.

---

## Option 2 — GitHub Pages (durable, requires repo)

Best if you want the demo and the source side-by-side under one URL.

1. Push the repo to GitHub. Make sure `app/` is at the root.
2. Repository → Settings → Pages.
3. Source: **Deploy from a branch**. Branch: **main**. Folder: **/(root)** *or* **/docs**.
4. If you use root, the demo is at `https://<username>.github.io/<repo>/app/`. If you copy `app/*` into `/docs`, it's at `https://<username>.github.io/<repo>/`.

**Caveats.**

- GitHub Pages serves from the root by default, so you may want to add a tiny `index.html` at the repo root that redirects to `app/index.html`:
  ```html
  <!doctype html>
  <meta http-equiv="refresh" content="0; url=app/index.html">
  ```
- Initial deploy takes 1–2 minutes after the first push. Subsequent updates are usually under 30 seconds.

**Cost.** Free for public repos. Free for private repos on a Pro plan.

---

## Option 3 — Vercel (more polished, slightly more setup)

Best if you anticipate adding any backend in the future (the FastAPI scaffold in `src/api/research_export.py`, for example).

1. Sign up at [https://vercel.com](https://vercel.com), GitHub login.
2. **Import Project** → select the GitHub repo.
3. Framework: **Other**. Root directory: **app**. Build command: leave empty. Output directory: leave empty.
4. Deploy. URL appears in ~30 seconds.

**Why Vercel over Netlify.** Slightly faster cold starts, better preview deploys per commit, and serverless-functions support if you later add the FastAPI backend (Vercel can host Python).

**Cost.** Free tier covers 100 GB bandwidth, unlimited static deployments.

---

## A note on the embedded data

The demo loads its 1.68 MB synthetic bundle from `app/data.js`. All three hosts above will serve this fine — it's a regular JavaScript file. If you want the file to be smaller for slower connections, you can `gzip` it (Netlify and Vercel do this automatically; GitHub Pages does too) and the wire size drops to roughly 350 KB.

---

## Pre-deploy checklist

Before you push the URL to your committee, walk through this once on the deployed site:

- [ ] All seven tabs render: Encounter, Provider Workspace, Map, Graph, Alerts, Evaluation, Architecture.
- [ ] At least one clinician scenario (e.g., Hernandez) populates and highlights entities.
- [ ] At least one vet scenario (e.g., vet_rocco) populates and highlights entities.
- [ ] The map shows all 120 households across the 15 counties.
- [ ] The graph view loads with 694 nodes visible (it may take 2–3 seconds to settle).
- [ ] The alerts tab shows 12 alerts with the Pinal anomaly at the top.
- [ ] The evaluation tab shows the four hero numbers (0.904 / 0.884 / 0.894 / 1.2 ms).
- [ ] The hand-back UI banner appears when you load a scenario with low-confidence extractions.
- [ ] No console errors in the browser developer tools.

---

## Recommended URL handoff

For the committee:

> **Live demo:** *(your URL)*
> **Source:** *(GitHub repo URL)*
> **Slide deck:** [link to docs/ONE-HealthRecord_Capstone.pdf]
> **Model card:** [link to docs/model_card.md]
> **Evaluation report:** [link to docs/evaluation_report.md]

Add this paragraph to the bottom of the slide-14 footer if you decide to deploy before the in-person presentation — that way committee members can re-explore the demo on their own laptops afterwards.
