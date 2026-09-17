"""Stream one raw-CMIP6 monthly tas store into cell-area-weighted annual GMST."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from acquire_cmip6_native_cell_area import fetch

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def annualize(monthly, start: int, stop: int):
    """Calendar-second weighted 12-month means, rejecting gaps/duplicates."""
    import math

    by_year = {}
    for row in monthly:
        by_year.setdefault(row["year"], []).append(row)
    if set(by_year) != set(range(start, stop + 1)):
        raise ValueError("GMST year support differs")
    out = []
    for year in range(start, stop + 1):
        rows = sorted(by_year[year], key=lambda r: r["month"])
        if [r["month"] for r in rows] != list(range(1, 13)):
            raise ValueError(f"GMST month support differs: {year}")
        denominator = math.fsum(r["seconds"] for r in rows)
        if denominator not in (365 * 86400, 366 * 86400):
            raise ValueError(f"GMST annual calendar duration differs: {year}")
        value = math.fsum(r["gmst_month_k"] * r["seconds"] for r in rows) / denominator
        if not 150 < value < 350:
            raise ValueError(f"GMST physical range differs: {year}")
        out.append(dict(year=year, gmst_value_k=value, seconds=denominator))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=("GFDL-ESM4", "IPSL-CM6A-LR"), required=True)
    p.add_argument("--experiment", choices=("historical", "ssp126", "ssp585"), required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--dependency-dir", type=Path)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh output required")
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    import numpy as np
    import cftime
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)

    mp = ROOT / "data/interim/pangeo_monthly_store_metadata_20260908/result.json"
    cp = ROOT / "data/interim/pangeo_monthly_coordinates_units_20260908/result.json"
    inv, coords = json.loads(mp.read_text()), json.loads(cp.read_text())
    if coords["metadata_inventory_sha256"] != sha(mp):
        raise ValueError("monthly metadata and coordinate receipts differ")
    selector = lambda r: (r["source"]["source_id"], r["source"]["experiment_id"], r["source"]["variable_id"]) == (args.model, args.experiment, "tas")
    rows = [r for r in inv["records"] if selector(r)]
    axes = [r for r in coords["records"] if selector(r)]
    if len(rows) != 1 or len(axes) != 1:
        raise ValueError("exact same-realization monthly tas source absent")
    row, axis = rows[0], axes[0]
    meta_path = ROOT / row["metadata_file"]
    if sha(meta_path) != row["metadata_sha256"]:
        raise ValueError("monthly tas metadata changed")
    meta = json.loads(meta_path.read_text())["metadata"]
    coordinates = {}
    for chunk in axis["chunks"]:
        path = ROOT / chunk["file"]
        if sha(path) != chunk["sha256"]:
            raise ValueError("monthly tas coordinate chunk changed")
        name = chunk["variable"]
        spec = meta[name + "/.zarray"]
        coordinates[name] = np.frombuffer(
            numcodecs.get_codec(spec["compressor"]).decode(path.read_bytes()),
            dtype=spec["dtype"]).reshape(spec["shape"])
    ta = row["time_attributes"]
    dates = cftime.num2date(coordinates["time"], ta["units"], calendar=ta["calendar"])
    bound_name = ta["bounds"]
    bound_attrs = meta[bound_name + "/.zattrs"]
    bounds = cftime.num2date(coordinates[bound_name], bound_attrs.get("units", ta["units"]), calendar=ta["calendar"])
    seconds = np.array([(hi - lo).total_seconds() for lo, hi in bounds])
    years = np.array([d.year for d in dates])
    months = np.array([d.month for d in dates])
    start, stop = (1981, 2010) if args.experiment == "historical" else (2015, 2100)
    selected = np.flatnonzero((years >= start) & (years <= stop))
    if len(selected) != 12 * (stop - start + 1):
        raise ValueError("selected GMST source months incomplete")
    if not np.isfinite(seconds[selected]).all() or not (seconds[selected] > 0).all():
        raise ValueError("invalid source month durations")

    area_dir = ROOT / f"data/interim/cmip6_{args.model.lower().replace('-', '_')}_native_area_20260917"
    area_receipt_path = area_dir / "result.json"
    area_receipt = json.loads(area_receipt_path.read_text())
    area_path = area_dir / "native_cell_area.npz"
    if area_receipt["model"] != args.model or sha(area_path) != area_receipt["output_sha256"]:
        raise ValueError("native area binding differs")
    with np.load(area_path, allow_pickle=False) as saved:
        area = saved["area_m2"].astype(np.float64)
        if (not np.allclose(saved["latitude"], coordinates["lat"], atol=1e-10, rtol=0)
                or not np.allclose(saved["longitude"], coordinates["lon"], atol=1e-10, rtol=0)):
            raise ValueError("native area and tas coordinates differ")
    area_sum = float(np.sum(area, dtype=np.float64))
    spec = row["variable_array"]
    size = math.prod(spec["chunks"]) * np.dtype(spec["dtype"]).itemsize
    if (size > 192 * 1024**2 or spec["filters"] is not None or spec["order"] != "C"
            or tuple(spec["chunks"][1:]) != area.shape or spec["compressor"]["id"] != "blosc"):
        raise ValueError("unsupported tas chunk size or layout")

    monthly, receipts = [], []
    for chunk_number in sorted(set(selected // spec["chunks"][0])):
        key = f"{int(chunk_number)}.0.0"
        url = row["metadata_url"].removesuffix(".zmetadata") + "tas/" + key
        # A separate compressed-transfer cap keeps the simultaneous input
        # buffer plus decoded chunk well below the sampled 512 MiB guard.
        # The already verified GFDL SSP585 temperature chunk is 107,521,299
        # compressed bytes, so the first 96 MiB cap correctly stopped before
        # decoding it. A 112 MiB cap still leaves the <=192 MiB decoded chunk
        # plus buffers below the sampled 512 MiB worker ceiling.
        content, receipt = fetch(url, min(size + 1024**2, 112 * 1024**2))
        nbytes, cbytes, _ = _cbuffer_sizes(content)
        if nbytes != size or cbytes != len(content):
            raise ValueError("monthly tas compressed chunk header differs")
        decoded = numcodecs.get_codec(spec["compressor"]).decode(content)
        del content
        data = np.frombuffer(decoded, dtype=spec["dtype"]).reshape(spec["chunks"])
        for index in selected[selected // spec["chunks"][0] == chunk_number]:
            plane = data[index % spec["chunks"][0]]
            if not np.isfinite(plane).all() or np.any(plane == spec["fill_value"]):
                raise ValueError("required tas grid month is missing")
            value = float(np.sum(plane.astype(np.float64) * area, dtype=np.float64) / area_sum)
            monthly.append(dict(year=int(years[index]), month=int(months[index]),
                                seconds=float(seconds[index]), gmst_month_k=value))
        receipts.append(receipt)
        del data, decoded
        print("GMST source chunk verified", key, flush=True)
    annual = annualize(monthly, start, stop)
    if len({(r["year"], r["month"]) for r in monthly}) != len(monthly):
        raise ValueError("duplicate GMST source month")
    args.out_dir.mkdir(parents=True)
    result = dict(status="raw_cmip6_annual_gmst_built", source=row["source"], license=row["license"],
                  calendar=ta["calendar"], years=[start, stop], annual=annual, monthly=monthly,
                  source_chunks=receipts, area_receipt_sha256=sha(area_receipt_path),
                  area_output_sha256=sha(area_path), source_metadata_sha256=sha(meta_path),
                  coordinate_receipt_sha256=sha(cp), code_sha256=sha(Path(__file__)),
                  limitation="Raw-CMIP6 area-weighted annual GMST only; no precipitation response, agricultural outcome, damage, or SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False))
    print(result["status"], args.model, args.experiment, len(annual), flush=True)


if __name__ == "__main__":
    main()
