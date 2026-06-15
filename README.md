# Macro Job Market Papers

A small, automatically refreshed directory of macroeconomics PhD job market candidates at leading US and UK economics departments. Department scope follows IDEAS/RePEc rankings, while candidate and paper information comes from official department pages and candidate websites.

The current scope covers 14 leading US departments selected from IDEAS/RePEc rankings and the top 8 UK university economics departments.

## How it works

- `index.html`, `static/styles.css`, and `static/app.js` form a static GitHub Pages site.
- `scripts/update_data.py` checks official department pages, filters for macro fields, resolves job market paper links, and writes `data/candidates.json`.
- `data/paper_overrides.json` records a small number of verified paper links for sites whose markup does not identify a job market paper reliably.
- `placements.html` and `static/placements.js` show confirmed destinations and pending announcements for every current candidate.
- `scripts/update_placements.py` merges the current candidate list with reviewed records in `data/placement_overrides.json` and writes `data/placements.json`.
- `scripts/update_candidate_details.py` adds reviewed abstract summaries, normalized research topics, and placement types for advanced filtering.
- `.github/workflows/refresh-and-deploy.yml` tests every push and refreshes the data every Monday. GitHub Pages publishes the `main` branch.
- Existing records are retained for one failed refresh, preventing a temporary department outage from emptying the public site.

## Local development

```powershell
py -m pip install -r requirements.txt
py scripts/update_data.py
py scripts/update_placements.py
py scripts/update_candidate_details.py
py -m http.server 8000
```

Open `http://localhost:8000`.

Run tests with:

```powershell
py -m pytest -q
```

## Inclusion rule

A record is published only when:

1. The candidate appears on an official monitored department page.
2. The listed field contains a macroeconomics signal, including international macro, monetary economics, macro-finance, or growth.
3. A job market paper title and working paper link can be resolved.

The rankings are experimental and incomplete, as explained by IDEAS/RePEc. See the [US department ranking](https://ideas.repec.org/top/top.usecondept.html) and [UK institution ranking](https://ideas.repec.org/top/top.uk.html).
