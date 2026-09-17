"""Fetch and validate small native-grid CMIP6 area fields for monthly GMST."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "GFDL-ESM4": "https://storage.googleapis.com/cmip6/CMIP6/CMIP/NOAA-GFDL/GFDL-ESM4/historical/r1i1p1f1/fx/areacella/gr1/v20190726/",
    "IPSL-CM6A-LR": "https://storage.googleapis.com/cmip6/CMIP6/CMIP/IPSL/IPSL-CM6A-LR/historical/r1i1p1f1/fx/areacella/gr/v20180803/",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked_area(area, latitude, longitude):
    """Reject missing/misaligned/nonphysical source areas before using GMST."""
    import numpy as np

    if area.shape != (len(latitude), len(longitude)):
        raise ValueError("area shape differs from native climate grid")
    if not np.isfinite(area).all() or not (area > 0).all():
        raise ValueError("cell areas must be finite and strictly positive")
    total = float(np.sum(area, dtype=np.float64))
    sphere = 4 * math.pi * 6371000.0**2
    if not 0.98 * sphere <= total <= 1.02 * sphere:
        raise ValueError("cell areas do not sum to approximately Earth surface")
    return total


def fetch(url: str, max_bytes: int):
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-precipitation-research/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(max_bytes + 1)
        headers = dict(response.headers)
        server_hash = ",".join(response.headers.get_all("x-goog-hash", []))
    if not data or len(data) > max_bytes:
        raise ValueError(f"public source exceeds registered transfer bound: {url}")
    md5 = next((p.strip()[4:] for p in server_hash.split(",") if p.strip().startswith("md5=")), None)
    if md5 and base64.b64encode(hashlib.md5(data).digest()).decode() != md5:
        raise ValueError("public source checksum mismatch")
    return data, dict(url=url, bytes=len(data), sha256=digest(data),
                      server_md5_verified=bool(md5), headers=headers)


def decode_chunk(base: str, name: str, metadata: dict, np, numcodecs, cbuffer_sizes):
    spec = metadata[f"{name}/.zarray"]
    shape = tuple(spec["shape"])
    if (spec["compressor"]["id"] != "blosc" or spec["filters"] is not None
            or spec["order"] != "C" or tuple(spec["chunks"]) != shape):
        raise ValueError(f"unsupported static grid layout: {name}")
    size = math.prod(shape) * np.dtype(spec["dtype"]).itemsize
    if size > 2 * 1024**2:
        raise ValueError("static grid chunk exceeds 2 MiB decoded bound")
    key = ".".join("0" for _ in shape)
    data, receipt = fetch(base + name + "/" + key, 2 * 1024**2)
    nbytes, cbytes, _ = cbuffer_sizes(data)
    if nbytes != size or cbytes != len(data):
        raise ValueError("static grid compressed header differs from metadata")
    values = np.frombuffer(numcodecs.get_codec(spec["compressor"]).decode(data),
                           dtype=spec["dtype"]).reshape(shape).copy()
    if not np.isfinite(values).all() or np.any(values == spec["fill_value"]):
        raise ValueError(f"missing static grid values: {name}")
    return values, receipt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=tuple(SOURCES), required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--dependency-dir", type=Path)
    args = p.parse_args()
    if args.out_dir.exists():
        raise ValueError("fresh output required")
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))
    import numpy as np
    import numcodecs
    from numcodecs.blosc import _cbuffer_sizes, set_nthreads
    set_nthreads(1)

    base = SOURCES[args.model]
    raw, metadata_receipt = fetch(base + ".zmetadata", 512 * 1024)
    metadata = json.loads(raw)["metadata"]
    attrs = metadata[".zattrs"]
    expected_grid = "gr1" if args.model == "GFDL-ESM4" else "gr"
    if (attrs["source_id"], attrs["experiment_id"], attrs["variant_label"], attrs["grid_label"]) != (args.model, "historical", "r1i1p1f1", expected_grid):
        raise ValueError("static area source identity differs")
    if metadata["areacella/.zattrs"]["units"] != "m2":
        raise ValueError("area units differ")
    if "Creative Commons" not in attrs.get("license", ""):
        raise ValueError("source license not declared")
    latitude, lat_receipt = decode_chunk(base, "lat", metadata, np, numcodecs, _cbuffer_sizes)
    longitude, lon_receipt = decode_chunk(base, "lon", metadata, np, numcodecs, _cbuffer_sizes)
    area, area_receipt = decode_chunk(base, "areacella", metadata, np, numcodecs, _cbuffer_sizes)
    total = checked_area(area, latitude, longitude)

    matrix_path = ROOT / "data/interim/pangeo_monthly_reduction_matrix_20260908/result.json"
    matrix = json.loads(matrix_path.read_text())
    matches = [r for r in matrix["records"] if r["source"]["source_id"] == args.model]
    if len(matches) != 6:
        raise ValueError("exact historical/SSP pr/tas source matrix absent")
    bindings = []
    for row in matches:
        result_path = ROOT / row["directory"] / "result.json"
        receipt = json.loads(result_path.read_text())
        if digest(result_path.read_bytes()) != row["result_sha256"]:
            raise ValueError("monthly reduction receipt hash differs")
        path = ROOT / row["directory"] / "native_monthly_climatologies.npz"
        if digest(path.read_bytes()) != receipt["output_sha256"]:
            raise ValueError("monthly reduction array hash differs")
        with np.load(path, allow_pickle=False) as saved:
            # The static and monthly GFDL coordinate payloads differ by
            # only 1e-14-degree serialization roundoff. Use a fixed absolute
            # tolerance far below any grid-spacing or interpolation scale.
            if (not np.allclose(saved["lat"], latitude, rtol=0, atol=1e-10)
                    or not np.allclose(saved["lon"], longitude, rtol=0, atol=1e-10)):
                if saved["lat"].shape != latitude.shape or saved["lon"].shape != longitude.shape:
                    raise ValueError(f"static area and {row['source']} climate coordinate shapes differ")
                raise ValueError(
                    f"static area and {row['source']} climate coordinates differ: "
                    f"max |lat|={float(np.max(np.abs(saved['lat']-latitude))):.9g}, "
                    f"max |lon|={float(np.max(np.abs(saved['lon']-longitude))):.9g}; "
                    f"first static/climate lat={latitude[0]}/{saved['lat'][0]}, "
                    f"lon={longitude[0]}/{saved['lon'][0]}")
        bindings.append(dict(source=row["source"], result_sha256=row["result_sha256"]))

    args.out_dir.mkdir(parents=True)
    output = args.out_dir / "native_cell_area.npz"
    np.savez_compressed(output, latitude=latitude, longitude=longitude, area_m2=area)
    result = dict(status="native_cell_area_verified", model=args.model,
                  source_base=base, source_metadata=metadata_receipt,
                  source_chunks=dict(latitude=lat_receipt, longitude=lon_receipt, area=area_receipt),
                  source_identity={k: attrs[k] for k in ("source_id", "experiment_id", "variant_label", "grid_label")},
                  source_license=attrs["license"], native_shape=list(area.shape),
                  total_area_m2=total, monthly_bindings=bindings,
                  monthly_matrix_sha256=digest(matrix_path.read_bytes()),
                  output_sha256=digest(output.read_bytes()),
                  code_sha256=digest(Path(__file__).read_bytes()),
                  limitation="Exact raw-CMIP6 grid-area input only; not a GMT response, rainfall change, crop outcome, or SCC.")
    (args.out_dir / "result.json").write_text(json.dumps(result, indent=2))
    print(result["status"], args.model, area.shape, total, flush=True)


if __name__ == "__main__":
    main()
