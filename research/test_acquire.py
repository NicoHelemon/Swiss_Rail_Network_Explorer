"""Acquisition must detect a truncated successful HTTP export, not just return 200."""

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.acquire import download


FIELDS = ["_id", "BETRIEBSTAG", "FAHRT_BEZEICHNER", "PRODUKT_ID"]


def row(identifier):
    return {"_id": str(identifier), "BETRIEBSTAG": "14.09.2026", "FAHRT_BEZEICHNER": "fixture", "PRODUKT_ID": "Zug"}


def page(rows):
    return FIELDS, rows, "synthetic-fixture-hash"


class AcquisitionTests(unittest.TestCase):
    def test_pages_are_continued_until_actual_last_record_and_empty_tail(self):
        responses = [page([row(9)]), page([row(1), row(4)]), page([row(9)]), page([row(9)]), page([])]
        with tempfile.TemporaryDirectory() as folder:
            with patch("research.acquire.fetch_page", side_effect=responses):
                result = download({"id": "fixture", "url": "https://example.org/day.csv"}, "2026-09-14", Path(folder))
            self.assertTrue(result["coverage_verified"])
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["last_source_id"], 9)
            self.assertEqual(result["pages"][1]["offset"], 2)

    def test_http_eof_short_of_high_water_id_is_rejected(self):
        responses = [page([row(9)]), page([row(1), row(4)]), page([])]
        with tempfile.TemporaryDirectory() as folder:
            with patch("research.acquire.fetch_page", side_effect=responses):
                with self.assertRaisesRegex(ValueError, "before reaching"):
                    download({"id": "fixture", "url": "https://example.org/day.csv"}, "2026-09-14", Path(folder))
            self.assertFalse((Path(folder) / "audit/2026-09-14-download.json").exists())

    def test_ignored_offset_and_repeated_ids_are_rejected(self):
        responses = [page([row(9)]), page([row(1), row(4)]), page([row(1), row(4)])]
        with tempfile.TemporaryDirectory() as folder:
            with patch("research.acquire.fetch_page", side_effect=responses):
                with self.assertRaisesRegex(ValueError, "Repeated/nonmonotonic"):
                    download({"id": "fixture", "url": "https://example.org/day.csv"}, "2026-09-14", Path(folder))


if __name__ == "__main__":
    unittest.main()
