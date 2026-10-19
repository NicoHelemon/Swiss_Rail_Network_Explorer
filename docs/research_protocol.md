# Swiss Rail Delay Lab — provisional research protocol

This is a plan for evidence collection, not a description of completed analysis. Dataset-specific choices remain subject to the feasibility gates in [data_feasibility.md](data_feasibility.md). The V2 frontend should be built after source suitability and results are established.

## Provenance and raw data

Keep raw daily files outside Git under `data/raw/`. Record the dataset/resource URL and identifier, service date, retrieval time, original byte count, SHA-256, documentation references, source license, and schema. Do not record credentials. Never overwrite a raw file silently if the publisher revises it: preserve or identify versions by their hashes. Use HTTPS with normal certificate verification. Select resources from metadata rather than inventing download URL patterns.

Investigate one or two actual daily files before committing to a larger interval. The audit sample is deliberately not an analytical sample: the first rows of a file may be ordered by operator, service, or station. Its counts cannot estimate population coverage or missingness.

## Cleaning and sequence audit

Retain original row identities and raw status fields. Record exclusion counts as a sequential funnel, with denominators. Check duplicate keys, operator/journey identifier collisions, repeated stations and loops, missing or non-monotonic stop order, cancellations, and the availability of rail-service labels. Count coverage by day, operator, category, and station before and after filtering. Do not infer network-wide coverage from an operator-specific subset.

Define journey identity only after inspecting documented identifiers. Preserve complete sequences before forming adjacent-stop pairs. Missing or invalid intermediate stops should invalidate the affected adjacent pairs, not turn non-adjacent stops into neighbors. Separate genuine repeated calls at a station from duplicate snapshots. Do not infer chronological stop sequence from names, lexicographic identifiers, or unexplained row order.

Parse schedule and event timestamps using documented date and timezone conventions, including departures after midnight and Europe/Zurich DST transitions. Reject or explicitly resolve ambiguous/nonexistent local times according to source evidence. Preserve signed delays; do not silently replace negative delays with zero. Report extreme and implausible durations before choosing any exclusions, and report sensitivity to those choices.

## Exploratory analysis

Use a small set of useful figures with explicit populations and counts:

- Arrival/departure delay distributions, with quantiles and tails. Make any chart clipping visible and keep metrics on their declared full population.
- Paired change: arrival delay B minus departure delay A, grouped by departure delay and scheduled segment duration. Distinguish recovery from increase; specify any tolerance justified by timestamp precision.
- A limited set of station/segment/category/time-of-day comparisons with minimum sample counts, coverage, and distribution summaries. Discuss selection and measurement differences; do not interpret association as cause.
- Daily measurement-quality and exclusion summaries, including observed/estimated/forecast/unknown proportions only after their semantics are verified.

If comparing scheduled and observed segment durations, show the algebraic relation to delay change. These are not independent confirming measurements.

## Conditional prediction experiment — only if admissible

Target: next-stop arrival delay in minutes. Candidate issue point: observed departure from the previous stop. Finalize wording and operational interpretation after the as-of availability audit.

Candidate features: current departure delay, original scheduled running time, verified station identities, category, day of week, and scheduled time of day. Any previous-delay feature must come from events preceding the issue point, with a documented rule for missing history. Do not use arrival B, realized running time A→B, final maximum journey delay, downstream events, future aggregates, or undocumented forecasts. Keep target columns outside the feature table and whitelist feature names explicitly.

Choose date boundaries before inspecting test performance. For a 14–28 day interval, start with contiguous train/validation/test periods with sufficient full-day coverage; use exact dates in the final report. Assign whole journeys to one partition. Purge boundary-crossing journeys or implement a time embargo so no training outcome occurs after validation/test issue time. Disclose new stations/segments/categories and calendar coverage in later splits.

Fit preprocessing exclusively on training data. Evaluate:

1. Zero delay.
2. Persistence: arrival delay B = departure delay A.
3. Ridge regression with an appropriately fitted categorical/numeric preprocessing pipeline.
4. One simple nonlinear candidate if sample size and resources justify it; compare to persistence and Ridge before adding complexity.

Use validation data to make model decisions. Open the held-out test set once for the declared final comparisons; disclose any subsequent exploratory checks. Do not tune on test subsets.

Report identical evaluation rows for all methods, with missing-feature handling declared. Include MAE, RMSE, signed mean error (`prediction − observation`), MAE difference versus persistence, tail error summaries, and subset counts. Estimate uncertainty with journey- or day-grouped resampling as supported by the interval; do not treat adjacent stops as independent samples. Few held-out days limit day-level uncertainty estimates.

Look at error differences by departure delay, station/segment, service category, time of day, and date when counts permit. Do not present small subsets as robust findings. Prefer held-out grouped permutation checks or ablations to naive feature-importance rankings; associations are not causal explanations.

## Reproducible publication

Store compact, generated frontend outputs with a schema version, input hashes/date range, filtering counts, split dates, model settings, random seed, dependency versions, and generation command. Exclude raw archives, full row-level exports, temporary files, and trained binaries from Git by default. Verify every displayed aggregate against generated outputs. Publish historical observations and model predictions with distinct labels; do not claim real-time functionality.

Keep V1 accessible through a Git tag and, if straightforward, a legacy route. Publish meaningful tested milestones. The main V2 site must present only established results or explicitly state incomplete sections. Until source access and feasibility are resolved, preserve the working V1 deployment.
