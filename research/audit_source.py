"""Small, dependency-free official-source audit. Not an analysis/model pipeline.

Run from the repository root; use --help. CSV fixture tests use synthetic data.
No dataset schema or status meaning is assumed before actual source inspection.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import zipfile


API = "https://data.opentransportdata.swiss/api/3/action/package_show"
USER_AGENT = "SwissRailDelayLab/0.1 (independent research source audit)"


def get_bytes(url, max_bytes):
    if urlsplit(url).scheme != "https":
        raise ValueError("Only HTTPS source URLs are accepted")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        if urlsplit(response.url).scheme != "https":
            raise ValueError("Source redirected to an insecure URL")
        advertised = response.headers.get("Content-Length")
        if advertised and int(advertised) > max_bytes:
            raise ValueError("Source exceeds the configured byte budget")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("Source exceeds the configured byte budget")
        return body, response.url


def resource_inventory(body):
    payload = json.loads(body)
    if payload.get("success") is not True or not isinstance(payload.get("result"), dict):
        raise ValueError("Source did not return a successful CKAN package result")
    package = payload["result"]
    resources = package.get("resources")
    if not isinstance(resources, list):
        raise ValueError("Metadata has no resource list")
    return {
        "dataset": {k: package.get(k) for k in (
            "id", "name", "title", "notes", "license_id", "license_title",
            "license_url", "metadata_created", "metadata_modified", "url",
        )},
        "resources": [{k: r.get(k) for k in (
            "id", "name", "description", "url", "format", "size", "hash",
            "created", "last_modified", "mimetype",
        )} for r in resources],
    }


def inspect_csv(stream, max_rows=10000):
    # First-row sample is for schema discovery only, never representative EDA.
    if max_rows < 1:
        raise ValueError("max_rows must be positive")
    sample = stream.read(65536)
    if not sample:
        raise ValueError("Empty CSV source")
    stream.seek(0)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t,")
    except csv.Error as error:
        raise ValueError("Cannot determine CSV delimiter; inspect source manually") from error
    reader = csv.DictReader(stream, dialect=dialect)
    fields = reader.fieldnames
    if not fields or len(set(fields)) != len(fields):
        raise ValueError("Missing or duplicate column names")
    status_fields = [f for f in fields if "STATUS" in f.upper()]
    statuses = {f: Counter() for f in status_fields}
    missing = Counter()
    rows = 0
    for row in reader:
        if rows == max_rows:
            break
        if None in row or any(v is None for v in row.values()):
            raise ValueError("CSV row does not match the header")
        rows += 1
        for field, value in row.items():
            if not value.strip():
                missing[field] += 1
        for field in status_fields:
            statuses[field][row[field]] += 1
    return {
        "columns": fields, "delimiter": dialect.delimiter,
        "sample_rows": rows, "max_rows": max_rows,
        "sampling": "First rows only; not representative of the dataset",
        "missing_in_sample": {field: missing[field] for field in fields},
        "status_tokens_in_sample": {field: dict(counts) for field, counts in statuses.items()},
        "status_semantics": "Not inferred; verify current official documentation",
    }


def inspect_file(path, max_rows, max_expanded_bytes):
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.infolist() if m.filename.lower().endswith(".csv") and not m.is_dir()]
            if len(members) != 1:
                raise ValueError("Expected one CSV in the daily archive; inspect the archive inventory first")
            member = members[0]
            if member.file_size > max_expanded_bytes:
                raise ValueError("Expanded CSV exceeds the byte budget; explicitly raise it after inspecting metadata")
            with archive.open(member) as binary:
                with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
                    result = inspect_csv(stream, max_rows)
            return {"archive_member": member.filename, **result}
    if path.stat().st_size > max_expanded_bytes:
        raise ValueError("CSV exceeds the byte budget")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return inspect_csv(stream, max_rows)


def save_json(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["metadata", "sample", "inspect"])
    parser.add_argument("--dataset", default="ist-daten-v2")
    parser.add_argument("--resource-id", help="Exact ID from retrieved metadata; no automatic bulk downloads")
    parser.add_argument("--file", type=Path, help="Local source for the inspect command")
    parser.add_argument("--output", type=Path, default=Path("data/audit/source-audit.json"))
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--max-mb", type=int, default=64, help="Maximum download bytes in MiB")
    parser.add_argument("--max-expanded-mb", type=int, default=256)
    parser.add_argument("--max-rows", type=int, default=10000)
    args = parser.parse_args(argv)
    if min(args.max_mb, args.max_expanded_mb, args.max_rows) < 1:
        parser.error("Budgets and row count must be positive")
    if args.command == "sample" and not args.resource_id:
        parser.error("sample requires --resource-id from the official inventory")
    if args.command == "inspect" and not args.file:
        parser.error("inspect requires --file")
    report = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "command": args.command, "status": "started"}
    try:
        if args.command == "inspect":
            report["inspection"] = inspect_file(args.file, args.max_rows, args.max_expanded_mb * 1024**2)
        else:
            report["metadata_url"] = API + "?" + urlencode({"id": args.dataset})
            body, _ = get_bytes(report["metadata_url"], 16 * 1024**2)
            report.update(resource_inventory(body))
            if args.command == "sample":
                matches = [r for r in report["resources"] if r["id"] == args.resource_id]
                if len(matches) != 1:
                    raise ValueError("Resource ID is not unique/present in official metadata")
                resource = matches[0]
                body, resolved = get_bytes(resource["url"], args.max_mb * 1024**2)
                digest = hashlib.sha256(body).hexdigest()
                args.raw_dir.mkdir(parents=True, exist_ok=True)
                suffix = ".zip" if zipfile.is_zipfile(io.BytesIO(body)) else ".csv"
                raw_path = args.raw_dir / (digest + suffix)
                if raw_path.exists():
                    if hashlib.sha256(raw_path.read_bytes()).hexdigest() != digest:
                        raise ValueError("Existing raw file fails its content hash")
                else:
                    raw_path.write_bytes(body)
                report["download"] = {"resource": resource, "resolved_url": resolved, "bytes": len(body), "sha256": digest, "local_file": str(raw_path)}
                report["inspection"] = inspect_file(raw_path, args.max_rows, args.max_expanded_mb * 1024**2)
        report["status"] = "success"
    except (HTTPError, URLError, ValueError, OSError, csv.Error, UnicodeError, zipfile.BadZipFile) as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        report["error"] = str(error)
        save_json(args.output, report)
        print(f"Source audit failed ({type(error).__name__}); evidence saved to {args.output}", file=sys.stderr)
        return 2
    save_json(args.output, report)
    print(f"Source audit saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
