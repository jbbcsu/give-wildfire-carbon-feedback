# FishMIP–FAO blocked level prediction

## Design

Each FishMIP path receives one multiplicative scale calibrated only on
1990--1999. It then predicts 2000--2014 FAO global marine tonnage. The fixed
benchmark predicts the calibration-block observed mean in every holdout year.
The comparison is run for the contract observed/quality status set and literal
`A`-only tonnage.

## Results

Holdout relative RMSE:

| FishMIP path | Contract quality set | `A` only |
|---|---:|---:|
| GFDL-ESM4 / BOATS | 3.75% | 7.39% |
| GFDL-ESM4 / EcoOcean | 10.91% | 16.57% |
| IPSL-CM6A-LR / BOATS | 12.26% | 17.70% |
| IPSL-CM6A-LR / EcoOcean | 11.60% | 16.93% |
| Constant observed-mean benchmark | 3.40% | 7.96% |

No FishMIP path beats the constant benchmark under the contract quality set.
Under `A` only, GFDL/BOATS is slightly better (7.39% versus 7.96%); the other
three are substantially worse. The apparent full-period level correlations
therefore do not translate into robust blocked predictive superiority.

## Boundary

This split was evaluated after related historical evidence had been inspected,
so it is not a pristine preregistered test and is not used to select a model.
Observed landings combine ecology, effort, management, markets, technology,
and reporting. The result blocks direct empirical weighting of the four paths
by historical level fit; it does not invalidate their use as structural
scenarios.

A separate implementation reconstructed all 48 saved metrics directly from
the full reconciled FishStat export with maximum discrepancy `6.94e-17`. No
causal climate effect, welfare, marginal carbon pulse, damage, or SCC is
estimated.
