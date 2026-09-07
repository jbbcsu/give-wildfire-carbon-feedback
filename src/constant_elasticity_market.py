"""Uncalibrated, closed-market surplus accounting; not a crop/SCC model.

Independent mathematical implementation, not a replication of Hultgren et al.
Normalize baseline price/quantity to one: supply = exp(s)*p**es, demand = p**-ed.
Caller supplies the economic units and must separately justify the shock s.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Market:
    supply_elasticity: float
    demand_elasticity_magnitude: float
    baseline_value: float
    value_unit: str

    def __post_init__(self):
        for name in ('supply_elasticity', 'demand_elasticity_magnitude', 'baseline_value'):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{name} must be finite and positive')
        if not isinstance(self.value_unit, str) or not self.value_unit.strip():
            raise ValueError('explicit value unit required')
        if not math.isfinite(self.supply_elasticity+self.demand_elasticity_magnitude):
            raise ValueError('elasticity sum overflows')


def _finite(value, name):
    if not math.isfinite(value):
        raise ValueError(f'nonfinite {name}')
    return value


def _exprel(value):
    """expm1(x)/x with its continuous zero limit."""
    return math.expm1(value)/value if value else 1.


def paired_surplus(market: Market, baseline_log_supply_shift: float,
                   increment_log_supply_shift: float) -> dict:
    """Surplus change for a declared supply increment, avoiding level subtraction.

    Positive total_surplus_change is a benefit; positive damage_change is loss.
    This is an accounting derivative harness, not an emissions pulse conversion.
    """
    _finite(baseline_log_supply_shift, 'baseline supply shift')
    _finite(increment_log_supply_shift, 'supply increment')
    es, ed = market.supply_elasticity, market.demand_elasticity_magnitude
    base_log_price = -baseline_log_supply_shift/(es+ed)
    change_log_price = -increment_log_supply_shift/(es+ed)
    try:
        scale = market.baseline_value * math.exp((1-ed)*base_log_price)
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError('baseline market value underflowed or is nonfinite')
        z = (1-ed)*change_log_price
        change_cs = -scale*change_log_price*_exprel(z)
        change_ps = scale*math.expm1(z)/(1+es)
        # Algebraic sum, stabilized for tiny increments and ed near one.
        change_total = scale*increment_log_supply_shift/(1+es)*_exprel(z)
        derivative = scale/(1+es)
    except OverflowError as error:
        raise ValueError('market calculation outside finite numeric domain') from error
    values = dict(consumer_surplus_change=change_cs, producer_surplus_change=change_ps,
                  total_surplus_change=change_total, damage_change=-change_total,
                  derivative_total_surplus_wrt_log_supply_at_baseline=derivative)
    for name, value in values.items():
        _finite(value, name)
    return dict(**values, value_unit=market.value_unit,
                role='uncalibrated_closed_market_accounting', causal_or_scc_result=False)


def equilibrium(market: Market, log_supply_shift: float) -> dict:
    """Evaluate ratios to the zero-shift baseline and associated surplus changes."""
    _finite(log_supply_shift, 'supply shift')
    es, ed = market.supply_elasticity, market.demand_elasticity_magnitude
    log_price = -log_supply_shift/(es+ed)
    log_quantity = -ed*log_price
    try:
        price, quantity = math.exp(log_price), math.exp(log_quantity)
    except OverflowError as error:
        raise ValueError('equilibrium outside finite numeric domain') from error
    if min(price, quantity) <= 0 or not all(map(math.isfinite, (price, quantity))):
        raise ValueError('equilibrium ratios underflowed or are nonfinite')
    return dict(price_ratio=price, quantity_ratio=quantity,
                log_price_ratio=log_price, log_quantity_ratio=log_quantity,
                **paired_surplus(market, 0., log_supply_shift))


def productivity_to_supply(log_productivity: float, supply_elasticity: float,
                           *, convention: str) -> float:
    """Two explicit hypothetical mappings; neither is selected for production.

    horizontal_output: shift supply quantity at every price by exp(log_productivity).
    fixed_input_cost: C_A(q)=C_0(q/A), hence supply scales by A**(1+es).
    """
    _finite(log_productivity, 'productivity change')
    if not math.isfinite(supply_elasticity) or supply_elasticity <= 0:
        raise ValueError('positive finite supply elasticity required')
    if convention == 'horizontal_output':
        result = log_productivity
    elif convention == 'fixed_input_cost':
        result = (1+supply_elasticity)*log_productivity
    else:
        raise ValueError('explicit, recognized shock mapping required')
    return _finite(result, 'mapped supply change')
