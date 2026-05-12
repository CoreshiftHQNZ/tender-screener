# Coreshift Tender Screener

Daily triage of currently-open [NZ GETS](https://www.gets.govt.nz/) tender listings, scored against Coreshift HQ's fit profile.

**Live:** _populated after first GitHub Pages deploy._

The screener is a single static HTML page. GitHub Actions runs nightly, pulls fresh tender metadata via the Apify NZ GETS scraper, scores each item, rebuilds the page, and deploys it to GitHub Pages. Stars / dismissals / notes persist in the viewing browser's `localStorage`.

## How it works

```
fetch (Apify)  ->  data/raw.json
score (rules)  ->  data/scored.json
build (Jinja)  ->  dist/index.html  ->  GitHub Pages
```

| File | Purpose |
|---|---|
| [screener/fetch.py](screener/fetch.py) | Apify call → `data/raw.json` |
| [screener/score.py](screener/score.py) | Apply rules + flag new-since-last-run → `data/scored.json` |
| [screener/build.py](screener/build.py) | Render template with embedded data → `dist/index.html` |
| [screener/rules.py](screener/rules.py) | **Scoring rules — edit here to retune** |
| [screener/dates.py](screener/dates.py) | Parse GETS's human-readable close-date format |
| [screener/templates/index.html.j2](screener/templates/index.html.j2) | UI template |
| [.github/workflows/refresh.yml](.github/workflows/refresh.yml) | Nightly cron + deploy |

## Scoring

Score starts at **50** and is adjusted by keyword matches against the tender title. The Apify scraper does not return descriptions, so scoring is metadata-only — strong heuristic, not a verdict. Negative signals (panel procurement, hardware supply, managed service) usually appear in titles; positive signals (prototype / MVP / AI) often don't, so many items sit at 50 with no signal either way. Use the live page to click through anything that looks interesting.

Buckets:

- **80+** strong fit (green)
- **60–79** worth a read
- **40–59** marginal (no signal — title is generic)
- **20–39** weak
- **<20** auto-reject

`contractValue` from the scraper is always `0` on the public listing — value-band scoring from the original brief was dropped.

## Local dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cp .env.example .env
# put your APIFY_TOKEN in .env

python -m screener.fetch    # refresh data/raw.json
python -m screener.score    # rescore (also computes "new since last run")
python -m screener.build    # rebuild dist/index.html
open dist/index.html
```

Re-running fetch + score + build is idempotent on the same day. `score.py` reads the prior `data/scored.json` to flag items whose `rfxId` is new since the last run — so the diff lives in the commit history.

## Tuning the rules

All keyword patterns and weights are in [screener/rules.py](screener/rules.py). Add/remove/reweight `PLUS` and `MINUS` entries — no other file needs to change. Re-run `python -m screener.score && python -m screener.build` to see the effect.

## Deployment

GitHub Actions runs `.github/workflows/refresh.yml` nightly. The workflow:

1. Fetches fresh data from Apify (using the `APIFY_TOKEN` repo secret)
2. Re-scores
3. Rebuilds `dist/index.html`
4. Commits the regenerated `data/*.json` and `dist/index.html` back to `main`
5. Deploys `dist/` to GitHub Pages

To trigger a manual refresh: **Actions → Refresh → Run workflow**.

## Files we deliberately commit

`data/raw.json`, `data/scored.json`, and `dist/index.html` are committed (not gitignored) so the "new since last run" diff and the Pages deployment both have stable inputs.
