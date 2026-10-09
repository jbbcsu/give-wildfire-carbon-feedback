#!/usr/bin/env python3
"""Download and verify the public Moore et al. (2026) GIVE replication archive."""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path


URL = (
    "https://zenodo.org/api/records/21483095/files/"
    "lrennels/paper-2026-give-labor-ag-v1.0.1.zip/content"
)
EXPECTED_MD5 = "0c20052410bce36831e56b2a599aa243"
ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "moore_2026"
ARCHIVE = VENDOR / "paper-2026-give-labor-ag-v1.0.1.zip"


def md5(path: Path) -> str:
    digest = hashlib.md5()  # nosec B324: integrity check required by Zenodo metadata
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists() or md5(ARCHIVE) != EXPECTED_MD5:
        temporary = ARCHIVE.with_suffix(".zip.part")
        with urllib.request.urlopen(URL) as response, temporary.open("wb") as target:
            shutil.copyfileobj(response, target, length=1024 * 1024)
        if md5(temporary) != EXPECTED_MD5:
            raise RuntimeError("Downloaded archive does not match Zenodo MD5")
        temporary.replace(ARCHIVE)

    with zipfile.ZipFile(ARCHIVE) as source:
        source.extractall(VENDOR)
    print(f"verified and extracted {ARCHIVE}")


if __name__ == "__main__":
    main()

