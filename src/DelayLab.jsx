import { useEffect, useState } from "react";
import "./lab.css";

const REPO = "https://github.com/NicoHelemon/Swiss_Rail_Network_Explorer";
const MODEL_NAMES = {
  zero: "Zero delay",
  persistence: "Persistence",
  bias_corrected_persistence: "Bias-corrected persistence*",
  ridge: "Ridge regression",
  hist_gradient_boosting: "Histogram gradient boosting",
};
const number = (value, digits = 0) =>
  new Intl.NumberFormat("en-GB", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
const signed = (value, digits = 3) =>
  `${value > 0 ? "+" : ""}${number(value, digits)}`;
const percent = (a, b) => `${number((100 * a) / b, 1)}%`;

function Bars({
  rows,
  total,
  unit = "",
  valueDigits = 2,
  color = "red",
  label,
}) {
  const values = rows.map((row) => row.value);
  const low = Math.min(0, ...values),
    high = Math.max(0.001, ...values);
  const span = high - low,
    zero = (-low / span) * 100;
  return (
    <div className={`lab-bars ${color}`} role="group" aria-label={label}>
      {rows.map((row, i) => (
        <div className="lab-bar-row" key={`${row.label}-${i}`}>
          <span className="lab-bar-label" title={row.label}>
            {row.label}
          </span>
          <div className="lab-bar-track">
            <i className="lab-bar-zero" style={{ left: `${zero}%` }} />
            <span
              className="lab-bar-fill"
              style={{
                left: `${((Math.min(0, row.value) - low) / span) * 100}%`,
                width: `${(Math.abs(row.value) / span) * 100}%`,
              }}
            />
          </div>
          <span className="lab-bar-number" data-value={row.value}>
            {total
              ? percent(row.value, total)
              : `${number(row.value, valueDigits)}${unit}`}
          </span>
        </div>
      ))}
      <details className="lab-values">
        <summary>Show chart values</summary>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Group</th>
                <th>{total ? "Count" : "Value"}</th>
                {total && <th>Share</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  <th>{row.label}</th>
                  <td>{number(row.value, total ? 0 : valueDigits)}</td>
                  {total && <td>{percent(row.value, total)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

function Section({ id, index, title, intro, children }) {
  return (
    <section id={id} className="lab-section" aria-labelledby={`${id}-title`}>
      <div className="lab-section-heading">
        <span>{index}</span>
        <h2 id={`${id}-title`}>{title}</h2>
      </div>
      {intro && <p className="lab-section-intro">{intro}</p>}
      {children}
    </section>
  );
}

function Comparison({ data }) {
  const [dimension, setDimension] = useState("category");
  const [metric, setMetric] = useState("median");
  let rows;
  if (dimension === "station")
    rows = data.stations
      .slice(0, 15)
      .map((row) => ({ label: row.name, value: row[metric], n: row.n }));
  else
    rows = data.breakdowns[dimension]
      .slice()
      .sort(
        dimension === "hour"
          ? (a, b) => a.value - b.value
          : (a, b) => b.n - a.n,
      )
      .slice(0, dimension === "hour" ? 24 : 15)
      .map((row) => ({
        label:
          dimension === "hour"
            ? `${String(row.value).padStart(2, "0")}:00`
            : String(row.value),
        value: row[metric],
        n: row.n,
      }));
  return (
    <article className="lab-card">
      <div className="lab-card-heading">
        <div>
          <h3>Arrival delay by group</h3>
          <p>Minutes, conditional on eligible consecutive-call pairs.</p>
        </div>
        <div className="lab-controls">
          <label>
            Group
            <select
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
              aria-label="Analysis grouping"
            >
              <option value="category">Train category</option>
              <option value="station">Arrival station</option>
              <option value="operator">Operator</option>
              <option value="hour">Scheduled departure hour</option>
            </select>
          </label>
          <label>
            Statistic
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              aria-label="Delay statistic"
            >
              <option value="median">Median</option>
              <option value="mean">Mean</option>
              <option value="p90">90th percentile</option>
            </select>
          </label>
        </div>
      </div>
      <Bars rows={rows} unit=" min" label="Grouped arrival delay" color="ink" />
      <p className="lab-caption">
        {dimension === "station"
          ? "15 most observed arrival stations, each with at least 500 eligible pairs."
          : dimension === "hour"
            ? "Scheduled departure hour in Europe/Zurich; groups with at least 200 pairs."
            : "Most observed groups, each with at least 200 eligible pairs."}{" "}
        Differences reflect service mix and measurement/selection effects; they
        do not identify a station or operator as a cause.
      </p>
      <details>
        <summary>Group sample sizes</summary>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Group</th>
                <th>Eligible pairs</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  <th>{row.label}</th>
                  <td>{number(row.n)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </article>
  );
}

function Prediction({ data }) {
  const model = data.models,
    selected = model.selected_on_validation;
  const [split, setSplit] = useState("test");
  const [errorModel, setErrorModel] = useState(selected);
  const [subset, setSubset] = useState("operating_date");
  const metrics = model.metrics[split];
  const interval = model.intervals[selected];
  return (
    <>
      <div className="lab-note">
        <strong>A retrospective conditional experiment.</strong> Final REAL
        departure records are used to predict final next-call arrival delay. The
        archive does not establish when values were published or revised, so
        this is not a real-time or as-of backtest.
      </div>
      <div className="lab-split-grid">
        {["train", "validation", "test"].map((name) => (
          <div key={name}>
            <span>{name}</span>
            <strong>
              {model.splits[name].dates[0]} → {model.splits[name].dates.at(-1)}
            </strong>
            <p>
              {number(model.splits[name].n)} pairs ·{" "}
              {number(model.splits[name].journeys)} journeys
            </p>
          </div>
        ))}
      </div>
      <p className="lab-caption">
        Whole journeys stay together. {number(model.splits.purged.journeys)}{" "}
        boundary-crossing journeys ({number(model.splits.purged.n)} pairs) were
        purged so training outcomes precede validation issue times, and
        validation outcomes precede test issue times.
      </p>
      <article className="lab-card">
        <div className="lab-card-heading">
          <div>
            <h3>Model comparison</h3>
            <p>
              Errors in minutes. Lower MAE and RMSE are better. Mean error =
              prediction − observation.
            </p>
          </div>
          <label className="lab-select-label">
            Evaluation period
            <select
              value={split}
              onChange={(e) => setSplit(e.target.value)}
              aria-label="Evaluation split"
            >
              <option value="test">Held-out test</option>
              <option value="validation">Validation</option>
              <option value="train">Training (in-sample)</option>
            </select>
          </label>
        </div>
        <div className="lab-table-scroll">
          <table className="lab-model-table">
            <caption>
              {split === "test"
                ? "Held-out test"
                : split === "train"
                  ? "In-sample training"
                  : "Validation"}{" "}
              · {number(model.splits[split].n)} identical evaluation rows for
              every method
            </caption>
            <thead>
              <tr>
                <th>Method</th>
                <th>MAE</th>
                <th>RMSE</th>
                <th>Mean error</th>
                <th>Δ MAE vs persistence</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(metrics).map(([key, row]) => (
                <tr
                  key={key}
                  className={key === selected ? "lab-selected-row" : ""}
                >
                  <th>
                    {MODEL_NAMES[key]}
                    {key === selected && (
                      <small>Selected on validation MAE</small>
                    )}
                  </th>
                  <td data-metric={`${split}-${key}-mae`}>
                    {number(row.mae, 3)}
                  </td>
                  <td>{number(row.rmse, 3)}</td>
                  <td>{signed(row.mean_error)}</td>
                  <td>{signed(row.mae - metrics.persistence.mae)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lab-caption">
          Zero predicts 0. Persistence copies departure delay A. Ridge uses
          scaled numeric features and training-fitted one-hot
          station/category/operator encodings. The nonlinear candidate uses
          training-fitted categorical encodings. Fixed settings are documented
          in the repository; preprocessing is fitted on training only.
        </p>
        <p className="lab-caption">
          <strong>* Additional diagnostic:</strong> corrected persistence adds{" "}
          {signed(model.bias_correction_minutes, 3)} min, the mean
          arrival-minus-departure delay from training. It was added after the
          initial test inspection and did not select or alter the original
          models. Its comparison is exploratory.
        </p>
      </article>
      {interval && (
        <div className="lab-finding">
          <strong>
            {MODEL_NAMES[selected]} was selected on validation MAE.
          </strong>
          <p>
            On the test period, its MAE difference from persistence is{" "}
            {signed(interval.difference)} min; the 95% paired journey-bootstrap
            interval is [{signed(interval.lower_95)},{" "}
            {signed(interval.upper_95)}] min. Negative means lower error. This
            interval retains within-journey dependence but not all shared
            day/route shocks; three test days are not evidence of seasonal
            robustness.
          </p>
        </div>
      )}
      <div className="lab-two-column">
        <article className="lab-card">
          <div className="lab-card-heading">
            <div>
              <h3>Test error distribution</h3>
              <p>Signed error, prediction − observation, in minutes.</p>
            </div>
          </div>
          <label className="lab-select-label">
            Method
            <select
              value={errorModel}
              onChange={(e) => setErrorModel(e.target.value)}
              aria-label="Error distribution model"
            >
              {Object.keys(model.error_histograms).map((key) => (
                <option key={key} value={key}>
                  {MODEL_NAMES[key]}
                </option>
              ))}
            </select>
          </label>
          <Bars
            rows={model.error_histograms[errorModel].map((row) => ({
              label: row.label,
              value: row.n,
            }))}
            total={model.splits.test.n}
            label="Test prediction error distribution"
          />
        </article>
        <article className="lab-card">
          <h3>Predictive dependence, not explanation</h3>
          <p className="lab-caption">
            A single exploratory permutation check on{" "}
            {number(model.permutation_importance[0]?.sample_n || 0)} sampled
            test rows. The increase in MAE when a feature is shuffled indicates
            dependence of the selected model on that input. Correlation,
            implausible shuffled combinations, and service-specific measurement
            conventions affect interpretation. These are not causal effects.
          </p>
          <Bars
            rows={model.permutation_importance.map((row) => ({
              label: row.feature.replaceAll("_", " "),
              value: row.mae_increase,
            }))}
            unit=" min"
            label="Exploratory permutation dependence"
            color="ink"
          />
          <p className="lab-caption">
            Test rows with an unseen arrival-station ID:{" "}
            {number(model.unseen_test_values_row_counts.next_station_id)}.
            Unseen station-pair segments:{" "}
            {number(model.unseen_test_values_row_counts.segment)}. Most test
            traffic uses previously seen stations/segments.
          </p>
        </article>
      </div>
      <article className="lab-card">
        <div className="lab-card-heading">
          <div>
            <h3>Where does the comparison change?</h3>
            <p>Test subsets; no model is tuned from these comparisons.</p>
          </div>
          <label className="lab-select-label">
            Breakdown
            <select
              value={subset}
              onChange={(e) => setSubset(e.target.value)}
              aria-label="Prediction subgroup"
            >
              <option value="operating_date">Operating date</option>
              <option value="category">Category</option>
              <option value="operator">Operator</option>
              <option value="segment">Most observed segments</option>
              <option value="departure_delay">Departure-delay band</option>
            </select>
          </label>
        </div>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Subset</th>
                <th>Pairs</th>
                <th>Persistence MAE</th>
                <th>Corrected MAE*</th>
                <th>{MODEL_NAMES[selected]} MAE</th>
              </tr>
            </thead>
            <tbody>
              {model.subsets[subset].map((row) => (
                <tr key={String(row.value)}>
                  <th>{row.value}</th>
                  <td>{number(row.n)}</td>
                  <td>{number(row.metrics.persistence.mae, 3)}</td>
                  <td>
                    {number(row.metrics.bias_corrected_persistence.mae, 3)}
                  </td>
                  <td>{number(row.metrics[selected].mae, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lab-caption">
          Category/operator/date groups require at least 200 pairs; shown
          segments require 500 and are limited to the 15 most observed.
          Departure-delay bands show their actual counts. Large samples of
          adjacent stops do not remove day-level uncertainty.
        </p>
      </article>
      <article className="lab-card">
        <h3>Notable failures and remaining source anomalies</h3>
        <p className="lab-caption">
          The largest selected-model errors are shown below, not hand-picked
          successes. Some include implausibly early departures or large
          schedule/event reversals. They may reflect source or timetable
          inconsistencies as well as operational variation. No new exclusion was
          introduced after seeing these test errors.
        </p>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Day / recorded segment</th>
                <th>Departure delay</th>
                <th>Arrival delay</th>
                <th>Prediction</th>
                <th>Absolute error</th>
              </tr>
            </thead>
            <tbody>
              {(model.failure_cases || []).map((row, i) => (
                <tr key={i}>
                  <th>
                    {row.operating_date} · {row.station} → {row.next_station}
                  </th>
                  <td>{number(row.departure_delay, 2)}</td>
                  <td>{number(row.arrival_delay, 2)}</td>
                  <td>{number(row.prediction, 2)}</td>
                  <td>{number(row.absolute_error, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </>
  );
}

function Journey({ data }) {
  const [key, setKey] = useState(data.journeys[0]?.key);
  const journey = data.journeys.find((row) => row.key === key);
  if (!journey) return <p>No eligible historical example is available.</p>;
  const selected = data.models.selected_on_validation;
  const segments = journey.segments;
  const width = Math.max(680, segments.length * 70 + 100),
    height = 290;
  const values = segments.flatMap((row) => [
    row.arrival_delay,
    row[`prediction_${selected}`],
  ]);
  const min = Math.min(-1, ...values) - 0.3,
    max = Math.max(2, ...values) + 0.3;
  const x = (i) => 55 + (i * (width - 100)) / Math.max(1, segments.length - 1);
  const y = (value) => 205 - ((value - min) / (max - min)) * 175;
  const pathFor = (field) =>
    segments
      .map(
        (row, i) =>
          `${i === 0 || row.stop_index !== segments[i - 1].stop_index + 1 ? "M" : "L"}${x(i)},${y(row[field])}`,
      )
      .join(" ");
  const clock = (value) => (value ? value.slice(11, 19) : "—");
  return (
    <article className="lab-card">
      <label className="lab-journey-select">
        Historical journey
        <select
          value={key}
          onChange={(e) => setKey(e.target.value)}
          aria-label="Historical journey"
        >
          {data.journeys.map((row) => (
            <option key={row.key} value={row.key}>
              {row.label}
            </option>
          ))}
        </select>
      </label>
      <p className="lab-caption">
        {journey.note} Times below are Europe/Zurich. These ten examples are
        chosen deterministically by category and journey reference, not for
        prediction accuracy.
      </p>
      <div className="lab-chart-legend">
        <span>
          <i className="observed" />
          REAL arrival delay
        </span>
        <span>
          <i className="predicted" />
          {MODEL_NAMES[selected]} prediction
        </span>
      </div>
      <div
        className="lab-journey-scroll"
        tabIndex={0}
        role="region"
        aria-label="Scrollable journey chart"
      >
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Reported arrival delay and retrospective predictions at eligible successive recorded calls"
        >
          <title>Journey arrival-delay evolution</title>
          {[0, 1, 2, 3, 4].map((i) => {
            const value = min + ((max - min) * i) / 4;
            return (
              <g key={i}>
                <line
                  x1="45"
                  x2={width - 30}
                  y1={y(value)}
                  y2={y(value)}
                  stroke="#e4e6e7"
                />
                <text
                  x="36"
                  y={y(value) + 4}
                  textAnchor="end"
                  fill="#58636a"
                  fontSize="11"
                >
                  {number(value, 1)}
                </text>
              </g>
            );
          })}
          <text x="10" y="14" fontSize="11" fill="#58636a">
            min
          </text>
          <path
            d={pathFor("arrival_delay")}
            fill="none"
            stroke="#2d3841"
            strokeWidth="2"
          />
          <path
            d={pathFor(`prediction_${selected}`)}
            fill="none"
            stroke="#b83232"
            strokeWidth="2"
            strokeDasharray="5 3"
          />
          {segments.map((row, i) => (
            <g key={i}>
              <circle cx={x(i)} cy={y(row.arrival_delay)} r="4" fill="#2d3841">
                <title>
                  {row.next_station}: REAL {number(row.arrival_delay, 2)} min;
                  prediction {number(row[`prediction_${selected}`], 2)} min
                </title>
              </circle>
              <circle
                cx={x(i)}
                cy={y(row[`prediction_${selected}`])}
                r="3"
                fill="#b83232"
              />
              <text
                transform={`translate(${x(i)},224) rotate(32)`}
                fill="#37424b"
                fontSize="11"
              >
                {row.next_station}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <details>
        <summary>Scheduled times, REAL events and predictions</summary>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Recorded segment</th>
                <th>Scheduled arrival B</th>
                <th>REAL arrival B</th>
                <th>Departure delay A</th>
                <th>Arrival delay B</th>
                <th>Prediction B</th>
              </tr>
            </thead>
            <tbody>
              {segments.map((row, i) => (
                <tr key={i}>
                  <th>
                    {row.station} → {row.next_station}
                  </th>
                  <td>{clock(row.next_scheduled_arrival)}</td>
                  <td>{clock(row.next_event_arrival)}</td>
                  <td>{number(row.departure_delay, 2)}</td>
                  <td>{number(row.arrival_delay, 2)}</td>
                  <td>{number(row[`prediction_${selected}`], 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <details>
        <summary>Original reported calls and statuses</summary>
        <div className="lab-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Stop as reported</th>
                <th>Scheduled arrival</th>
                <th>Reported arrival</th>
                <th>Arrival status</th>
                <th>Scheduled departure</th>
                <th>Reported departure</th>
                <th>Departure status</th>
              </tr>
            </thead>
            <tbody>
              {journey.calls.map((row, i) => (
                <tr key={i}>
                  <th>{row.HALTESTELLEN_NAME}</th>
                  <td>{row.ANKUNFTSZEIT || "—"}</td>
                  <td>{row.AN_PROGNOSE || "—"}</td>
                  <td>{row.AN_PROGNOSE_STATUS || "Blank / forecast"}</td>
                  <td>{row.ABFAHRTSZEIT || "—"}</td>
                  <td>{row.AB_PROGNOSE || "—"}</td>
                  <td>{row.AB_PROGNOSE_STATUS || "Blank / forecast"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lab-caption">
          Literal source strings, including any foreign calls; no timezone
          conversion is imposed on this raw table. A forecast/estimate is not
          displayed as a REAL observation.
        </p>
      </details>
    </article>
  );
}

export default function DelayLab() {
  const [data, setData] = useState(null),
    [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    fetch("/lab-results.json", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Results unavailable");
        return response.json();
      })
      .then((value) => {
        if (value.schema_version !== 1 || value.models.status !== "evaluated")
          throw new Error("Invalid results");
        setData(value);
      })
      .catch((reason) => {
        if (reason.name !== "AbortError") setError(true);
      });
    return () => controller.abort();
  }, []);
  if (!data)
    return (
      <main className="lab-loading">
        <h1>Swiss Rail Delay Lab</h1>
        <p role="status">
          {error
            ? "The precomputed results could not be loaded. Please refresh or consult the repository."
            : "Loading precomputed historical results…"}
        </p>
        {error && <a href={REPO}>Open the project repository</a>}
      </main>
    );
  const summary = data.summary,
    models = data.models;
  const selected = models.selected_on_validation,
    test = models.metrics.test;
  return (
    <>
      <a className="lab-skip" href="#overview">
        Skip to content
      </a>
      <header className="lab-header">
        <div>
          <a className="lab-brand" href="#overview">
            Swiss Rail Delay Lab
          </a>
          <span className="lab-status">
            Independent project · Work in progress
          </span>
        </div>
        <div className="lab-header-links">
          <a href={REPO}>Code & reproducibility</a>
          <a href="/v1">V1 demo</a>
        </div>
      </header>
      <nav className="lab-nav" aria-label="Study sections">
        <a href="#overview">Overview</a>
        <a href="#analysis">Delay analysis</a>
        <a href="#prediction">Prediction</a>
        <a href="#journeys">Journey explorer</a>
        <a href="#methodology">Data & methodology</a>
      </nav>
      <main className="lab-main">
        <section
          id="overview"
          className="lab-overview"
          aria-labelledby="lab-title"
        >
          <p className="lab-eyebrow">
            HISTORICAL STUDY · {data.coverage.start} TO {data.coverage.end}
          </p>
          <h1 id="lab-title">Swiss Rail Delay Lab</h1>
          <p className="lab-subtitle">
            Exploring and predicting train delays using Swiss public transport
            data
          </p>
          <p className="lab-question">
            Can we understand and predict how delays evolve between successive
            railway stations?
          </p>
          <p className="lab-lead">
            This study examines consecutive recorded train calls in official
            Ist-Daten v2 exports. It compares simple next-call delay predictions
            on later operating days, using precomputed historical results. It
            does not provide live train information.
          </p>
          <div className="lab-note">
            <strong>Scope matters.</strong> Only eligible Swiss-station pairs
            with REAL departure and arrival records are analyzed. The source
            also contains forecasts and estimates, which are excluded. These
            results are not a network-wide punctuality measure or evidence of
            operational bottlenecks.
          </div>
          <div className="lab-stats">
            <div>
              <span>Exported rail calls</span>
              <strong>{number(data.quality.raw_rail_rows)}</strong>
              <small>Complete filtered datastore exports</small>
            </div>
            <div>
              <span>Eligible recorded segments</span>
              <strong>{number(summary.n)}</strong>
              <small>{number(summary.journeys)} distinct dated journeys</small>
            </div>
            <div>
              <span>Station IDs represented</span>
              <strong>{number(summary.stations)}</strong>
              <small>{number(summary.operators)} reported operators</small>
            </div>
            <div>
              <span>Operating-day coverage</span>
              <strong>{data.coverage.days} days</strong>
              <small>
                {data.coverage.days} operating days;{" "}
                {models.splits.test.dates.length} held-out test days
              </small>
            </div>
          </div>
          <div className="lab-overview-findings">
            <h2>What this sample shows</h2>
            <ul>
              <li>
                Reported delay decreases by at least one minute in{" "}
                <strong>
                  {percent(summary.decrease_at_least_1_min, summary.n)}
                </strong>{" "}
                of eligible segments, and increases by at least one minute in{" "}
                <strong>
                  {percent(summary.increase_at_least_1_min, summary.n)}
                </strong>
                . Timetable allowances and timestamp conventions can contribute.
              </li>
              <li>
                <strong>{MODEL_NAMES[selected]}</strong>, selected on
                validation, has test MAE{" "}
                <strong>{number(test[selected].mae, 3)} min</strong>, compared
                with <strong>{number(test.persistence.mae, 3)} min</strong> for
                persistence and{" "}
                <strong>
                  {number(test.bias_corrected_persistence.mae, 3)} min
                </strong>{" "}
                for the additional bias-corrected diagnostic.
              </li>
              <li>
                The tested gradient boosting has test RMSE{" "}
                <strong>
                  {number(test.hist_gradient_boosting.rmse, 3)} min
                </strong>
                , versus <strong>{number(test.persistence.rmse, 3)} min</strong>{" "}
                for persistence. Better MAE does not guarantee better tail
                behavior.
              </li>
            </ul>
          </div>
        </section>
        <Section
          id="analysis"
          index="01"
          title="Delay analysis"
          intro="All descriptive figures use the same eligible REAL/REAL paired sample. Delays are signed minutes relative to the reported schedule; early events remain negative."
        >
          <div className="lab-two-column">
            <article className="lab-card">
              <h3>Arrival delay at the next recorded call</h3>
              <p className="lab-caption">
                Median {number(summary.arrival_median, 2)} min · 90th percentile{" "}
                {number(summary.arrival_p90, 2)} min. Bins are left-inclusive,
                right-exclusive; tails are included.
              </p>
              <Bars
                rows={data.distributions.arrival.map((row) => ({
                  label: row.label,
                  value: row.n,
                }))}
                total={summary.n}
                label="Arrival delay distribution in minutes"
              />
            </article>
            <article className="lab-card">
              <h3>Change from departure A to arrival B</h3>
              <p className="lab-caption">
                Arrival delay B − departure delay A. Median{" "}
                {signed(summary.change_median, 2)} min. A negative value is a
                decrease in reported delay, not a causal attribution.
              </p>
              <Bars
                rows={data.distributions.change.map((row) => ({
                  label: row.label,
                  value: row.n,
                }))}
                total={summary.n}
                label="Reported delay change distribution in minutes"
                color="ink"
              />
            </article>
          </div>
          <Comparison data={data} />
        </Section>
        <Section
          id="prediction"
          index="02"
          title="Predicting the next recorded arrival"
          intro="How much information do final departure records contain beyond copying the current delay? These results answer a retrospective question on this specific sample."
        >
          <Prediction data={data} />
        </Section>
        <Section
          id="journeys"
          index="03"
          title="A historical journey, call by call"
          intro="Inspect scheduled times, source statuses, realized delays and model predictions in concrete test-set examples."
        >
          <Journey data={data} />
        </Section>
        <Section
          id="methodology"
          index="04"
          title="Data & methodology"
          intro="The limitations are part of the result. Full code, acquisition checks, input hashes, model settings and experimental decisions are available in the repository."
        >
          <div className="lab-two-column">
            <article className="lab-card">
              <h3>Source and measurement</h3>
              <p>
                Data:{" "}
                <a href={data.provenance.source}>
                  opentransportdata.swiss — Ist-Daten v2
                </a>
                . Daily public datastore rail exports, operating days{" "}
                {data.coverage.start} to {data.coverage.end}. No GTFS, weather
                or synthetic observations were used.
              </p>
              <p>
                <code>REAL</code> identifies a producer-classified realized
                event. <code>GESCHAETZT</code> means estimated,{" "}
                <code>PROGNOSE</code> or blank means forecast, and{" "}
                <code>UNBEKANNT</code> means unknown. Only REAL departure A and
                REAL arrival B enter the paired analysis.
              </p>
              <p>
                Schedules are minute-rounded; event precision varies.{" "}
                <a href={data.provenance.documentation}>The cookbook</a>{" "}
                describes both estimated events and last forecasts. A REAL label
                is not independent measurement validation.
              </p>
              <p>
                <a href={data.provenance.terms}>Official terms</a> apply.
                Source: opentransportdata.swiss. Analysis by{" "}
                <a href="https://github.com/NicoHelemon">NicoHelemon</a>, an
                independent EPFL MSc graduate interested in data science and
                railway operations.
              </p>
            </article>
            <article className="lab-card">
              <h3>Reconstruction and validation</h3>
              <p>
                Journey keys combine operating date, operator and journey
                reference. Calls are sorted by planned arrival, falling back to
                planned departure. Missing or tied ordering times exclude the
                whole journey:{" "}
                {number(data.quality.ambiguous_journeys_excluded)} journeys in
                this interval.
              </p>
              <p>
                Calls are sequenced before excluding unreliable, cancelled,
                pass-through or foreign endpoints. Invalid intermediate calls
                are never removed and bridged. BPUIC station normalization uses
                documented seven-digit prefixes; SLOID-only endpoints are
                excluded.
              </p>
              <p>
                There is no explicit sequence index or publication history.
                These are consecutive <em>recorded</em> calls, not an
                independently validated complete GTFS itinerary. Local times are
                interpreted as Europe/Zurich; no DST transition occurs in this
                interval.
              </p>
              <p>
                Initial unbounded CSV exports were found to be truncated despite
                HTTP 200. The corrected pipeline verifies bounded rail pages,
                monotonic IDs, stable highest source ID, an empty final page,
                and SHA-256 checksums. Equivalence to original uploaded archives
                is not independently established.
              </p>
            </article>
          </div>
          <article className="lab-card">
            <h3>From recorded pairs to the analytical sample</h3>
            <p className="lab-caption">
              After duplicate/order checks,{" "}
              {number(data.quality.consecutive_recorded_pairs)} consecutive
              recorded rail pairs were candidates. Each row below uses the
              retained population from the preceding row, so exclusions are not
              double-counted.
            </p>
            <div className="lab-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Sequential rule</th>
                    <th>Excluded</th>
                    <th>Retained</th>
                  </tr>
                </thead>
                <tbody>
                  {data.quality.funnel.map((row) => (
                    <tr key={row.step}>
                      <th>{row.step}</th>
                      <td>{number(row.excluded)}</td>
                      <td>{number(row.retained)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="lab-caption">
              Gross date-offset anomalies are excluded using the declared
              ±12-hour delay guard, not repaired. Sensitivity retained counts:{" "}
              {data.quality.delay_bound_sensitivity
                .map(
                  (row) =>
                    `${row.absolute_delay_bound_minutes === null ? "no bound" : `±${row.absolute_delay_bound_minutes} min`}: ${number(row.retained_pairs)}`,
                )
                .join(" · ")}
              . Ordinary negative delays and positive tails are not clipped.
            </p>
            <details>
              <summary>Daily coverage and retained pairs</summary>
              <div className="lab-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Operating day</th>
                      <th>Exported rail calls</th>
                      <th>Eligible pairs</th>
                      <th>Ambiguous journeys excluded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.quality.daily.map((row) => (
                      <tr key={row.date}>
                        <th>{row.date}</th>
                        <td>{number(row.rail_rows)}</td>
                        <td>{number(row.retained_pairs)}</td>
                        <td>{number(row.ambiguous_journeys)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <details>
              <summary>
                Literal arrival/departure status counts in rail exports
              </summary>
              <div className="lab-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Arrival status</th>
                      <th>Departure status</th>
                      <th>Rail calls</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.quality.status_combinations.map((row, i) => (
                      <tr key={i}>
                        <th>{row.AN_PROGNOSE_STATUS || "Blank"}</th>
                        <td>{row.AB_PROGNOSE_STATUS || "Blank"}</td>
                        <td>{number(row.len)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <details>
              <summary>
                Missing raw values, including structurally absent events
              </summary>
              <p className="lab-caption">
                Counts out of {number(data.quality.raw_rail_rows)} exported rail
                calls. Origins can legitimately have no arrival and termini no
                departure; these counts are not all measurement failures.
              </p>
              <div className="lab-table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Missing values</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(
                      data.quality.missing_values_in_rail_calls || {},
                    ).map(([field, n]) => (
                      <tr key={field}>
                        <th>
                          <code>{field}</code>
                        </th>
                        <td>{number(n)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </article>
          <div className="lab-two-column">
            <article className="lab-card">
              <h3>What the experiment cannot establish</h3>
              <ul>
                <li>
                  Publication-time availability of final observations or
                  timetable revisions.
                </li>
                <li>
                  Performance on new seasons, disruptions, or genuinely unseen
                  routes.
                </li>
                <li>
                  Complete coverage of Swiss trains: absent journeys, status
                  differences and exclusions create selection bias.
                </li>
                <li>
                  Causal station effects, delay propagation mechanisms, or
                  operational bottlenecks.
                </li>
              </ul>
              <p>
                This is a short retrospective study, not an operational
                forecasting product. No conclusions about passenger demand,
                capacity or transfer reliability follow from these figures.
              </p>
            </article>
            <article className="lab-card">
              <h3>Reproduce and inspect</h3>
              <p>
                The Python pipeline downloads official records, validates
                inputs, reconstructs pairs, and evaluates the fixed models. The
                website loads one compact precomputed JSON file; no raw archives
                or model training occur in the browser.
              </p>
              <div className="lab-resource-links">
                <a href={`${REPO}/blob/main/README.md`}>
                  Setup and reproduction instructions
                </a>
                <a href={`${REPO}/blob/main/docs/data_feasibility.md`}>
                  Source feasibility and decisions
                </a>
                <a href={`${REPO}/blob/main/docs/results.md`}>
                  Results and failure cases
                </a>
                <a href="/lab-results.json" download>
                  Download the complete compact results JSON
                </a>
              </div>
              <p className="lab-caption">
                Generated {data.generated_at_utc.slice(0, 19).replace("T", " ")}{" "}
                UTC. The JSON includes source URLs, daily hashes, dependency
                versions, split dates, and model settings. Future work: longer
                held-out periods, independent schedule checks, and collection of
                timestamped publication histories.
              </p>
            </article>
          </div>
        </Section>
        <footer className="lab-footer">
          <p>Swiss Rail Delay Lab · Independent project · Work in progress</p>
          <p>
            Not affiliated with SBB or any transport operator.{" "}
            <a href="/v1">Original synthetic network demo</a>
          </p>
        </footer>
      </main>
    </>
  );
}
