# Unsent Hultgren replication-data request

**Status:** draft only. Do not send without project-owner approval.

**To:** Andrew Hultgren (`ahultgr@illinois.edu`)

**Subject:** Primitive climate and spatial-weight inputs for Hultgren et al. (2025)

Dear Professor Hultgren,

We are developing an independent precipitation-sensitive agricultural-damages
extension for the GIVE model and would like to use your published maize weather
response as an external benchmark. We reviewed the Nature Supplementary
Information and pinned the public GitLab replication repository at commit
`3ccdffcd4e4ff6e55566ce76e2aac130ee86349a`.

We recovered `corn_gmfd_v1_ready.dta` from public Git history at commit
`dae5fe8d0d4a260328e4baa45b547368bd6790b3`. Using it, we reproduce the 49
published maize coefficients to relative L2 error `2.42e-14`, the covariance
matrix to `2.65e-6`, all calendar/phase assignments, and the Iroquois local
response plot. We also confirmed that monthly precipitation is transformed in
each grid cell before crop-weighted aggregation and that temperature exposure
uses Snyder's Tmin--Tmax sinusoidal integration.

The remaining gap is upstream. The current public repository and the reviewed
historical commit do not appear to include the primitive GMFD daily precipitation,
minimum-temperature and maximum-temperature inputs, the SAGE any-crop pixel
weights used for administrative aggregation, or the corresponding future
NEX-GDDP transformed inputs. The current
`Fig1/Crop_Coverage/data/crops/corn_gmfd_v1.dta` contains only identifiers,
years, planted area and harvested area; the published
`agglomerated-world-new-hierid-crop-weights.csv` is a downstream
administrative aggregation table rather than the grid-cell weather weights.

Could you provide or identify a version-matched access route for:

1. the historical GMFD daily inputs or the intermediate grid-cell weather
   features used to produce the administrative-unit regression variables;
2. the exact SAGE any-crop grid weights, including source version and the
   pixel-to-impact-region overlap and normalization convention used for weather
   aggregation;
3. the complete GADM/source-unit-to-`hierid` agglomeration membership crosswalk
   (the public hierarchy identifies one terminal label per impact region but is
   not sufficient to recover all source-unit memberships by name);
4. the future NEX-GDDP transformed weather inputs (or an equivalent
   administrative-unit weather-feature output) and their historical baseline
   convention; and
5. the applicable reuse and redistribution terms for these inputs and the
   prepared regression data.

We can run a clearly labeled alternative-product benchmark using ISIMIP
weather and MIRCA maize weights, but we do not want to represent that as an
exact replication of your climate-input pipeline. Any help locating the
version-matched inputs would be greatly appreciated.

Best regards,

[Name and affiliation]
