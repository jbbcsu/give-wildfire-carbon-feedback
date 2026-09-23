#!/usr/bin/env python3
"""Split a validated state CDL grid into deterministic whole-county chunks."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def county_counts(path: Path) -> Counter[str]:
    result: Counter[str] = Counter()
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(batch_size=65536, columns=["county_geoid"]):
        for value in batch.column(0).to_pylist():
            result[str(value).zfill(5)] += 1
    return result


def assign_chunks(counts: Counter[str], maximum_rows: int) -> list[list[str]]:
    if maximum_rows <= 0:
        raise ValueError("maximum rows must be positive")
    chunks: list[list[str]] = []
    current: list[str] = []
    rows = 0
    for county in sorted(counts):
        count = int(counts[county])
        if count > maximum_rows:
            raise ValueError(f"county {county} alone exceeds chunk row limit")
        if current and rows + count > maximum_rows:
            chunks.append(current)
            current = []
            rows = 0
        current.append(county)
        rows += count
    if current:
        chunks.append(current)
    if not chunks:
        raise ValueError("grid selected no counties")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-rows", type=int, default=250000)
    parser.add_argument("--audit-out", type=Path, required=True)
    arguments = parser.parse_args()
    parquet = pq.ParquetFile(arguments.grid)
    counts = county_counts(arguments.grid)
    chunks = assign_chunks(counts, arguments.max_rows)
    county_to_chunk = {
        county: index for index, counties in enumerate(chunks) for county in counties
    }
    arguments.out_dir.mkdir(parents=True, exist_ok=True)
    writers: dict[int, pq.ParquetWriter] = {}
    paths = {
        index: arguments.out_dir / f"grid_chunk_{index:03d}.parquet"
        for index in range(len(chunks))
    }
    rows_written = Counter()
    try:
        for batch in parquet.iter_batches(batch_size=32768):
            county_values = [str(value).zfill(5) for value in batch["county_geoid"].to_pylist()]
            chunk_values = {county_to_chunk[value] for value in county_values}
            for index in sorted(chunk_values):
                selected = pa.array([county_to_chunk[value] == index for value in county_values])
                table = pa.Table.from_batches([batch]).filter(selected)
                if index not in writers:
                    writers[index] = pq.ParquetWriter(
                        paths[index], table.schema, compression="zstd", use_dictionary=True
                    )
                writers[index].write_table(table)
                rows_written[index] += table.num_rows
    finally:
        for writer in writers.values():
            writer.close()
    records = []
    for index, counties in enumerate(chunks):
        path = paths[index]
        expected = sum(counts[county] for county in counties)
        actual = int(rows_written[index])
        if actual != expected or pq.ParquetFile(path).metadata.num_rows != expected:
            raise ValueError(f"chunk {index} row count differs")
        records.append({
            "chunk": index,
            "path": str(path),
            "sha512": sha512(path),
            "rows": actual,
            "counties": counties,
        })
    if sum(row["rows"] for row in records) != parquet.metadata.num_rows:
        raise ValueError("chunk rows do not reconstruct source grid")
    audit = {
        "schema": "cdl_agricultural_grid_county_chunks_v1",
        "source": {
            "path": str(arguments.grid),
            "sha512": sha512(arguments.grid),
            "rows": parquet.metadata.num_rows,
        },
        "maximum_rows_per_chunk": arguments.max_rows,
        "county_count": len(counts),
        "chunk_count": len(records),
        "chunks": records,
        "claim_boundary": "computational partition only; no exposure, response, damage, or SCC result",
    }
    arguments.audit_out.parent.mkdir(parents=True, exist_ok=True)
    arguments.audit_out.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "chunks": len(records), "counties": len(counts),
        "rows": parquet.metadata.num_rows,
        "maximum_chunk_rows": max(row["rows"] for row in records),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
