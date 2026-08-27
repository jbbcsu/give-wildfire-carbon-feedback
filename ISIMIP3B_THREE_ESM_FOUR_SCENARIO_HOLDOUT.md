# Three-ESM by four-scenario joint holdout

Status: **both bounded holdout products pass; the emulator is not promoted and no damage or SCC use is authorized.**

The exact bounded product now spans GFDL-ESM4, IPSL-CM6A-LR, and MPI-ESM1-2-HR, each using its frozen realization across historical, SSP1-2.6, SSP3-7.0, and SSP5-8.5. The joint training artifact has 339,570 rows for eleven rainfall/temperature feature families.

Whole-ESM holdouts improved on the cell-mean benchmark in 22/33 folds, with median RMSE ratio 0.997053 and worst ratio 1.011815. Held-out GFDL improved in only 2/11 folds, while held-out IPSL and MPI each improved in 10/11.

Whole-scenario holdouts improved in 25/44 folds, with median RMSE ratio 0.998104 and worst ratio 1.030947. Improvement counts were 1/11 historical, 9/11 SSP1-2.6, 6/11 SSP3-7.0, and 9/11 SSP5-8.5. Historical generalization remains the clearest weakness.

These results are bounded engineering evidence only: seven nonoverlapping harvest years, maize/rainfed, and two latitude rows. Two frozen ESMs, complete temporal coverage, common-random-number baseline/pulse pairing, support flags, zero-pulse/pre-divergence identity, decreasing-pulse convergence, yield response, damages, and SCC integration remain open.
