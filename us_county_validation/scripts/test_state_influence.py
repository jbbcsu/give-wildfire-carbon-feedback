"""Check contrast algebra and saved full-reference/sample consistency."""
import json
import math
from run_state_influence import point_contrasts, PROJECT


def main():
    fit = {'coefficients': [dict(term=k, estimate=v) for k, v in {
        'precipitation_per_100mm': 0.1,
        'precipitation_per_100mm_squared': -0.01,
        'stage2_precip_share': -0.2,
    }.items()]}
    out = point_contrasts(fit, 400)
    assert math.isclose(out['quantity_log_difference'], 0.01, abs_tol=1e-14)
    assert math.isclose(out['timing_percent_difference'], 100*math.expm1(-0.02))
    root = PROJECT/'data/provenance'
    current = json.loads((root/'us_state_influence_20260904.json').read_text())
    earlier = json.loads((root/'us_reporting_heat_sensitivity_20260904.json').read_text())
    assert current['input'] == earlier['input']
    assert len(current['estimates']) == 34
    for variant in ['baseline', 'additional_stage_tmax']:
        for crop in ['corn_grain', 'soybeans']:
            rows = [r for r in current['estimates'] if r['variant']==variant and r['crop']==crop]
            full = next(r for r in rows if r['omitted_state'] is None)
            assert {r['omitted_state'] for r in rows[1:]} == set(full['states_remaining'])
            for row in rows:
                assert row['status'] == 'estimated'
                assert row['reference_precipitation_mm'] == full['reference_precipitation_mm']
                if row['omitted_state'] is not None:
                    assert row['omitted_state'] not in row['states_remaining']
                    assert row['rows'] < full['rows']
            old = next(r['result'] for r in earlier['estimates']
                       if r['variant']==variant and r['crop']==crop
                       and r['practice']=='non_irrigated' and r['form']==full['form'])
            expected = point_contrasts(old, full['reference_precipitation_mm'])
            for key, value in expected.items():
                assert math.isclose(full['contrasts'][key], value, rel_tol=1e-10, abs_tol=1e-12)
    print('contrast algebra, source, omission coverage and full-reference checks passed')


if __name__ == '__main__':
    main()
