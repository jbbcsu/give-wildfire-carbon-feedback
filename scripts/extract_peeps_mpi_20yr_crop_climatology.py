#!/usr/bin/env python3
"""Stream one verified MPI Zarr chunk into 20-year crop-center month sums."""
import argparse
import base64
import calendar
import hashlib
import json
from pathlib import Path
import shutil
import ssl
import sys
import urllib.request

import certifi

from reconstruct_peeps_mpi_ssp585_rainfall import crc32c


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "data/interim/peeps_mpi_ssp585_metadata_20260917/result.json"
COORDINATES = ROOT / "data/interim/peeps_mpi_ssp585_coordinates_v2_20260917/result.json"
MAPPING = ROOT / "data/interim/peeps_mpi_crop_mapping_20260917/result.json"
EXPECTED = {
    METADATA: "96d0057abb0776eec9dc55aa137fa5c3313622404e6afb3ce3045c77432113c0",
    COORDINATES: "0c77d5a44c35f5aec0d6fc14a8630e28177d038c1e81af1833a64464d955092b",
    MAPPING: "abd8058f696eca10c3c614bdc24db32830e38f41808ee1960234248c5ee2fa9c",
}
CHUNKS = {"r1i1p1f1": (0, 1), "r2i1p1f1": (0, 1, 3, 4)}
PERIODS = {"early": (2015, 2034), "late": (2081, 2100)}
MAX_COMPRESSED = 160 * 2**20


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def selected_months(first, chunk_index):
    """Return selected (period, year, month, local plane) tuples."""
    selection = []
    for local in range(min(first, 1032 - chunk_index*first)):
        time_index = chunk_index*first + local
        year, month0 = 2015 + time_index//12, time_index % 12
        for period, (start, end) in PERIODS.items():
            if start <= year <= end:
                selection.append((period, year, month0+1, local))
    return selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member", choices=tuple(CHUNKS), required=True)
    parser.add_argument("--chunk-index", type=int, required=True)
    parser.add_argument("--dependency-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.out_dir.resolve()
    dependency = args.dependency_dir.resolve()
    if (output.exists() or not output.is_relative_to(ROOT / "data/interim")
            or not dependency.is_relative_to(ROOT / "data/interim")
            or args.chunk_index not in CHUNKS[args.member]
            or shutil.disk_usage(ROOT).free < 130 * 2**30):
        parser.error("frozen chunk, ignored fresh output/dependency, disk reserve required")
    for path, expected in EXPECTED.items():
        if sha(path) != expected:
            raise ValueError("frozen source manifest changed: " + str(path))
    sys.path.insert(0, str(dependency))
    import numpy as np
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)
    metadata = json.loads(METADATA.read_text())
    coordinates = json.loads(COORDINATES.read_text())
    mapping = json.loads(MAPPING.read_text())
    if (coordinates["source_member_variable_axes_equal"] is not True
            or coordinates["metadata_sha256"] != EXPECTED[METADATA]
            or mapping["status"] != "verified_peeps_native_rainfed_maize_center_mapping_not_exposure"):
        raise ValueError("coordinate/mapping source gate changed")
    mapping_file = MAPPING.parent / "mapping.npz"
    if sha(mapping_file) != mapping["mapping_sha256"]:
        raise ValueError("crop mapping array changed")
    with np.load(mapping_file, allow_pickle=False) as saved:
        ii, jj, hectares = saved["ii"].astype(int), saved["jj"].astype(int), saved["hectares"].astype(float)
    if (len(ii) != 30821 or len(jj) != len(ii) or len(hectares) != len(ii)
            or not np.isfinite(hectares).all() or not np.all(hectares > 0)):
        raise ValueError("crop-center support changed")
    matches = [item for item in metadata["records"] if item["variable"] == "pr" and item["member_id"] == args.member]
    if len(matches) != 1:
        raise ValueError("precipitation member not unique")
    record = matches[0]
    meta_path = METADATA.parent / record["metadata_file"]
    if sha(meta_path) != record["metadata_sha256"]:
        raise ValueError("member metadata changed")
    spec = json.loads(meta_path.read_text())["metadata"]["pr/.zarray"]
    if (spec["dtype"] != "<f4" or spec["filters"] is not None or spec["order"] != "C"
            or spec["compressor"]["id"] != "blosc" or spec["chunks"][1:] != [192, 384]
            or spec["shape"] != [1032, 192, 384]):
        raise ValueError("Zarr precipitation layout changed")
    first = spec["chunks"][0]
    selected = selected_months(first, args.chunk_index)
    if not selected or len(set((p, y, m) for p, y, m, _ in selected)) != len(selected):
        raise ValueError("expected selected period-month planes missing or duplicated")
    key = f"{args.chunk_index}.0.0"
    url = record["metadata_url"].removesuffix(".zmetadata") + "pr/" + key
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-precipitation-research/1.0",
                                                  "Accept-Encoding": "identity"})
    with urllib.request.urlopen(request, context=ssl.create_default_context(cafile=certifi.where()), timeout=120) as response:
        if response.status != 200 or response.headers.get("Content-Encoding"):
            raise ValueError("unexpected source HTTP response")
        declared = response.headers.get("Content-Length")
        if declared is not None and int(declared) > MAX_COMPRESSED:
            raise ValueError("compressed source chunk over cap")
        content = response.read(MAX_COMPRESSED + 1)
        source_hash = ",".join(response.headers.get_all("x-goog-hash", []))
    if len(content) > MAX_COMPRESSED or (declared is not None and len(content) != int(declared)):
        raise ValueError("source chunk length changed")
    checks = {}
    for kind in ("crc32c", "md5"):
        match = [item.strip().split("=", 1)[1] for item in source_hash.split(",") if item.strip().startswith(kind + "=")]
        observed = crc32c(content) if kind == "crc32c" else base64.b64encode(hashlib.md5(content).digest()).decode()
        if match and match != [observed]:
            raise ValueError("source GCS " + kind + " differs")
        checks[kind] = bool(match)
    content_sha = hashlib.sha256(content).hexdigest()
    decoded_bytes, compressed_bytes, _ = _cbuffer_sizes(content)
    plane_bytes = 192*384*4
    count_expected = min(first, 1032 - args.chunk_index*first)
    if compressed_bytes != len(content) or decoded_bytes not in (count_expected*plane_bytes, first*plane_bytes):
        raise ValueError("decoded chunk allocation differs")
    decoded = numcodecs.get_codec(spec["compressor"]).decode(content)
    del content
    if len(decoded) != decoded_bytes:
        raise ValueError("decoded chunk length differs")
    cube = np.frombuffer(decoded, dtype="<f4").reshape(decoded_bytes//plane_bytes, 192, 384)
    sums = {period: np.zeros((12, len(ii)), dtype=np.float64) for period in PERIODS}
    counts = {period: np.zeros(12, dtype=np.int64) for period in PERIODS}
    negative_native = 0
    for period, year, month, local in selected:
        plane = cube[local]
        if not np.isfinite(plane).all() or np.any(plane == spec["fill_value"]):
            raise ValueError("selected source plane missing/nonfinite")
        negative_native += int(np.count_nonzero(plane < 0))
        if np.any(plane < 0):
            raise ValueError("selected source plane has negative rainfall")
        sums[period][month-1] += plane[ii, jj].astype(np.float64)*86400*calendar.monthrange(year, month)[1]
        counts[period][month-1] += 1
    del cube, decoded
    output.mkdir(parents=True)
    artifact = output / "monthly_crop_center_partial.npz"
    np.savez_compressed(artifact, ii=ii, jj=jj, hectares=hectares,
                        **{f"{period}_sum_mm": sums[period] for period in PERIODS},
                        **{f"{period}_counts": counts[period] for period in PERIODS})
    result = {
        "status": "single_source_chunk_20yr_partial_not_climate_response_or_scc",
        "member": args.member, "chunk_index": args.chunk_index,
        "periods": {name: list(years) for name, years in PERIODS.items()},
        "source_manifest_sha256": EXPECTED[METADATA],
        "coordinate_manifest_sha256": EXPECTED[COORDINATES],
        "mapping_manifest_sha256": EXPECTED[MAPPING],
        "source_url": url, "source_compressed_bytes": compressed_bytes,
        "source_compressed_sha256": content_sha,
        "gcs_crc32c_verified": checks["crc32c"], "gcs_md5_verified": checks["md5"],
        "decoded_bytes": decoded_bytes, "selected_plane_count": len(selected),
        "selected_native_negative_cells": negative_native,
        "partial_counts": {name: counts[name].tolist() for name in PERIODS},
        "partial_array_sha256": sha(artifact),
        "crop_center_count": len(ii), "rainfed_maize_area_ha": float(hectares.sum()),
        "yield_damage_scc_estimated": False,
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "member", "chunk_index", "selected_plane_count", "gcs_crc32c_verified")}))


if __name__ == "__main__":
    main()
