# Ist-Daten v2 — feasibility assessment

**Status: blocked before source inspection; prediction feasibility is not established.**

Assessment attempted on 2026-10-19. No official observations have been downloaded or analyzed. No model has been fitted. V1 remains the main application and continues to label its network as synthetic. This document is a checkpoint, not a completed feasibility report.

## What was actually verified

- The existing React/Vite project is committed at `7c056cf7ec7f3eaf2c711eb4a6de3bd3568dbd9e`. The local `v1.0.0` tag preserves that version. No application code or hosting configuration has been changed for V2.
- HTTPS requests to the Ist-Daten v2 dataset page and CKAN metadata endpoint were rejected by the environment's egress proxy. The response was `403 Forbidden` from `envoy`, with `CONNECT tunnel failed` for the API. This happens before reaching the source server; it is **not evidence that the dataset needs credentials or is unavailable**.
- The environment's saved network policy was restricted, with package-manager presets and no custom allowed domains. A draft now adds `data.opentransportdata.swiss`, `opentransportdata.swiss`, and `swissrailnetworkexplorer.netlify.app`. Saving a draft does not apply runtime access or publish an environment.
- The Netlify site cannot currently be reached through this environment either. No Netlify authentication binding or local CLI configuration was present in the prior setup. Deployment and deployed-site validation are not complete.

## Candidate official sources — not yet read

- [Ist-Daten v2](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2)
- [Dataset metadata API](https://data.opentransportdata.swiss/api/3/action/package_show?id=ist-daten-v2)
- [GTFS timetable documentation](https://opentransportdata.swiss/en/cookbook/timetable-cookbook/gtfs/)
- [Service points v2](https://data.opentransportdata.swiss/en/dataset/service-point-v2)

The source names and URLs come from the project brief. Their current schemas, licensing, update frequency, archive dates, record semantics, and observation coverage have **not** been independently verified. No license or redistribution permission is assumed. No secondary copy or synthetic replacement has been used.

## Questions that must be resolved from documentation AND actual files

| Question | Evidence required | Current finding |
| --- | --- | --- |
| Historical coverage and downloads | Resource inventory, dates, formats, sizes, update timestamps | Not inspected |
| License and attribution | Dataset-specific license and applicable terms | Not inspected |
| Scheduled versus observed timestamps | Field definitions and sampled records | Not inspected |
| REAL / ESTIMATED / FORECAST / UNKNOWN | Exact official definitions, counts, missingness, examples | Meanings not assumed |
| Prediction-time availability | Event publication/ingestion timestamps, revision policy, archival snapshot semantics | Unknown; critical validity question |
| Rail-service identification | Official category/product definitions and sample values | Not inspected |
| Journey identity | Documented identifiers scoped by operating date/operator as appropriate, collision audit | Not inspected |
| Successive stops | Reliable sequence field or demonstrably unambiguous ordering; gaps, loops, and duplicate events | Not inspected |
| Station identity | Station/service-point identifiers and platform grouping semantics | Not inspected |
| Cancellations and non-commercial stops | Flags and treatment in archive | Not inspected |
| Overnight and DST events | Operating date versus actual calendar date; time-zone semantics | Not inspected |
| Timetable revisions | Which scheduled times are preserved and when they became known | Not inspected |

## Prediction feasibility gates

The proposed target is arrival delay at the next recorded, verified successive stop B, measured relative to the source's documented scheduled arrival. The prediction issue time would be the observed departure from stop A. Both the meaning of “observed” and the completeness of stop succession need evidence before this definition can be finalized.

1. **Measurement:** reliable realized departure A and arrival B can be distinguished from estimates, forecasts, missing values, and cancellations. Do not classify a value as realized just because a timestamp exists.
2. **Sequence:** A and B belong to one journey and are successive eligible stops in an explicitly defined sequence. Do not drop invalid intermediate rows and silently join across them.
3. **Timing:** departure A is no later than arrival B, with documented time-zone, operating-day, and overnight handling. Ties or inconsistent order must be audited, not arbitrarily resolved.
4. **Information availability:** every feature must have been known at prediction issue time. A final daily archive may contain retrospectively corrected observations and forecasts. A final observed event timestamp alone does not establish when that value was published or revised.
5. **Separation:** entire journeys belong to one chronological partition; all outcomes used in training must precede the validation issue period. Preprocessing and any historical aggregates must be fitted from training history only.

If final observations are available but their as-of availability cannot be established, **do not advertise a deployment-realistic historical prediction experiment**. A clearly qualified retrospective conditional analysis may be possible, but that changes the interpretation and needs a user decision after the source is inspected. If reliable successive observations themselves cannot be reconstructed, prefer a narrower descriptive analysis. If observations cannot support even that, explain the limitation rather than publishing fabricated results.

## Next executable steps

1. Apply the saved network domains in environment settings; save and publish as requested by the product. Then retry the actual metadata request. Additional official download hosts will be added only if discovered in source metadata.
2. Run `python research/audit_source.py metadata --output data/audit/ist-daten-v2.json` to retain a compact resource inventory and retrieval timestamp. This command has been tested for its current blocked-access outcome and against explicitly synthetic parser fixtures; a successful live metadata retrieval is **not yet verified**.
3. Read current official documentation and terms. Choose one or two reasonably sized daily resources from the actual inventory; do not download a month first. The audit tool's `sample` command requires an explicit resource ID and enforces a byte budget.
4. Inspect the actual header, timestamp/status values, cancellations, and journey sequences. Replace this provisional report with source-backed findings and measured quality counts.
5. Select a reproducible complete historical interval (initially 14–28 days if suitable), establish the admissible prediction task, and proceed to the [research protocol](research_protocol.md).

No scientific phase is marked complete at this checkpoint. Neither source access nor prediction feasibility can be inferred from the presence of an audit script.
