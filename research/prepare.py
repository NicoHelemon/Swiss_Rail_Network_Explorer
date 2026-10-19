"""Validate daily official exports, preserve sequence before exclusions, create paired events."""

import argparse
import json
from pathlib import Path

import polars as pl

from research.acquire import sha256_file
from research.audit_source import save_json


REQUIRED = [
    "_id", "BETRIEBSTAG", "FAHRT_BEZEICHNER", "BETREIBER_ID", "BETREIBER_ABK",
    "PRODUKT_ID", "VERKEHRSMITTEL_TEXT", "LINIEN_TEXT", "BPUIC", "HALTESTELLEN_NAME",
    "ANKUNFTSZEIT", "AN_PROGNOSE", "AN_PROGNOSE_STATUS", "ABFAHRTSZEIT",
    "AB_PROGNOSE", "AB_PROGNOSE_STATUS", "FAELLT_AUS_TF", "DURCHFAHRT_TF",
]
SCHEMA_VERSION = 1


def parse_time(column):
    return pl.coalesce(
        pl.col(column).str.strptime(pl.Datetime, "%d.%m.%Y %H:%M:%S", strict=False),
        pl.col(column).str.strptime(pl.Datetime, "%d.%m.%Y %H:%M", strict=False),
    ).dt.replace_time_zone("Europe/Zurich", ambiguous="null", non_existent="null").dt.convert_time_zone("UTC")


def minutes(later, earlier):
    return (pl.col(later) - pl.col(earlier)).dt.total_seconds() / 60


def event_pairs(frame):
    """No filtered-out middle stop can become an inferred adjacent connection.

    Adjacency means consecutive recorded calls ordered by planned event time;
    source completeness is not independently established by a GTFS crosswalk.
    Whole journeys with missing/tied planned ordering times are excluded.
    """
    quality = {"rail_rows": frame.height}
    identity_columns = [c for c in frame.columns if c != "_id"]
    frame = frame.unique(subset=identity_columns, maintain_order=True)
    quality["identical_duplicate_rows_removed"] = quality["rail_rows"] - frame.height
    for flag in ["FAELLT_AUS_TF", "DURCHFAHRT_TF"]:
        values = set(frame[flag].drop_nulls().unique().to_list())
        if not values.issubset({"true", "false"}):
            raise ValueError(f"Unrecognized boolean values in {flag}: {values}")
    frame = frame.with_columns(
        pl.concat_str(["BETRIEBSTAG", "BETREIBER_ID", "FAHRT_BEZEICHNER"], separator="|").alias("journey_key"),
        parse_time("ANKUNFTSZEIT").alias("scheduled_arrival"),
        parse_time("ABFAHRTSZEIT").alias("scheduled_departure"),
        parse_time("AN_PROGNOSE").alias("event_arrival"),
        parse_time("AB_PROGNOSE").alias("event_departure"),
        pl.col("FAELLT_AUS_TF").fill_null("false").eq("true").alias("cancelled"),
        pl.col("DURCHFAHRT_TF").fill_null("false").eq("true").alias("pass_through"),
        pl.col("BPUIC").str.contains(r"^85[0-9]{5}([0-9]{2})?$").fill_null(False).alias("swiss_numeric_id"),
        pl.col("BPUIC").str.slice(0, 7).alias("station_id"),
    ).with_columns(
        pl.coalesce("scheduled_arrival", "scheduled_departure").alias("planned_order"),
        (
            (pl.col("AN_PROGNOSE_STATUS") == "REAL") & (pl.col("AB_PROGNOSE_STATUS") == "REAL")
            & pl.col("event_arrival").is_not_null() & pl.col("event_departure").is_not_null()
            & (pl.col("event_departure") < pl.col("event_arrival"))
        ).fill_null(False).alias("inconsistent_real_dwell"),
    )
    quality["journeys_before_order_checks"] = frame["journey_key"].n_unique()
    quality["rail_rows_without_swiss_numeric_id"] = frame.filter(~pl.col("swiss_numeric_id")).height
    bad = frame.group_by("journey_key").agg(
        pl.col("planned_order").is_null().any().alias("missing_order"),
        (pl.col("planned_order").n_unique() != pl.len()).alias("tied_order"),
        pl.any_horizontal(pl.col("BETREIBER_ID").is_null(), pl.col("FAHRT_BEZEICHNER").is_null()).any().alias("missing_identity"),
    ).filter(pl.any_horizontal("missing_order", "tied_order", "missing_identity"))
    quality["ambiguous_journeys_excluded"] = bad.height
    ordered = frame.join(bad.select("journey_key"), on="journey_key", how="anti", nulls_equal=True).sort(["journey_key", "planned_order"])
    ordered = ordered.with_columns(pl.int_range(pl.len()).over("journey_key").alias("stop_index"))
    columns = [
        "BPUIC", "station_id", "HALTESTELLEN_NAME", "scheduled_arrival", "scheduled_departure",
        "event_arrival", "AN_PROGNOSE_STATUS", "cancelled", "pass_through", "swiss_numeric_id", "inconsistent_real_dwell",
    ]
    pairs = ordered.with_columns(*[pl.col(c).shift(-1).over("journey_key").alias("next_" + c) for c in columns])
    pairs = pairs.filter(pl.col("next_BPUIC").is_not_null())
    quality["consecutive_recorded_pairs"] = pairs.height
    funnel = []

    def retain(name, predicate):
        nonlocal pairs
        before = pairs.height
        pairs = pairs.filter(predicate.fill_null(False))
        funnel.append({"step": name, "before": before, "excluded": before - pairs.height, "retained": pairs.height})

    retain("Both stops have Swiss 7/9-digit numeric IDs", pl.col("swiss_numeric_id") & pl.col("next_swiss_numeric_id"))
    retain("Neither record is cancelled or pass-through", ~pl.any_horizontal("cancelled", "next_cancelled", "pass_through", "next_pass_through"))
    retain("No contradictory REAL arrival/departure order within either call", ~pl.any_horizontal("inconsistent_real_dwell", "next_inconsistent_real_dwell"))
    retain("Departure A and arrival B statuses are both REAL", (pl.col("AB_PROGNOSE_STATUS") == "REAL") & (pl.col("next_AN_PROGNOSE_STATUS") == "REAL"))
    retain("Required scheduled and REAL timestamps are present", pl.all_horizontal(*[pl.col(c).is_not_null() for c in ["scheduled_departure", "next_scheduled_arrival", "event_departure", "next_event_arrival"]]))
    pairs = pairs.with_columns(
        minutes("event_departure", "scheduled_departure").alias("departure_delay"),
        minutes("next_event_arrival", "next_scheduled_arrival").alias("arrival_delay"),
        minutes("next_scheduled_arrival", "scheduled_departure").alias("scheduled_minutes"),
        minutes("next_event_arrival", "event_departure").alias("observed_minutes"),
    )
    retain("Positive scheduled segment and chronological realized events", (pl.col("scheduled_minutes") > 0) & (pl.col("observed_minutes") >= 0))
    retain("Different normalized stations", pl.col("station_id") != pl.col("next_station_id"))
    quality["delay_bound_sensitivity"] = [
        {
            "absolute_delay_bound_minutes": bound,
            "retained_pairs": pairs.filter((pl.col("departure_delay").abs() <= bound) & (pl.col("arrival_delay").abs() <= bound)).height if bound is not None else pairs.height,
        }
        for bound in [60, 180, 720, None]
    ]
    quality["extreme_date_examples"] = pairs.filter(
        (pl.col("departure_delay").abs() > 720) | (pl.col("arrival_delay").abs() > 720)
    ).select("journey_key", "BPUIC", "next_BPUIC", "departure_delay", "arrival_delay").head(5).to_dicts()
    retain("Absolute delay at most 12 hours: declared date-integrity guard", (pl.col("departure_delay").abs() <= 720) & (pl.col("arrival_delay").abs() <= 720))
    pairs = pairs.with_columns(
        (pl.col("arrival_delay") - pl.col("departure_delay")).alias("delay_change"),
        pl.col("scheduled_departure").dt.convert_time_zone("Europe/Zurich").dt.hour().alias("hour"),
        pl.col("scheduled_departure").dt.convert_time_zone("Europe/Zurich").dt.weekday().alias("weekday"),
        pl.col("scheduled_departure").dt.convert_time_zone("Europe/Zurich").dt.date().cast(pl.String).alias("scheduled_date"),
        pl.col("BETRIEBSTAG").str.strptime(pl.Date, "%d.%m.%Y").cast(pl.String).alias("operating_date"),
        pl.col("VERKEHRSMITTEL_TEXT").fill_null("Unknown").alias("category"),
        pl.col("BETREIBER_ABK").fill_null("Unknown").alias("operator"),
    ).select(
        "journey_key", "stop_index", "operating_date", "scheduled_date", "station_id", "next_station_id",
        pl.col("HALTESTELLEN_NAME").alias("station"), pl.col("next_HALTESTELLEN_NAME").alias("next_station"),
        "operator", "category", "LINIEN_TEXT", "scheduled_departure", "next_scheduled_arrival",
        "event_departure", "next_event_arrival", "departure_delay", "arrival_delay", "delay_change",
        "scheduled_minutes", "observed_minutes", "hour", "weekday",
    )
    quality["funnel"] = funnel
    quality["retained_pairs"] = pairs.height
    quality["retained_journeys"] = pairs["journey_key"].n_unique()
    return pairs, quality


def prepare(path, root=Path("data")):
    path, root = Path(path), Path(root)
    day = path.name[:10]
    manifest = json.loads((root / "audit" / f"{day}-download.json").read_text())
    if not manifest.get("coverage_verified") or sha256_file(path) != manifest["sha256"]:
        raise ValueError("Incomplete or corrupted raw source")
    source = pl.scan_csv(path, infer_schema=False, ignore_errors=False, truncate_ragged_lines=False)
    missing = set(REQUIRED) - set(source.collect_schema().names())
    if missing:
        raise ValueError(f"Required columns missing: {missing}")
    dates = source.select(pl.col("BETRIEBSTAG").unique()).collect()["BETRIEBSTAG"].to_list()
    if dates != [__import__("datetime").date.fromisoformat(day).strftime("%d.%m.%Y")]:
        raise ValueError(f"Unexpected operating dates: {dates}")
    overview = source.select(pl.len()).collect().item()
    if overview != manifest["rows"]:
        raise ValueError("Parsed row count differs from the verified acquisition manifest")
    products = source.group_by("PRODUKT_ID").len().collect().to_dicts()
    rail = source.filter(pl.col("PRODUKT_ID") == "Zug").collect()
    status_counts = rail.group_by("AN_PROGNOSE_STATUS", "AB_PROGNOSE_STATUS").len().sort("len", descending=True).to_dicts()
    operator_counts = rail.group_by("BETREIBER_ABK").len().sort("len", descending=True).to_dicts()
    pairs, quality = event_pairs(rail)
    quality.update({"schema_version": SCHEMA_VERSION, "date": day, "source_rows": overview, "products": products, "rail_status_combinations": status_counts, "rail_operators": operator_counts, "input_sha256": manifest["sha256"]})
    (root / "processed").mkdir(parents=True, exist_ok=True)
    output = root / "processed" / f"{day}.parquet"
    pairs.write_parquet(output)
    quality["parquet_sha256"] = sha256_file(output)
    save_json(root / "audit" / f"{day}-quality.json", quality)
    print(f"{day}: {overview:,} source rows; {rail.height:,} rail rows; {pairs.height:,} REAL/REAL adjacent pairs", flush=True)
    return quality


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=Path("data"))
    args = parser.parse_args()
    for path in args.files:
        prepare(path, args.root)


if __name__ == "__main__":
    main()
