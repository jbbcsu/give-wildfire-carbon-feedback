# Precipitation metrics and weather-source uncertainty: focused update

Status: literature review, not new empirical evidence. Reviewed September 8,
2026 while the regional climate acquisition chain continued. This is not a
systematic review or a claim that all relevant papers have been found.

## Closely overlapping global precipitation study

Jin, H., Zhang, K., Liu, M., and Yu, X. (2026), *Disentangling the relative
impacts of precipitation metrics on global crop yields*, Journal of Cleaner
Production, [doi:10.1016/j.jclepro.2026.147663](https://doi.org/10.1016/j.jclepro.2026.147663).
The publisher's indexed abstract describes a machine-learning comparison for
global rice, wheat and maize over 1982–2015. It reports annual precipitation
as the highest-ranked indicator, followed by maximum daily precipitation and
extreme intensity; it also reports substantial geographic heterogeneity.
These are the authors' findings, not a reproduction by this project.

Access: publisher-indexed abstract/highlights and limited section excerpts
were retrieved; direct publisher-page opening failed. Full Methods, supplement,
code, temperature/CO2/irrigation controls, validation splits and uncertainty
procedures have NOT been verified. Do not infer that a control or validation
step is absent because it is not described in the accessible abstract.

Implication for this project: no claim to be the first global comparison of
rainfall amounts and extremes using machine learning. Feature ranking is not
itself an identified precipitation damage function. The useful distinction to
develop is the economic estimand and independently tested climate-to-yield-to-
welfare chain, not an architecture chosen merely to look different. Our
quantity-first decision must stand on our own validation, not this ranking.

## Weather-source uncertainty already has direct agricultural precedent

Parkes, B., Higginbottom, T. P., Hufkens, K., Ceballos, F., Kramer, B., and
Foster, T. (2019), *Weather dataset choice introduces uncertainty to estimates
of crop yield responses to climate variability and change*, Environmental
Research Letters, [doi:10.1088/1748-9326/ab5ebb](https://doi.org/10.1088/1748-9326/ab5ebb).
The author-institution [publication record](https://research.manchester.ac.uk/en/publications/weather-dataset-choice-introduces-uncertainty-to-estimates-of-cro/)
reports that gridded weather products differ across India and that these
differences affect estimated crop responses and weather exposure. This
supports explicitly evaluating input-source uncertainty; it does not identify
the cause of our U.S. GSWP/nClimGrid differences. Review depth here is the
institutional abstract/metadata and publisher-indexed excerpts, not a full
replication or Methods audit. Publisher retrieval was blocked by robots.

## Operational consequence

The next study holds NASS outcomes, county-years, calendars, model family and
irrigation definitions fixed while fitting separately with factual GSWP and
nClimGrid weather. It tests whether the response changes with weather source.
It does not average the sources, correct one using the other, call either
error-free, or export existing barred coefficients into counterclim paths.
The prospective contract is `US_SOURCE_MATCHED_RESPONSE_PROTOCOL_20260908.md`.
It is exploratory because the historical outcome years were already used.

Existing relevant literature and GDHY source-dependence qualifications remain
in `AGRICULTURE_RESEARCH.md`, `GDHY_SUPPORT_AUDIT.md`, and `SOURCES.md`.
This update does not establish a global causal response, anthropogenic forcing
contrast, adaptation parameter, welfare mapping, or SCC increment.
