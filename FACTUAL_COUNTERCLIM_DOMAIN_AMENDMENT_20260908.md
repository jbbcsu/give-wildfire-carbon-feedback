# Explicit counterclim domain amendment after a preserved failure

The original full-rectangle completeness gate rejected the first downloaded
counterclim precipitation file:2,753,608nonfinite values. Inspection of the
unchanged1981–1990file found686cells finite on all3,652days,754cells missing
on every day and zero intermittently missing cells. All four pre-existing
crop calendars have exactly the same686valid cells; none has missing weather.
The original failed gate, file, receipt and log remain preserved.

This is a domain correction, not imputation or relaxation of crop completeness.
A separate source-specific validator may accept counterclim data only when
finite support EXACTLY equals the fixed GGCMI2015soc four-calendar mask, for
every day. It must reject any missing crop value, intermittent availability,
infinity, finite value outside the registered static mask, different masks
across calendars or anything other than the686/754split. Negative crop-domain
precipitation, wrong grid/dates/units and source identity still fail closed.
No observations or cells are dropped from the originally planned crop sample.

This validation is restricted to the three registered GSWP3-W5E5 ISIMIP3a
counterclim datasets,version20220506, and the same two-row pilot. Factual and
GCM full-rectangle validators are unchanged. Use the distinct status
crop_domain_climate_content_validated and report full-grid missing counts,
crop missing counts and all calendar hashes. Existing untouched payloads may
be revalidated using a NEW receipt with the original failure/file hashes;
do not redownload, overwrite a failed receipt or call the initial run passed.

No counterfactual yield/damage results have been computed or inspected before
this amendment. The criterion is the pre-existing crop support, not a
data-selected result. Record this amendment's hash in new receipts and products.
Future comparison still requires exact factual-product parity, paired daily
axes, all crop years and all originally registered scientific gates.
