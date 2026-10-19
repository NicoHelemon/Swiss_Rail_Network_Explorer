# Ist-Daten v2 — feasibility assessment

**Decision: feasible for a qualified retrospective analysis of consecutive recorded rail calls. Not a validated as-of or real-time prediction experiment.**

Updated on 2026-10-19 after reading the current official documentation and downloading actual records. The project author explicitly chose descriptive analysis plus a retrospective model comparison, accepting the publication-time limitation described below. No synthetic observations are included in the analytical dataset. V1 is preserved by the published `v1.0.0` tag.

## Sources actually inspected

- [Ist-Daten v2 catalogue](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2).
- [Current cookbook, English](https://opentransportdata.swiss/en/cookbook/historic-and-statistics-cookbook/actual-data/) and its German counterpart.
- [Official terms](https://opentransportdata.swiss/en/terms-of-use/).
- [14 September 2026 resource detail](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2/resource/2aa700b9-51d0-4b9d-9428-d237c8684181).
- Actual CSV records obtained through the **public CSV datastore export linked on each official resource page**, with the documented CKAN filter `PRODUKT_ID=Zug`.

GTFS, service-point reference data, weather, and any secondary dataset have not been used. Graph measures are not required for this research task.

## Access, archive, and license

The catalogue listed 50 daily resources covering 2026-08-30 through 2026-10-18 at inspection time, with daily updates. Earlier data is linked at `archive.opentransportdata.swiss`, but that archive's contents and retention were not verified. The chosen study interval is **2026-09-14 through 2026-09-27**, two complete operating weeks available in the current catalogue. It avoids the publisher's documented 2026-10-12 disruption (incorrect lines/missing line breaks).

The terms allow obtaining, processing, analyzing, and publishing file-based open data without registration/payment; analyses require source citation and the data user's authorship. This is a source-specific set of terms, not an assumed Creative Commons license. Resource metadata says reference is not required, whereas the general terms request attribution: this project cites the source and terms in either case. The terms also discuss regular raw-data updates. This project publishes an explicitly dated historical study, not a current/raw data service.

Initial requests were blocked by the cloud egress policy. Catalogue/documentation access now works. The JSON metadata API still responds with an upstream HTTP 403, so `research.audit_source` records that response and reads the same resource links from the accessible public HTML catalogue. Missing metadata fields are not invented. Original uploaded CSV links redirect to an additional Cloudflare R2 hostname that remains blocked in the current runtime. No credential is inferred to be missing: file-based data is documented as public.

### A real acquisition defect caught during validation

A large unbounded datastore export returned HTTP 200 and an apparently clean CSV EOF **before the source table ended**. For 2026-09-14 it contained 1,664,000 rows; a public descending-ID query showed the table continued through ID 2,647,493, and an offset query returned row 1,664,001. Many early exports ended on a 32,000-row boundary, the page size in the published CKAN 2.11.5 exporter. The underlying server-side reason is not established. Those partial exports and their derived artifacts were quarantined under ignored `data/*/unverified/` directories. Their preliminary statistics are superseded and are not used for final results.

The corrected acquisition requests **bounded pages of rail records only**, sorted by source `_id`. For each day it verifies:

1. Exact `PRODUKT_ID=Zug` and operating date in every record.
2. A consistent schema and strictly increasing, nonoverlapping record IDs across pages.
3. The highest filtered source ID before and after acquisition is unchanged and matches the final downloaded record.
4. A query beyond the final downloaded row offset is empty.
5. Source-page hashes, final CSV SHA-256, row counts, URLs, and retrieval time are saved. Cached files must pass their hashes before reuse.

This verifies the complete **public datastore rail subset as retrieved**. It does not establish byte equality or full equivalence to the publisher's original uploaded archive, nor does it establish coverage of every Swiss train. CSV normalization and the datastore `_id` field are disclosed. The corrected 2026-09-14 acquisition contains **179,471 rail-call rows**, rather than the 162,330 rail rows in the discarded partial export. After the declared cleaning rules it yields **129,626 eligible adjacent-call pairs**. The full interval's actual counts are generated, not extrapolated from this day.

## Time and status semantics

The cookbook says daily records can contain realized event times **or the last forecast received**; journeys without real-time information may be absent. A nonempty `AN_PROGNOSE` or `AB_PROGNOSE` is not automatically a realized observation.

The actual file and German documentation use these tokens:

| Raw status | Meaning | Main paired analysis |
| --- | --- | --- |
| `REAL` | Effective arrival/departure at a past call | Required for departure A and arrival B |
| `GESCHAETZT` | Plausible estimated actual time | Excluded |
| `PROGNOSE` or blank | Forecast | Excluded |
| `UNBEKANNT` | No known forecast/event at this or preceding calls | Excluded |

The English documentation translates the latter three labels as ESTIMATED, FORECAST, and UNKNOWN. The pipeline retains the literal German source values. Status counts are audited rather than inferred from names. `REAL` is a producer classification, not an independent measurement calibration. Coverage can vary across operators and time.

Scheduled arrival/departure timestamps are minute-rounded. Reported event times may contain seconds or already be rounded by the operator. The full dates are parsed independently of the operating date, so after-midnight calls are not forced onto the operating-day calendar date. Local times are interpreted as Europe/Zurich, consistent with the Swiss display context; the source schema does not explicitly establish timezone semantics for every foreign record. The analytical endpoint filter retains Swiss numeric station IDs; the selected September period has no Swiss DST transition. Ambiguous or nonexistent DST times become null and cannot silently enter valid pairs.

## Journey reconstruction and exclusions

Journey identity is `(BETRIEBSTAG, BETREIBER_ID, FAHRT_BEZEICHNER)`. References are not treated as globally unique across dates. Operator and rail category fields come directly from the source. A rail filter does not include separately classified products such as `Zahnradbahn` or `Metro`; this scope is intentional.

There is **no explicit stop-sequence field**. Calls are ordered by scheduled arrival, falling back to scheduled departure when arrival is absent. Entire journeys with missing identity, missing order times, or tied planned ordering times are excluded. Identical duplicate payloads are removed; repeated station visits at different times are retained. The result is **consecutive recorded calls in planned-time order**, not verified physical track adjacency. No GTFS crosswalk independently establishes that all commercial calls are present.

All candidate rail calls are sequenced **before** pair exclusions. Unreliable/cancelled/pass-through/foreign intermediate calls therefore cannot be removed and silently bridged. Eligible pairs require Swiss 7- or 9-digit numeric BPUIC endpoints, both endpoints not cancelled or pass-through, no contradictory REAL arrival/departure ordering within either call, REAL departure A and arrival B, all required timestamps, a positive scheduled segment, nonnegative realized running time, and different normalized station IDs. For documented 9-digit BPUICs the first seven digits identify the station; SLOID-only identifiers are not guessed into this mapping and are excluded/countable.

The first inspected day exposed events almost 24 hours earlier than the timetable on three journeys. Dates are **not corrected or shifted**. A declared absolute-delay limit of 12 hours excludes such gross date inconsistencies. Sensitivity counts are retained at 60, 180, 720 minutes and without this limit. No negative delays are clipped to zero, and normal positive tails remain in the primary metrics. Every sequential exclusion has a before/excluded/retained count. Extreme examples are retained in the audit files.

## Prediction task and information availability

**Target:** REAL arrival delay at the next eligible consecutive recorded call B, in minutes relative to scheduled arrival. Candidate inputs include final REAL departure delay A, scheduled running time, station identities, category/operator, scheduled hour, and weekday.

The documented and actual schema contains **no event publication timestamp, ingestion timestamp, revision history, or versioned as-of timetable**. Final event values do not prove what was available exactly at departure A. The daily file can also contain retrospectively corrected information. A strict operational historical backtest is therefore **not established** by this dataset alone.

The accepted experiment is conditional and retrospective: do these final-record features predict final next-call delay on later operating days better than persistence? It is not a demonstration of real-time deployability. Training, preprocessing, and model selection use earlier data only. Whole journeys crossing the chronological boundaries are purged, including when realized outcomes cross midnight. No future realized running time, arrival B, or final whole-journey aggregate enters the feature whitelist.

Fixed initial dates: train 14–21 September; validation 22–24 September; test 25–27 September 2026. Settings, metric definitions, bootstrap unit, and seed are recorded in `research/config.json` before held-out evaluation. These two weeks and three held-out days are too short to establish seasonal robustness. Journey-level uncertainty intervals do not fully capture shared day/route shocks.

## Reproducibility and remaining limitations

See [the research protocol](research_protocol.md), exact manifests under ignored `data/audit/`, the pinned Python requirements, and the final generated frontend output. Raw downloads and trained/full row-level artifacts are not committed. Preprocessing outputs carry both raw-input and Parquet hashes. Completeness of exported rail rows must not be confused with representativeness of national railway operations. Filtering REAL/REAL pairs, missing source journeys, conservative sequence exclusions, and omitted SLOID-only records can create selection bias. Station associations are not causal effects; a decrease in reported delay can reflect timetable allowances, timestamp conventions, or measurement differences rather than an identified operational mechanism.

Model performance and full-period findings must be read from the generated results after actual evaluation. No performance is claimed by this feasibility report.
