#!/usr/bin/env python3
"""Audit whether the published fisheries benchmark can be added to core GIVE."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_tokens(text: str, tokens: list[str], source: str) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, f"required tokens absent from {source}: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--give-root", type=Path, required=True)
    parser.add_argument("--blue-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "fresh output required")
    mortality_path = args.give_root / "packages/MimiGIVE/src/components/cromar_mortality_damages.jl"
    aggregator_path = args.give_root / "packages/MimiGIVE/src/components/DamageAggregator.jl"
    for path in (mortality_path, aggregator_path, args.blue_receipt):
        require(path.is_file(), f"source missing: {path}")

    mortality = mortality_path.read_text()
    aggregator = aggregator_path.read_text()
    blue = json.loads(args.blue_receipt.read_text())
    require(blue["schema"] == "blue_scc_fisheries_literature_benchmark_audit_v1", "Blue-SCC receipt schema differs")
    require_tokens(mortality, [
        "baseline_mortality_rate = Parameter(index=[time, country])",
        "v.mortality_change[t,c] = p.β_mortality[c] * p.temperature[t]",
        "v.excess_death_rate[t,c] = p.baseline_mortality_rate[t,c] * v.mortality_change[t,c]",
        "v.mortality_costs[t,c] = p.vsl[t,c] * v.excess_deaths[t,c]",
    ], "Cromar mortality component")
    require_tokens(aggregator, [
        "include_cromar_mortality = Parameter{Bool}(default=true)",
        "include_ag = Parameter{Bool}(default=true)",
        "include_energy = Parameter{Bool}(default=true)",
        "p.include_cromar_mortality ? v.cromar_mortality_damage[t] : 0.",
        "p.include_ag               ? v.agriculture_damage[t] : 0.",
    ], "GIVE damage aggregator")
    method = blue["method_readout"]
    require("nutrient" in method["nutrition_pathway"].lower(), "nutrition pathway differs")
    require("profit" in method["market_pathway"].lower(), "market pathway differs")
    published = blue["published_figure4_baseline_summary"]
    require(abs(published["fisheries_total_scc_usd_per_tco2"] -
                published["fisheries_market_scc_usd_per_tco2"] -
                published["fisheries_nonmarket_use_scc_usd_per_tco2"]) <= 1e-12,
            "published component arithmetic differs")

    output = {
        "schema": "fisheries_give_overlap_audit/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "published_benchmark_not_additive_pending_overlap_and_welfare_resolution",
        "published_benchmark_usd_per_tco2": published,
        "core_give_findings": {
            "cromar_mortality_enabled_by_default": True,
            "cromar_uses_country_baseline_mortality_rate": True,
            "cromar_values_excess_deaths_with_vsl": True,
            "agriculture_enabled_by_default": True,
            "mortality_and_agriculture_enter_total_damage": True,
        },
        "overlap_findings": {
            "nutrition_mortality": {
                "status": "potential_overlap_requires_cause_and_pathway_reconciliation",
                "reason": "The published nutrition component values mortality from seafood nutrient availability, while core GIVE already values a temperature-linked change applied to country baseline mortality. The inspected core component has no cause-specific exclusion for fisheries nutrition.",
                "required_resolution": "Reconcile death causes, baseline rates, exposure pathways and VSL conventions; report nutrition separately until incremental deaths are demonstrated outside the retained Cromar response.",
            },
            "market": {
                "status": "welfare_and_macro_overlap_unresolved",
                "reason": "The published market benchmark uses profit projections plus regional output multipliers rather than explicit consumer and producer surplus.",
                "required_resolution": "Separate direct fisheries surplus from indirect/induced output effects and test overlap with agriculture, energy and any aggregate macroeconomic damage before addition.",
            },
            "terrestrial_food": {
                "status": "substitution_overlap_unresolved",
                "reason": "Seafood substitution and undernutrition can interact with terrestrial food prices and consumption represented by the agriculture replacement.",
                "required_resolution": "Use a joint food-market treatment or exclude terrestrial food-price welfare from the fisheries module.",
            },
        },
        "claim_gates": {
            "published_benchmark_verified": True,
            "published_total_additive_to_give": False,
            "published_market_additive_to_give": False,
            "published_nutrition_additive_to_give": False,
            "local_fisheries_scc_estimated": False,
            "fishmip_to_welfare_mapping_estimated": False,
        },
        "recommended_reporting": {
            "external_total_benchmark": published["fisheries_total_scc_usd_per_tco2"],
            "external_market_benchmark": published["fisheries_market_scc_usd_per_tco2"],
            "external_nutrition_benchmark": published["fisheries_nonmarket_use_scc_usd_per_tco2"],
            "label": "published external benchmark only; not a GIVE add-on or local estimate",
        },
        "sources": {
            "blue_receipt": {"path": str(args.blue_receipt), "sha256": digest(args.blue_receipt)},
            "give_cromar_component": {"path": "packages/MimiGIVE/src/components/cromar_mortality_damages.jl", "sha256": digest(mortality_path)},
            "give_damage_aggregator": {"path": "packages/MimiGIVE/src/components/DamageAggregator.jl", "sha256": digest(aggregator_path)},
        },
        "implementation": {"path": str(Path(__file__).resolve().relative_to(Path(__file__).resolve().parents[1])), "sha256": digest(Path(__file__).resolve())},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "claim_gates": output["claim_gates"]}, indent=2))


if __name__ == "__main__":
    main()
