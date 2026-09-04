"""Finite, exploratory robustness matrix using the validated historical panel."""
import argparse
import copy
import json
from pathlib import Path
from estimate_us_direct_practice_precipitation_association import (
    DEFAULT_CONFIG, PROJECT, load_config, validate_panel, estimate, sha256,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output already exists')
    config = load_config(DEFAULT_CONFIG)
    frame, source = validate_panel(config)
    variants = ['baseline', 'additional_stage_tmax', 'reporting_2000_2018']
    results = []
    for variant in variants:
        cfg = copy.deepcopy(config)
        data = frame
        if variant == 'additional_stage_tmax':
            cfg['models']['heat_controls'] += [f'stage{i}_tmax_mean_c' for i in [1,2,3]]
        if variant == 'reporting_2000_2018':
            data = frame.loc[frame.harvest_year >= 2000].copy()
        for crop in config['input']['crops']:
            for practice in config['input']['practices']:
                for form in config['models']['forms']:
                    entry = dict(variant=variant, crop=crop, practice=practice, form=form)
                    try:
                        fitted = estimate(data, crop, practice, form, cfg)
                        fitted['is_registered_primary_form_for_crop'] = (
                            variant == 'baseline' and fitted['is_registered_primary_form_for_crop'])
                        entry.update(status='estimated', result=fitted)
                    except (ValueError, ArithmeticError) as error:
                        entry.update(status='failed', reason=str(error))
                    results.append(entry)
    result = dict(schema='us_reporting_heat_sensitivity_v1', input=source,
                  config_sha256=sha256(DEFAULT_CONFIG),
                  implementation_sha256=sha256(Path(__file__)),
                  base_estimator_sha256=sha256(Path(__file__).with_name('estimate_us_direct_practice_precipitation_association.py')),
                  protocol_sha256=sha256(PROJECT/'us_county_validation/US_REPORTING_HEAT_SENSITIVITY_20260904.md'),
                  role='exploratory_historical_associations',
                  causal_or_scc_result=False, estimates=results)
    temporary = args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    temporary.replace(args.out)
    print(f'{len(results)} cells; {sum(x["status"] == "failed" for x in results)} failed')


if __name__ == '__main__':
    main()
