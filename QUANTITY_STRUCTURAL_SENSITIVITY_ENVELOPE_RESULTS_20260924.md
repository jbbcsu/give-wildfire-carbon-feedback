# Quantity-channel structural-sensitivity envelope

## Scope

The smallest converged pulse is summarized across the complete balanced design:
26 climate models, three adaptation cases, two tail rules, three registered
elasticity pairs, two yield-to-supply mappings, and four Ramsey schedules. The
3,744 values are equally summarized design cells. They are not Monte Carlo
draws, and their percentiles are not confidence or probability intervals.

## Results

| Ramsey schedule | Cells | Mean | Median | 2.5th design percentile | 97.5th design percentile | Full range | Negative cells |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.5% | 936 | -$0.009695 | -$0.010009 | -$0.016664 | $0.001023 | -$0.017939 to $0.005039 | 912 |
| 2.0% | 936 | -$0.006608 | -$0.006886 | -$0.011373 | $0.001037 | -$0.012211 to $0.003482 | 900 |
| 2.5% | 936 | -$0.004861 | -$0.005107 | -$0.008409 | $0.000990 | -$0.008971 to $0.002593 | 900 |
| 3.0% | 936 | -$0.003805 | -$0.003960 | -$0.006635 | $0.000917 | -$0.007014 to $0.002049 | 900 |

Values are 2020 USD per tCO2; negative values denote benefits. At the 2%
schedule, conditional means are -$0.00616, -$0.00658, and -$0.00708 for fixed,
trend, and upper adaptation; -$0.00661 under either tail treatment after
rounding; and -$0.00721 versus -$0.00601 for fixed-input-cost versus
horizontal-output supply mappings.

## Validation and interpretation

The source 11,232-value diagnostic was previously reconstructed independently
from all 1,052,064 annual rows within `1.22e-16` USD per tCO2. The smallest two
pulses agree within `6.89e-6` relatively. The central 104-value subset matches
the fully paired 26-model GIVE replacement summary exactly.

Only the central subset has been rerun through paired GIVE. The other cells are
paired-equivalent diagnostics under the validated anchored-linear accounting
identity; they are not described as paired executions. This envelope captures
registered climate-model and structural-choice spread, not empirical
coefficient uncertainty, and still omits rainfall timing, drought, temperature,
other crops, irrigation adaptation, trade, storage, and adaptation costs.
