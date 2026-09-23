version 18
clear all
set more off

args data_path estimate_path log_path
if `"`data_path'"' == "" | `"`estimate_path'"' == "" | `"`log_path'"' == "" {
    display as error "usage: do hultgren_reproduce_maize_historical.do DATA_PATH ESTIMATE_PATH LOG_PATH"
    exit 198
}

log using `"`log_path'"', text replace name(hultgren_reproduce)
use `"`data_path'"', clear

* Published maize long-run-precipitation spline caps.
capture drop pbarcut_gdd pbarcut_kdd pbarcut_prcp
generate double pbarcut_gdd = cond(lr_prcp_crop >= 200, 200, lr_prcp_crop)
generate double pbarcut_kdd = cond(lr_prcp_crop >= 100, 100, lr_prcp_crop)
generate double pbarcut_prcp = cond(lr_prcp_crop >= 250, 250, lr_prcp_crop)

* Exact ordered RHS stored in the published .ster file.  The response terms are
* interacted separately with income, irrigation, long-run temperature, capped
* long-run precipitation, and their temperature-by-precipitation interaction.
local rhs ""
foreach weather in gdd kdd {
    local capvar pbarcut_`weather'
    local rhs "`rhs' `weather' c.`weather'#c.ln_gdppc c.`weather'#c.irrigated_share c.`weather'#c.lr_tmax_crop c.`weather'#c.`capvar' c.`weather'#c.lr_tmax_crop#c.`capvar'"
}
foreach power in 1 2 {
    foreach bin in 1 2 3 {
        local weather prcp_poly_`power'_bin`bin'
        local rhs "`rhs' `weather' c.`weather'#c.ln_gdppc c.`weather'#c.irrigated_share c.`weather'#c.lr_tmax_crop c.`weather'#c.pbarcut_prcp c.`weather'#c.lr_tmax_crop#c.pbarcut_prcp"
    }
}

reghdfe ln_yield `rhs', absorb(uid i.adm1_fact##c.(time time_sqr) adm0_year) vce(cluster adm0_year adm1_fact) residuals(hultgren_replication_resid)
estimates save `"`estimate_path'"', replace
estimates describe
log close hultgren_reproduce
exit, clear
