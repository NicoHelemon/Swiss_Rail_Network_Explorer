"""Render docs/results.md from the same compact artifact used by the website."""

import json
from pathlib import Path


def write_report(data):
    s, m, q = data['summary'], data['models'], data['quality']
    names = {'zero': 'Zero delay', 'persistence': 'Persistence', 'bias_corrected_persistence': 'Bias-corrected persistence*', 'ridge': 'Ridge', 'hist_gradient_boosting': 'Histogram gradient boosting'}
    rows = ['# Swiss Rail Delay Lab — results', '',
        'This report is generated from `public/lab-results.json`, the website artifact. Regenerate with `python -m research.report`.', '',
        f"Operating days: **{data['coverage']['start']} to {data['coverage']['end']}**. Source: [Ist-Daten v2, opentransportdata.swiss](https://data.opentransportdata.swiss/en/dataset/ist-daten-v2). Analysis by NicoHelemon; independent project, not affiliated with SBB or any operator.", '',
        f"Verified public datastore rail exports: **{q['raw_rail_rows']:,} calls**. Eligible sample: **{s['n']:,} REAL/REAL consecutive-recorded-call pairs**, from {s['journeys']:,} dated journeys, {s['stations']:,} station IDs and {s['operators']} operators. This is a selected sample, not a network-wide punctuality measure or a census of Swiss services.", '',
        '## Descriptive findings', '',
        f"Median next-call arrival delay is {s['arrival_median']:.3f} min; P90 {s['arrival_p90']:.3f}; P99 {s['arrival_p99']:.3f}. Negative delays remain negative.", '',
        f"Reported delay decreases by at least one minute in {100*s['decrease_at_least_1_min']/s['n']:.1f}% of eligible pairs and increases by at least one minute in {100*s['increase_at_least_1_min']/s['n']:.1f}%. Median change is {s['change_median']:.3f} min. Timetable allowances, rounded commercial schedules and event conventions can contribute; this does not identify a causal recovery mechanism.", '',
        '## Chronological evaluation', '',
        '| Partition | First/last operating day | Pairs | Journeys |', '| --- | --- | ---: | ---: |']
    for key in ['train', 'validation', 'test', 'purged']:
        split = m['splits'][key]
        rows.append(f"| {key} | {split['dates'][0]} / {split['dates'][-1]} | {split['n']:,} | {split['journeys']:,} |")
    rows += ['', 'Whole-journey purging ensures training outcomes precede validation issue times and validation outcomes precede test issue times. Preprocessing is fitted on training only. There is no random row split. Final records have no publication/revision history: this is a **retrospective conditional experiment, not an as-of or real-time backtest**.', '',
        '### Held-out test results', '', 'Errors are in minutes. Mean error = prediction − observation. Every method uses identical test rows.', '',
        '| Method | MAE | RMSE | Mean error | P90 absolute error | P99 absolute error |', '| --- | ---: | ---: | ---: | ---: | ---: |']
    for key, row in m['metrics']['test'].items():
        rows.append(f"| {names[key]} | {row['mae']:.6f} | {row['rmse']:.6f} | {row['mean_error']:+.6f} | {row['absolute_error_p90']:.6f} | {row['absolute_error_p99']:.6f} |")
    rows += ['', f"**{names[m['selected_on_validation']]}** was selected by validation MAE among the original four prespecified methods. The tested nonlinear model has worse test RMSE than persistence despite lower MAE. This describes the tested settings/period, not an inherent ranking of model families.", '',
        f"*Bias-corrected persistence adds the training-only mean change, {m['bias_correction_minutes']:+.6f} min. **This diagnostic was added after initial test inspection**, with no change or tuning of the original models. It is exploratory; selection still uses the original candidates. Subsequent subgroup and permutation diagnostics did not change model selection or filtering.", '',
        '### Uncertainty and generalization', '']
    for key, ci in m['intervals'].items():
        rows.append(f"- {names[key]} minus persistence MAE: {ci['difference']:+.6f} min; paired journey-bootstrap 95% interval [{ci['lower_95']:+.6f}, {ci['upper_95']:+.6f}], {ci['replicates']} replicates.")
    rows += ['', 'The bootstrap retains within-journey dependence, not all common day/route shocks. Only three test days were evaluated; seasonal/disruption robustness is not established. Most test traffic uses previously observed stations/segments. The JSON and website include operator/category/date/segment/departure-delay subgroup counts and metrics.', '',
        '### Notable failure cases', '', 'Largest selected-model errors, retained in the test population:', '',
        '| Day | Operator/category | Recorded segment | Departure delay | Arrival delay | Prediction | Absolute error |', '| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for row in m['failure_cases']:
        rows.append(f"| {row['operating_date']} | {row['operator']} / {row['category']} | {row['station']} → {row['next_station']} | {row['departure_delay']:.3f} | {row['arrival_delay']:.3f} | {row['prediction']:.3f} | {row['absolute_error']:.3f} |")
    rows += ['', 'Some cases have implausibly early departures or large schedule/event reversals. They may reflect source/timetable anomalies as well as operations; they are not classified as confirmed disruption events. No post-test exclusion was introduced to remove these failures. REAL status is not independent measurement validation.', '',
        '## Data quality', '', f"{q['ambiguous_journeys_excluded']:,} journeys were excluded for missing/tied planned order or missing identity. There were then {q['consecutive_recorded_pairs']:,} candidate pairs. Sequential exclusions:", '',
        '| Rule | Excluded | Retained |', '| --- | ---: | ---: |']
    for row in q['funnel']:
        rows.append(f"| {row['step']} | {row['excluded']:,} | {row['retained']:,} |")
    rows += ['', 'Sensitivity counts before the main absolute-delay guard:', '', '| Bound (min) | Retained pairs |', '| --- | ---: |']
    for row in q['delay_bound_sensitivity']:
        rows.append(f"| {row['absolute_delay_bound_minutes'] if row['absolute_delay_bound_minutes'] is not None else 'None'} | {row['retained_pairs']:,} |")
    rows += ['', '## Limitations and reproducibility', '',
        '- No event publication/revision history; no operational deployment claim.',
        '- Planned-time ordering of consecutive recorded calls, no explicit sequence index or independent GTFS completeness check.',
        '- Missing journeys, REAL/REAL filtering, numeric Swiss-ID filtering and conservative exclusions can create selection bias.',
        '- Rounded schedules and varying event conventions affect interpretation. Station features can absorb service mix and measurement effects; permutation importance is not causal.',
        '- Initially truncated unbounded exports were quarantined and superseded. The used paginated rail exports have high-water, empty-tail and checksum checks. Equivalence to original uploaded archives is not independently established.',
        '- Raw files and full row-level prediction exports are excluded from Git. Saved resource IDs and daily input hashes are committed in the compact outputs; publisher retention may limit fresh historical downloads.',
        '- Longer walk-forward evaluation, weather/demand features, independent calibration and prospective collection remain future work.', '',
        'See the README, pinned requirements, `research/config.json`, `research/sources-2026-09.json`, the feasibility report, and the provenance block in the frontend JSON. Original settings were committed before held-out evaluation in milestone `e467d91`.', '',
        f"Artifact generated at {data['generated_at_utc']}.", '']
    Path('docs/results.md').write_text('\n'.join(rows))


if __name__ == '__main__':
    write_report(json.loads(Path('public/lab-results.json').read_text()))
