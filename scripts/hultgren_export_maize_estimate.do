version 18
clear all
set more off

args estimate_path output_log
if `"`estimate_path'"' == "" | `"`output_log'"' == "" {
    display as error "usage: do hultgren_export_maize_estimate.do ESTIMATE_PATH OUTPUT_LOG"
    exit 198
}

capture log close _all
log using `"`output_log'"', text replace name(hultgren_export)
estimates use `"`estimate_path'"'
ereturn list
matrix list e(b), format(%21.15g)
matrix list e(V), format(%21.15g)
log close hultgren_export
exit, clear
