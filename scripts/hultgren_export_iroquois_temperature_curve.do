version 18
clear all
set more off

args data_path estimate_path output_path
if `"`data_path'"' == "" | `"`estimate_path'"' == "" | `"`output_path'"' == "" {
    display as error "usage: do hultgren_export_iroquois_temperature_curve.do DATA ESTIMATE OUTPUT"
    exit 198
}

use `"`data_path'"', clear
estimates use `"`estimate_path'"'

drop if missing(lr_tmax_crop, ln_gdppc, irrigated_share, lr_prcp_crop, ln_yield)
keep if adm2 == "iroquois" & iso == "USA"

egen sample_tbar = mean(lr_tmax_crop)
egen sample_pbar = mean(lr_prcp_crop)
egen sample_inc = mean(ln_gdppc)
egen sample_ir = mean(irrigated_share)
collapse (mean) sample_tbar sample_pbar sample_inc sample_ir (count) ln_yield
rename ln_yield num_obs
generate double ln_yield = .

expand 40
generate double tavg = _n
generate double gdd_plot = cond(tavg <= 8, 0, cond(tavg < 31, tavg - 8, 23))
generate double kdd_plot = cond(tavg <= 31, 0, tavg - 31)
generate double pbarcut_gdd = min(sample_pbar, 200)
generate double pbarcut_kdd = min(sample_pbar, 100)

predictnl double response = ///
    _b[gdd] * gdd_plot + ///
    _b[c.gdd#c.ln_gdppc] * gdd_plot * sample_inc + ///
    _b[c.gdd#c.irrigated_share] * gdd_plot * sample_ir + ///
    _b[c.gdd#c.lr_tmax_crop] * gdd_plot * sample_tbar + ///
    _b[c.gdd#c.pbarcut_gdd] * gdd_plot * pbarcut_gdd + ///
    _b[c.gdd#c.lr_tmax_crop#c.pbarcut_gdd] * gdd_plot * sample_tbar * pbarcut_gdd + ///
    _b[kdd] * kdd_plot + ///
    _b[c.kdd#c.ln_gdppc] * kdd_plot * sample_inc + ///
    _b[c.kdd#c.irrigated_share] * kdd_plot * sample_ir + ///
    _b[c.kdd#c.lr_tmax_crop] * kdd_plot * sample_tbar + ///
    _b[c.kdd#c.pbarcut_kdd] * kdd_plot * pbarcut_kdd + ///
    _b[c.kdd#c.lr_tmax_crop#c.pbarcut_kdd] * kdd_plot * sample_tbar * pbarcut_kdd, ///
    se(standard_error)

order tavg response standard_error gdd_plot kdd_plot num_obs sample_tbar sample_pbar sample_inc sample_ir
export delimited using `"`output_path'"', replace
exit, clear
