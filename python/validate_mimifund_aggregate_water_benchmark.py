"""Independently validate the MimiFUND aggregate-water benchmark outputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def validate(config_path: Path) -> dict[str, object]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    require(config["schema"] == "mimifund_aggregate_water_benchmark_config/v1", "bad schema")
    require(set(config["hard_gates"].values()) == {False}, "a scientific gate is open")

    for key in ("manifest_path", "script_path"):
        path = ROOT / config["execution"][key]
        expected = config["execution"][key.replace("path", "sha256")]
        require(path.is_file() and sha256(path) == expected, f"execution artifact mismatch: {key}")
    deflator_path = ROOT / config["price_conversion"]["source_path"]
    require(sha256(deflator_path) == config["price_conversion"]["source_sha256"],
            "deflator source mismatch")
    deflators = {row["observation_date"][:4]: Decimal(row["A191RD3A086NBEA"])
                 for row in rows(deflator_path) if row["A191RD3A086NBEA"] != "."}
    factor = deflators["2020"] / deflators["1995"]
    require(factor == Decimal(config["price_conversion"]["multiply_by"]),
            "price conversion differs from pinned source")

    output_rows = {}
    for name in ("cases", "annual_central", "region_central"):
        spec = config["outputs"][name]
        path = ROOT / spec["path"]
        require(path.is_file() and sha256(path) == spec["sha256"], f"output mismatch: {name}")
        output_rows[name] = rows(path)

    cases = output_rows["cases"]
    require(len(cases) == 4, "four pulse cases required")
    by_case = {(row["pulse_shape"], int(row["pulse_size_tco2"])): row for row in cases}
    require(set(by_case) == {("one_year", 10_000_000), ("one_year", 100_000_000),
                            ("ten_year", 10_000_000), ("ten_year", 100_000_000)},
            "pulse cases changed")
    central = by_case[("one_year", 10_000_000)]
    source_scc = Decimal(central["aggregate_water_scc_1995usd_per_tco2"])
    target_scc = Decimal(central["aggregate_water_scc_2020usd_per_tco2"])
    require(abs(target_scc - source_scc * factor) < Decimal("0.000000000002"),
            "central price conversion fails")
    require(math.isclose(float(source_scc), config["claim"]["central_aggregate_water_scc_1995usd_per_tco2"],
                         rel_tol=0, abs_tol=5e-13), "central source SCC changed")

    alternate = float(by_case[("one_year", 100_000_000)]["aggregate_water_scc_1995usd_per_tco2"])
    relative = abs(alternate - float(source_scc)) / abs(float(source_scc))
    require(relative < 1e-4, "pulse-size sensitivity exceeds tolerance")
    require(math.isclose(relative, config["claim"]["one_year_pulse_size_relative_difference"],
                         rel_tol=1e-8, abs_tol=1e-12), "pulse-size claim changed")

    annual = output_rows["annual_central"]
    require(len(annual) == 276 and int(annual[0]["year"]) == 2025 and int(annual[-1]["year"]) == 2300,
            "annual path coverage changed")
    annual_sum = sum(Decimal(row["discounted_global_marginal_damage_1995usd_per_tco2"])
                     for row in annual)
    require(abs(annual_sum - source_scc) < Decimal("0.00000000002"), "annual path does not sum to SCC")

    regional = [Decimal(row["discounted_aggregate_water_scc_2020usd_per_tco2"])
                for row in output_rows["region_central"]]
    require(len(regional) == 16, "FUND region count changed")
    positive = sum(value for value in regional if value > 0)
    negative = sum(value for value in regional if value < 0)
    gross = sum(abs(value) for value in regional)
    net = sum(regional)
    cancellation = Decimal(1) - abs(net) / gross
    require(abs(net - target_scc) < Decimal("0.00000000001"), "region totals do not reconcile")
    require(abs(float(cancellation) - config["claim"]["regional_cancellation_fraction"]) < 1e-12,
            "regional cancellation claim changed")

    return {
        "schema": "mimifund_aggregate_water_validation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_external_aggregate_water_benchmark_not_municipal",
        "checks_passed": 35,
        "central_aggregate_water_scc_2020usd_per_tco2": float(target_scc),
        "regional_positive_sum_2020usd_per_tco2": float(positive),
        "regional_negative_sum_2020usd_per_tco2": float(negative),
        "regional_cancellation_fraction": float(cancellation),
        "additive_to_baseline_give": False,
        "config_sha256": sha256(config_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        default=ROOT / "config/mimifund_aggregate_water_benchmark_v1.json")
    args = parser.parse_args()
    try:
        result = validate(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, sort_keys=True))
        return 1
    config = json.loads(args.config.read_text(encoding="utf-8"))
    output = ROOT / config["outputs"]["validation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
