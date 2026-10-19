import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const data = JSON.parse(
  readFileSync(new URL("../public/lab-results.json", import.meta.url), "utf8"),
);
const sum = (rows) => rows.reduce((total, row) => total + row.n, 0);

test("published distributions account for every eligible pair including tails", () => {
  assert.equal(sum(data.distributions.arrival), data.summary.n);
  assert.equal(sum(data.distributions.change), data.summary.n);
  assert.equal(
    data.summary.decrease_at_least_1_min +
      data.summary.increase_at_least_1_min +
      data.summary.change_below_1_min,
    data.summary.n,
  );
});

test("the exclusion funnel is continuous and conserves denominators", () => {
  let remaining = data.quality.consecutive_recorded_pairs;
  for (const row of data.quality.funnel) {
    assert.equal(row.before, remaining);
    assert.equal(row.excluded + row.retained, row.before);
    remaining = row.retained;
  }
  assert.equal(remaining, data.summary.n);
  assert.equal(
    data.quality.daily.reduce((s, row) => s + row.retained_pairs, 0),
    remaining,
  );
});

test("chronological partitions plus purged rows cover the analytical dataset", () => {
  const splits = data.models.splits;
  assert.equal(
    Object.values(splits).reduce((s, row) => s + row.n, 0),
    data.summary.n,
  );
  assert.ok(splits.train.dates.at(-1) < splits.validation.dates[0]);
  assert.ok(splits.validation.dates.at(-1) < splits.test.dates[0]);
});

test("all methods and error histograms use identical held-out rows", () => {
  for (const [name, metrics] of Object.entries(data.models.metrics.test)) {
    assert.equal(metrics.n, data.models.splits.test.n);
    assert.equal(sum(data.models.error_histograms[name]), metrics.n);
    assert.ok(metrics.rmse >= metrics.mae);
    assert.ok(Math.abs(metrics.mean_error) <= metrics.mae + 1e-12);
  }
});

test("selection uses original validation candidates and discloses the later diagnostic", () => {
  const model = data.models;
  const best = model.selection_candidates.reduce((a, b) =>
    model.metrics.validation[a].mae <= model.metrics.validation[b].mae ? a : b,
  );
  assert.equal(model.selected_on_validation, best);
  assert.ok(!model.selection_candidates.includes("bias_corrected_persistence"));
  assert.match(model.additional_diagnostic, /after initial test inspection/);
});

test("daily source provenance accounts for every exported rail call", () => {
  const inputs = data.provenance.inputs;
  assert.equal(new Set(inputs.map((row) => row.date)).size, data.coverage.days);
  assert.equal(
    inputs.reduce((s, row) => s + row.rows, 0),
    data.quality.raw_rail_rows,
  );
  for (const row of inputs) {
    assert.match(row.sha256, /^[a-f0-9]{64}$/);
    assert.ok(
      row.source_url.startsWith("https://data.opentransportdata.swiss/"),
    );
    assert.ok(!row.source_url.includes("Signature"));
  }
});

test("historical examples report timestamp-derived signed delays consistently", () => {
  for (const journey of data.journeys)
    for (const row of journey.segments) {
      const observed = Date.parse(row.next_event_arrival);
      assert.ok(observed >= Date.parse(row.event_departure));
      assert.ok(
        Math.abs(
          (observed - Date.parse(row.next_scheduled_arrival)) / 60000 -
            row.arrival_delay,
        ) < 1e-9,
      );
    }
});
