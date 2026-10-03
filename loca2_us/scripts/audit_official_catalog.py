#!/usr/bin/env python3
"""Audit official LOCA2 metadata without downloading climate arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any


SCIENCEBASE = {
    "county_v20220519": "https://www.sciencebase.gov/catalog/item/673d0719d34e6b795de6b593?format=json",
    "precip_extremes_v20240915": "https://www.sciencebase.gov/catalog/item/691cfb65d4be021d1d89b487?format=json",
}
STAC = {
    "root": "https://api.water.usgs.gov/gdp/pygeoapi/stac/stac-collection/LOCA2?f=json",
    "historical_daily": "https://api.water.usgs.gov/gdp/pygeoapi/stac/stac-collection/LOCA2/CMIP6-LOCA2.historical.daily?f=json",
    "future_daily": "https://api.water.usgs.gov/gdp/pygeoapi/stac/stac-collection/LOCA2/CMIP6-LOCA2.future.daily?f=json",
}
ZMETADATA = {
    "historical_daily": "https://usgs.osn.mghpcc.org/mdmf/gdp/LOCA2/CMIP6-LOCA2.historical.daily.zarr/.zmetadata",
    "future_daily": "https://usgs.osn.mghpcc.org/mdmf/gdp/LOCA2/CMIP6-LOCA2.future.daily.zarr/.zmetadata",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def fetch_json(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "GIVE-LOCA2-metadata-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        require(len(body) <= 16 * 1024 * 1024, "metadata response exceeds 16 MiB guard")
        content_type = response.headers.get("Content-Type", "")
    return json.loads(body), {
        "url": url,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": content_type,
    }


def sciencebase_summary(payload: dict[str, Any]) -> dict[str, Any]:
    files = [
        {"name": item["name"], "bytes": int(item.get("size", 0)), "url": item.get("url")}
        for item in payload.get("files", [])
    ]
    return {
        "id": payload["id"],
        "title": payload["title"],
        "rights": payload.get("rights"),
        "has_children": bool(payload.get("hasChildren", False)),
        "files": files,
        "total_file_bytes": sum(item["bytes"] for item in files),
    }


def stac_summary(payload: dict[str, Any]) -> dict[str, Any]:
    assets = payload.get("assets", {})
    zarr = assets.get("zarr-s3-osn", {})
    return {
        "id": payload["id"],
        "description": payload.get("description"),
        "extent": payload.get("extent"),
        "zarr_href": zarr.get("href"),
        "zarr_type": zarr.get("type"),
        "storage_options": zarr.get("xarray:storage_options"),
    }


def zmetadata_summary(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload["metadata"]
    variables = sorted(
        key[:-8] for key in metadata if key.endswith("/.zattrs") and key[:-8] in {"pr", "tasmin", "tasmax"}
    )
    result: dict[str, Any] = {
        "global_attributes": metadata[".zattrs"],
        "variables": variables,
        "arrays": {},
    }
    for variable in variables:
        result["arrays"][variable] = {
            "attributes": metadata[f"{variable}/.zattrs"],
            "shape": metadata[f"{variable}/.zarray"]["shape"],
            "chunks": metadata[f"{variable}/.zarray"]["chunks"],
            "dtype": metadata[f"{variable}/.zarray"]["dtype"],
        }
    return result


def build_audit(fetcher=fetch_json) -> dict[str, Any]:
    payloads: dict[str, dict[str, Any]] = {}
    fetches: dict[str, dict[str, Any]] = {}
    source_groups = (
        ("", SCIENCEBASE),
        ("", STAC),
        ("zmetadata_", ZMETADATA),
    )
    for prefix, sources in source_groups:
        for name, url in sources.items():
            key = f"{prefix}{name}"
            require(key not in payloads, f"duplicate metadata key: {key}")
            payloads[key], fetches[key] = fetcher(url)

    county = sciencebase_summary(payloads["county_v20220519"])
    revised = sciencebase_summary(payloads["precip_extremes_v20240915"])
    historical = stac_summary(payloads["historical_daily"])
    future = stac_summary(payloads["future_daily"])
    historical_z = zmetadata_summary(payloads["zmetadata_historical_daily"])
    future_z = zmetadata_summary(payloads["zmetadata_future_daily"])

    def is_cc0(text: str | None) -> bool:
        normalized = (text or "").lower()
        return "cc0" in normalized or "creative commons zero" in normalized

    require(is_cc0(county["rights"]), "county release is not recorded as CC0")
    require(is_cc0(revised["rights"]), "revised extremes release is not recorded as CC0")
    require(future_z["arrays"]["pr"]["attributes"]["LOCA2_version"] == "v20240915", "future precipitation version differs")
    require(historical_z["arrays"]["pr"]["attributes"]["LOCA2_version"] == "v20240915", "historical precipitation version differs")
    require(future_z["variables"] == ["pr", "tasmax", "tasmin"], "future daily variables differ")
    require(historical_z["variables"] == ["pr", "tasmax", "tasmin"], "historical daily variables differ")
    require(future["extent"]["temporal"]["interval"][0] == ["2015-01-01T00:00:00Z", "2100-12-31T00:00:00Z"], "future temporal extent differs")
    require(historical["extent"]["temporal"]["interval"][0] == ["1950-01-01T00:00:00Z", "2014-12-31T00:00:00Z"], "historical temporal extent differs")
    require(future_z["arrays"]["pr"]["chunks"][0] == 1, "future precipitation is not member-chunked")
    require(max(item["bytes"] for item in revised["files"]) > 16 * 1024**3, "revised grid bundle size expectation differs")

    return {
        "schema": "loca2_official_catalog_audit/v1",
        "status": "pass",
        "scope": "metadata_only_no_climate_array_download",
        "sciencebase": {"county_v20220519": county, "precip_extremes_v20240915": revised},
        "stac": {"historical_daily": historical, "future_daily": future},
        "zmetadata": {"historical_daily": historical_z, "future_daily": future_z},
        "fetches": fetches,
        "decisions": {
            "primary_daily_source": "USGS_WMA_STAC_Zarr",
            "precipitation_version": "v20240915",
            "pilot_access": "bounded_Zarr_region_reads",
            "full_national_NetCDF_download": False,
            "official_annual_extremes_role": "climate_validation_not_crop_season_substitute",
            "outcome_fit_authorized": False,
            "causal_damage_or_SCC_claim": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    result = build_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "scope": result["scope"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
