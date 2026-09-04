"""Leave-one-state-out coefficient influence, at fixed full-sample rainfall."""
import argparse
import copy
import json
import math
from pathlib import Path

from estimate_us_direct_practice_precipitation_association import (
    DEFAULT_CONFIG, PROJECT, ESTIMATION_PRIMITIVES, load_config, validate_panel,
    estimate, sha256,
)


def point_contrasts(fit, reference_mm):
    b = {c['term']: c['estimate'] for c in fit['coefficients']}
    reference = reference_mm / 100
    delta = b['precipitation_per_100mm'] + b['precipitation_per_100mm_squared'] * (2*reference+1)
    result = dict(quantity_log_difference=delta,
                  quantity_percent_difference=100*math.expm1(delta))
    if 'stage2_precip_share' in b:
        result['timing_percent_difference'] = 100*math.expm1(0.1*b['stage2_precip_share'])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output already exists')
    config = load_config(DEFAULT_CONFIG)
    frame, source = validate_panel(config)
    records = []
    for variant in ['baseline', 'additional_stage_tmax']:
        cfg = copy.deepcopy(config)
        if variant == 'additional_stage_tmax':
            cfg['models']['heat_controls'] += [f'stage{i}_tmax_mean_c' for i in [1, 2, 3]]
        for crop in ['corn_grain', 'soybeans']:
            subset = frame.loc[frame.outcome_crop.eq(crop) & frame.irrigation_practice.eq('non_irrigated')]
            reference = float(subset.precip_mm.median())
            form = cfg['models']['primary_form_by_crop'][crop]
            for omitted in [None, *sorted(subset.state.unique())]:
                data = subset if omitted is None else subset.loc[subset.state.ne(omitted)]
                entry = dict(variant=variant, crop=crop, form=form,
                    omitted_state=omitted, reference_precipitation_mm=reference,
                    states_remaining=sorted(data.state.unique()), rows=len(data))
                try:
                    fitted = estimate(data, crop, 'non_irrigated', form, cfg)
                    entry.update(status='estimated', counties=fitted['counties'],
                                 contrasts=point_contrasts(fitted, reference))
                except (ValueError, ArithmeticError) as error:
                    entry.update(status='failed', reason=str(error))
                records.append(entry)
    result = dict(schema='us_state_influence_v1', input=source,
        config_sha256=sha256(DEFAULT_CONFIG), code_sha256=sha256(Path(__file__)),
        estimator_sha256=sha256(Path(__file__).with_name('estimate_us_direct_practice_precipitation_association.py')),
        primitives_sha256=sha256(ESTIMATION_PRIMITIVES),
        protocol_sha256=sha256(PROJECT/'us_county_validation/US_STATE_INFLUENCE_PROTOCOL_20260904.md'),
        role='exploratory_coefficient_influence_not_out_of_sample_validation',
        causal_or_scc_result=False, estimates=records)
    temporary = args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    temporary.replace(args.out)
    print(f'{len(records)} fits; {sum(r["status"] == "failed" for r in records)} failures')


if __name__ == '__main__':
    main()
