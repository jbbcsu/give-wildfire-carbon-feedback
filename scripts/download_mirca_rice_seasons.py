#!/usr/bin/env python3
"""Acquire and selectively extract MIRCA-OS v2 rice-season source files.

The 1.54 GB archive and calendar tables remain under ignored data/raw. Exact
byte lengths and local SHA-512 digests are pinned before any extraction.
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


BASE = "https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/data/contents"
ARCHIVE = {
    "url": f"{BASE}/Monthly%20Growing%20Area%20Grids/Monthly%20Growing%20Area%20Grids.rar",
    "name": "Monthly_Growing_Area_Grids_v2.rar",
    "size": 1537240142,
    "sha512": "b01ca694d47967024bc8544037a381a6f267503dfeb12ea0b89dcc1ed23b35bdb8b8ce1cd5af014169f5616c12a2facc960ae8f8b0209bdc4adf6d768cb56a7c",
    "hydroshare_checksum": "0a5495c3d24e9611c571940b0e03b8ab-15",
}
CALENDARS = (
    {
        "system": "ir",
        "url": f"{BASE}/Crop%20Calendar/MIRCA-OS_2000_ir_v2.csv",
        "name": "MIRCA-OS_2000_ir_v2.csv",
        "size": 9264277,
        "sha512": "76af4b0c55012e693ce2926c249c65cb7d1efe7e1484fb298751ceb3d0bfd284e196a36a63038febe248faf3c05a60e3b90e5b21649bc396dd3567914765c836",
        "hydroshare_checksum": "2772eff73a28e8a379935402ae5dc993-1",
    },
    {
        "system": "rf",
        "url": f"{BASE}/Crop%20Calendar/MIRCA-OS_2000_rf_v2.csv",
        "name": "MIRCA-OS_2000_rf_v2.csv",
        "size": 9295446,
        "sha512": "9d0beb530f39f751918dfa2193625b0361e6aa4a3a0940bf551379e0fbc401031b366453a3952bde831a8c8b920e64f9876b5901e330f66db5358ea81181a558",
        "hydroshare_checksum": "b021ccd74a6ed455e2eaa73ae360d35c-1",
    },
)
YEARS = (2000, 2005, 2010, 2015, 2020)
SEASONS = (1, 2, 3)
SYSTEMS = ("ir", "rf")


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_file(path: Path, expected_size: int, expected_sha512: str) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Missing source file {path}")
    if path.stat().st_size != expected_size:
        raise ValueError(f"Byte length differs for {path}: {path.stat().st_size} != {expected_size}")
    observed_sha512 = sha512(path)
    if observed_sha512 != expected_sha512:
        raise ValueError(f"SHA-512 differs for {path}")
    return {"size_bytes": expected_size, "sha512": observed_sha512}


def one_part_etag(path: Path) -> str:
    content_md5 = hashlib.md5(path.read_bytes(), usedforsecurity=False).digest()
    return hashlib.md5(content_md5, usedforsecurity=False).hexdigest() + "-1"


def download(
    source_url: str,
    destination: Path,
    expected_size: int,
    expected_sha512: str,
    opener: Callable[..., BinaryIO] = urlopen,
) -> None:
    partial = destination.with_suffix(destination.suffix + ".partial")
    partial.unlink(missing_ok=True)
    request = Request(source_url, headers={"User-Agent": "GIVE-precipitation-SCC/1.0"})
    try:
        with opener(request, timeout=3600) as response, partial.open("wb") as target:
            shutil.copyfileobj(response, target, length=8 * 1024 * 1024)
        verify_file(partial, expected_size, expected_sha512)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def selected_members() -> list[str]:
    return [
        f"{year}/MIRCA-OS_Rice{season}_{year}_{system}.nc"
        for year in YEARS
        for season in SEASONS
        for system in SYSTEMS
    ]


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
    root = Path(args.out_dir)
    root.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    archive_path = root / str(ARCHIVE["name"])
    archive_status = "existing"
    if not archive_path.exists():
        download(
            str(ARCHIVE["url"]), archive_path, int(ARCHIVE["size"]), str(ARCHIVE["sha512"])
        )
        archive_status = "downloaded"
    archive_record = {
        "kind": "monthly_archive",
        "source_url": ARCHIVE["url"],
        "path": str(archive_path),
        "status": archive_status,
        "hydroshare_checksum": ARCHIVE["hydroshare_checksum"],
        **verify_file(archive_path, int(ARCHIVE["size"]), str(ARCHIVE["sha512"])),
    }
    records.append(archive_record)

    calendar_dir = root / "crop_calendar"
    calendar_dir.mkdir(parents=True, exist_ok=True)
    for definition in CALENDARS:
        path = calendar_dir / str(definition["name"])
        status = "existing"
        if not path.exists():
            download(
                str(definition["url"]), path, int(definition["size"]), str(definition["sha512"])
            )
            status = "downloaded"
        identity = verify_file(path, int(definition["size"]), str(definition["sha512"]))
        if one_part_etag(path) != definition["hydroshare_checksum"]:
            raise ValueError(f"HydroShare one-part object identity differs for {path}")
        records.append(
            {
                "kind": "calendar_csv",
                "system": definition["system"],
                "source_url": definition["url"],
                "path": str(path),
                "status": status,
                "hydroshare_checksum": definition["hydroshare_checksum"],
                **identity,
            }
        )

    extracted: list[Path] = []
    if not args.skip_extract:
        extracted = extract_selected(archive_path, root / "monthly_rice")
    manifest = {
        "schema_version": 1,
        "landing_page": "https://www.hydroshare.org/resource/e4582ca0042148338bb5e0148b749ed6/",
        "license": "CC-BY-4.0",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "records": records,
        "selected_member_count": len(selected_members()),
        "selected_extracted_files": len(extracted),
        "role": "candidate rice-season irrigation weights; not response, damage, or SCC",
    }
    (root / "RICE_SEASON_SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
