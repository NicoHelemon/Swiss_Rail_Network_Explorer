# Swiss Rail Delay Lab

An independent, reproducible study of how reported train delays evolve between consecutive recorded calls. Built by an EPFL MSc graduate interested in data science and railway operations. **Not affiliated with SBB or any transport operator.**

V2 uses genuine official **Ist-Daten v2** records. It is a retrospective conditional analysis, not a real-time forecasting system. The original synthetic network explorer remains available at **`/v1`**, with its original code preserved by Git tag **`v1.0.0`**.

## Run the website

Node.js 24 LTS is pinned in `.nvmrc` (minimum 22.12).

```sh
npm ci
npm run dev
```

For production validation:

```sh
npm test
npm run build
npm run preview
```

Vite prints the local address. Build output is `dist/`. The website is React + Vite, plain CSS, locally bundled fonts, lightweight HTML/SVG charts, and a precomputed JSON artifact. No backend, authentication, API key, Python runtime, raw archive download, or browser-side model training is needed for hosting. D3 powers only the legacy network demo.

In restricted cloud machines, use `npm ci --cache /workspace/.cache/npm` if the default home cache is not writable.

## Actual data and results

- Source: [Ist-Daten v2](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2), **opentransportdata.swiss**.
- Operating days: **2026-09-14 through 2026-09-27**.
- Verified public datastore rail exports: **2,478,897 calls** (`PRODUKT_ID=Zug`).
- Eligible sample: **1,794,857 REAL-departure / REAL-arrival paired segments**, 181,728 dated journeys, 1,558 normalized station IDs and 33 reported operators.
- Train: 14–21 September; validation: 22–24; test: 25–27. Whole-journey time-boundary purging removes 9,522 pairs from 945 journeys.
- Test: **375,721 pairs from 38,266 journeys**.

| Method                      | Test MAE (min) | Test RMSE (min) |
| --------------------------- | -------------: | --------------: |
| Zero delay                  |          1.110 |           2.320 |
| Persistence                 |          0.785 |           1.082 |
| Bias-corrected persistence* |          0.646 |           0.917 |
| Ridge                       |          0.335 |           0.612 |
| Histogram gradient boosting |          0.501 |           1.366 |

Ridge was selected on validation MAE among the original four fixed methods. The nonlinear candidate's lower MAE than persistence does not prevent worse RMSE/tail behavior. **The bias-corrected diagnostic was added after the initial test inspection**, using a correction estimated only on training. It did not change or select the original models. Its comparison is exploratory.

Reported delay decreases by at least one minute in 26.9% of eligible pairs and increases by at least one minute in 2.0%. Timetable allowances and measurement conventions can contribute; this is not causal evidence of operational recovery.

The complete [generated results report](docs/results.md) includes signed error, tail errors, uncertainty, failure cases, exclusions and sensitivity counts. The website exposes subgroup comparisons, historical journey examples and source statuses. All displayed figures come from [the committed compact JSON](public/lab-results.json), not mock data.

## What the study can and cannot establish

The archive supplies final daily records, including forecasts and estimates. Only producer-classified **REAL** departure A and REAL arrival B enter the paired sample. REAL is not independent measurement validation.

There are **no publication/ingestion timestamps, revision history or versioned as-of schedules**. The project author explicitly chose a qualified retrospective comparison: given final departure records, can we predict final next-call delay on later operating days? This does not prove those exact features were available at departure A or demonstrate operational deployability.

Journeys are keyed by operating date + operator + journey reference. Calls are ordered by scheduled arrival, falling back to departure. Entire journeys with missing/tied planned ordering are excluded. Calls are sequenced before pair filtering, so missing/unreliable/cancelled/foreign intermediate calls are not silently bridged. The target is the **next recorded call**, not verified physical track adjacency or an independently reconstructed complete GTFS itinerary.

The analysis excludes non-rail product categories, nonnumeric/SLOID-only Swiss station identifiers, cancellations/pass-through calls, contradictory REAL dwell ordering, missing required timestamps, nonpositive scheduled segments, negative observed running times and gross absolute-delay date offsets above 12 hours. Ordinary negative delays and positive tails are retained. All exclusions and alternative delay-bound counts are reported. Some remaining extreme test errors may reflect source/timetable anomalies; no post-test exclusion removes them.

Only two weeks and three test days were studied. Journey-level bootstrap intervals do not fully capture common date/route shocks. Most test traffic uses previously seen stations and segments. Filtering and missing source journeys create selection bias. Neither station associations nor permutation scores establish causes or bottlenecks.

See [data feasibility](docs/data_feasibility.md) and the [research protocol](docs/research_protocol.md). GTFS, service-point references, weather and synthetic observations were **not used**. Longer walk-forward testing, independent schedule checks and prospective publication histories remain future work.

## Reproduce the Python analysis

Use Python 3.12. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r research/requirements.txt
python -m unittest discover -s research -p 'test_*.py'

# Cached files are SHA-256 verified; missing files are acquired in bounded pages.
python -m research.acquire --inventory research/sources-2026-09.json --start 2026-09-14 --end 2026-09-27 --workers 2

POLARS_MAX_THREADS=4 python -m research.prepare data/raw/*-rail.csv
POLARS_MAX_THREADS=4 OMP_NUM_THREADS=4 python -m research.analyze
python -m research.report
npm test
npm run build
```

The raw rail subset is approximately 0.55 GB for these dates; processing does not download all bus/tram records. Two acquisition workers and four compute threads are sufficient. Raw CSVs, intermediate Parquet, audits and full test predictions remain under ignored `data/`. Do not commit them. The frontend result bundle is about 0.2 MB.

`research/sources-2026-09.json` preserves the official resource identifiers. With no `--inventory`, acquisition discovers the current catalogue instead. **Publisher retention may limit fresh historical downloads**; a saved identifier is not a backup. Existing raw caches plus their manifests allow reproduction without relying on new downloads. A cache with a missing/invalid manifest, wrong resource ID, or hash mismatch fails rather than being silently reused.

Every daily acquisition verifies strictly increasing IDs across bounded pages, unchanged maximum rail ID before/after download, an empty page beyond the final offset, date/product/schema consistency, page hashes and the final CSV checksum. This matters: unbounded official exports were observed to end at a 32,000-row boundary with HTTP 200 even though more records existed. Those incomplete extracts were quarantined and superseded; none enter the results. These checks establish completeness of the public datastore rail subset as retrieved, **not equivalence to the original uploaded CSV archive or coverage of all Swiss trains**.

The original uploaded-CSV storage hostname was unavailable through this cloud runtime, so the pipeline uses the **public datastore CSV export linked on each official resource page**, with CKAN's supported rail filter and pagination. The JSON metadata API returned 403; discovery transparently used public catalogue HTML. Direct official hosts needed by this pipeline are `data.opentransportdata.swiss` and `opentransportdata.swiss`; the original storage route is not needed.

Final source provenance, raw and code/config hashes, dependency versions, dates, model parameters and seed are embedded in the generated JSON. Regeneration changes its generation timestamp, but fixed inputs/configuration reproduce cohort counts and deterministic model metrics. The original models/settings were committed in milestone `e467d91` before held-out evaluation. No deep learning, graph measures or target-derived aggregate features are used.

## Tests and checks

- Python unit tests use **explicitly synthetic fixtures only** to test acquisition truncation detection, pagination, missing/bad rows, duplicate/order handling, no bridging of invalid calls, date anomalies, DST ambiguity, chronological purging, feature whitelisting and metric signs. Synthetic fixtures never enter public results.
- Node tests check the V1 graph algorithms and the V2 result artifact: histogram totals, exclusion-funnel conservation, chronological partition counts, equal evaluation populations, validation-only selection, provenance and timestamp-derived journey delays.
- Real Chromium checks exercise V2 controls, grouped metrics, split/model/subgroup selectors, historical journeys, raw-data disclosures, responsive layouts and the retained V1 graph. Automated accessibility checks supplement these tests; they do not prove complete accessibility.

## Deploy on Netlify

`netlify.toml` configures Node 24, build command **`npm run build`**, publish directory **`dist`**, and `/v1` routing. The generated JSON is committed, so **Netlify does not run Python or download research data**.

Connect this GitHub repository to a Netlify project, select branch `main`, leave the base directory empty, and deploy. Subsequent pushes to the connected production branch trigger Netlify's build. No secrets/environment variables are needed for the static site. An authenticated Netlify CLI can alternatively deploy `dist`; do not assume cloud Git access implies Netlify account access.

## Structure

```text
research/
  acquire.py, sources-2026-09.json   Verified official rail acquisition
  audit_source.py                  Public metadata/schema inspection
  prepare.py                       Sequence validation and event pairs
  model.py, config.json             Retrospective evaluation
  analyze.py, report.py             Compact outputs and written report
  requirements.txt, test_*.py       Pinned Python dependencies and tests
public/lab-results.json              Precomputed, source-linked results
src/DelayLab.jsx, src/lab.css         V2 presentation
src/App.jsx, src/components/         Retained V1 schematic explorer
src/data/, src/lib/graph.js          V1 synthetic graph and algorithms
```

Data source and [official terms](https://opentransportdata.swiss/en/terms-of-use/) are cited on the website. Analysis by [NicoHelemon](https://github.com/NicoHelemon). Fonts are bundled under their package OFL licenses. No official SBB branding is used.
