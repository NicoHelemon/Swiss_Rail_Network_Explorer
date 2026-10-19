# Ist-Daten v2 — feasibility assessment

**Status: official catalogue/documentation inspected; raw-file access still blocked; prediction feasibility is not established.**

Assessment updated on 2026-10-19 after the initial network settings were applied. Official pages are now accessible. No official observation file has been downloaded or analyzed and no model has been fitted. Documentation examples are not treated as downloaded observations. V1 remains the main application and continues to label its network as synthetic. This document is a checkpoint, not a completed feasibility report.

## What was actually verified

- The existing React/Vite project is committed at `7c056cf7ec7f3eaf2c711eb4a6de3bd3568dbd9e`. The published `v1.0.0` tag preserves that version. No application code or hosting configuration has been changed for V2.
- Initially, requests were rejected before reaching the source (`CONNECT tunnel failed`, proxy HTTP 403). After the first three domains were enabled, the catalogue, current cookbook, terms, and resource-detail page returned HTTP 200. The public CKAN JSON API still returns an upstream HTTP 403; this must not be confused with the original network denial. The audit command can now use the public HTML catalogue instead, explicitly reporting the metadata format and missing fields.
- The catalogue lists daily CSV resources from **2026-08-30 through 2026-10-18** at inspection time and states a daily update interval. It links an archive for earlier periods; archive contents and retention are not yet verified.
- The catalogue warns of a production disruption on **2026-10-12**, with incorrect lines/missing line breaks. Avoid silently treating that day as ordinary data. A potential initial interval is 2026-09-14 through 2026-09-27, subject to actual file inspection, coverage, and quality checks.
- The resource page for **2026-09-14** reports a **641.2 MB CSV**, data updated on 2026-09-15 at 05:11:40 +0200. This is metadata, not a locally verified file size. Resource ID: `2aa700b9-51d0-4b9d-9428-d237c8684181`. Do not download full weeks before testing small samples and a streaming approach.
- A HEAD request to the official download URL returns HTTP 302 to **`83025b28472d6aa2bf5ae59f3724aa78.eu.r2.cloudflarestorage.com`**. Downloading the proposed first 2 MiB failed before any CSV bytes were saved. This newly discovered storage host has been added to the configuration draft alongside the original three domains; runtime access remains to be applied/tested. Signed download URLs expire after 60 seconds according to their redirect parameters; the stable catalogue URL should be used, and signed query parameters must not be persisted.
- No Netlify deployment or deployed-site validation has been completed for V2. The existing `main` branch and V1 app remain unchanged.

## Official sources read

- [Ist-Daten v2](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2)
- [Dataset metadata API](https://data.opentransportdata.swiss/api/3/action/package_show?id=ist-daten-v2)
- [Current actual-data cookbook](https://opentransportdata.swiss/en/cookbook/historic-and-statistics-cookbook/actual-data/) — English and German versions inspected.
- [Official terms](https://opentransportdata.swiss/en/terms-of-use/) — file-based data requires no registration/payment, processed analyses may be published, source URL must be cited, and analysis authorship belongs to the data user. These are source-specific terms, not an assumed CC license. Resource metadata says “Reference Not Required”, while the general terms request attribution: cite both the source and applicable terms anyway. The terms also discuss regular raw-data updates; historical frozen analyses must be explicitly dated and must not masquerade as a current data service.
- [2026-09-14 resource detail](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2/resource/2aa700b9-51d0-4b9d-9428-d237c8684181)

GTFS and service-point datasets from the brief have not yet been inspected or used. No secondary copy or synthetic replacement has been used.

## Documented semantics and validity warnings

The cookbook explicitly says daily files mix effective event times with the last forecast received; journeys without real-time information may be absent. Consequently, timestamps in a column named `AN_PROGNOSE` or `AB_PROGNOSE` are not automatically realized observations.

The German schema lists raw status tokens `REAL` (effective event), `GESCHAETZT` (plausible estimated event), `PROGNOSE` or blank (forecast), and `UNBEKANNT` (no known forecast/event at this or preceding stops). The English page translates the latter tokens as ESTIMATED/FORECAST/UNKNOWN. Actual file tokens still need inspection; do not assume translated labels occur in the CSV. The cookbook explains that SBB/BLS/SOB normal-gauge records can contain control-system-derived estimates and latest forecasts. A REAL-only subset could therefore have substantial operator/route selection bias.

The documented fields include operating date, journey reference, operator, product type, category/line text, cancellation/additional-service/pass-through flags, BPUIC, SLOID, and scheduled and forecast/event timestamps with their statuses. Scheduled times are minute-rounded, while event values may have seconds (or already be rounded by the operator). Full timestamp dates can differ from the operating date. The schema does **not document event publication timestamps, ingestion timestamps, revision history, or a stop-sequence index**. Journey ordering and information availability cannot be taken for granted.

Version 2 explicitly allows foreign stops and 7-/9-digit BPUICs or SLOID-like identifiers. A later, evidently older section of the same cookbook still describes Swiss-only/truncated journeys. Treat the V2-specific notes as the current stated coverage, and test actual identifiers and journey boundaries; this documentation inconsistency must remain visible.

## Questions that must be resolved from documentation AND actual files

| Question | Evidence required | Current finding |
| --- | --- | --- |
| Historical coverage and downloads | Resource inventory, dates, formats, sizes, update timestamps | Catalogue/resource pages inspected; file bodies pending |
| License and attribution | Dataset-specific license and applicable terms | Terms and resource metadata read; source citation retained |
| Scheduled versus observed timestamps | Field definitions and sampled records | Documentation distinguishes them; file-level quality unknown |
| REAL / ESTIMATED / FORECAST / UNKNOWN | Exact official definitions, counts, missingness, examples | Documented definitions read; actual tokens/counts pending |
| Prediction-time availability | Event publication/ingestion timestamps, revision policy, archival snapshot semantics | Not present in documented schema; critical limitation |
| Rail-service identification | Official category/product definitions and sample values | Product field documented; actual values pending |
| Journey identity | Documented identifiers scoped by operating date/operator as appropriate, collision audit | Journey reference documented; uniqueness needs data |
| Successive stops | Reliable sequence field or demonstrably unambiguous ordering; gaps, loops, and duplicate events | No sequence field documented; reconstruction must be tested |
| Station identity | Station/service-point identifiers and platform grouping semantics | V2 identifier variations documented; mappings untested |
| Cancellations and non-commercial stops | Flags and treatment in archive | Flags documented; actual representation pending |
| Overnight and DST events | Operating date versus actual calendar date; time-zone semantics | Full dates documented; explicit timezone/revision rules need verification |
| Timetable revisions | Which scheduled times are preserved and when they became known | As-of schedule availability is not established |

## Prediction feasibility gates

The proposed target is arrival delay at the next recorded, verified successive stop B, measured relative to the source's documented scheduled arrival. The prediction issue time would be the observed departure from stop A. Both the meaning of “observed” and the completeness of stop succession need evidence before this definition can be finalized.

1. **Measurement:** reliable realized departure A and arrival B can be distinguished from estimates, forecasts, missing values, and cancellations. Do not classify a value as realized just because a timestamp exists.
2. **Sequence:** A and B belong to one journey and are successive eligible stops in an explicitly defined sequence. Do not drop invalid intermediate rows and silently join across them.
3. **Timing:** departure A is no later than arrival B, with documented time-zone, operating-day, and overnight handling. Ties or inconsistent order must be audited, not arbitrarily resolved.
4. **Information availability:** every feature must have been known at prediction issue time. A final daily archive may contain retrospectively corrected observations and forecasts. A final observed event timestamp alone does not establish when that value was published or revised.
5. **Separation:** entire journeys belong to one chronological partition; all outcomes used in training must precede the validation issue period. Preprocessing and any historical aggregates must be fitted from training history only.

If final observations are available but their as-of availability cannot be established, **do not advertise a deployment-realistic historical prediction experiment**. A clearly qualified retrospective conditional analysis may be possible, but that changes the interpretation and needs a user decision after the source is inspected. If reliable successive observations themselves cannot be reconstructed, prefer a narrower descriptive analysis. If observations cannot support even that, explain the limitation rather than publishing fabricated results.

## Next executable steps

1. Apply the newly saved exact Cloudflare storage domain in environment settings; save and publish as requested by the product. Do not replace the three domains already working. Recheck the official download route after that state change.
2. Run `python research/audit_source.py metadata --output data/audit/ist-daten-v2.json` to retain a compact inventory. It records the denied JSON API and obtains CSV links from the accessible public catalogue. Missing HTML metadata fields remain null rather than invented.
3. Retrieve a small bounded prefix before any complete daily file. The current `sample` command downloads a whole resource up to a hard byte budget, so its default 64 MiB limit intentionally cannot download the 641.2 MB resource. Implement/test a bounded streaming sample and then complete-file streaming if justified; do not merely raise all budgets and fetch two weeks into memory.
4. Inspect the actual header, timestamp/status values, cancellations, and journey sequences. Replace this provisional report with source-backed findings and measured quality counts.
5. Select a reproducible complete historical interval (initially 14–28 days if suitable), establish the admissible prediction task, and proceed to the [research protocol](research_protocol.md).

No scientific phase is marked complete at this checkpoint. Neither source access nor prediction feasibility can be inferred from the presence of an audit script.
