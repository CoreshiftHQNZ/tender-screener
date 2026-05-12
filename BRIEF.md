# Brief: NZ GETS Tender Screener for Coreshift HQ

**Owner:** Ricky (ricky@coreshifthq.com)
**Drafted:** 2026-05-13
**Status:** Handover to Claude Code

---

## 1. Goal

Build a tender screening tool that pulls live tender listings from the New Zealand Government Electronic Tenders Service (GETS), scores each one against Coreshift HQ's "what's worth bidding on" profile, and surfaces a triaged list Ricky can review daily. The user manually reviews the shortlist and asks for deeper analysis on individual tenders.

**Non-goal:** Don't try to fully automate the bid/no-bid decision. The aim is to reduce hundreds of listings to the handful worth a closer look.

## 2. Background

Coreshift HQ is an AI-driven development agency. All development is delivered by Claude Code, so timelines are AI-development-paced, not traditional. The agency wants to identify NZ government RFPs/ROIs/RFTs it has a genuine chance of winning.

A walkthrough of one tender (ACC RFP 104739 — "External Facing BI Reporting Platform") confirmed the screener's value: that RFP looked attractive from its title and contract value, but reading the doc revealed it's a turnkey-SaaS procurement (ACC explicitly says they don't want integration/delivery partners). The screener needs to catch that kind of signal at the indexing layer before time is wasted.

A prototype artifact has already been built showing the desired UX. It's saved alongside this brief at `screener_prototype.html`. **Read it first** — it shows the layout, the scoring rules in JS, and the state model (star/dismiss/notes/flag-for-deep-dive, all persisted in localStorage).

## 3. Architecture (recommended)

Three components, plus a schedule:

```
┌───────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  fetch_gets   │ ───► │   score_items    │ ───► │  build_html     │
│  (Apify API)  │      │  (rules engine)  │      │  (static site)  │
└───────────────┘      └──────────────────┘      └─────────────────┘
        │                                                  │
        ▼                                                  ▼
   data/raw.json                                  dist/index.html
                                                  (open in browser)

  Scheduled nightly via launchd / cron
```

**Why static HTML, not a web app:** The prototype was originally targeted at a Cowork artifact, but Cowork's sandbox blocks direct API calls and there's no Apify MCP available in the registry. A self-contained static HTML file (data embedded at build time) is simpler, has no runtime dependencies, and Ricky can open it in any browser. State (starred, dismissed, notes) persists per-browser in localStorage — that's fine for a one-user tool.

**Optional v2:** Wrap the fetcher + scorer as a small MCP server, then the same data can be exposed to Cowork as live tools. Out of scope for v1.

### Data source

Use the Apify actor `fortuitous_pirate/nz-gets-scraper` (https://apify.com/fortuitous_pirate/nz-gets-scraper). Output schema per the listing:

```json
{
  "rfxId": "ABC-12345",
  "referenceNumber": "LIC-2025-001",
  "title": "...",
  "tenderType": "RFP",
  "organization": "...",
  "closeDate": "2025-01-15",
  "awardDate": "...",
  "supplierName": "...",
  "contractValue": "...",
  "status": "Active"
}
```

Input parameters: `searchType` (`current` for open tenders), `keyword`, `tenderTypes[]`, `organization`, `minValue`, `limit` (default 500).

Pricing: $3 per 1,000 results. A daily full-current pull is ≈$0.001/day.

**Alternative actor** if the primary one underperforms: `helixdatalabs/nz-gets-tenders-api` — same domain, untested but advertised as more API-friendly.

### Apify API endpoint

```
POST https://api.apify.com/v2/acts/fortuitous_pirate~nz-gets-scraper/run-sync-get-dataset-items?token=$APIFY_TOKEN
Content-Type: application/json
{ "searchType": "current", "limit": 500 }
```

### Document enrichment (defer)

The Apify scraper returns metadata only — title, agency, close date, contract value. To do deep fit analysis (the ACC-style "is this actually a SaaS procurement?" check) we'd need the attached RFP documents. The GETS portal gates attachments behind a "register interest" flow per RFP, which is awkward to automate at scale.

**For v1: don't enrich.** Score on metadata alone. Ricky reviews the shortlist manually and copies anything he wants a deep-dive on into a chat with Claude — that's the intended workflow.

**For v2 stretch:** investigate whether the GETS public detail page (`gets.govt.nz/{org}/ExternalTenderDetails.htm?id={rfxId}`) has scrapable descriptions even without "registering interest". If yes, fetch the page text per item and feed it into the scorer.

## 4. Coreshift fit profile (scoring rules)

Port these from `screener_prototype.html` (lines 270–315 in the `RULES` const). Score starts at **50** and is adjusted by keyword matches and contract value.

### Positive signals

| Pattern | Weight | Why |
|---|---|---|
| `mvp \| prototype \| proof of concept \| poc \| discovery` | +22 | Prototype/discovery framing — Coreshift's sweet spot |
| `ai \| machine learning \| llm \| generative` | +18 | AI/ML scope |
| `custom build \| custom development \| bespoke \| agile` | +15 | Custom/agile build language |
| `modernisation \| modernization \| replace.*legacy` | +12 | Legacy modernisation |
| `automation \| automated \| automate` | +12 | Automation scope |
| `dashboard \| visualisation \| visualization \| data viz` | +10 | Dashboard / data viz |
| `web app \| web platform \| web-based \| portal \| microsite` | +10 | Web build |
| `internal tool \| internal tooling \| internal workflow` | +10 | Internal tooling |
| `integration \| api \| integrate with` | +5 | Integration work |

### Negative signals (hard knock-downs)

| Pattern | Weight | Why |
|---|---|---|
| `turnkey.*saas\|product\|solution\|platform` | −45 | Turnkey SaaS product procurement (e.g. ACC 104739) |
| `existing productised\|product\|saas\|solution\|platform` | −45 | Requires existing product |
| `panel agreement \| panel of (approved )?suppliers \| panel refresh` | −40 | Panel procurement |
| `hardware \| supply of \| manufacture \| peripherals \| workstation refresh` | −40 | Physical goods |
| `deployed in N comparable agencies` | −35 | Reference-customer threshold |
| `vendor-managed (saas \| service)` | −30 | Vendor-managed SaaS |
| `security clearance \| top secret \| secret clearance` | −25 | Security clearance |
| `managed service` | −15 | Ops/support contract |
| `itil` | −10 | ITIL framing |
| `iso 27001.*certif` | −10 | Demands existing ISO 27001 |

### Value-band scoring

Apply on top of keyword scoring using midpoint of `contractValueLow` / `contractValueHigh`:

- < $50k → −8 (likely below floor)
- $50k–$250k → +8 (prototype sweet spot)
- $250k–$1M → +12 (build sweet spot)
- $1M–$2.5M → +6 (workable but large)
- $2.5M+ → −4 (incumbent-favoured)
- Not disclosed → 0

Clamp final score to 0–100.

### Bucketing

- 80+ → strong fit (green)
- 60–79 → worth a read
- 40–59 → marginal
- 20–39 → weak
- <20 → auto-reject

These thresholds drive the colour coding in the UI. Calibrate them against a 2-week backtest if anything looks off.

## 5. UI requirements

The prototype HTML at `screener_prototype.html` is the reference design. Match its behaviour:

- Sortable table: ★ (starred), Fit score, Close date (with "X days" urgency hint), Title, Agency, Type, Value, Actions
- Filters: status (active / starred / dismissed / all), agency text search, min-fit slider, hide-closed checkbox
- Click row → expanded panel with: description (when we have it), reason breakdown (which rules fired), notes textarea, "Open in GETS" link, "Flag for deep-dive" button
- localStorage persists: starred IDs, dismissed IDs, expanded panels, notes per ID, current sort
- Light mode only, system font, neutral palette, colour only for urgency/score
- Banner at top: "Last refreshed: {timestamp} · {count} active tenders"

The build step embeds the scored JSON into the HTML as a JS constant. No external data fetch at view time — Cowork artifact sandbox compatibility is preserved if we later port back.

## 6. Files & layout

```
/Users/Ricky/Documents/Claude/Projects/Tenders/
├── BRIEF.md                       ← this doc
├── screener_prototype.html        ← reference UI + scoring rules
├── screener/
│   ├── README.md                  ← run instructions
│   ├── .env.example               ← APIFY_TOKEN=
│   ├── pyproject.toml             ← deps (httpx, jinja2)
│   ├── src/
│   │   ├── fetch.py               ← Apify call → data/raw.json
│   │   ├── score.py               ← rules engine → data/scored.json
│   │   ├── build.py               ← Jinja → dist/index.html
│   │   └── rules.py               ← the scoring rules (single source of truth)
│   ├── templates/
│   │   └── index.html.j2          ← UI template (lift from prototype)
│   ├── data/
│   │   ├── raw.json               ← latest Apify pull
│   │   └── scored.json            ← scored + sorted
│   └── dist/
│       └── index.html             ← what Ricky opens in his browser
└── archive/                       ← per-tender deep-dives go here over time
    └── 2026-05-13_ACC-104739_passed.md   ← already exists in spirit
```

## 7. Setup, dependencies, scheduling

- Python 3.11+
- Deps: `httpx`, `jinja2`, `python-dateutil` (avoid heavy frameworks)
- `APIFY_TOKEN` lives in `screener/.env` (gitignored). **Ricky will provide a fresh token — do not commit the one he pasted in chat; that one will be rotated.**
- Run modes:
  - `python -m screener.fetch` → just refresh raw.json
  - `python -m screener.score` → re-score using current rules
  - `python -m screener.build` → regenerate dist/index.html
  - `make refresh` (or equivalent) → all three
- Schedule via macOS launchd (Ricky is on Mac): nightly at 06:00 NZST. Provide a `screener.plist` template and install instructions in the README.

## 8. Acceptance criteria

A v1 build is done when:

1. `make refresh` (or equivalent) completes in under 60 seconds and produces a `dist/index.html` containing today's open NZ GETS tenders, each scored.
2. Opening `dist/index.html` in a browser shows the table, sortable + filterable, with state persisting between reloads.
3. Re-running the ACC 104739 backtest produces a fit score under 20 (auto-reject bucket). If it doesn't, the rules are wrong — fix them, don't fudge the threshold.
4. README covers: install, configure token, manual run, schedule install, where to edit scoring rules.
5. Scoring rules are isolated in `rules.py` so Ricky (or a future Claude conversation) can tweak weights without touching the rest.

## 9. Stretch / future

- **Deep-dive trigger:** "Flag for deep-dive" button writes a marker file `archive/_pending/{rfxId}.md` with the metadata + GETS link, so Claude (in a future conversation) can pick those up and produce ACC-style writeups on demand.
- **Document enrichment:** automate fetching the GETS public detail page so the description is real, not just the title.
- **Multi-jurisdiction:** the Apify author also publishes scrapers for AusTender (Australia) and others. Same scoring rules, multi-source feed.
- **Cowork MCP:** wrap fetch+score as a small MCP server (Python, FastMCP). Then a Cowork artifact can show the same data live without a rebuild step. Reusable across other Claude clients too.

## 10. Notes & gotchas

- **Apify sandbox blocked from Cowork:** that's why this is being handed off — the bash sandbox in Cowork can't reach api.apify.com or gets.govt.nz. Claude Code on Ricky's local Mac has no such restriction.
- **The ACC RFP** is in `/Users/Ricky/Downloads/RFPID-34053552-ACC-BI/` — a useful regression test case for the scorer. Title alone ("External Facing BI Reporting Platform") wouldn't trip many of the negative rules, but the description excerpt does (turnkey SaaS, no integration partners). When v2 enrichment lands, the description fields should drive the negative scores hard.
- **The token Ricky pasted in chat** (redacted before commit; GitHub secret scanning blocks pushes that contain it) should be considered compromised. He'll rotate it before handing the project to Claude Code. Don't bake it into source.
- **localStorage is per-browser:** if Ricky uses multiple browsers, his starred/dismissed state won't sync. Acceptable for v1. v2 could persist state to a JSON file via a tiny local server.

---

**Suggested first move for Claude Code:** read `screener_prototype.html` end-to-end before writing any new code — the JS already encodes the scoring rules and UI state model. Translate, don't reinvent.
