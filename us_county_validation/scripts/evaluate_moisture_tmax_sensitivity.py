"""Exploratory competing-moisture prediction under additional Tmax controls."""
import argparse
import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
from evaluate_us_competing_moisture import evaluate_frames
from build_us_competing_moisture_inputs import KEYS, DEFAULT_PROTOCOL, load_protocol, sha256

PROJECT = Path(__file__).resolve().parents[2]


def add_tmax(common, levels):
    if levels.duplicated(KEYS).any():
        raise ValueError('duplicate level keys')
    base_keys = [k for k in KEYS if k != 'harvest_year']
    names = [f'stage{i}_tmax_mean_c' for i in [1, 2, 3]]
    selected = levels[KEYS+names].copy()
    if not np.isfinite(selected[names].to_numpy(dtype=float)).all():
        raise ValueError('nonfinite maximum temperature')
    for name in names.copy():
        selected[name+'_squared'] = selected[name]**2
        names.append(name+'_squared')
    joined = common.merge(selected, on=KEYS, how='left', validate='one_to_one')
    previous = selected.rename(columns={'harvest_year':'difference_previous_harvest_year',
                                       **{n:n+'_previous' for n in names}})
    joined = joined.merge(previous, on=base_keys+['difference_previous_harvest_year'],
                          how='left', validate='one_to_one')
    if list(joined[KEYS].itertuples(index=False, name=None)) != list(common[KEYS].itertuples(index=False, name=None)):
        raise ValueError('endpoint join changed row order')
    result = common.copy()
    for name in names:
        value = joined[name].to_numpy() - joined[name+'_previous'].to_numpy()
        if not np.isfinite(value).all():
            raise ValueError('missing/nonfinite difference endpoint')
        result['d_'+name] = value
    return result, names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    receipt = PROJECT/'data/provenance/us_competing_moisture_independent_audit_20260826.json'
    pins = json.loads(receipt.read_text())['hash_audit']['sha256']
    folder = PROJECT/'data/interim/us_county/competing_moisture_predictive_v1'
    paths = dict(common=folder/'common_outcomes_controls_folds.parquet',
                 direct_input=folder/'direct_weather.parquet', pdsi_input=folder/'pdsi.parquet',
                 direct_raw=PROJECT/'data/interim/us_county/nass_direct_practice_nclimgrid_1981_2019.parquet',
                 protocol=DEFAULT_PROTOCOL)
    hashes = {k:sha256(p) for k,p in paths.items()}
    if any(hashes[k] != pins[k] for k in paths):
        raise ValueError('retained input differs from independent-audit hash')
    frames = {k:pd.read_parquet(p).sort_values(KEYS).reset_index(drop=True)
              for k,p in paths.items() if k != 'protocol'}
    common, direct, pdsi = [frames[k] for k in ['common','direct_input','pdsi_input']]
    for frame in [direct, pdsi]:
        if not frame[KEYS].equals(common[KEYS]) or frame.duplicated(KEYS).any():
            raise ValueError('common support mismatch')
    protocol = load_protocol(DEFAULT_PROTOCOL)
    modified, names = add_tmax(common, frames['direct_raw'])
    cfg = copy.deepcopy(protocol)
    cfg['features']['common_temperature_controls'] += names
    results = {}
    for label, data, config in [('baseline',common,protocol), ('additional_stage_tmax',modified,cfg)]:
        print('Evaluating '+label, flush=True)
        results[label] = evaluate_frames(data, direct, pdsi, config)
        results[label]['exploratory_sensitivity_not_new_registered_validation'] = True
    result = dict(schema='us_moisture_tmax_sensitivity_v1', input_sha256=hashes,
                  audit_receipt_sha256=sha256(receipt), code_sha256=sha256(Path(__file__)),
                  evaluator_sha256=sha256(Path(__file__).with_name('evaluate_us_competing_moisture.py')),
                  protocol_sha256=sha256(PROJECT/'us_county_validation/US_MOISTURE_TMAX_PROTOCOL_20260905.md'),
                  added_level_controls=names, causal_or_scc_result=False, results=results)
    temporary = args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    temporary.replace(args.out)
    print('Completed '+str(sum(len(r['metrics']) for r in results.values()))+' metric rows')


if __name__ == '__main__':
    main()
