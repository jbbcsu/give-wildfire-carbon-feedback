#!/usr/bin/env python3
"""Acquire, verify, and selectively extract MIRCA-OS v2 area grids.

Raw inputs remain under data/raw and are excluded from Git. The exact source
archive identity is pinned here and in the tracked provenance record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
from typing import BinaryIO, Callable
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/"
    "data/contents/Annual%20Harvested%20Area%20Grids/Annual%20Harvested%20Area%20Grids.rar"
)
ARCHIVE_NAME = "Annual_Harvested_Area_Grids_v2.rar"
EXPECTED_SIZE = 284005995
EXPECTED_MD5 = "c9243bf18d1b31b50ebd9cbfa0f9b3ab"
EXPECTED_SHA512 = "7f60928c50f86c129de90b8d8056c5fbdc640dc03613a2a610f4c5fe412b83bd911ac7d836d91495525b11f4a8ed93e68af95d2c1ece4ddc83c1208ce4fc7600"
YEARS = {2000: "00", 2005: "05", 2010: "10", 2015: "15", 2020: "20"}
CROPS = ("Maize", "Rice", "Soybeans", "Wheat")
SYSTEMS = ("ir", "rf")


def digests(path: Path) -> tuple[str, str]:
    md5 = hashlib.md5(usedforsecurity=False)
    sha512 = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            md5.update(block)
            sha512.update(block)
    return md5.hexdigest(), sha512.hexdigest()


def verify_archive(
    path: Path,
    *,
    expected_size: int = EXPECTED_SIZE,
    expected_md5: str = EXPECTED_MD5,
    expected_sha512: str = EXPECTED_SHA512,
) -> dict[str, object]:
    if path.stat().st_size != expected_size:
        raise ValueError(f"Archive byte length differs: {path.stat().st_size} != {expected_size}")
    md5, sha512 = digests(path)
    if md5 != expected_md5 or sha512 != expected_sha512:
        raise ValueError("Archive checksum differs from the pinned HydroShare object")
    return {"size_bytes": expected_size, "md5": md5, "sha512": sha512}


def selected_members() -> list[str]:
    return [
        f"{folder}/30-arcminute/MIRCA-OS_{crop}_{year}_{system}_30arcmin_v2.tif"
        for year, folder in YEARS.items()
        for crop in CROPS
        for system in SYSTEMS
    ]


def download(destination: Path, opener: Callable[..., BinaryIO] = urlopen) -> None:
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = Request(SOURCE_URL, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=1800) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=8 * 1024 * 1024)
        verify_archive(partial)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def extract_selected(archive: Path, destination: Path) -> list[Path]:
    executable = shutil.which("bsdtar")
    if executable is None:
        raise RuntimeError("Selective RAR extraction requires bsdtar/libarchive")
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [executable, "-xf", str(archive), "-C", str(destination), *selected_members()],
        check=True,
    )
    extracted = [destination / member for member in selected_members()]
    missing = [str(path) for path in extracted if not path.is_file()]
    if missing:
        raise RuntimeError(f"Selective extraction is incomplete: {missing[:3]}")
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/raw/mirca_os_v2")
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / ARCHIVE_NAME
    status = "existing"
    if not archive.exists():
        download(archive)
        status = "downloaded"
    identity = verify_archive(archive)
    extracted: list[Path] = []
    if not args.skip_extract:
        extracted = extract_selected(archive, out_dir / "extracted_30arcmin")
    record = {
        "source_url": SOURCE_URL,
        "landing_page": "https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/",
        "license": "CC-BY-4.0",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "status": status,
        "archive": str(archive),
        **identity,
        "selected_extracted_files": len(extracted),
        "role": "fixed irrigation exposure-weight input; not response, damage, or SCC",
    }
    (out_dir / "SOURCE_MANIFEST.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
