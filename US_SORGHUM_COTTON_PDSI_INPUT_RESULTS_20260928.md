# U.S. sorghum and cotton PDSI input results

## Result

All 475 outcome counties match 2019 TIGER GEOIDs. The prespecified Census
county-change screen excludes Adams, Arapahoe, and Weld Counties, Colorado,
pending historical-boundary resolution. Those exclusions remove 44 sorghum
pairs and no cotton pairs, leaving 5,226 sorghum and 3,501 cotton paired
county-years in 472 unique counties.

The pinned NOAA nClimDiv county PDSI snapshot supplies all 226,560 required
county-months for 1980--2019. Under the fixed-primary NASS crop calendar, the
pipeline constructs preplant-90-day, three equal-duration stage, and full-
season PDSI summaries. The final panel contains 17,454 practice rows and all
8,727 exact pairs, with 25 complete PDSI fields and no missing cells.
Independent validation confirms that each pair contains both practices and
that every PDSI feature is identical across them.

## Interpretation boundary

This is a complete historical input, not a response estimate. PDSI is retained
as a mutually exclusive moisture-stress representation: raw precipitation and
temperature are not co-included in this panel. The index is monthly and the
stage statistics are day-weighted monthly values, not daily observations.
NASS usual dates are fixed state-level calendars shared across practices; the
cotton calendar covers all cotton while the outcome is upland cotton. NOAA's
PDSI excludes irrigation and is not realized soil moisture. No causal,
national, future-climate, damage, or SCC claim is authorized.

