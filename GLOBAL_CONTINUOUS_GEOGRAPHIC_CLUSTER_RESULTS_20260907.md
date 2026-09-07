# Continuous global geographic-validation audit

## Result

The preregistered five-fold audit preserves the September 6 temporal endpoints
but excludes every held-out 10-degree source block from its fold's training
sample. Exact parent support reproduces: 404,671 training and 57,767 terminal
maize pairs, and 166,870 training and 26,004 terminal soybean pairs. Terminal
support spans 123 maize and 55 soybean source blocks, with at least nine blocks
in every crop-fold cell.

| Crop | Model | Pooled held-out RMSE |
|---|---:|---:|
| Maize | Heat controls | 0.293743 |
| Maize | Rainfall quantity | 0.292703 |
| Maize | Quantity + distribution | 0.292909 |
| Maize | Seasonal scPDSI | 0.292955 |
| Maize | Stage scPDSI | 0.292852 |
| Soybean | Heat controls | 0.179393 |
| Soybean | Rainfall quantity | 0.178443 |
| Soybean | Quantity + distribution | 0.177431 |
| Soybean | Seasonal scPDSI | 0.180696 |
| Soybean | Stage scPDSI | 0.180312 |

Paired 5,000-draw source-block bootstrap intervals are conditional on the five
fixed fits. Maize quantity minus controls is -0.001040, with a 95% descriptive
interval of [-0.002109, +0.000135]. Soybean quantity minus controls is
-0.000950 [-0.002301, +0.000535], and soybean quantity-plus-distribution minus
quantity is -0.001012 [-0.002518, +0.000734]. Each crosses zero. Historical
scPDSI minus quantity also crosses zero for maize. For soybean, seasonal and
stage scPDSI are descriptively worse than quantity: +0.002253
[+0.001349, +0.003119] and +0.001869 [+0.000235, +0.003278], respectively.

These are retrospective predictive diagnostics on equal-weight grid-year
pairs. The bootstrap treats 10-degree blocks as descriptive source clusters;
it does not define a random target population or resolve all spatial and GDHY
dependence. No interval is a causal confidence interval and no specification
is promoted.

## Reproducibility and resource gate

The evaluator reads one retained derived Parquet file at a time, separately
for 1982--2010 and 2011--2016, in 8,192-row batches and 10-degree latitude
blocks. The run completed in 24.1 seconds with 394,936,320 bytes peak sampled
process-group RSS; its 15,817-byte aggregate artifact reproduced byte-for-byte
on a second bounded run at SHA-256
`7d570f825259e72764b6ddb54c501c6f2c2833005f05290ef6558bb0eb1fb3a3`.
Six tamper classes plus exact support, hash, fold, condition-number, output-
suppression, result-size, and memory checks pass.

The machine began below the 150 GiB large-work disk floor. Therefore no data
was downloaded, rehydrated, moved, or generated, and no large climate work was
authorized. The small existing-derived audit used an additional 130 GiB stop
floor. Coefficients and row predictions were not saved. Causal response,
future projection, FAIR, damage, welfare, and SCC gates remain closed.
