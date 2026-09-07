"""Hypothetical shocks with published candidate elasticities; not damages."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from constant_elasticity_market import Market,equilibrium,paired_surplus,productivity_to_supply

CONFIG=ROOT/'config/roberts_schlenker_a8_candidate_elasticities_20260907.json'
PROTOCOL=ROOT/'WELFARE_NORMALIZED_SENSITIVITY_PROTOCOL_20260907.md'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rounded_multiplier_check(supply,demand_signed,printed,coefficient_decimals=3,multiplier_decimals=2):
    if not all(map(math.isfinite,(supply,demand_signed,printed))) or supply<=0 or demand_signed>=0 or printed<=0:
        raise ValueError('invalid elasticity/multiplier signs')
    half_unit=.5*10**(-coefficient_decimals)
    gap=supply-demand_signed
    if gap<=2*half_unit:
        raise ValueError('rounding interval reaches a singular elasticity gap')
    expected=[1/(gap+2*half_unit),1/(gap-2*half_unit)]
    tolerance=.5*10**(-multiplier_decimals)
    observed=[printed-tolerance,printed+tolerance]
    if max(expected[0],observed[0])>min(expected[1],observed[1]):
        raise ValueError('printed multiplier inconsistent with rounded elasticities')
    return dict(reciprocal_from_rounded_coefficients=1/gap,
                coefficient_rounding_implied_interval=expected,
                printed_rounding_interval=observed,rounding_consistent=True)


def evaluate(config):
    if config['production_calibration_authorized'] is not False or config['damage_or_scc_authorized'] is not False:
        raise ValueError('source configuration unexpectedly authorizes production')
    if [r['id'] for r in config['columns']]!=['1a','1b','1c','2a','2b','2c']:
        raise ValueError('incomplete or reordered registered source columns')
    output=dict(role='normalized_hypothetical_productivity_sensitivity',hypothetical_shocks=True,
                empirical_damage_estimate=False,causal_or_scc_result=False,
                value_unit='fraction_of_declared_baseline_market_value',uncertainty_intervals=False,
                source_rounding_checks=[],states=[])
    for column in config['columns']:
        es,ed=column['supply'],-column['demand_signed']
        check=rounded_multiplier_check(es,-ed,column['printed_multiplier'],config['source_rounding_decimals'],config['multiplier_rounding_decimals'])
        output['source_rounding_checks'].append(dict(column=column['id'],**check))
        market=Market(es,ed,1.,output['value_unit'])
        for convention in ('horizontal_output','fixed_input_cost'):
            ds_dloga=1. if convention=='horizontal_output' else 1.+es
            for factor in (.99,1.,1.01):
                loga=math.log(factor)
                shift=productivity_to_supply(loga,es,convention=convention)
                state=equilibrium(market,shift)
                supplied=math.exp(shift)*state['price_ratio']**es
                demanded=state['price_ratio']**(-ed)
                if not math.isclose(supplied,demanded,rel_tol=1e-12,abs_tol=1e-12):
                    raise ValueError('market clearing fails')
                if not math.isclose(state['consumer_surplus_change']+state['producer_surplus_change'],state['total_surplus_change'],rel_tol=1e-10,abs_tol=1e-12):
                    raise ValueError('surplus accounting fails')
                # equilibrium's paired accounting starts at zero; request the
                # derivative at this nonzero state explicitly, not at zero.
                local=paired_surplus(market,shift,0.)
                analytic=local['derivative_total_surplus_wrt_log_supply_at_baseline']*ds_dloga
                epsilon=1e-6
                upper=paired_surplus(market,shift,epsilon*ds_dloga)['total_surplus_change']
                lower=paired_surplus(market,shift,-epsilon*ds_dloga)['total_surplus_change']
                numeric=(upper-lower)/(2*epsilon)
                if not math.isclose(analytic,numeric,rel_tol=1e-8,abs_tol=1e-10):
                    raise ValueError('productivity derivative check fails')
                output['states'].append(dict(source_column=column['id'],convention=convention,
                    hypothetical_productivity_factor=factor,log_supply_shift=shift,
                    price_ratio=state['price_ratio'],quantity_ratio=state['quantity_ratio'],
                    consumer_surplus_fraction=state['consumer_surplus_change'],
                    producer_surplus_fraction=state['producer_surplus_change'],
                    total_surplus_fraction=state['total_surplus_change'],
                    damage_fraction=state['damage_change'],
                    local_surplus_derivative_wrt_log_productivity=analytic,
                    centered_derivative_absolute_error=abs(analytic-numeric)))
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    config=json.loads(CONFIG.read_text())
    output=evaluate(config)
    output.update(config_path=str(CONFIG.relative_to(ROOT)),config_sha256=sha256(CONFIG),
                  protocol_sha256=sha256(PROTOCOL),code_sha256=sha256(Path(__file__)),
                  market_implementation_sha256=sha256(ROOT/'src/constant_elasticity_market.py'))
    args.out.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print('6 rounding checks and 36 normalized hypothetical states passed; no empirical damages')


if __name__=='__main__':
    main()
