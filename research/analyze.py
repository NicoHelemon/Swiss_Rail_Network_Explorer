"""Generate compact, provenance-linked results only after complete source validation."""

from datetime import date, datetime, timedelta, timezone
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np
import polars as pl

from research.acquire import sha256_file
from research.audit_source import save_json
from research.model import fit_models


def required_dates(config):
    start, end = [date.fromisoformat(config[key]) for key in ["start", "end"]]
    return [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]


def load_dataset(root, config):
    root = Path(root)
    frames, quality, inputs = [], [], []
    for day in required_dates(config):
        path = root / "processed" / f"{day}.parquet"
        audit = json.loads((root / "audit" / f"{day}-quality.json").read_text())
        manifest = json.loads((root / "audit" / f"{day}-download.json").read_text())
        if not manifest.get("coverage_verified") or audit["input_sha256"] != manifest["sha256"] or audit.get("parquet_sha256") != sha256_file(path):
            raise ValueError(f"Unverified or stale processed inputs for {day}")
        frames.append(pl.read_parquet(path))
        quality.append(audit)
        inputs.append({"date": day, "resource_id": manifest["resource_id"], "source_url": manifest["source_url"], "sha256": manifest["sha256"], "rows": manifest["rows"], "bytes": manifest["bytes"], "retrieved_at_utc": manifest["retrieved_at_utc"], "last_source_id": manifest["last_source_id"]})
    frame = pl.concat(frames)
    if frame.select("journey_key", "stop_index").is_duplicated().any():
        raise ValueError("Duplicate journey/stop pairs in analytical data")
    if not np.allclose((frame["observed_minutes"] - frame["scheduled_minutes"]).to_numpy(), frame["delay_change"].to_numpy()):
        raise ValueError("Duration/delay-change identity does not hold")
    return frame, quality, inputs


def summary(frame):
    n = frame.height
    return {
        "n": n, "journeys": frame["journey_key"].n_unique(),
        "stations": len(set(frame["station_id"]) | set(frame["next_station_id"])),
        "operators": frame["operator"].n_unique(),
        "arrival_mean": float(frame["arrival_delay"].mean()),
        "arrival_median": float(frame["arrival_delay"].median()),
        "arrival_p90": float(frame["arrival_delay"].quantile(.9, interpolation="linear")),
        "arrival_p99": float(frame["arrival_delay"].quantile(.99, interpolation="linear")),
        "departure_median": float(frame["departure_delay"].median()),
        "change_mean": float(frame["delay_change"].mean()),
        "change_median": float(frame["delay_change"].median()),
        "decrease_at_least_1_min": frame.filter(pl.col("delay_change") <= -1).height,
        "increase_at_least_1_min": frame.filter(pl.col("delay_change") >= 1).height,
        "change_below_1_min": frame.filter(pl.col("delay_change").abs() < 1).height,
    }


def breakdown(frame, dimension, minimum=200):
    results = frame.group_by(dimension).agg(
        pl.len().alias("n"), pl.col("arrival_delay").mean().alias("mean"),
        pl.col("arrival_delay").median().alias("median"),
        pl.col("arrival_delay").quantile(.9, interpolation="linear").alias("p90"),
        pl.col("delay_change").mean().alias("change_mean"),
        (pl.col("delay_change") <= -1).mean().alias("decrease_share"),
    ).filter(pl.col("n") >= minimum).sort("n", descending=True)
    return [{"value": r.pop(dimension), **r} for r in results.to_dicts()]


def histogram(values, edges, labels):
    return [{"label": label, "n": int(count)} for label, count in zip(labels, np.histogram(values, bins=edges)[0])]


def journey_examples(frame, root, model_report):
    predictions = pl.read_parquet(Path(root) / "processed" / "test_predictions.parquet")
    # Deterministic category-diverse examples, not selected for model success.
    candidates = predictions.group_by("journey_key", "category").agg(pl.len().alias("n")).filter(pl.col("n") >= 6).sort(["category", "journey_key"])
    selected = candidates.unique(subset="category", keep="first", maintain_order=True).head(10)
    journeys = []
    for key in selected["journey_key"]:
        pairs = predictions.filter(pl.col("journey_key") == key).sort("stop_index")
        day = pairs["operating_date"][0]
        raw = pl.scan_csv(Path(root) / "raw" / f"{day}-rail.csv", infer_schema=False)
        source = raw.with_columns(pl.concat_str(["BETRIEBSTAG", "BETREIBER_ID", "FAHRT_BEZEICHNER"], separator="|").alias("journey_key")).filter(pl.col("journey_key") == key).collect()
        # The displayed raw calls include missing/forecast events honestly.
        calls = source.select("BPUIC", "HALTESTELLEN_NAME", "ANKUNFTSZEIT", "ABFAHRTSZEIT", "AN_PROGNOSE", "AB_PROGNOSE", "AN_PROGNOSE_STATUS", "AB_PROGNOSE_STATUS", "FAELLT_AUS_TF").to_dicts()
        segments = pairs.select("stop_index", "station", "next_station", "scheduled_departure", "next_scheduled_arrival", "event_departure", "next_event_arrival", "departure_delay", "arrival_delay", *[c for c in pairs.columns if c.startswith("prediction_")]).to_dicts()
        for segment in segments:
            for column in ["scheduled_departure", "next_scheduled_arrival", "event_departure", "next_event_arrival"]:
                segment[column] = segment[column].astimezone(__import__("zoneinfo").ZoneInfo("Europe/Zurich")).isoformat()
        journeys.append({
            "key": key, "date": day, "operator": pairs["operator"][0], "category": pairs["category"][0],
            "label": f"{pairs['category'][0]} · {pairs['operator'][0]} · {pairs['station'][0]} → {pairs['next_station'][-1]} · {day}",
            "calls": calls, "segments": segments,
            "note": "Deterministic historical test-set example. Eligible segment endpoints are shown; omitted/ineligible segments are not joined. Original call rows are shown separately, with literal source statuses.",
        })
    return journeys


def run(root=Path("data"), output=Path("public/lab-results.json")):
    config_path = Path("research/config.json")
    config = json.loads(config_path.read_text())
    frame, quality, inputs = load_dataset(root, config)
    # Fixed configurations are committed before the first held-out evaluation.
    model_report = fit_models(frame, config, root)
    stations = frame.group_by("next_station_id").agg(
        pl.col("next_station").mode().sort().first().alias("name"),
        pl.len().alias("n"), pl.col("arrival_delay").median().alias("median"),
        pl.col("arrival_delay").mean().alias("mean"),
        pl.col("arrival_delay").quantile(.9, interpolation="linear").alias("p90"),
    ).filter(pl.col("n") >= 500).sort("n", descending=True).head(40).rename({"next_station_id": "id"}).to_dicts()
    segments = frame.group_by("station_id", "next_station_id").agg(
        pl.col("station").mode().sort().first(), pl.col("next_station").mode().sort().first(),
        pl.len().alias("n"), pl.col("delay_change").mean().alias("change_mean"),
        pl.col("delay_change").median().alias("change_median"),
        pl.col("arrival_delay").mean().alias("mean"),
    ).filter(pl.col("n") >= 500).sort("n", descending=True).head(40).to_dicts()
    funnels = quality[0]["funnel"]
    combined_funnel = [{"step": step["step"], **{field: sum(day["funnel"][i][field] for day in quality) for field in ["before", "excluded", "retained"]}} for i, step in enumerate(funnels)]
    quality_summary = {
        "raw_rail_rows": sum(day["source_rows"] for day in quality),
        "raw_journeys": sum(day["journeys_before_order_checks"] for day in quality),
        "ambiguous_journeys_excluded": sum(day["ambiguous_journeys_excluded"] for day in quality),
        "identical_duplicate_rows_removed": sum(day["identical_duplicate_rows_removed"] for day in quality),
        "consecutive_recorded_pairs": sum(day["consecutive_recorded_pairs"] for day in quality),
        "funnel": combined_funnel,
        "daily": [{"date": day["date"], "rail_rows": day["rail_rows"], "retained_pairs": day["retained_pairs"], "ambiguous_journeys": day["ambiguous_journeys_excluded"]} for day in quality],
        "status_combinations": pl.concat([pl.DataFrame(day["rail_status_combinations"]) for day in quality]).group_by("AN_PROGNOSE_STATUS", "AB_PROGNOSE_STATUS").agg(pl.col("len").sum()).sort("len", descending=True).to_dicts(),
        "delay_bound_sensitivity": [{"absolute_delay_bound_minutes": bound, "retained_pairs": sum(next(row["retained_pairs"] for row in day["delay_bound_sensitivity"] if row["absolute_delay_bound_minutes"] == bound) for day in quality)} for bound in [60, 180, 720, None]],
    }
    arrival_bins = [-np.inf, -5, -2, -1, 0, 1, 2, 3, 5, 10, 20, 60, np.inf]
    arrival_labels = ["< −5", "−5 to −2", "−2 to −1", "−1 to 0", "0 to 1", "1 to 2", "2 to 3", "3 to 5", "5 to 10", "10 to 20", "20 to 60", "≥ 60"]
    change_bins = [-np.inf, -5, -2, -1, -.5, 0, .5, 1, 2, 5, np.inf]
    change_labels = ["< −5", "−5 to −2", "−2 to −1", "−1 to −0.5", "−0.5 to 0", "0 to 0.5", "0.5 to 1", "1 to 2", "2 to 5", "≥ 5"]
    bundle = {
        "schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage": {"start": config["start"], "end": config["end"], "days": len(inputs), "scope": "Official Ist-Daten v2 public datastore rail exports (PRODUKT_ID=Zug), paired REAL departure/arrival events at Swiss numeric station IDs. Complete filtered exports verified; nationwide service coverage and equivalence to original uploaded CSV archives are not independently established."},
        "summary": summary(frame), "quality": quality_summary,
        "distributions": {"arrival": histogram(frame["arrival_delay"].to_numpy(), arrival_bins, arrival_labels), "change": histogram(frame["delay_change"].to_numpy(), change_bins, change_labels)},
        "breakdowns": {key: breakdown(frame, key) for key in ["category", "operator", "hour", "operating_date"]},
        "stations": stations, "segments": segments, "models": model_report,
        "journeys": journey_examples(frame, root, model_report),
        "provenance": {"source": "https://data.opentransportdata.swiss/en/dataset/ist-daten-v2", "documentation": "https://opentransportdata.swiss/en/cookbook/historic-and-statistics-cookbook/actual-data/", "terms": "https://opentransportdata.swiss/en/terms-of-use/", "inputs": inputs, "config_sha256": sha256_file(config_path), "python": platform.python_version(), "versions": {package: importlib.metadata.version(package) for package in ["polars", "pyarrow", "numpy", "pandas", "scikit-learn", "scipy"]}, "command": "POLARS_MAX_THREADS=4 OMP_NUM_THREADS=4 python -m research.analyze"},
    }
    # Disallow NaN/infinite values in the actual browser payload.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"Published {output}: {output.stat().st_size:,} bytes, {frame.height:,} eligible segments", flush=True)
    return bundle


if __name__ == "__main__":
    run()
