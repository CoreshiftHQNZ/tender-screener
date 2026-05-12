# Coreshift Tender Screener

Daily triage of currently-open [NZ GETS](https://www.gets.govt.nz/) tender listings, scored against Coreshift HQ's fit profile.

**Live:** https://coreshifthqnz.github.io/tender-screener/

The screener is a single static HTML page. GitHub Actions runs nightly, scrapes fresh metadata directly from the public GETS listing pages, scores each item, rebuilds the page, and deploys it to GitHub Pages. Stars / dismissals / notes persist in the viewing browser's `localStorage`.

## How it works

```
fetch (scrape gets.govt.nz)  ->  data/raw.json
score (rules)                ->  data/scored.json
build (Jinja)                ->  dist/index.html  ->  GitHub Pages
```

| File | Purpose |
|---|---|
| [screener/fetch.py](screener/fetch.py) | Paginated scrape of `gets.govt.nz/ExternalIndex.htm` → `data/raw.json` |
| [screener/score.py](screener/score.py) | Apply rules + flag new-since-last-run → `data/scored.json` |
| [screener/build.py](screener/build.py) | Render template with embedded data → `dist/index.html` |
| [screener/rules.py](screener/rules.py) | **Scoring rules — edit here to retune** |
| [screener/dates.py](screener/dates.py) | Parse GETS's human-readable close-date format |
| [screener/templates/index.html.j2](screener/templates/index.html.j2) | UI template |
| [.github/workflows/refresh.yml](.github/workflows/refresh.yml) | Nightly cron + deploy |

## Scoring

Score starts at **50** and is adjusted by keyword matches against the tender title. The GETS public listing does not include descriptions, so scoring is metadata-only — strong heuristic, not a verdict. Negative signals (panel procurement, hardware supply, managed service) usually appear in titles; positive signals (prototype / MVP / AI) often don't, so many items sit at 50 with no signal either way. Use the live page to click through anything that looks interesting.

Buckets:

- **80+** strong fit (green)
- **60–79** worth a read
- **40–59** marginal (no signal — title is generic)
- **20–39** weak
- **<20** auto-reject

Contract value isn't published on the GETS listing — value-band scoring from the original brief was dropped.

## Local dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

python -m screener.fetch    # scrape latest from gets.govt.nz -> data/raw.json
python -m screener.score    # rescore (also computes "new since last run")
python -m screener.build    # rebuild dist/index.html
open dist/index.html
```

No credentials required — the GETS public listing is open and the scraper hits only the index page (no per-tender registration).

Re-running fetch + score + build is idempotent on the same day. `score.py` reads the prior `data/scored.json` to flag items whose `rfxId` is new since the last run — so the diff lives in the commit history.

## Tuning the rules

All keyword patterns and weights are in [screener/rules.py](screener/rules.py). Add/remove/reweight `PLUS` and `MINUS` entries — no other file needs to change. Re-run `python -m screener.score && python -m screener.build` to see the effect.

## Deployment

GitHub Actions runs `.github/workflows/refresh.yml` nightly. The workflow:

1. Scrapes the GETS listing
2. Re-scores
3. Rebuilds `dist/index.html`
4. Commits the regenerated `data/*.json` and `dist/index.html` back to `main`
5. Deploys `dist/` to GitHub Pages

To trigger a manual refresh: **Actions → Refresh → Run workflow**.

## Files we deliberately commit

`data/raw.json`, `data/scored.json`, and `dist/index.html` are committed (not gitignored) so the "new since last run" diff and the Pages deployment both have stable inputs.
