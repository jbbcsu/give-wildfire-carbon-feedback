#!/usr/bin/env python3
"""Acquire a bounded, checksummed sequence of official weekly USDM shapes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import tomllib
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import shapefile


URL_TEMPLATE = "https://droughtmonitor.unl.edu/data/shapefiles_m/USDM_{yyyymmdd}_M.zip"


def build_url(map_date: pd.Timestamp) -> str:
    return URL_TEMPLATE.format(yyyymmdd=map_date.strftime("%Y%m%d"))


def expected_base(map_date: pd.Timestamp) -> str:
    return f"USDM_{map_date.strftime('%Y%m%d')}"


def validate_archive(payload: bytes, map_date: pd.Timestamp) -> dict[str, object]:
    if not payload:
        raise ValueError(f"empty USDM archive for {map_date.date()}")
    base = expected_base(map_date)
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        if bad := archive.testzip():
            raise ValueError(f"USDM ZIP CRC failure in {bad}")
        names = set(archive.namelist())
        required = {f"{base}.{suffix}" for suffix in ("shp", "shx", "dbf", "prj")}
        if missing := required - names:
            raise ValueError(f"USDM archive lacks {sorted(missing)}")
        projection = archive.read(f"{base}.prj").decode("utf-8").upper()
        if "WGS_1984" not in projection and "WGS 84" not in projection:
            raise ValueError("USDM shape projection is not documented WGS84")
        reader = shapefile.Reader(
            shp=BytesIO(archive.read(f"{base}.shp")),
            shx=BytesIO(archive.read(f"{base}.shx")),
            dbf=BytesIO(archive.read(f"{base}.dbf")),
        )
        fields = [field[0] for field in reader.fields[1:]]
        if "DM" not in fields:
            raise ValueError("USDM shape lacks DM severity field")
        records = list(reader.iterShapeRecords())
        if not records:
            raise ValueError("USDM shape contains no records")
        dm_position = fields.index("DM")
        severities = [int(item.record[dm_position]) for item in records]
        if not set(severities) <= set(range(5)):
            raise ValueError(f"USDM severity records are not a subset of 0..4: {severities}")
        if any(item.shape.shapeType not in {5, 15, 25} for item in records):
            raise ValueError("USDM archive contains non-polygon geometry")
        return {
            "members": sorted(names),
            "records": len(records),
            "severity_values": sorted(set(severities)),
            "records_by_severity": {
                str(value): severities.count(value) for value in sorted(set(severities))
            },
            "bbox": [
                min(item.shape.bbox[0] for item in records),
                min(item.shape.bbox[1] for item in records),
                max(item.shape.bbox[2] for item in records),
                max(item.shape.bbox[3] for item in records),
            ],
        }


def manifest_identities(path: Path) -> dict[str, set[tuple[int, str]]]:
    identities: dict[str, set[tuple[int, str]]] = {}
    if not path.exists():
        return identities
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            name = Path(str(row["file"])).name
            identity = (int(row["bytes"]), str(row["sha512"]).lower())
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid manifest line {line_number}") from error
        identities.setdefault(name, set()).add(identity)
    conflicts = {name: values for name, values in identities.items() if len(values) > 1}
    if conflicts:
        raise ValueError(f"conflicting pinned archive identities: {sorted(conflicts)[:5]}")
    return identities


def atomic_write(target: Path, payload: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--limit", type=int, help="optional bounded pilot count")
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    start = pd.Timestamp(contract["first_map_date"])
    end = pd.Timestamp(contract["last_map_date"])
    frequency = int(contract["frequency_days"])
    dates = list(pd.date_range(start, end, freq=f"{frequency}D"))
    if len(dates) != int(contract["expected_archives"]):
        raise ValueError("configured date range does not match expected archive count")
    if arguments.limit is not None:
        if arguments.limit <= 0:
            raise ValueError("--limit must be positive")
        dates = dates[: arguments.limit]
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = arguments.out_dir / "MANIFEST.jsonl"
    identities = manifest_identities(manifest)
    with manifest.open("a", encoding="utf-8") as stream:
        for map_date in dates:
            target = arguments.out_dir / f"{expected_base(map_date)}_M.zip"
            if target.is_file() and target.stat().st_size > 0:
                payload = target.read_bytes()
                status = "existing_validated"
            else:
                response = subprocess.run(
                    ["curl", "--fail", "--location", "--silent", "--show-error",
                     "--max-time", str(arguments.timeout_seconds), build_url(map_date)],
                    check=True,
                    capture_output=True,
                )
                payload = response.stdout
                status = "downloaded"
            validation = validate_archive(payload, map_date)
            identity = (len(payload), hashlib.sha512(payload).hexdigest())
            previous = identities.get(target.name, set())
            if previous and identity not in previous:
                raise ValueError(f"archive identity changed for {target.name}")
            if status == "downloaded":
                atomic_write(target, payload)
            if previous and identity in previous:
                print(f"{status}: {target.name} ({identity[0]} bytes; manifest identity unchanged)")
                continue
            now = datetime.now(UTC).isoformat()
            record = {
                "source": "U.S. Drought Monitor weekly map shapefile archive",
                "url": build_url(map_date),
                "map_date": map_date.date().isoformat(),
                "checked_utc": now,
                "retrieved_utc": now if status == "downloaded" else None,
                "status": status,
                "bytes": identity[0],
                "sha512": identity[1],
                "file": str(target),
                **validation,
            }
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            print(f"{status}: {target.name} ({identity[0]} bytes)")


if __name__ == "__main__":
    main()
