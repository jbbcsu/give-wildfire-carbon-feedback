"""Bounded-latitude retrospective predictive benchmark; aggregate output only."""
import argparse
import hashlib
import json
import gc
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['crop', 'lat', 'lon_360', 'harvest_year']


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def moments(x, y):
    return (np.einsum('ni,nj->ij', x, x, optimize=False),
            np.einsum('ni,n->i', x, y, optimize=False), float(np.dot(y,y)), len(y))


def read_band(path, columns, lower):
    pieces=[]
    for batch in pq.ParquetFile(path).iter_batches(batch_size=8192, columns=columns, use_threads=False):
        frame=batch.to_pandas()
        mask=frame.lat.ge(lower) & frame.lat.lt(lower+10) & frame.yield_t_ha.gt(0)
        if mask.any():
            pieces.append(frame.loc[mask].copy())
    return pd.concat(pieces,ignore_index=True) if pieces else pd.DataFrame(columns=columns)


def score(train, test):
    gram, cross, _, n = train
    scale = np.sqrt(np.diag(gram)/n)
    if np.any(scale <= 0):
        raise ValueError('zero training scale')
    standardized = gram/np.outer(scale,scale)
    condition = float(np.linalg.cond(standardized))
    if not np.isfinite(condition) or condition > 1e10:
        raise ValueError('ill-conditioned Gram matrix')
    beta = np.linalg.solve(standardized, cross/scale)/scale
    g, c, yy, count = test
    sse = float(yy-2*np.dot(beta,c)+np.einsum('i,ij,j->',beta,g,beta,optimize=False))
    if sse < -1e-8*max(yy,1):
        raise ValueError('negative prediction loss')
    mean = cross[0]/n
    reference = yy-2*mean*c[0]+count*mean**2
    return dict(train_pairs=n, test_pairs=count, rmse=float(np.sqrt(max(sse,0)/count)),
                r2_vs_training_mean=float(1-sse/reference), scaled_gram_condition=condition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('output exists')
    output = dict(role='exploratory_retrospective_prediction_only', causal_or_scc_result=False,
                  code_sha256=sha(Path(__file__)),
                  protocol_sha256=sha(ROOT/'GLOBAL_CONTINUOUS_TEMPORAL_PROTOCOL_20260906.md'), crops={})
    for crop, code, threshold in [('maize','mai',29),('soy','soy',30)]:
        paths, hashes = {}, {}
        for family in ['direct','heat','scpdsi']:
            receipt_path = ROOT/f'outputs/continuous_global_panel_1982_2016_v1/{crop}_1982_2016_{family}_assembly_receipt.json'
            receipt = json.loads(receipt_path.read_text())
            paths[family] = ROOT/receipt['output']['path']
            actual = sha(paths[family])
            if actual != receipt['output']['sha256']:
                raise ValueError('assembly hash mismatch')
            hashes[family] = dict(data_sha256=actual, receipt_sha256=sha(receipt_path))
        direct = ['log1p_precip_mm','stage1_precip_share','stage2_precip_share',
                  'cdd_max_days','rx5day_mm','precipitation_concentration_hhi']
        heat = [f'stage{i}_tmean_c' for i in [1,2,3]] + [f'stage{i}_tmax_{threshold}c_degree_days' for i in [1,2,3]]
        drought = ['season_scpdsi_mean'] + [f'stage{i}_scpdsi_mean' for i in [1,2,3]]
        specs = dict(controls_only=heat, quantity=heat+direct[:1],
                     quantity_distribution=heat+direct, scpdsi_mean=heat+drought[:1],
                     scpdsi_stages=heat+drought[1:])
        totals, bands = {}, []
        for lower in range(-90,90,10):
            tables = {}
            for family, columns in [('direct',direct),('heat',heat),('scpdsi',drought)]:
                tables[family] = read_band(paths[family], KEYS+['yield_t_ha']+columns,lower)
                if tables[family].duplicated(KEYS).any():
                    raise ValueError('duplicate candidate keys')
            frame = tables['direct'].merge(tables['heat'],on=KEYS,validate='one_to_one',suffixes=('','_heat'))
            frame = frame.merge(tables['scpdsi'],on=KEYS,validate='one_to_one',suffixes=('','_scpdsi'))
            del tables
            if frame.empty:
                continue
            if set(frame.crop.astype(str)) != {code}:
                raise ValueError('wrong crop')
            for name in ['yield_t_ha_heat','yield_t_ha_scpdsi']:
                if not np.allclose(frame.yield_t_ha,frame[name],equal_nan=True):
                    raise ValueError('outcomes differ across families')
            features = direct+heat+drought
            frame = frame.loc[frame.yield_t_ha.notna() & frame.yield_t_ha.gt(0)].sort_values(KEYS)
            if frame.empty:
                continue
            if not np.isfinite(frame[features].to_numpy()).all():
                raise ValueError('nonfinite features on observed support')
            groups = frame.groupby(['crop','lat','lon_360'],observed=True)
            consecutive = groups.harvest_year.diff().eq(1).to_numpy()
            differences = groups[features].diff()
            logy = np.log(frame.yield_t_ha)
            dy = logy.groupby([frame.crop,frame.lat,frame.lon_360],observed=True).diff().to_numpy()
            years = frame.harvest_year.to_numpy()
            train = consecutive & (years <= 2010)
            cells = list(zip(frame.lat,frame.lon_360))
            train_cells = {cells[i] for i in np.flatnonzero(train)}
            test = consecutive & (years >= 2012) & np.array([c in train_cells for c in cells])
            bands.append(dict(lat_min=lower, lat_max_exclusive=lower+10,
                              train_pairs=int(train.sum()),test_pairs=int(test.sum())))
            for model, columns in specs.items():
                year = (years-2000)/10
                x = np.column_stack([np.ones(len(frame)),year,year**2,differences[columns].to_numpy()])
                for label, mask in [('train',train),('test',test)]:
                    if not mask.any():
                        continue
                    m = moments(x[mask],dy[mask]); key=(model,label)
                    totals[key] = m if key not in totals else tuple(a+b for a,b in zip(totals[key],m))
            del frame, differences
            gc.collect()
            print(crop,lower,'completed',flush=True)
        results = {}
        for model in specs:
            try:
                results[model] = dict(status='completed', **score(totals[model,'train'],totals[model,'test']))
            except (ValueError, KeyError) as error:
                results[model] = dict(status='failed', reason=str(error))
        output['crops'][crop] = dict(input_hashes=hashes,bands=bands,metrics=results)
    temporary=args.out.with_suffix('.partial')
    temporary.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    temporary.replace(args.out)


if __name__ == '__main__':
    main()
