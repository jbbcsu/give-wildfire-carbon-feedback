"""Exploratory country-year control sensitivity; no causal response export."""
import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import tomllib

import numpy as np
import pyarrow.parquet as pq

from global_historical_moisture_associations import (
    DIRECT, DROUGHT, ROOT, cluster_fit, contrast_vectors, moments, partial_contrast,
)
from global_continuous_geographic_cluster_audit import (
    prepare_differences, resolve_inputs, sha256,
)


def absorb(x, y, groups):
    _, inverse = np.unique(groups, return_inverse=True)
    counts = np.bincount(inverse)
    sx = np.zeros((len(counts), x.shape[1]))
    sy = np.zeros(len(counts))
    np.add.at(sx, inverse, x)
    np.add.at(sy, inverse, y)
    return (x-sx[inverse]/counts[inverse, None],
            y-sy[inverse]/counts[inverse], len(counts), int((counts==1).sum()))


def absorbed_fit(x, y, groups, clusters):
    rx, ry, h, singletons = absorb(x, y, groups)
    n, p = x.shape
    if n <= h+p:
        raise ValueError('no residual degrees of freedom after absorption')
    blocks = {int(g): moments(rx[clusters==g], ry[clusters==g]) for g in np.unique(clusters)}
    beta, covariance, audit = cluster_fit(blocks)
    # cluster_fit accounts for p slopes; add the h absorbed intercept parameters.
    covariance *= (n-p)/(n-h-p)
    return beta, covariance, dict(**audit, absorbed_intercepts=h,
                                  singleton_intercept_groups=singletons,
                                  residual_degrees_of_freedom=n-h-p)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output must be new')
    protocol = ROOT/'GLOBAL_COUNTRY_CONTROL_PROTOCOL_20260907.md'
    mapping_receipt = ROOT/'data/provenance/global_country_proxy_20260907.json'
    receipt = json.loads(mapping_receipt.read_text())
    path = ROOT/receipt['output']['path']
    if sha256(path) != receipt['output']['sha256']:
        raise ValueError('country-proxy table hash mismatch')
    if sha256(protocol) != receipt['protocol_sha256']:
        raise ValueError('country-control protocol changed after construction')
    table = pq.read_table(path).to_pylist()
    mapping = {(r['lat'],r['lon_360']):r['country_label'] for r in table}
    if len(mapping) != len(table):
        raise ValueError('duplicate country grid keys')
    if any((r['country_count']==1) != bool(r['country_label']) for r in table):
        raise ValueError('country assignment includes ambiguous cells')
    del table
    config_path = ROOT/'config/global_continuous_geographic_cluster_v1.toml'
    config = tomllib.loads(config_path.read_text())
    output = dict(role='exploratory_country_proxy_year_association_sensitivity',
                  causal_or_scc_result=False, production_response_export=False,
                  code_sha256=sha256(Path(__file__)), protocol_sha256=sha256(protocol),
                  mapping_receipt_sha256=sha256(mapping_receipt),
                  mapping_table_sha256=sha256(path),
                  helper_hashes={name:sha256(ROOT/'scripts'/name) for name in (
                      'global_historical_moisture_associations.py',
                      'global_continuous_geographic_cluster_audit.py')}, crops={})
    for crop, code, threshold in [('maize','mai',29),('soy','soy',30)]:
        paths, hashes = resolve_inputs(config,crop)
        heat = [f'stage{i}_tmean_c' for i in (1,2,3)] + [
            f'stage{i}_tmax_{threshold}c_degree_days' for i in (1,2,3)]
        features = heat+DIRECT+DROUGHT
        specs = dict(quantity=heat+DIRECT[:1], quantity_distribution=heat+DIRECT,
                     scpdsi_mean=heat+DROUGHT[:1], scpdsi_stages=heat+DROUGHT[1:])
        pieces, support = [], Counter()
        for lower in range(-90,90,10):
            data = prepare_differences(paths,DIRECT,heat,DROUGHT,lower,1982,2010)
            if data is None:
                continue
            if data['crop_codes'] != [code]:
                raise ValueError('wrong crop')
            keys = list(zip(data['lat'],data['lon']))
            status = np.array(['absent' if k not in mapping else
                               'ambiguous' if mapping[k] is None else 'singleton'
                               for k in keys])
            support.update(status.tolist())
            mask = status=='singleton'
            if mask.any():
                pieces.append(dict(
                    country=np.array([mapping[k] or '' for k in keys if k in mapping
                                      and mapping[k] is not None]),
                    years=data['years'][mask], lat=data['lat'][mask], lon=data['lon'][mask],
                    y=data['dy'][mask],
                    x=np.column_stack([data['differences'][f][mask] for f in features])))
            del data
            gc.collect()
        if not pieces:
            raise ValueError('no unambiguous mapped support')
        joined = {k:np.concatenate([part[k] for part in pieces]) for k in pieces[0]}
        del pieces
        gc.collect()
        n = len(joined['y'])
        if n != support['singleton'] or not np.isin(joined['years'],np.arange(1983,2011)).all():
            raise ValueError('mapped support or training-year mismatch')
        countries, country_ids = np.unique(joined['country'], return_inverse=True)
        years = joined['years']-1983
        cy = country_ids*28+years
        geographic = (np.floor((joined['lat']+90)/20).astype(int)*1000
                      + np.floor(joined['lon']/20).astype(int))
        fits = []
        for control, groups in [('year_intercepts',years), ('country_year_intercepts',cy)]:
            for family, columns in specs.items():
                x = joined['x'][:,[features.index(f) for f in columns]]
                for clustering, ids in [('country_proxy',country_ids),('20_degree_blocks',geographic)]:
                    item = dict(time_controls=control, moisture_family=family,
                                clustering=clustering)
                    try:
                        beta, covariance, audit = absorbed_fit(x,joined['y'],groups,ids)
                        vectors = contrast_vectors(columns,family)
                        item.update(status='completed', **audit,
                                    contrasts={k:partial_contrast(beta,covariance,v)
                                               for k,v in vectors.items()})
                    except (ValueError,FloatingPointError,np.linalg.LinAlgError) as error:
                        item.update(status='failed', reason=str(error))
                    fits.append(item)
                del x
                print(crop,control,family,'complete',flush=True)
        output['crops'][crop] = dict(input_hashes=hashes,
            support={k:int(support[k]) for k in ('singleton','ambiguous','absent')},
            original_pairs=sum(support.values()), mapped_country_labels=len(countries),
            mapped_country_years=len(np.unique(cy)), fits=fits)
        del joined
        gc.collect()
    temporary = args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)
    if any(f['status']!='completed' for c in output['crops'].values() for f in c['fits']):
        raise SystemExit('one or more planned fits failed; result record retained')


if __name__ == '__main__':
    np.seterr(invalid='raise',divide='raise',over='raise')
    main()
