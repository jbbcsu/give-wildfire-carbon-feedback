#!/usr/bin/env python3
"""Decompose the matched PEEPS monthly SCC diagnostic by country and FUND region."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from build_epa_fair_hultgren_quantity_damage_paths import ADAPTATION, PULSES, VALUE, adaptation_factors, country_market_damage
from build_epa_fair_hultgren_quantity_fund_paths import validated_price_registry
from build_hultgren_monthly_precip_climatology import CALENDAR_COLUMNS, RAIN_COLUMNS
from build_hultgren_peeps_monthly_slope_panel import SLOPE_COLUMNS
from build_hultgren_precip_basis_climatology import FEATURES, require
from build_peeps_fair_hultgren_monthly_damage_paths import KEYS, YEARS, common_physical_support, year_offsets
from build_peeps_monthly_scc_decomposition import DISCOUNT_RATES, MOLECULAR_C_TO_CO2, PRICE_2005_TO_2020
from decompose_peeps_monthly_damage_paths import feature_delta, monthly_anomaly


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decomposition-receipt", type=Path, required=True)
    parser.add_argument("--global-scc", type=Path, required=True)
    parser.add_argument("--global-scc-receipt", type=Path, required=True)
    parser.add_argument("--slope-panel", type=Path, required=True)
    parser.add_argument("--response-panel", type=Path, required=True)
    parser.add_argument("--fair", type=Path, required=True)
    parser.add_argument("--cpc", type=Path, required=True)
    parser.add_argument("--price-registry", type=Path, required=True)
    parser.add_argument("--country-crosswalk", type=Path, required=True)
    parser.add_argument("--country-output", type=Path, required=True)
    parser.add_argument("--region-output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    require(not args.country_output.exists() and not args.region_output.exists() and not args.receipt.exists(), "fresh outputs required")
    decomposition_receipt = json.loads(args.decomposition_receipt.read_text())
    global_receipt = json.loads(args.global_scc_receipt.read_text())
    require(decomposition_receipt["schema"] == "peeps_monthly_damage_decomposition/v1", "decomposition receipt differs")
    require(global_receipt["schema"] == "peeps_monthly_scc_decomposition/v1", "global SCC receipt differs")
    require(global_receipt["output"]["sha256"] == digest(args.global_scc), "global SCC hash differs")
    joint_receipt_path = Path(decomposition_receipt["sources"]["joint_paths"]["receipt"])
    joint_receipt = json.loads(joint_receipt_path.read_text())
    require(digest(joint_receipt_path) == decomposition_receipt["sources"]["joint_paths"]["receipt_sha256"], "joint receipt hash differs")
    sources = decomposition_receipt["sources"]
    for label, path in (("slope_panel", args.slope_panel), ("response_panel", args.response_panel), ("fair", args.fair)):
        require(sources[label]["sha256"] == digest(path), f"{label} hash differs")
    _, price_scalar = validated_price_registry(args.price_registry)

    cpc = pd.read_csv(args.cpc)
    require(cpc.year.tolist() == list(range(2020, 2301)), "CPC years differ")
    base_cpc = float(cpc.loc[cpc.year.eq(2020), "net_cpc_2005usd_per_person"].iloc[0])
    discount = {
        label: np.asarray([(base_cpc / float(row.net_cpc_2005usd_per_person)) ** eta / (1.0 + prtp) ** (int(row.year) - 2020) for row in cpc.itertuples(index=False)])
        for label, prtp, eta in DISCOUNT_RATES
    }

    slopes = pd.read_parquet(args.slope_panel)
    response = pd.read_parquet(args.response_panel).sort_values(["iso3", *KEYS]).reset_index(drop=True)
    fair_frame = pd.read_csv(args.fair)
    fair_paths = {pulse: dict(zip(part.year.astype(int), part.difference_k.astype(float), strict=True)) for pulse in PULSES for part in [fair_frame.loc[fair_frame.pulse_size_gtc.eq(pulse)].sort_values("year")]}
    cells = slopes[KEYS].drop_duplicates().sort_values(KEYS).reset_index(drop=True)
    cells["cell_id"] = np.arange(len(cells), dtype=np.int32)
    slopes = slopes.merge(cells, on=KEYS, how="left", validate="many_to_one").sort_values(["cell_id", "regime"]).reset_index(drop=True)
    response = response.merge(cells, on=KEYS, how="inner", validate="many_to_one").sort_values(["iso3", *KEYS]).reset_index(drop=True)
    cell_id = slopes.cell_id.to_numpy(dtype=np.int32)
    area = slopes.mirca_area_ha.to_numpy(dtype=np.float64)
    baseline = slopes[RAIN_COLUMNS].to_numpy(dtype=np.float64)
    slope_values = slopes[SLOPE_COLUMNS].to_numpy(dtype=np.float64)
    months = slopes[CALENDAR_COLUMNS].to_numpy(dtype=np.int16)
    offsets = year_offsets(slopes)
    valid_regime, _ = common_physical_support(baseline, slope_values, months, offsets, fair_paths)
    invalid_cells = np.unique(cell_id[~valid_regime])
    valid_cell = np.ones(len(cells), dtype=bool)
    valid_cell[invalid_cells] = False
    require(int((~valid_cell).sum()) == joint_receipt["support"]["excluded_combined_crop_cells"], "physical support differs")
    keep = valid_cell[cell_id]
    cell_id, area, baseline, slope_values, months, offsets = (array[keep] for array in (cell_id, area, baseline, slope_values, months, offsets))
    response = response.loc[valid_cell[response.cell_id.to_numpy(dtype=np.int32)]].copy().reset_index(drop=True)
    require(len(response) == decomposition_receipt["support"]["response_rows"], "response support differs")
    cell_area = np.bincount(cell_id, weights=area, minlength=len(cells))
    season_total = baseline.sum(axis=1)
    response_cell = response.cell_id.to_numpy(dtype=np.int32)
    coefficients = response[[f"effective_{feature}" for feature in FEATURES]].to_numpy(dtype=np.float64)
    values = response[VALUE].to_numpy(dtype=np.float64)
    iso = response.iso3.to_numpy()
    starts = np.r_[0, np.flatnonzero(iso[1:] != iso[:-1]) + 1]
    country_iso = iso[starts]
    country_value = np.add.reduceat(values, starts)

    accumulators = {
        (pulse, adaptation, label, channel): np.zeros(len(country_iso), dtype=np.float64)
        for pulse in PULSES if pulse > 0
        for adaptation in ADAPTATION
        for label, _, _ in DISCOUNT_RATES
        for channel in ("joint_monthly_pattern", "quantity_reference", "timing_increment")
    }
    for pulse in (value for value in PULSES if value > 0):
        for year_index, year in enumerate(YEARS):
            joint_anomaly = monthly_anomaly(slope_values, months, offsets, fair_paths[pulse], int(year))
            quantity_anomaly = baseline * (joint_anomaly.sum(axis=1) / season_total)[:, None]
            country_damages = {}
            for channel, anomaly in (("joint_monthly_pattern", joint_anomaly), ("quantity_reference", quantity_anomaly)):
                regime_delta = feature_delta(baseline, anomaly)
                cell_delta = np.zeros((len(cells), len(FEATURES)), dtype=np.float64)
                for column in range(len(FEATURES)):
                    numerator = np.bincount(cell_id, weights=area * regime_delta[:, column], minlength=len(cells))
                    cell_delta[valid_cell, column] = numerator[valid_cell] / cell_area[valid_cell]
                country_damages[channel] = {}
                raw_response = np.sum(cell_delta[response_cell] * coefficients, axis=1)
                for adaptation in ADAPTATION:
                    factor = float(adaptation_factors(np.asarray([year]), adaptation)[0])
                    adapted = np.where(raw_response < 0.0, raw_response * factor, raw_response)
                    ratios = np.add.reduceat(np.exp(adapted) * values, starts) / country_value
                    country_damages[channel][adaptation] = country_market_damage(country_value, ratios[:, None])[:, 0]
            for adaptation in ADAPTATION:
                damage_vectors = {
                    "joint_monthly_pattern": country_damages["joint_monthly_pattern"][adaptation],
                    "quantity_reference": country_damages["quantity_reference"][adaptation],
                }
                damage_vectors["timing_increment"] = damage_vectors["joint_monthly_pattern"] - damage_vectors["quantity_reference"]
                for label, _, _ in DISCOUNT_RATES:
                    scalar = discount[label][year_index] * price_scalar / 1e9 * MOLECULAR_C_TO_CO2 / pulse
                    for channel, vector in damage_vectors.items():
                        accumulators[(pulse, adaptation, label, channel)] += scalar * vector

    crosswalk = pd.read_csv(args.country_crosswalk, encoding="utf-8-sig").rename(columns={"ISO3": "iso3"})
    require(not crosswalk.iso3.duplicated().any(), "country crosswalk duplicates")
    country_meta = pd.DataFrame({"iso3": country_iso}).merge(crosswalk[["iso3", "country", "fundregion"]], on="iso3", how="left", validate="one_to_one")
    unmapped_iso3 = sorted(country_meta.loc[country_meta.fundregion.isna(), "iso3"].tolist())
    country_meta["country"] = country_meta.country.fillna(country_meta.iso3)
    country_meta["fundregion"] = country_meta.fundregion.fillna("UNMAPPED")
    records = []
    for key, values_2005 in accumulators.items():
        pulse, adaptation, label, channel = key
        for index, value in enumerate(values_2005):
            records.append({"iso3": country_iso[index], "country": country_meta.country.iloc[index], "fund_region": country_meta.fundregion.iloc[index], "pulse_size_gtc": pulse, "adaptation": adaptation, "discount_rate_label": label, "channel": channel, "partial_scc_component_usd2005_per_tco2": value, "partial_scc_component_usd2020_per_tco2": value * PRICE_2005_TO_2020})
    country = pd.DataFrame(records).sort_values(["adaptation", "pulse_size_gtc", "discount_rate_label", "channel", "iso3"]).reset_index(drop=True)
    region = country.groupby(["fund_region", "pulse_size_gtc", "adaptation", "discount_rate_label", "channel"], as_index=False)[["partial_scc_component_usd2005_per_tco2", "partial_scc_component_usd2020_per_tco2"]].sum()
    global_reconstruction = country.groupby(["pulse_size_gtc", "adaptation", "discount_rate_label", "channel"], as_index=False).partial_scc_component_usd2020_per_tco2.sum()
    global_scc = pd.read_csv(args.global_scc)[["pulse_size_gtc", "adaptation", "discount_rate_label", "channel", "partial_scc_diagnostic_usd2020_per_tco2"]]
    comparison = global_reconstruction.merge(global_scc, on=["pulse_size_gtc", "adaptation", "discount_rate_label", "channel"], validate="one_to_one")
    reconstruction_error = float(np.max(np.abs(comparison.partial_scc_component_usd2020_per_tco2 - comparison.partial_scc_diagnostic_usd2020_per_tco2)))
    require(reconstruction_error <= 1e-15, f"country reconstruction differs: {reconstruction_error}")
    identity = country.pivot(index=["iso3", "pulse_size_gtc", "adaptation", "discount_rate_label"], columns="channel", values="partial_scc_component_usd2020_per_tco2")
    identity_error = float(np.max(np.abs(identity.joint_monthly_pattern - identity.quantity_reference - identity.timing_increment)))
    require(identity_error <= 1e-15, f"country channel identity differs: {identity_error:.17g}")

    args.country_output.parent.mkdir(parents=True, exist_ok=True)
    country.to_csv(args.country_output, index=False)
    region.to_csv(args.region_output, index=False)
    central = country.loc[country.pulse_size_gtc.eq(0.000025) & country.adaptation.eq("fixed") & country.discount_rate_label.eq("2.0%")]
    summaries = {}
    for channel in ("joint_monthly_pattern", "quantity_reference", "timing_increment"):
        selected = central.loc[central.channel.eq(channel)].sort_values("partial_scc_component_usd2020_per_tco2")
        summaries[channel] = {"gross_negative": float(selected.loc[selected.partial_scc_component_usd2020_per_tco2.lt(0), "partial_scc_component_usd2020_per_tco2"].sum()), "gross_positive": float(selected.loc[selected.partial_scc_component_usd2020_per_tco2.gt(0), "partial_scc_component_usd2020_per_tco2"].sum()), "negative_country_count": int(selected.partial_scc_component_usd2020_per_tco2.lt(0).sum()), "positive_country_count": int(selected.partial_scc_component_usd2020_per_tco2.gt(0).sum()), "most_negative": selected.head(5)[["iso3", "country", "partial_scc_component_usd2020_per_tco2"]].to_dict("records"), "most_positive": selected.tail(5).sort_values("partial_scc_component_usd2020_per_tco2", ascending=False)[["iso3", "country", "partial_scc_component_usd2020_per_tco2"]].to_dict("records")}
    result = {"schema": "peeps_monthly_scc_country_decomposition/v1", "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "one_esm_country_and_fund_region_accounting_decomposition_not_local_causal_effects", "definition": "country accounting components of the matched one-ESM joint monthly-pattern, quantity-reference, and timing-increment maize SCC diagnostic", "sources": {"decomposition_receipt": {"path": str(args.decomposition_receipt), "sha256": digest(args.decomposition_receipt)}, "global_scc": {"path": str(args.global_scc), "sha256": digest(args.global_scc), "receipt": str(args.global_scc_receipt), "receipt_sha256": digest(args.global_scc_receipt)}, "slope_panel": {"path": str(args.slope_panel), "sha256": digest(args.slope_panel)}, "response_panel": {"path": str(args.response_panel), "sha256": digest(args.response_panel)}, "fair": {"path": str(args.fair), "sha256": digest(args.fair)}, "cpc": {"path": str(args.cpc), "sha256": digest(args.cpc)}, "country_crosswalk": {"path": str(args.country_crosswalk), "sha256": digest(args.country_crosswalk)}}, "support": {"countries": len(country_iso), "fund_regions_including_unmapped": int(region.fund_region.nunique()), "unmapped_country_codes": unmapped_iso3, "country_rows": len(country), "region_rows": len(region)}, "validation": {"maximum_absolute_global_reconstruction_error_usd2020_per_tco2": reconstruction_error, "maximum_absolute_country_channel_identity_error_usd2020_per_tco2": identity_error}, "central_fixed_2pct_smallest_pulse": summaries, "outputs": {"country": {"path": str(args.country_output), "bytes": args.country_output.stat().st_size, "sha256": digest(args.country_output)}, "region": {"path": str(args.region_output), "bytes": args.region_output.stat().st_size, "sha256": digest(args.region_output)}}, "claim_gates": {"country_accounting": True, "country_causal_effect": False, "country_total_damage": False, "paired_replacement_scc": False}, "limitations": ["One ESM/scenario and maize only.", "Country components are national-market accounting contributions, not local causal effects or total country damages.", "ATG is absent from the archived GIVE/FUND crosswalk and is preserved as UNMAPPED rather than assigned to a guessed region.", "Monthly means omit daily drought and extremes.", "The standard deterministic GIVE discount path retains Moore agriculture."], "implementation": {"path": str(Path(__file__).resolve()), "sha256": digest(Path(__file__).resolve())}}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "validation": result["validation"], "central": summaries, "outputs": result["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
