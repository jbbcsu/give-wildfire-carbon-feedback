# U.S. state direct-practice terminal validation: support audit

## Purpose

Assess whether USDA NASS state-level survey yields can provide a genuinely
newer validation target for the existing U.S. precipitation/drought analysis.
The central target is reported **non-irrigated** corn and soybean yield; the
reported-irrigated series is retained as a comparison, not as a treatment
effect. This support audit reads counts only and cannot estimate a climate
response.

## Frozen source query

Query the official USDA NASS Quick Stats count endpoint separately for each
year 2012--2025, crop (corn and soybean), and production practice (irrigated
and non-irrigated). Require:

- source `SURVEY`, sector `CROPS`, aggregate level `STATE`;
- statistic `YIELD`, frequency `ANNUAL`, reference period `YEAR`;
- class `ALL CLASSES`, domain `TOTAL`, unit `BU / ACRE`;
- utilization `GRAIN` for corn and `BEANS` for soybean; and
- no geography or value filter beyond the fields above.

The API key must be read from the ignored `.secrets/nass.env` file and must
never enter a URL, log, output, exception, or Git artifact. Save only exact
key-free query parameters, counts, retrieval time, and code/protocol hashes.

## Feasibility rule fixed before counts

The intended terminal block is 2020--2025, following a 2012--2019 development
period. A crop/practice series is called *state-panel feasible* only if every
terminal year has at least eight reported state rows and the six terminal
years contain at least 60 state-year rows in total. This is a support rule,
not a power calculation or model-selection criterion. Counts do not establish
that the same states persist through time or that weather can be aligned;
those are separate pre-fit gates.

If non-irrigated support passes, the next stage may acquire the exact records
and construct an outcome-blind state/calendar/weather overlap. No regression
specification may be chosen from the state yield values. State exposures must
use independently fixed crop-area weights and the same direct-rain versus
PDSI competing-family logic. County and state estimates must not be pooled as
if they were independent observations.

## Interpretation boundary

State-level validation would test temporal and geographic transfer of a model
family; it would not make historical associations causal, identify an
irrigation effect, supply a global agricultural response, or authorize damages
or SCC. Suppressed or absent NASS rows remain absent and are never zero-filled.
