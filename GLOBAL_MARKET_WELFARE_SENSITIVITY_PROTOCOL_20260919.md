# Global-market structural welfare sensitivity protocol

Status: frozen before execution. This is a prespecified market-geography
sensitivity to the country-market structural benchmark, not an empirical damage
function, preferred-model selection, or SCC result.

The country-market benchmark revealed that one small, severely affected and
highly inelastic national market can dominate the welfare sum. The project
registry already specifies a single-world-market sensitivity. This analysis
therefore repeats the same joint temperature-plus-precipitation maize cases,
fixed-management assumption, three elasticity pairs, two yield-to-supply
mappings, common-support value proxies and USD2005 conversion, but aggregates
all valued country/regime supply shifts **before** evaluating one global market.

For each crop-model/climate/scenario/calendar/elasticity/mapping case:

1. retain only country/regime rows with a complete baseline-value proxy;
2. convert value once with the registered central price scalar;
3. compute `s_r=log(A_r)` for horizontal output or
   `s_r=(1+e)log(A_r)` for fixed-input cost;
4. compute `s_global=log(sum_r w_r exp(s_r))` using fixed covered-value shares;
5. evaluate one fully anticipated constant-elasticity market; and
6. compare the resulting signed change with the already saved sum of separate
   country-market changes under the identical case assumptions.

Missing-value production remains unvalued and is not rescaled. If any valued
regime multiplier is nonpositive, the global case is mechanically inadmissible;
no clipping, dropping or imputation is permitted. CARAIB and EPIC-TAMU remain
separate structural alternatives. No result is selected because it is smaller.

The output must report the global supply multiplier, global-market damage,
country-market diagnostic, their difference and ratio where defined, value and
missing-production coverage, minimum regime multiplier, invalid identities and
false empirical/GIVE/SCC authorization flags. An independent implementation
will reconstruct the source joins and both market geographies without importing
either builder.

One worker at a time remains limited to sampled 512 MiB RSS, 64 MiB owned output
and the 130 GiB free-disk floor. All numerical outputs remain ignored.
