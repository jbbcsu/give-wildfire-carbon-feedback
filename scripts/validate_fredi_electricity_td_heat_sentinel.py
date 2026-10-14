#!/usr/bin/env python3
"""Independent validator for the FrEDI v4.1.1 ElecTD-only sentinel."""

from __future__ import annotations

import csv
import hashlib
import json
import resource
import sys
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 60


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(262144):
            h.update(block)
    return h.hexdigest()


def json_data(path: Path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def dec(value: str) -> Decimal:
    result = Decimal(value)
    assert result.is_finite()
    return result


def peak_mib() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024 if sys.platform == "darwin" else 1024)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config_path = root / "config/fredi_electricity_heat_v4_1_1.json"
    config = json_data(config_path)
    manifest_path = root / config["source_manifest"]
    manifest = json_data(manifest_path)
    for item in manifest["files"]:
        relative = item["raw_path"]
        if relative is None:
            assert item["vendored"] is False
            continue
        source = root / relative
        assert source.stat().st_size == item["bytes"]
        assert digest(source) == item["sha256"]
    alignment_path = root / config["alignment_audit"]
    alignment = json_data(alignment_path)
    assert alignment["status"] == "PASS"
    tolerance = Decimal(str(alignment["absolute_tolerance"]))
    assert tolerance <= Decimal("1e-6")
    assert all(Decimal(str(row["max_abs_difference"])) <= tolerance for row in alignment["comparisons"])
    assert all(row["unmatched_rows"] == 0 for row in alignment["comparisons"])

    authorization = {row["endpoint"]: row["authorized_for_output"] for row in config["endpoint_gates"]}
    assert authorization == {
        "generation_and_capacity": False,
        "building_heating_and_cooling_demand": False,
        "transmission_and_distribution": True,
        "transmission_only": False,
        "distribution_only": False,
    }
    assert config["claim_status"]["SCC"] == "closed"
    assert config["claim_status"]["global_extrapolation"] == "prohibited"

    raw = root / "data/raw/fredi_data/inst/extdata/fredi"
    models = config["sentinel"]["models"]
    variants = config["sentinel"]["variants"]
    # Audit the excluded bundled surface without using its values.
    sd_rows = list(csv_rows(raw / "gcm/ElecSD_scaledimpacts.csv"))
    assert len(sd_rows) == 1519
    assert {row["sector"] for row in sd_rows} == {"ElecSD"}
    assert {row["variant"] for row in sd_rows} == {"NA"}
    assert {row["impactType"] for row in sd_rows} == {"NA"}
    assert Counter(row["modelUnitValue"] for row in sd_rows) == Counter(
        {"1": 294, "2": 294, "3": 294, "4": 245, "5": 245, "6": 147}
    )

    td_values = {}
    states = set()
    td_count = 0
    for row in csv_rows(raw / "gcm/ElecTD_scaledimpacts.csv"):
        td_count += 1
        assert row["sector"] == "ElecTD"
        assert row["impactType"] == "NA" and row["impactYear"] == "NA"
        states.add(row["postal"])
        temperature_bin = int(row["modelUnitValue"])
        if temperature_bin in (1, 2):
            key = (row["postal"], row["model"], row["variant"], temperature_bin)
            assert key not in td_values
            td_values[key] = dec(row["value"])
    assert td_count == 4557 and len(states) == 49
    assert len(td_values) == 49 * 6 * 3 * 2

    td_growth = {}
    growth_rows = 0
    years = set()
    for row in csv_rows(raw / "scalars/Scalar_damageAdj_elecTD_growthFactor.csv"):
        growth_rows += 1
        assert row["scalarName"] == "elecTD_growthFactor"
        years.add(int(row["year"]))
        if int(row["year"]) == 2020:
            td_growth[row["postal"]] = dec(row["value"])
    assert growth_rows == 4312
    assert years == set(range(2006, 2091)) | {2100, 2200, 2300}
    assert set(td_growth) == states

    expected = {}
    half = Decimal("0.5")
    quantizer = Decimal("0.000001")
    for variant in variants:
        for model in models:
            state_terms = []
            for postal in sorted(states):
                lower = td_values[(postal, model, variant, 1)]
                upper = td_values[(postal, model, variant, 2)]
                state_terms.append((lower + upper) * half * td_growth[postal])
            expected[(variant, model)] = sum(state_terms, Decimal("0")).quantize(quantizer)

    output_path = root / config["sentinel"]["output"]
    output_rows = list(csv_rows(output_path))
    assert len(output_rows) == 18
    observed = {}
    for row in output_rows:
        assert row["scope"] == "CONUS_48_plus_DC"
        assert row["model_type"] == "GCM"
        assert row["driver_conus_degC_rel1995"] == "1.5"
        assert row["economic_year"] == "2020"
        assert row["released_sector"] == "ElecTD"
        assert row["endpoint_resolution"] == "combined_transmission_distribution"
        key = (row["variant"], row["gcm"])
        assert key not in observed
        observed[key] = dec(row["annual_impact_2015usd_per_year"])
    assert observed == expected
    assert not any("ElecSD" in value for row in output_rows for value in row.values())

    receipt_path = root / config["sentinel"]["receipt"]
    receipt = json_data(receipt_path)
    assert receipt["config"]["sha256"] == digest(config_path)
    assert receipt["source_manifest"]["sha256"] == digest(manifest_path)
    assert receipt["alignment_audit"]["sha256"] == digest(alignment_path)
    assert receipt["output"] == {
        "path": config["sentinel"]["output"],
        "sha256": digest(output_path),
        "rows": 18,
    }
    for path, expected_hash in receipt["execution_code"].items():
        assert digest(root / path) == expected_hash
    assert receipt["endpoint_authorization"] == authorization
    assert receipt["claim_status"] == config["claim_status"]
    assert peak_mib() < 512
    print(json.dumps({
        "status": "PASS",
        "independent_rows_recomputed": len(observed),
        "state_dc_count": len(states),
        "max_abs_difference_2015usd_per_year": "0.000000",
        "computed_sector": "ElecTD",
        "excluded_bundled_sector": "ElecSD",
        "peak_rss_mib": round(peak_mib(), 3),
        "matched_pulse_gate": "CLOSED",
        "scc_gate": "CLOSED",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
