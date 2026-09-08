"""Independent K.1/K.4 price/quantity implementation, not a welfare replication.

Source: Hultgren et al. 2025, doi:10.1038/s41586-025-09085-w, SI-76/80/81.
Caller supplies expected/realized normalized supply shifts; no smoothing,
inventory constraints, expenditure caps, surplus, adaptation or SCC here.
"""
import math


def market_response(*, supply_elasticity, demand_elasticity_magnitude,
                    expected_log_supply_ratio, realized_log_supply_ratio,
                    price_shrinkage):
    values=(supply_elasticity,demand_elasticity_magnitude,
            expected_log_supply_ratio,realized_log_supply_ratio,price_shrinkage)
    if any(isinstance(x,bool) or not math.isfinite(x) for x in values):
        raise ValueError('finite non-Boolean parameters required')
    e,d=supply_elasticity,demand_elasticity_magnitude
    if e<=0 or d<=0 or not math.isfinite(e+d) or not 0<=price_shrinkage<=1:
        raise ValueError('positive elasticities and shrinkage in [0,1] required')
    a,b=expected_log_supply_ratio,realized_log_supply_ratio
    expected_p=-a/(e+d);expected_q=-d*expected_p
    raw_q=expected_q+(b-a);raw_p=-raw_q/d
    if not all(math.isfinite(x) for x in (expected_p,expected_q,raw_q,raw_p)):
        raise ValueError('intermediate log values are nonfinite')
    if price_shrinkage==0:final_p=raw_p
    elif price_shrinkage==1:final_p=expected_p
    else:
        # Arithmetic price blend, not a weighted mean of log prices.
        x=math.log1p(-price_shrinkage)+raw_p
        y=math.log(price_shrinkage)+expected_p
        hi=max(x,y);final_p=hi+math.log1p(math.exp(min(x,y)-hi))
    logs=dict(expected_price_ratio=expected_p,expected_quantity_ratio=expected_q,
              raw_price_ratio=raw_p,raw_quantity_ratio=raw_q,
              final_price_ratio=final_p,final_quantity_ratio=-d*final_p)
    try:ratios={key:math.exp(value) for key,value in logs.items()}
    except OverflowError as error:raise ValueError('ratios outside finite numerical domain') from error
    if any(not math.isfinite(x) or x<=0 for x in ratios.values()):
        raise ValueError('nonpositive/nonfinite ratio')
    return dict(**ratios,role='published_sequence_price_quantity_only',
                welfare_computed=False,causal_or_scc_result=False)
