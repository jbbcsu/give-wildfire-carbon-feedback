version 18
clear all
set more off

args estimate_path coefficient_csv covariance_csv metadata_txt
if `"`estimate_path'"' == "" | `"`coefficient_csv'"' == "" | ///
   `"`covariance_csv'"' == "" | `"`metadata_txt'"' == "" {
    display as error "usage: do hultgren_export_maize_estimate_machine.do ESTIMATE COEFFICIENT_CSV COVARIANCE_CSV METADATA_TXT"
    exit 198
}

estimates use `"`estimate_path'"'
matrix b = e(b)
matrix V = e(V)
local names : colfullnames b
local count = colsof(b)

tempname coefficient_file covariance_file metadata_file
file open `coefficient_file' using `"`coefficient_csv'"', write text replace
file write `coefficient_file' "index,term,estimate" _n
forvalues i = 1/`count' {
    local term : word `i' of `names'
    local value = el(b, 1, `i')
    file write `coefficient_file' "`i',`term'," %24.17g (`value') _n
}
file close `coefficient_file'

file open `covariance_file' using `"`covariance_csv'"', write text replace
file write `covariance_file' "row_index,column_index,row_term,column_term,covariance" _n
forvalues i = 1/`count' {
    local row_term : word `i' of `names'
    forvalues j = 1/`count' {
        local column_term : word `j' of `names'
        local value = el(V, `i', `j')
        file write `covariance_file' "`i',`j',`row_term',`column_term'," %24.17g (`value') _n
    }
}
file close `covariance_file'

file open `metadata_file' using `"`metadata_txt'"', write text replace
file write `metadata_file' "stata_version=`c(stata_version)'" _n
file write `metadata_file' "stata_flavor=`c(flavor)'" _n
file write `metadata_file' "coefficient_count=`count'" _n
file write `metadata_file' "N=" %24.17g (e(N)) _n
file write `metadata_file' "N_full=" %24.17g (e(N_full)) _n
file write `metadata_file' "N_clust1=" %24.17g (e(N_clust1)) _n
file write `metadata_file' "N_clust2=" %24.17g (e(N_clust2)) _n
file write `metadata_file' "r2=" %24.17g (e(r2)) _n
file write `metadata_file' "r2_within=" %24.17g (e(r2_within)) _n
file write `metadata_file' "depvar=`e(depvar)'" _n
file write `metadata_file' "cmd=`e(cmd)'" _n
file write `metadata_file' "vce=`e(vce)'" _n
file write `metadata_file' "clustvar=`e(clustvar)'" _n
file write `metadata_file' "absvars=`e(absvars)'" _n
file write `metadata_file' "indepvars=`e(indepvars)'" _n
file close `metadata_file'
exit, clear
