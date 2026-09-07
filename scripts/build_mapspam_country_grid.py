"""Conservative country-label proxy from an existing crop footprint, not borders."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import tomllib

import pyarrow as pa
import pyarrow.parquet as pq

from audit_mapspam_gec_resolution import parse_nga_genc_gec
from audit_mapspam_faostat_welfare_crosswalk import parse_unsd_m49

ROOT = Path(__file__).resolve().parents[1]


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def half_degree_center(latitude, longitude):
    if not (math.isfinite(latitude) and math.isfinite(longitude)
            and -90 < latitude < 90 and -180 < longitude < 180):
        raise ValueError('invalid coordinate')
    indices = [(latitude+90)*12-.5, (longitude+180)*12-.5]
    if any(abs(value-round(value)) > 1e-6 for value in indices):
        raise ValueError('not a five-arc-minute center')
    ilat, ilon = (round(value)//6 for value in indices)
    return ilat*.5-90+.25, (ilon*.5-180+.25) % 360


def summarize_cells(cells):
    rows = []
    for (lat, lon), item in sorted(cells.items()):
        labels, count = item
        if not labels or count > 36 or count < len(labels):
            raise ValueError('invalid fine-cell count')
        rows.append(dict(lat=lat, lon_360=lon,
                         country_label=next(iter(labels)) if len(labels)==1 else None,
                         country_count=len(labels), mapspam_5m_cell_count=count))
    return rows


def source_file(manifest, kind):
    record = tomllib.loads(manifest.read_text())
    item, = [f for f in record['files'] if f['kind']==kind]
    path = ROOT/item['local_ignored_path']
    if digest(path, 'sha512') != item['local_sha512']:
        raise ValueError('official crosswalk source hash mismatch')
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or args.receipt.exists():
        raise ValueError('outputs must be new')
    source = ROOT/'data/interim/welfare_weights/mapspam2000_maize_soy_production.csv'
    extraction_path = source.with_name('mapspam2000_maize_soy_production.audit.json')
    extraction = json.loads(extraction_path.read_text())['extraction']
    if digest(source, 'sha512') != extraction['output_sha512']:
        raise ValueError('selected MapSPAM source hash mismatch')
    audit_path = source.with_name('mapspam_gec_resolution.audit.json')
    audit = json.loads(audit_path.read_text())
    nga = source_file(ROOT/'data/provenance/nga_genc_gec_crosswalk.toml',
                      'selected_official_genc_gec_crosswalk')
    unsd = source_file(ROOT/'data/provenance/unsd_m49_country_codes.toml',
                       'selected_country_code_page')
    official = parse_nga_genc_gec(nga)['gec_to_genc']
    current_iso, _ = parse_unsd_m49(unsd)
    mapping = {r['stat_code']: r for r in audit['per_stat_code']}
    if len(mapping) != len(audit['per_stat_code']):
        raise ValueError('duplicate stat-code mapping')
    for code, record in mapping.items():
        resolved = record['resolved_iso3']
        prefix = record['admin2_fips_prefix']
        expected = code if code in current_iso else official.get(prefix)
        if not resolved or expected != resolved:
            raise ValueError('country label not reproduced from official sources')
        if prefix in official and official[prefix] != resolved:
            raise ValueError('country-prefix disagreement')
    cells, counts = {}, Counter()
    with source.open(newline='') as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            code = row['stat_code']
            record = mapping[code]
            if row['admin2_fips'][:2] != record['admin2_fips_prefix']:
                raise ValueError('source row country-prefix mismatch')
            key = half_degree_center(float(row['latitude']), float(row['longitude']))
            labels, count = cells.get(key, (set(), 0))
            labels.add(record['resolved_iso3'])
            cells[key] = labels, count+1
            counts[code] += 1
    if sum(counts.values()) != audit['mapspam_selected_rows']:
        raise ValueError('source row count mismatch')
    if any(counts[code] != r['row_count'] for code, r in mapping.items()):
        raise ValueError('per-code counts changed')
    rows = summarize_cells(cells)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_suffix('.partial')
    pq.write_table(pa.Table.from_pylist(rows), temporary, compression='zstd')
    temporary.replace(args.out)
    inputs = [source, extraction_path, audit_path, nga, unsd]
    result = dict(role='country_label_proxy_from_modeled_crop_footprint',
                  causal_or_scc_result=False, redistribution_authorized=False,
                  code_sha256=digest(Path(__file__)),
                  protocol_sha256=digest(ROOT/'GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md'),
                  inputs={str(p.relative_to(ROOT)):digest(p) for p in inputs},
                  source_fine_cells=sum(counts.values()), half_degree_cells=len(rows),
                  singleton_country_cells=sum(r['country_count']==1 for r in rows),
                  ambiguous_country_cells=sum(r['country_count']>1 for r in rows),
                  singleton_country_labels=len({r['country_label'] for r in rows if r['country_label']}),
                  output=dict(path=str(args.out), sha256=digest(args.out), bytes=args.out.stat().st_size))
    args.receipt.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('inputs',)}))


if __name__ == '__main__':
    main()
