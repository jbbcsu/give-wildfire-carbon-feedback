# Unsent Hultgren replication-data request

**Status:** draft only. Do not send without project-owner approval.

**To:** Andrew Hultgren (`ahultgr@illinois.edu`)

**Subject:** Missing regression input in Hultgren et al. (2025) replication package

Dear Professor Hultgren,

We are developing an independent precipitation-sensitive agricultural-damages
extension for the GIVE model and would like to reproduce your published maize
weather response as an external benchmark. We reviewed the Nature
Supplementary Information and pinned the public GitLab replication repository
at commit `3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`.

The public code expects
`impact_data/for_regressions/corn_gmfd_v1_ready.dta`, but that file is not in
the repository. The Box link currently given in the repository README
(`a1ni7tthdtw5qqss5iifpe1mc7otqmte`) returned HTTP 404 when checked on 23
September 2026. We also inspected the older `impact_data.zip` retained in the
repository's Git history; it contains historical projection outputs but not
the required regression input and predates the final 2025 estimate.

Could you provide a current access route for the version-matched regression
data, or point us to its replacement? We would also appreciate confirmation of:

1. the applicable reuse and redistribution terms for the regression data;
2. whether `prcp_poly_1_bin1`--`bin3` and `prcp_poly_2_bin1`--`bin3` are sums
   of grid-cell monthly polynomial transforms within the maize phases (month
   1, months 2--4, and months 5+), or a different numerical aggregation; and
3. the baseline moderator values or source fields used to reproduce the
   published local response plots (`ln_gdppc`, `irrigated_share`,
   `lr_tmax_crop`, and the capped long-run precipitation terms).

We have successfully opened the published maize estimate and independently
exported its 49 coefficients and complete covariance matrix, but we are not
applying those coefficients to future climate until the historical transform
and baseline-covariate numerics can be reproduced. Any help identifying the
version-matched data would be greatly appreciated.

Best regards,

[Name and affiliation]
