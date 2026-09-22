#!/usr/bin/env python3
"""Stream the frozen national USDM state-year archive into one bounded panel."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tomllib
from io import BytesIO
from pathlib import Path
from types import ModuleType

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


DOWNLOADER = load_module("usdm_download", HERE / "download_usdm_county_statistics.py")
PREPARER = load_module("usdm_prepare", HERE / "prepare_usdm_county_weeks.py")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest_identities(path: Path) -> dict[str, tuple[int, str]]:
    identities: dict[str, set[tuple[int, str]]] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        name = Path(str(record["file"])).name
        identity = (int(record["bytes"]), str(record["sha512"]).lower())
        if len(identity[1]) != 128:
            raise ValueError(f"manifest line {number} has invalid SHA-512")
        identities.setdefault(name, set()).add(identity)
    conflicts = {name: values for name, values in identities.items() if len(values) != 1}
    if conflicts:
        raise ValueError(f"manifest has conflicting identities for {sorted(conflicts)[:5]}")
    return {name: next(iter(values)) for name, values in identities.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--audit-out", type=Path, required=True)
    parser.add_argument("--area-sum-tolerance", type=float, default=0.15)
    arguments = parser.parse_args()
    contract = tomllib.loads(arguments.config.read_text(encoding="utf-8"))
    states = [str(value).upper() for value in contract["states"]]
    year_min = int(contract["year_min"])
    year_max = int(contract["year_max"])
    expected = len(states) * (year_max - year_min + 1)
    if expected != int(contract["expected_state_year_files"]):
        raise ValueError("config state/year product differs from expected_state_year_files")
    if len(states) != len(set(states)):
        raise ValueError("config contains duplicate states")
    manifest_path = arguments.raw_dir / "MANIFEST.jsonl"
    identities = manifest_identities(manifest_path)
    corrections = {
        (
            str(record["state"]), int(record["query_year"]),
            str(record["county_geoid"]), str(record["map_date"]),
        ): record
        for record in contract.get("source_corrections", [])
    }
    if len(corrections) != len(contract.get("source_corrections", [])):
        raise ValueError("config contains duplicate source corrections")
    corrections_seen: set[tuple[str, int, str, str]] = set()

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    counties: set[str] = set()
    date_min = None
    date_max = None
    file_records = []
    try:
        for state in states:
            for year in range(year_min, year_max + 1):
                name = f"usdm_county_area_pct_{state}_{year}.csv"
                path = arguments.raw_dir / name
                if not path.is_file():
                    raise FileNotFoundError(f"missing frozen USDM input {path}")
                payload = path.read_bytes()
                identity = (len(payload), hashlib.sha512(payload).hexdigest())
                if identities.get(name) != identity:
                    raise ValueError(f"raw/manifest identity mismatch for {name}")
                source_audit = DOWNLOADER.validate_payload(payload, state, year)
                raw = pd.read_csv(BytesIO(payload), dtype={"FIPS": "string"})
                area_columns = ["None", "D0", "D1", "D2", "D3", "D4"]
                sums = raw[area_columns].apply(pd.to_numeric, errors="raise").sum(axis=1)
                anomalous = raw.loc[(sums - 100).abs().gt(arguments.area_sum_tolerance)]
                for index, row in anomalous.iterrows():
                    county_geoid = str(row["FIPS"]).replace(".0", "").zfill(5)
                    key = (state, year, county_geoid, str(row["MapDate"]))
                    correction = corrections.get(key)
                    if correction is None:
                        raise ValueError(f"unregistered category-sum anomaly {key}: {sums.loc[index]}")
                    observed = float(sums.loc[index])
                    if abs(observed - float(correction["observed_category_sum"])) > 1e-9:
                        raise ValueError(f"registered source anomaly changed for {key}")
                    if correction["rule"] != "renormalize six exclusive category percentages to sum to 100":
                        raise ValueError(f"unsupported source correction rule for {key}")
                    raw.loc[index, area_columns] = (
                        pd.to_numeric(raw.loc[index, area_columns], errors="raise")
                        * (100.0 / observed)
                    )
                    corrections_seen.add(key)
                chunk = PREPARER.standardize(raw, arguments.area_sum_tolerance)
                # Adjacent calendar-year API requests can repeat the preceding
                # Tuesday whose validity interval covers January 1. Assign each
                # map once, to its own calendar year; crop-season interval
                # coverage is preserved by the preceding year's file.
                own_year = chunk.map_date.dt.year.eq(year)
                first_year_boundary = (
                    year == year_min
                ) & chunk.valid_end.ge(pd.Timestamp(year_min, 1, 1))
                chunk = chunk.loc[own_year | first_year_boundary].copy()
                if chunk.empty:
                    raise ValueError(f"calendar-year trim removed every row from {name}")
                if set(chunk.state) != {state}:
                    raise ValueError(f"standardized state mismatch for {name}")
                if chunk.duplicated(["county_geoid", "map_date"]).any():
                    raise ValueError(f"duplicate keys within {name}")
                table = pa.Table.from_pandas(chunk, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(
                        arguments.out, table.schema, compression="zstd", use_dictionary=True
                    )
                elif table.schema != writer.schema:
                    raise ValueError(f"Parquet schema drift in {name}")
                writer.write_table(table, row_group_size=100_000)
                total_rows += len(chunk)
                counties.update(map(str, chunk.county_geoid.unique()))
                local_min = chunk.map_date.min().date().isoformat()
                local_max = chunk.map_date.max().date().isoformat()
                date_min = local_min if date_min is None else min(date_min, local_min)
                date_max = local_max if date_max is None else max(date_max, local_max)
                file_records.append({
                    "state": state, "year": year, "file": name,
                    "source": "U.S. Drought Monitor county severity statistics REST service",
                    "url": DOWNLOADER.build_url(state, year),
                    "bytes": identity[0], "sha512": identity[1],
                    "raw_rows": source_audit["rows"], "retained_rows": len(chunk),
                })
    finally:
        if writer is not None:
            writer.close()
    if writer is None or len(file_records) != expected:
        raise RuntimeError("national USDM writer did not consume the frozen file set")
    parquet = pq.ParquetFile(arguments.out)
    if parquet.metadata.num_rows != total_rows:
        raise RuntimeError("Parquet row count does not reconcile with streamed chunks")
    audit = {
        "schema": "usdm_national_county_area_panel_v1",
        "contract": contract,
        "config": {"path": str(arguments.config), "sha256": sha256(arguments.config)},
        "manifest": {"path": str(manifest_path), "sha256": sha256(manifest_path)},
        "files": file_records,
        "file_count": len(file_records),
        "rows": total_rows,
        "counties": len(counties),
        "map_date_min": date_min,
        "map_date_max": date_max,
        "calendar_assignment_rule": (
            "retain each map in its own map-date calendar year, plus the preceding "
            "map carried by the first query when it covers 2001-01-01"
        ),
        "source_corrections_applied": len(corrections_seen),
        "area_basis": "county area; differs from published agricultural-area intersection",
        "source_documentation": "https://droughtmonitor.unl.edu/DmData/DataDownload/WebServiceInfo.aspx",
        "source_attribution": (
            "U.S. Drought Monitor; jointly produced by the National Drought Mitigation "
            "Center at the University of Nebraska-Lincoln, NOAA, and USDA"
        ),
        "output": {"path": str(arguments.out), "sha256": sha256(arguments.out)},
        "role": "historical_external_validation_only_not_future_projection_damage_or_scc",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    if corrections_seen != set(corrections):
        raise RuntimeError("not every frozen source correction was encountered exactly once")
    arguments.audit_out.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {total_rows} county-week rows from {len(file_records)} files; "
        f"counties={len(counties)}; dates={date_min}..{date_max}"
    )


if __name__ == "__main__":
    main()
