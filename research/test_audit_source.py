"""Synthetic parser fixtures only. These tests do not validate official data."""

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError
import zipfile

from research.audit_source import get_bytes, inspect_csv, inspect_file, main, resource_inventory


class AuditTests(unittest.TestCase):
    def test_csv_tokens_and_missingness_are_literal(self):
        result = inspect_csv(io.StringIO("ID;EVENT_STATUS;VALUE\na;REAL;\nb;UNKNOWN;2\nc;FORECAST;3\n"))
        self.assertEqual(result["sample_rows"], 3)
        self.assertEqual(result["status_tokens_in_sample"]["EVENT_STATUS"], {"REAL": 1, "UNKNOWN": 1, "FORECAST": 1})
        self.assertEqual(result["missing_in_sample"]["VALUE"], 1)
        self.assertIn("Not inferred", result["status_semantics"])

    def test_sampling_budget_and_invalid_schema(self):
        result = inspect_csv(io.StringIO("ID;VALUE\na;1\nb;2\n"), 1)
        self.assertEqual(result["sample_rows"], 1)
        with self.assertRaises(ValueError):
            inspect_csv(io.StringIO("ID;ID\na;b\n"))
        with self.assertRaises(ValueError):
            inspect_csv(io.StringIO("ID;VALUE\na;1;extra\n"))

    def test_inventory_retains_license_and_exact_resource_urls(self):
        payload = {"success": True, "result": {"name": "synthetic-fixture", "license_id": "fixture-only", "resources": [{"id": "r1", "url": "https://example.org/day.csv", "size": 123}]}}
        result = resource_inventory(json.dumps(payload))
        self.assertEqual(result["dataset"]["license_id"], "fixture-only")
        self.assertEqual(result["resources"][0]["url"], "https://example.org/day.csv")
        with self.assertRaises(ValueError):
            resource_inventory('{"success":false}')

    def test_failed_access_persists_evidence_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "audit.json"
            with patch("research.audit_source.get_bytes", side_effect=URLError("fixture: proxy denied")):
                code = main(["metadata", "--output", str(output)])
            self.assertEqual(code, 2)
            report = json.loads(output.read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["error_type"], "URLError")
            self.assertNotIn("resources", report)

    def test_download_budget_and_https_are_enforced(self):
        class Response(io.BytesIO):
            url = "https://example.org/fixture.csv"
            headers = {}

        with patch("research.audit_source.urlopen", return_value=Response(b"12345")):
            with self.assertRaisesRegex(ValueError, "byte budget"):
                get_bytes("https://example.org/fixture.csv", 4)
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            get_bytes("http://example.org/fixture.csv", 4)

    def test_zipped_csv_inspection_does_not_extract_members(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("daily.csv", "ID;VALUE\na;1\nb;2\n")
            self.assertEqual(inspect_file(path, 10, 1024)["sample_rows"], 2)
            self.assertFalse((Path(folder) / "daily.csv").exists())
            with self.assertRaisesRegex(ValueError, "byte budget"):
                inspect_file(path, 10, 1)

    def test_sample_records_provenance_and_inspects_mocked_source(self):
        payload = {"success": True, "result": {"name": "synthetic-fixture", "resources": [{"id": "r1", "url": "https://example.org/day.csv"}]}}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "report.json"
            with patch("research.audit_source.get_bytes", side_effect=[
                (json.dumps(payload).encode(), "https://example.org/metadata"),
                (b"ID;VALUE\na;1\nb;2\n", "https://example.org/day.csv"),
            ]):
                code = main(["sample", "--resource-id", "r1", "--output", str(output), "--raw-dir", str(Path(folder) / "raw")])
            report = json.loads(output.read_text())
            self.assertEqual(code, 0)
            self.assertEqual(report["inspection"]["sample_rows"], 2)
            self.assertEqual(len(report["download"]["sha256"]), 64)
            self.assertTrue(Path(report["download"]["local_file"]).is_file())


if __name__ == "__main__":
    unittest.main()
