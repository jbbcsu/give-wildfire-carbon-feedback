#!/usr/bin/env python3
"""Mocked tests for bounded, credential-safe Quick Stats fallback."""
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

SCRIPT = Path(__file__).with_name("download_nass_quickstats_api.py")
spec = importlib.util.spec_from_file_location("nass_api", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.DEFAULT_SECRETS == SCRIPT.resolve().parents[2] / ".secrets" / "nass.env"


class Response:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def args() -> SimpleNamespace:
    return SimpleNamespace(
        commodity="CORN", unit="BU / ACRE", year_min=2020, year_max=2020,
        source="SURVEY", series_discovery=False,
        prodn_practice="ALL PRODUCTION PRACTICES", util_practice="GRAIN",
    )


parameters = module.query_parameters(args())
assert parameters["agg_level_desc"] == "COUNTY"
assert parameters["freq_desc"] == "ANNUAL"
assert parameters["domain_desc"] == "TOTAL"
assert parameters["reference_period_desc"] == "YEAR"
assert parameters["util_practice_desc"] == "GRAIN"
assert parameters["year"] == "2020"
assert "year__GE" not in parameters and "year__LE" not in parameters

discovery_args = args()
discovery_args.series_discovery = True
discovery_args.unit = None
discovery_args.util_practice = None
discovery = module.query_parameters(discovery_args)
assert "unit_desc" not in discovery
assert "prodn_practice_desc" not in discovery
assert module.safe_stem(args()) == (
    "quickstats_corn_grain_all_production_practices_county_yield_2020"
)

calls: list[str] = []
def row(value, county_code):
    return {
        "Value": value,
        "year": 2020,
        "county_code": county_code,
        "source_desc": "SURVEY",
        "sector_desc": "CROPS",
        "commodity_desc": "CORN",
        "statisticcat_desc": "YIELD",
        "agg_level_desc": "COUNTY",
        "freq_desc": "ANNUAL",
        "reference_period_desc": "YEAR",
        "domain_desc": "TOTAL",
        "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
        "util_practice_desc": "GRAIN",
        "unit_desc": "BU / ACRE",
    }

def opener(request, timeout):
    parsed = urlparse(request.full_url)
    query = parse_qs(parsed.query)
    calls.append(parsed.path)
    assert query["key"] == ["test-key"]
    if parsed.path.endswith("/get_counts/"):
        return Response({"count": "2"})
    return Response({"data": [row("200", "001"), row("(D)", "003")]})

assert module.count_records(parameters, "test-key", opener) == 2
response = module.request_json(module.DATA_ENDPOINT, parameters, "test-key", opener)
with tempfile.TemporaryDirectory() as directory:
    raw, manifest = module.write_result(response, parameters, 2, Path(directory), "test")
    assert raw.exists() and manifest.exists()
    assert "test-key" not in raw.read_text(encoding="utf-8")
    record = json.loads(manifest.read_text(encoding="utf-8"))
    assert "key" not in record["query_parameters_excluding_key"]
    assert record["preflight_count"] == 2
assert calls == ["/api/get_counts/", "/api/api_GET/"]

data_called = False
def oversized_opener(request, timeout):
    global data_called
    path = urlparse(request.full_url).path
    if path.endswith("/api_GET/"):
        data_called = True
    return Response({"count": "50001"})

assert module.count_records(parameters, "test-key", oversized_opener) == 50001
assert not data_called

bad = {"data": [row("200", "001"), {**row("(D)", "003"), "year": 2021}]}
with tempfile.TemporaryDirectory() as directory:
    try:
        module.write_result(bad, parameters, 2, Path(directory), "bad")
    except RuntimeError as error:
        assert "violated requested year" in str(error)
    else:
        raise AssertionError("response rows outside the requested year should fail")

with tempfile.TemporaryDirectory() as directory:
    secrets = Path(directory) / "nass.env"
    secrets.write_text("NASS_API_KEY=secret-never-print\n", encoding="utf-8")
    assert module.read_key(secrets) == "secret-never-print"
    try:
        module.read_key(Path(directory) / "missing.env")
    except FileNotFoundError as error:
        assert "NASS_API_KEY" in str(error)
    else:
        raise AssertionError("missing secrets file should fail")

print("NASS Quick Stats API fallback mocked tests passed")
