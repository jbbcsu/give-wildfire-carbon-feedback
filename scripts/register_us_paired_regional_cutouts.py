"""Generate new regional child contracts from unchanged registered parent files."""
import argparse
import json
from pathlib import Path
from prepare_us_paired_regional_cutout import ROOT, BANDS, PROTOCOL, sha256, parent_and_payload


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        raise ValueError('fresh registry export required')
    records = []
    for band, bbox in BANDS.items():
        for scenario in ('obsclim', 'counterclim'):
            for variable in ('pr', 'tas', 'tasmax'):
                for first in (1981, 1991, 2001):
                    parent = ROOT/f'config/isimip3a_{scenario}_{variable}_{first}_cutout_20260908.json'
                    config = dict(role='registered_us_paired_regional_climate_request', band=band,
                        bbox_west_east_south_north=bbox, parent_source_config=str(parent.relative_to(ROOT)),
                        parent_source_config_sha256=sha256(parent), protocol_sha256=sha256(ROOT/PROTOCOL),
                        source_averaging_authorized=False, damage_or_scc_authorized=False)
                    parent_and_payload(config)
                    name = f'config/isimip3a_us_{band}_{scenario}_{variable}_{first}_20260908.json'
                    records.append(dict(path=name, config=config))
    args.out.write_text(json.dumps(dict(records=records, code_sha256=sha256(Path(__file__))), indent=2)+'\n')
    print('Prepared', len(records), 'new regional child contracts; no request or download submitted')


if __name__ == '__main__':
    main()
