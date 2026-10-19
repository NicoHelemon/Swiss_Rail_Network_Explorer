"""Predeclared retrospective experiment; never a claim of as-of operational validation."""

import json
from pathlib import Path
import time

import numpy as np
import polars as pl
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from research.audit_source import save_json


NUMERIC = ["departure_delay", "scheduled_minutes", "hour_sin", "hour_cos"]
CATEGORICAL = ["station_id", "next_station_id", "category", "operator", "weekday"]
FEATURES = NUMERIC + CATEGORICAL


def chronological_split(frame, config):
    """Whole journeys, purged using realized outcome/issue timestamps at boundaries."""
    val_day, test_day = config["validation_start"], config["test_start"]
    val_boundary = pl.lit(val_day + "T00:00:00").str.to_datetime().dt.replace_time_zone("Europe/Zurich").dt.convert_time_zone("UTC")
    test_boundary = pl.lit(test_day + "T00:00:00").str.to_datetime().dt.replace_time_zone("Europe/Zurich").dt.convert_time_zone("UTC")
    journeys = frame.group_by("journey_key").agg(
        pl.col("operating_date").first(),
        pl.col("event_departure").min().alias("first_issue"),
        pl.col("next_event_arrival").max().alias("last_outcome"),
    ).with_columns(
        pl.when((pl.col("operating_date") < val_day) & (pl.col("last_outcome") < val_boundary)).then(pl.lit("train"))
        .when((pl.col("operating_date") >= val_day) & (pl.col("operating_date") < test_day) & (pl.col("first_issue") >= val_boundary) & (pl.col("last_outcome") < test_boundary)).then(pl.lit("validation"))
        .when((pl.col("operating_date") >= test_day) & (pl.col("first_issue") >= test_boundary)).then(pl.lit("test"))
        .otherwise(pl.lit("purged")).alias("split")
    )
    result = frame.join(journeys.select("journey_key", "split"), on="journey_key", how="left")
    partitions = {name: result.filter(pl.col("split") == name) for name in ["train", "validation", "test", "purged"]}
    if any(partitions[name].height == 0 for name in ["train", "validation", "test"]):
        raise ValueError("Chronological split contains an empty required partition")
    train, validation, test = [partitions[name] for name in ["train", "validation", "test"]]
    assert train["next_event_arrival"].max() < validation["event_departure"].min()
    assert validation["next_event_arrival"].max() < test["event_departure"].min()
    sets = [set(partitions[name]["journey_key"]) for name in ["train", "validation", "test"]]
    assert not (sets[0] & sets[1] or sets[1] & sets[2] or sets[0] & sets[2])
    return partitions


def features(frame):
    # Explicit whitelist: no arrival B or observed A→B duration enters X.
    x = frame.with_columns(
        (pl.col("hour") * 2 * np.pi / 24).sin().alias("hour_sin"),
        (pl.col("hour") * 2 * np.pi / 24).cos().alias("hour_cos"),
        *[pl.col(c).cast(pl.String).fill_null("Unknown").alias(c) for c in CATEGORICAL],
    ).select(FEATURES).to_pandas()
    if x.isna().any().any():
        raise ValueError("Missing model feature escaped preprocessing")
    return x


def metrics(y, prediction):
    error = np.asarray(prediction) - np.asarray(y)
    return {
        "n": len(y), "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(np.sqrt(mean_squared_error(y, prediction))),
        "mean_error": float(error.mean()),
        "absolute_error_p90": float(np.quantile(np.abs(error), .9)),
        "absolute_error_p99": float(np.quantile(np.abs(error), .99)),
    }


def grouped_difference_interval(frame, y, candidate, persistence, replicates, seed):
    """Paired journey bootstrap of row-weighted MAE differences; not independent days."""
    grouped = frame.select("journey_key").with_columns(
        pl.Series("loss_difference", np.abs(candidate - y) - np.abs(persistence - y)),
    ).group_by("journey_key").agg(pl.col("loss_difference").sum().alias("loss_sum"), pl.len().alias("n"))
    losses, counts = grouped["loss_sum"].to_numpy(), grouped["n"].to_numpy()
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(replicates):
        index = rng.integers(0, len(grouped), len(grouped))
        estimates.append(float(losses[index].sum() / counts[index].sum()))
    return {
        "difference": float(losses.sum() / counts.sum()),
        "lower_95": float(np.quantile(estimates, .025)), "upper_95": float(np.quantile(estimates, .975)),
        "unit": "minutes", "resampling_unit": "journey", "replicates": replicates,
        "limitation": "Within-journey dependence retained; shared day/route shocks not fully represented. Only three held-out days.",
    }


def fit_models(frame, config, root=Path("data")):
    partitions = chronological_split(frame, config)
    split_info = {name: {
        "n": part.height, "journeys": part["journey_key"].n_unique(),
        "dates": sorted(part["operating_date"].unique().to_list()),
    } for name, part in partitions.items()}
    matrices = {name: features(partitions[name]) for name in ["train", "validation", "test"]}
    targets = {name: partitions[name]["arrival_delay"].to_numpy() for name in matrices}
    ridge_preprocessing = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("categories", OneHotEncoder(handle_unknown="ignore", min_frequency=50), CATEGORICAL),
    ])
    tree_preprocessing = ColumnTransformer([
        ("numeric", "passthrough", NUMERIC),
        ("categories", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1, max_categories=config["category_max_bins"]), CATEGORICAL),
    ])
    models = {
        "ridge": make_pipeline(ridge_preprocessing, Ridge(**config["ridge"])),
        "hist_gradient_boosting": make_pipeline(
            tree_preprocessing,
            HistGradientBoostingRegressor(
                **config["hist_gradient_boosting"],
                categorical_features=[False] * len(NUMERIC) + [True] * len(CATEGORICAL),
            ),
        ),
    }
    predictions = {name: {
        "zero": np.zeros(partitions[name].height),
        "persistence": partitions[name]["departure_delay"].to_numpy(),
    } for name in matrices}
    correction = float((targets["train"] - partitions["train"]["departure_delay"].to_numpy()).mean())
    for split in predictions:
        predictions[split]["bias_corrected_persistence"] = predictions[split]["persistence"] + correction
    training_seconds = {}
    for name, model in models.items():
        started = time.monotonic()
        with threadpool_limits(limits=4):
            model.fit(matrices["train"], targets["train"])
            training_seconds[name] = time.monotonic() - started
            for split in matrices:
                predictions[split][name] = model.predict(matrices[split])
        print(f"Fitted {name} in {training_seconds[name]:.1f}s", flush=True)
    evaluation = {split: {name: metrics(targets[split], prediction) for name, prediction in candidates.items()} for split, candidates in predictions.items()}
    # Predeclared selection uses validation only; test metrics never select a model.
    selection_candidates = ["zero", "persistence", "ridge", "hist_gradient_boosting"]
    selected = min(selection_candidates, key=lambda name: evaluation["validation"][name]["mae"])
    test = partitions["test"]
    y = targets["test"]
    for name in evaluation["test"]:
        evaluation["test"][name]["mae_difference_vs_persistence"] = evaluation["test"][name]["mae"] - evaluation["test"]["persistence"]["mae"]
    intervals = {name: grouped_difference_interval(
        test, y, predictions["test"][name], predictions["test"]["persistence"], config["bootstrap_replicates"], config["seed"],
    ) for name in models}
    subset_results = {}
    for dimension in ["category", "operator", "hour", "operating_date"]:
        group_results = []
        for value in test[dimension].unique().sort():
            mask = test[dimension].eq(value).to_numpy()
            if mask.sum() < 200:
                continue
            group_results.append({"value": value, "n": int(mask.sum()), "metrics": {
                name: metrics(y[mask], prediction[mask]) for name, prediction in predictions["test"].items()
            }})
        subset_results[dimension] = group_results
    segment_labels = test.select(pl.concat_str("station", "next_station", separator=" → ").alias("segment"))["segment"]
    subset_results["segment"] = []
    top_segments = segment_labels.value_counts(sort=True).filter(pl.col("count") >= 500).head(15)
    for value in top_segments["segment"]:
        mask = segment_labels.eq(value).to_numpy()
        subset_results["segment"].append({"value": value, "n": int(mask.sum()), "metrics": {name: metrics(y[mask], prediction[mask]) for name, prediction in predictions["test"].items()}})
    delay_bands = [(-np.inf, 0, "Early departure"), (0, 2, "0–2 min"), (2, 5, "2–5 min"), (5, 10, "5–10 min"), (10, np.inf, "10+ min")]
    subset_results["departure_delay"] = []
    departure = test["departure_delay"].to_numpy()
    for low, high, label in delay_bands:
        mask = (departure >= low) & (departure < high)
        if mask.sum():
            subset_results["departure_delay"].append({"value": label, "n": int(mask.sum()), "metrics": {name: metrics(y[mask], prediction[mask]) for name, prediction in predictions["test"].items()}})
    error_bins = [-np.inf, -5, -2, -1, -.5, 0, .5, 1, 2, 5, np.inf]
    error_labels = ["< −5", "−5 to −2", "−2 to −1", "−1 to −0.5", "−0.5 to 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2 to 5", "≥ 5"]
    error_histograms = {name: [{"label": label, "n": int(count)} for label, count in zip(error_labels, np.histogram(prediction - y, bins=error_bins)[0])] for name, prediction in predictions["test"].items()}
    # Grouped held-out permutation of the two main numeric predictors. This is
    # predictive dependence, not causality; correlated inputs can distort it.
    importance = []
    if selected in models:
        sample_n = min(20000, test.height)
        rng = np.random.default_rng(config["seed"])
        index = rng.choice(test.height, sample_n, replace=False)
        x = matrices["test"].iloc[index].copy()
        true = y[index]
        baseline = mean_absolute_error(true, predictions["test"][selected][index])
        for column in ["departure_delay", "scheduled_minutes", "station_id", "next_station_id", "category"]:
            shuffled = x.copy()
            shuffled[column] = rng.permutation(shuffled[column].to_numpy())
            with threadpool_limits(limits=4):
                loss = mean_absolute_error(true, models[selected].predict(shuffled))
            importance.append({"feature": column, "mae_increase": float(loss - baseline), "sample_n": sample_n})
    unknowns = {column: int((~test[column].is_in(partitions["train"][column].unique())).sum()) for column in ["station_id", "next_station_id", "category", "operator"]}
    train_segments = set(zip(partitions["train"]["station_id"], partitions["train"]["next_station_id"]))
    unknowns["segment"] = sum(pair not in train_segments for pair in zip(test["station_id"], test["next_station_id"]))
    report = {
        "status": "evaluated", "interpretation": config["prediction_interpretation"],
        "features": FEATURES, "config": config, "splits": split_info,
        "metrics": evaluation, "selected_on_validation": selected,
        "training_seconds": training_seconds, "intervals": intervals,
        "subsets": subset_results, "error_histograms": error_histograms,
        "permutation_importance": importance, "unseen_test_values_row_counts": unknowns,
        "test_evaluation_policy": "Original model configurations fixed before held-out evaluation; selected using validation MAE. No tuning on test. Subsequent diagnostic baseline and subgroup analyses are explicitly exploratory.",
        "selection_candidates": selection_candidates,
        "bias_correction_minutes": correction,
        "additional_diagnostic": "Bias-corrected persistence was added after initial test inspection to distinguish model gains from a constant departure-to-arrival offset. The offset is fitted on training rows only; no test tuning. It did not select or change the original models.",
    }
    test_output = test.with_columns(*[pl.Series("prediction_" + name, prediction) for name, prediction in predictions["test"].items()])
    report["failure_cases"] = test_output.with_columns(
        (pl.col("prediction_" + selected) - pl.col("arrival_delay")).abs().alias("absolute_error"),
    ).sort("absolute_error", descending=True).head(5).select(
        "operating_date", "operator", "category", "station", "next_station", "departure_delay", "arrival_delay",
        pl.col("prediction_" + selected).alias("prediction"), "absolute_error",
    ).to_dicts()
    root = Path(root)
    test_output.write_parquet(root / "processed" / "test_predictions.parquet")
    save_json(root / "audit" / "model_results.json", report)
    return report
