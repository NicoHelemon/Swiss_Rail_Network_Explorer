"""Synthetic fixtures check temporal separation and feature leakage, not performance."""

from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

import numpy as np
import polars as pl

from research.model import FEATURES, chronological_split, features, metrics


class ModelTests(unittest.TestCase):
    def test_signed_error_definition(self):
        result = metrics(np.array([1., 2.]), np.array([2., 4.]))
        self.assertEqual(result["mae"], 1.5)
        self.assertEqual(result["mean_error"], 1.5)
        self.assertAlmostEqual(result["rmse"], np.sqrt(2.5))

    def test_target_and_future_travel_time_do_not_enter_features(self):
        row = {"departure_delay": 1., "scheduled_minutes": 5., "hour": 8, "station_id": "a", "next_station_id": "b", "category": "S", "operator": "fixture", "weekday": 1, "arrival_delay": 2., "observed_minutes": 6.}
        first = features(pl.DataFrame([row]))
        changed = features(pl.DataFrame([{**row, "arrival_delay": 9999., "observed_minutes": 9999.}]))
        self.assertTrue(first.equals(changed))
        self.assertEqual(list(first.columns), FEATURES)

    def test_journeys_crossing_partition_boundaries_are_purged(self):
        def instant(value):
            return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
        data = pl.DataFrame({
            "journey_key": ["train", "train", "crossing", "validation", "test"],
            "operating_date": ["2026-09-14", "2026-09-14", "2026-09-21", "2026-09-22", "2026-09-25"],
            "event_departure": [instant(t) for t in ["2026-09-14T08:00", "2026-09-14T08:05", "2026-09-21T21:59", "2026-09-22T08:00", "2026-09-25T08:00"]],
            "next_event_arrival": [instant(t) for t in ["2026-09-14T08:04", "2026-09-14T08:09", "2026-09-21T22:05", "2026-09-22T08:05", "2026-09-25T08:05"]],
        })
        split = chronological_split(data, {"validation_start": "2026-09-22", "test_start": "2026-09-25"})
        self.assertEqual(split["train"].height, 2)
        self.assertEqual(split["purged"]["journey_key"].to_list(), ["crossing"])
        self.assertEqual(split["test"]["journey_key"].to_list(), ["test"])


if __name__ == "__main__":
    unittest.main()
