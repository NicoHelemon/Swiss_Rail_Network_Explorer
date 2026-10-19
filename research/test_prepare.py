"""Synthetic fixtures test sequence integrity; no synthetic records enter analyses."""

from datetime import date
from pathlib import Path
import unittest

import polars as pl

from research.acquire import resources_for_dates
from research.prepare import REQUIRED, event_pairs, parse_time


def stop(index, station, clock, status="REAL", cancelled="false", event_date="14.09.2026"):
    row = {column: None for column in REQUIRED}
    row.update({
        "_id": str(index), "BETRIEBSTAG": "14.09.2026", "FAHRT_BEZEICHNER": "fixture-journey",
        "BETREIBER_ID": "fixture-operator", "BETREIBER_ABK": "Fixture", "PRODUKT_ID": "Zug",
        "VERKEHRSMITTEL_TEXT": "Fixture", "BPUIC": station, "HALTESTELLEN_NAME": station,
        "ANKUNFTSZEIT": f"14.09.2026 {clock}", "ABFAHRTSZEIT": f"14.09.2026 {clock}",
        "AN_PROGNOSE": f"{event_date} {clock}:30", "AB_PROGNOSE": f"{event_date} {clock}:30",
        "AN_PROGNOSE_STATUS": status, "AB_PROGNOSE_STATUS": status,
        "FAELLT_AUS_TF": cancelled, "DURCHFAHRT_TF": "false",
    })
    return row


def frame(rows):
    return pl.DataFrame(rows, schema={c: pl.String for c in REQUIRED})


class PreparationTests(unittest.TestCase):
    def test_delays_are_signed_and_duration_identity_holds(self):
        pairs, _ = event_pairs(frame([stop(1, "8500001", "08:00"), stop(2, "8500002", "08:05")]))
        self.assertEqual(pairs.height, 1)
        self.assertEqual(pairs["departure_delay"][0], .5)
        self.assertEqual(pairs["arrival_delay"][0], .5)
        self.assertAlmostEqual(pairs["observed_minutes"][0] - pairs["scheduled_minutes"][0], pairs["delay_change"][0])

    def test_unreliable_or_cancelled_middle_stop_is_never_bridged(self):
        for status, cancelled in [("PROGNOSE", "false"), ("REAL", "true")]:
            pairs, _ = event_pairs(frame([
                stop(1, "8500001", "08:00"), stop(2, "8500002", "08:05", status, cancelled), stop(3, "8500003", "08:10"),
            ]))
            self.assertEqual(pairs.height, 0)

    def test_foreign_stop_is_not_removed_before_pairing(self):
        pairs, _ = event_pairs(frame([stop(1, "8500001", "08:00"), stop(2, "8100001", "08:05"), stop(3, "8500003", "08:10")]))
        self.assertEqual(pairs.height, 0)

    def test_ambiguous_order_excludes_whole_journey(self):
        pairs, quality = event_pairs(frame([stop(1, "8500001", "08:00"), stop(2, "8500002", "08:00"), stop(3, "8500003", "08:10")]))
        self.assertEqual(pairs.height, 0)
        self.assertEqual(quality["ambiguous_journeys_excluded"], 1)

    def test_duplicate_rows_do_not_create_new_connections(self):
        first = stop(1, "8500001", "08:00")
        duplicate = {**first, "_id": "999"}
        pairs, quality = event_pairs(frame([first, duplicate, stop(2, "8500002", "08:05")]))
        self.assertEqual(pairs.height, 1)
        self.assertEqual(quality["identical_duplicate_rows_removed"], 1)

    def test_date_offset_anomaly_is_excluded_without_rewriting_times(self):
        pairs, quality = event_pairs(frame([stop(1, "8500001", "08:00", event_date="13.09.2026"), stop(2, "8500002", "08:05", event_date="13.09.2026")]))
        self.assertEqual(pairs.height, 0)
        self.assertEqual(quality["delay_bound_sensitivity"][-1]["retained_pairs"], 1)
        self.assertEqual(len(quality["extreme_date_examples"]), 1)

    def test_timezone_dst_ambiguity_is_explicitly_null(self):
        values = pl.DataFrame({"t": ["25.10.2026 02:30", "29.03.2026 02:30", "14.09.2026 08:00"]})
        parsed = values.select(parse_time("t"))["t"]
        self.assertIsNone(parsed[0]); self.assertIsNone(parsed[1])
        self.assertEqual(parsed[2].hour, 6)

    def test_date_selection_requires_all_requested_days(self):
        inventory = {"resources": [{"name": "2026-09-14_istdaten.csv", "id": "fixture"}]}
        self.assertEqual(resources_for_dates(inventory, date(2026, 9, 14), date(2026, 9, 14))[0][1], "2026-09-14")
        with self.assertRaises(ValueError):
            resources_for_dates(inventory, date(2026, 9, 14), date(2026, 9, 15))


if __name__ == "__main__":
    unittest.main()
