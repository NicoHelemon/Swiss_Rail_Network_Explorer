"""Stream official public catalogue exports; no authentication or cloud storage needed."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from research.audit_source import USER_AGENT, fetch_inventory, save_json


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        while chunk := source.read(1024**2):
            digest.update(chunk)
    return digest.hexdigest()


def export_url(resource_id, **parameters):
    parameters = {
        "filters": json.dumps({"PRODUKT_ID": "Zug"}, separators=(",", ":")),
        "bom": "True", **parameters,
    }
    return f"https://data.opentransportdata.swiss/en/datastore/dump/{resource_id}?" + urlencode(parameters)


def fetch_page(url):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=90) as response:
        body = response.read(32 * 1024**2 + 1)
        if len(body) > 32 * 1024**2:
            raise ValueError("One export page exceeds the bounded response size")
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames
    if not fields or fields[:3] != ["_id", "BETRIEBSTAG", "FAHRT_BEZEICHNER"]:
        raise ValueError("Official export did not have the expected CSV header")
    rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError("Malformed CSV page; no rows from this page are accepted")
    return fields, rows, hashlib.sha256(body).hexdigest()


def highest_rail_id(resource_id):
    _, rows, _ = fetch_page(export_url(resource_id, sort="_id desc", limit=1))
    if len(rows) != 1 or rows[0]["PRODUKT_ID"] != "Zug":
        raise ValueError("Expected exactly one highest-ID rail record")
    return int(rows[0]["_id"])


def download(resource, day, root=Path("data"), max_bytes=256 * 1024**2):
    """Page the official, server-filtered rail export and verify its high-water ID.

    A large unbounded dump was observed to stop at a 32,000-row boundary while
    more records existed. HTTP EOF alone is therefore NOT a completeness check.
    This export is not assumed byte-identical to the original uploaded archive.
    """
    root = Path(root)
    path = root / "raw" / f"{day}-rail.csv"
    manifest_path = root / "audit" / f"{day}-download.json"
    if path.exists():
        if not manifest_path.exists():
            raise ValueError(f"Preserving existing {path}: no download manifest")
        manifest = json.loads(manifest_path.read_text())
        if not manifest.get("coverage_verified") or sha256_file(path) != manifest["sha256"]:
            raise ValueError(f"Cache integrity failure: {path}")
        if manifest["resource_id"] != resource["id"]:
            raise ValueError("Cached resource ID does not match the catalogue")
        print(f"Verified cached daily file: {day}", flush=True)
        return manifest
    expected_last = highest_rail_id(resource["id"])
    part = path.with_suffix(".csv.part")
    if part.exists():
        raise ValueError(f"Incomplete previous download at {part}; inspect/remove it explicitly before retrying")
    path.parent.mkdir(parents=True, exist_ok=True)
    total_rows, last_id, pages = 0, 0, []
    started = time.monotonic()
    try:
        fields = None
        with part.open("x", encoding="utf-8", newline="") as target:
            writer = None
            while last_id < expected_last:
                url = export_url(resource["id"], sort="_id", offset=total_rows, limit=32000)
                columns, rows, page_hash = fetch_page(url)
                if not rows or len(rows) > 32000:
                    raise ValueError("Empty/oversized page before reaching the source's last rail record")
                if fields is None:
                    fields = columns
                    writer = csv.DictWriter(target, fieldnames=fields)
                    writer.writeheader()
                elif fields != columns:
                    raise ValueError("CSV schema changed across pages")
                ids = [int(row["_id"]) for row in rows]
                if ids[0] <= last_id or any(a >= b for a, b in zip(ids, ids[1:])):
                    raise ValueError("Repeated/nonmonotonic IDs: pagination may be ignored or inconsistent")
                if any(row["PRODUKT_ID"] != "Zug" for row in rows):
                    raise ValueError("Source ignored the rail filter")
                expected_date = date.fromisoformat(day).strftime("%d.%m.%Y")
                if any(row["BETRIEBSTAG"] != expected_date for row in rows):
                    raise ValueError("Unexpected operating date in source page")
                writer.writerows(rows)
                last_id = ids[-1]
                pages.append({"offset": total_rows, "rows": len(rows), "first_id": ids[0], "last_id": last_id, "response_sha256": page_hash})
                total_rows += len(rows)
                target.flush()
                if target.tell() > max_bytes:
                    raise ValueError("Daily rail export exceeds safety byte budget")
                print(f"{day}: {total_rows:,} rail rows; last ID {last_id:,}/{expected_last:,}, {time.monotonic() - started:.0f}s", flush=True)
        if last_id != expected_last or highest_rail_id(resource["id"]) != expected_last:
            raise ValueError("Source high-water ID changed or was not reached")
        _, beyond, _ = fetch_page(export_url(resource["id"], sort="_id", offset=total_rows, limit=1))
        if beyond:
            raise ValueError("More rail records exist beyond downloaded offset")
        manifest = {
            "source_url": export_url(resource["id"]), "catalogue_resource_url": resource["url"],
            "resource_id": resource["id"], "service_date": day,
            "source": "Official catalogue CSV datastore export",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "bytes": part.stat().st_size, "sha256": sha256_file(part), "complete_download": True,
            "coverage_verified": True, "source_filter": {"PRODUKT_ID": "Zug"},
            "rows": total_rows, "last_source_id": last_id, "pages": pages,
            "completeness_check": "Ascending nonoverlapping pages; matching highest filtered ID before/after; empty page beyond final row offset. This verifies the public datastore rail subset, not equivalence to the original uploaded CSV or all Swiss services.",
        }
        part.rename(path)
        save_json(manifest_path, manifest)
        print(f"{day}: verified complete rail export, {total_rows:,} rows", flush=True)
        return manifest
    except Exception:
        # Preserve .part as explicit evidence; never treat it as a completed day.
        raise


def resources_for_dates(inventory, start, end):
    if end < start:
        raise ValueError("End date precedes start date")
    index = {}
    for resource in inventory["resources"]:
        name = resource.get("name") or ""
        try:
            day = date.fromisoformat(name[:10])
        except ValueError:
            continue
        if day in index:
            raise ValueError(f"Duplicate daily resources for {day}")
        index[day] = resource
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    missing = [str(day) for day in days if day not in index]
    if missing:
        raise ValueError(f"Dates absent from current official catalogue: {missing}; inspect archive separately")
    return [(index[day], day.isoformat()) for day in days]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--workers", type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    inventory = fetch_inventory("ist-daten-v2")
    save_json(args.root / "audit" / "inventory.json", inventory)
    selected = resources_for_dates(inventory, args.start, args.end)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda item: download(*item, root=args.root), selected))


if __name__ == "__main__":
    main()
