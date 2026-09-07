"""Synthetic numerical fixtures only, never empirical data."""
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
from global_continuous_temporal_benchmark import moments, score, read_band


def main():
    rng=np.random.default_rng(1906)
    x=np.column_stack([np.ones(200),rng.normal(size=(200,8))])
    y=rng.normal(size=200)
    left=moments(x[:60],y[:60]); right=moments(x[60:120],y[60:120])
    combined=tuple(a+b for a,b in zip(left,right))
    result=score(combined,moments(x[120:],y[120:]))
    beta=np.linalg.lstsq(x[:120],y[:120],rcond=None)[0]
    expected=np.sqrt(np.mean((y[120:]-np.einsum('ni,i->n',x[120:],beta,optimize=False))**2))
    assert np.isclose(result['rmse'],expected,rtol=1e-12)
    assert result['train_pairs']==120 and result['test_pairs']==80
    try:
        duplicated=np.ones((20,2))
        score(moments(duplicated,y[:20]),moments(duplicated,y[:20]))
    except ValueError:
        pass
    else:
        raise AssertionError('rank deficiency accepted')
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary)/'synthetic.parquet'
        pd.DataFrame({'lat':[0.,9.,10.,-1.,5.], 'yield_t_ha':[1.,2.,3.,4.,-1.]}).to_parquet(path)
        selected=read_band(path,['lat','yield_t_ha'],0)
        assert list(selected.lat)==[0.,9.]
    print('partitioned moments match least squares; singular design rejected; band/positive-yield filters verified')


if __name__=='__main__':
    main()
