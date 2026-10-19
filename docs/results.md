# Swiss Rail Delay Lab — results

This report is generated from `public/lab-results.json`, the website artifact. Regenerate with `python -m research.report`.

Operating days: **2026-09-14 to 2026-09-27**. Source: [Ist-Daten v2, opentransportdata.swiss](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2). Analysis by NicoHelemon; independent project, not affiliated with SBB or any operator.

Verified public datastore rail exports: **2,478,897 calls**. Eligible sample: **1,794,857 REAL/REAL consecutive-recorded-call pairs**, from 181,728 dated journeys, 1,558 station IDs and 33 operators. This is a selected sample, not a network-wide punctuality measure or a census of Swiss services.

## Descriptive findings

Median next-call arrival delay is 0.517 min; P90 2.333; P99 7.083. Negative delays remain negative.

Reported delay decreases by at least one minute in 26.9% of eligible pairs and increases by at least one minute in 2.0%. Median change is -0.517 min. Timetable allowances, rounded commercial schedules and event conventions can contribute; this does not identify a causal recovery mechanism.

## Chronological evaluation

| Partition | First/last operating day | Pairs | Journeys |
| --- | --- | ---: | ---: |
| train | 2026-09-14 / 2026-09-21 | 1,021,184 | 103,235 |
| validation | 2026-09-22 / 2026-09-24 | 388,430 | 39,282 |
| test | 2026-09-25 / 2026-09-27 | 375,721 | 38,266 |
| purged | 2026-09-21 / 2026-09-24 | 9,522 | 945 |

Whole-journey purging ensures training outcomes precede validation issue times and validation outcomes precede test issue times. Preprocessing is fitted on training only. There is no random row split. Final records have no publication/revision history: this is a **retrospective conditional experiment, not an as-of or real-time backtest**.

### Held-out test results

Errors are in minutes. Mean error = prediction − observation. Every method uses identical test rows.

| Method | MAE | RMSE | Mean error | P90 absolute error | P99 absolute error |
| --- | ---: | ---: | ---: | ---: | ---: |
| Zero delay | 1.109838 | 2.319840 | -0.782132 | 2.316667 | 7.433333 |
| Persistence | 0.785065 | 1.082281 | +0.574160 | 1.666667 | 3.250000 |
| Bias-corrected persistence* | 0.645535 | 0.917438 | +0.004453 | 1.296959 | 2.913626 |
| Ridge | 0.335157 | 0.612281 | -0.001360 | 0.744691 | 2.049769 |
| Histogram gradient boosting | 0.501186 | 1.366136 | +0.002467 | 1.004272 | 2.818444 |

**Ridge** was selected by validation MAE among the original four prespecified methods. The tested nonlinear model has worse test RMSE than persistence despite lower MAE. This describes the tested settings/period, not an inherent ranking of model families.

*Bias-corrected persistence adds the training-only mean change, -0.569708 min. **This diagnostic was added after initial test inspection**, with no change or tuning of the original models. It is exploratory; selection still uses the original candidates. Subsequent subgroup and permutation diagnostics did not change model selection or filtering.

### Uncertainty and generalization

- Ridge minus persistence MAE: -0.449909 min; paired journey-bootstrap 95% interval [-0.452182, -0.447435], 500 replicates.
- Histogram gradient boosting minus persistence MAE: -0.283879 min; paired journey-bootstrap 95% interval [-0.291819, -0.274312], 500 replicates.

The bootstrap retains within-journey dependence, not all common day/route shocks. Only three test days were evaluated; seasonal/disruption robustness is not established. Most test traffic uses previously observed stations/segments. The JSON and website include operator/category/date/segment/departure-delay subgroup counts and metrics.

### Notable failure cases

Largest selected-model errors, retained in the test population:

| Day | Operator/category | Recorded segment | Departure delay | Arrival delay | Prediction | Absolute error |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 2026-09-26 | SBB / NJ | St. Gallen → St. Margrethen SG | 4.117 | 57.767 | -0.339 | 58.106 |
| 2026-09-25 | SBB / NJ | St. Margrethen SG → Zürich HB | 51.383 | -1.533 | 40.952 | 42.486 |
| 2026-09-26 | MBC / R | Bière → Ballens | -39.250 | 1.000 | -36.120 | 37.120 |
| 2026-09-25 | MBC / R | Bière → Ballens | -39.667 | 0.417 | -36.512 | 36.929 |
| 2026-09-25 | SBB / NJ | Zürich HB → Basel SBB | 16.483 | 36.900 | 10.579 | 26.321 |

Some cases have implausibly early departures or large schedule/event reversals. They may reflect source/timetable anomalies as well as operations; they are not classified as confirmed disruption events. No post-test exclusion was introduced to remove these failures. REAL status is not independent measurement validation.

## Data quality

5,628 journeys were excluded for missing/tied planned order or missing identity. There were then 2,188,732 candidate pairs. Sequential exclusions:

| Rule | Excluded | Retained |
| --- | ---: | ---: |
| Both stops have Swiss 7/9-digit numeric IDs | 226,472 | 1,962,260 |
| Neither record is cancelled or pass-through | 57,269 | 1,904,991 |
| No contradictory REAL arrival/departure order within either call | 28,501 | 1,876,490 |
| Departure A and arrival B statuses are both REAL | 73,711 | 1,802,779 |
| Required scheduled and REAL timestamps are present | 0 | 1,802,779 |
| Positive scheduled segment and chronological realized events | 7,703 | 1,795,076 |
| Different normalized stations | 0 | 1,795,076 |
| Absolute delay at most 12 hours: declared date-integrity guard | 219 | 1,794,857 |

Sensitivity counts before the main absolute-delay guard:

| Bound (min) | Retained pairs |
| --- | ---: |
| 60 | 1,794,738 |
| 180 | 1,794,853 |
| 720 | 1,794,857 |
| None | 1,795,076 |

## Limitations and reproducibility

- No event publication/revision history; no operational deployment claim.
- Planned-time ordering of consecutive recorded calls, no explicit sequence index or independent GTFS completeness check.
- Missing journeys, REAL/REAL filtering, numeric Swiss-ID filtering and conservative exclusions can create selection bias.
- Rounded schedules and varying event conventions affect interpretation. Station features can absorb service mix and measurement effects; permutation importance is not causal.
- Initially truncated unbounded exports were quarantined and superseded. The used paginated rail exports have high-water, empty-tail and checksum checks. Equivalence to original uploaded archives is not independently established.
- Raw files and full row-level prediction exports are excluded from Git. Saved resource IDs and daily input hashes are committed in the compact outputs; publisher retention may limit fresh historical downloads.
- Longer walk-forward evaluation, weather/demand features, independent calibration and prospective collection remain future work.

See the README, pinned requirements, `research/config.json`, `research/sources-2026-09.json`, the feasibility report, and the provenance block in the frontend JSON. Original settings were committed before held-out evaluation in milestone `e467d91`.

Artifact generated at 2026-10-19T21:18:46.806702+00:00.
