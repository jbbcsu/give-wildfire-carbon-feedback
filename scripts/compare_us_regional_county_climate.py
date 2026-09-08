"""Regional source-matched county climate contrasts; no fitted crop response."""
import argparse
import json
from pathlib import Path
import pandas as pd
from build_us_regional_county_climate import ROOT, PROTOCOL, PAIR, base, checked, identity, sha256
from compare_us_paired_county_climate import paired_summary, CORE, HEAT, SHAPE

DIRECTORY = 'data/interim/us_regional_county_climate_20260908'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise ValueError('fresh regional comparison output required')
    receipt_path = ROOT/DIRECTORY/'receipt.json'
    r = json.loads(receipt_path.read_text())
    if r['status'] != 'us_regional_county_climate_inputs_validated' or r['protocol_sha256'] != sha256(ROOT/PROTOCOL) or r['code_sha256'] != sha256(ROOT/'scripts/build_us_regional_county_climate.py'):
        raise ValueError('regional construction status/source differs')
    products = {p['scenario']: p for p in r['products']}
    if set(products) != {'obsclim', 'counterclim'}:
        raise ValueError('regional climate paths differ')
    factual, counter = [pd.read_parquet(checked(products[s])) for s in ('obsclim', 'counterclim')]
    frame, source = base.validate_panel(base.load_config(base.DEFAULT_CONFIG))
    if source != r['input']:
        raise ValueError('regional NASS/nClimGrid input differs')
    heat_receipt_path = ROOT/'data/provenance/us_daily_heat_expansion_20260907.json'
    hr = json.loads(heat_receipt_path.read_text())
    heat_path = ROOT/'data/interim/us_county/nass_direct_practice_daily_heat_1981_2019.parquet'
    if sha256(heat_path) != hr['output_sha256']:
        raise ValueError('nClimGrid heat changed')
    frame = frame.merge(pd.read_parquet(heat_path, columns=PAIR+HEAT), on=PAIR, how='left', validate='many_to_one')
    frame = frame.loc[pd.MultiIndex.from_frame(frame[PAIR]).isin(pd.MultiIndex.from_frame(factual[PAIR]))]
    columns = CORE+HEAT+SHAPE+['zero_precipitation_season']
    reference = frame[PAIR+['season_start', 'season_end', 'season_days']+columns].drop_duplicates()
    if len(reference) != r['retained_county_years'] or reference.duplicated(PAIR).any():
        raise ValueError('regional weather not common across practices')
    for name in ('season_start', 'season_end'):
        reference[name] = pd.to_datetime(reference[name]).dt.normalize()
    for product in (factual, counter):
        pd.testing.assert_frame_equal(product.set_index(PAIR).sort_index()[['season_start', 'season_end', 'season_days']],
                                      reference.set_index(PAIR).sort_index()[['season_start', 'season_end', 'season_days']], check_dtype=False)
    result = dict(status='us_regional_county_climate_comparison_validated', crop_yield_estimated=False,
        causal_or_scc_result=False, national_representativeness_claimed=False, new_untouched_holdout=False,
        climate_receipt=identity(receipt_path), nclimgrid_source=source, heat_receipt=identity(heat_receipt_path),
        protocol_sha256=sha256(ROOT/PROTOCOL), code_sha256=sha256(Path(__file__)),
        comparison_helper_sha256=sha256(ROOT/'scripts/compare_us_paired_county_climate.py'), comparisons=[])
    for crop in ('corn_grain', 'soybeans'):
        f, c, n = [t.loc[t.outcome_crop == crop].copy() for t in (factual, counter, reference)]
        zero = pd.concat([t[PAIR+['zero_precipitation_season']] for t in (f, c, n)]).groupby(PAIR).zero_precipitation_season.max()
        shape_keys = zero.index[zero.eq(0)]
        sf, sc, sn = [t.loc[pd.MultiIndex.from_frame(t[PAIR]).isin(shape_keys)] for t in (f, c, n)]
        entry = dict(crop=crop, shape_excluded_county_years=int(zero.gt(0).sum()), contrasts=[])
        for label, a, b, sa, sb in [('factual_minus_counterclim', f, c, sf, sc), ('gswp_factual_minus_nclimgrid', f, n, sf, sn)]:
            entry['contrasts'].append(dict(name=label, core=paired_summary(a, b, CORE+HEAT),
                                          shape=paired_summary(sa, sb, SHAPE) if len(sa) else None))
        result['comparisons'].append(entry)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print([(e['crop'], [(c['name'], c['core']['rows'], c['core']['counties'], c['core']['differences']['precip_mm']['equal_county_mean']) for c in e['contrasts']]) for e in result['comparisons']])


if __name__ == '__main__':
    main()
