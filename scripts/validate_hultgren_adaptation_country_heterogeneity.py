#!/usr/bin/env python3
"""Independent aggregate validation for adaptation-country heterogeneity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.receipt.read_text())
    assert report["schema"] == "hultgren_adaptation_country_heterogeneity/v1"
    assert report["claim_gates"] == {
        "country_scenario_accounting": True,
        "estimated_adaptation_response": False,
        "causal_country_damage": False,
        "marginal_scc": False,
    }
    table_path = Path(report["output"]["path"])
    assert digest(table_path) == report["output"]["sha256"]
    table = pd.read_csv(table_path)
    assert len(table) == report["output"]["rows"]
    assert not table.duplicated(["scenario", "country_code", "climate_model"]).any()
    assert set(table.scenario) == {"fixed", "trend", "upper"}
    assert table.climate_model.nunique() == 5
    country = table.groupby(["scenario", "country_code"], as_index=False).agg(
        models=("climate_model", "nunique"),
        mean=("global_contribution", "mean"),
        negative=("global_contribution", lambda values: int((values < 0).sum())),
        positive=("global_contribution", lambda values: int((values > 0).sum())),
    )
    assert (country.models == 5).all()
    assert country.country_code.nunique() == report["country_count"]
    maximum_error = 0.0
    for scenario, saved in report["summaries"].items():
        group = country.loc[country.scenario.eq(scenario)]
        recomputed = {
            "global_equal_model_mean_log_yield": float(group["mean"].sum()),
            "gross_negative_country_contribution": float(group.loc[group["mean"] < 0, "mean"].sum()),
            "gross_positive_country_contribution": float(group.loc[group["mean"] > 0, "mean"].sum()),
            "countries_mean_negative": int((group["mean"] < 0).sum()),
            "countries_mean_positive": int((group["mean"] > 0).sum()),
            "countries_negative_all_five_models": int((group.negative == 5).sum()),
            "countries_positive_all_five_models": int((group.positive == 5).sum()),
            "countries_mixed_sign_across_models": int(((group.negative > 0) & (group.positive > 0)).sum()),
        }
        for key, value in recomputed.items():
            if isinstance(value, float):
                maximum_error = max(maximum_error, abs(value - saved[key]))
            else:
                assert value == saved[key]
    assert maximum_error <= 2e-14
    wide = country.pivot(index="country_code", columns="scenario", values="mean")
    flips = {
        "fixed_negative_to_upper_positive": int(((wide.fixed < 0) & (wide.upper > 0)).sum()),
        "fixed_positive_to_upper_negative": int(((wide.fixed > 0) & (wide.upper < 0)).sum()),
    }
    assert flips == report["sign_flips"]
    assert np.all(wide.upper.to_numpy() + 1e-14 >= wide.trend.to_numpy())
    assert np.all(wide.trend.to_numpy() + 1e-14 >= wide.fixed.to_numpy())
    output = {
        "status": "validated",
        "receipt": str(args.receipt),
        "receipt_sha256": digest(args.receipt),
        "output_sha256": digest(table_path),
        "rows": int(len(table)),
        "countries": int(wide.shape[0]),
        "maximum_summary_error": maximum_error,
        "sign_flips_match": True,
        "adaptation_monotonicity_passes": True,
        "claim_gates_closed": True,
    }
    assert not args.output.exists()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
