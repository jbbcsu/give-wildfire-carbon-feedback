# Next stage: source-matched historical checks before response transport

Status: prospective design, not completed analysis. The full-period future
GFDL/IPSL heat and rainfall diagnostics are complete. Do not repeat them.

## Why this step is needed

Future heat is frequently outside observed historical ranges, but this cannot
be attributed entirely to warming: the historical exposure source and future
bias-adjusted model source differ. Existing retained ISIMIP historical smoke
features cover only2012–2014 and one maize irrigation calendar; they cannot
stand in for the1982–2010training-period benchmark.

## Executable source and construction sequence

1. Inspect retained historical manifests without hydrating evicted raw files.
   Locate official catalogue records for GFDL-ESM4/IPSL-CM6A-LR r1i1p1f1 W5E5
   historical daily pr,tas,tasmax,1981–2010. Verify current rights, source
   version and date blocks; do not infer hashes or accept a mismatched member.
   Use the same two-row spatial cutouts and sequential64MiB acquisition batches
   under standing authorization, with130GiB free reserve. Start with GFDL;
   expand only after its baseline joint inputs validate.
2. Build harvest-year1982–2010rainfall/stage and heat inputs on the same four
   calendars and fixed irrigation shares. Reuse existing tested feature
   builders, but use a separate historical wrapper: the future-only wrapper
   must continue rejecting undocumented periods and synthetic future yields.
3. Compare historical **distributions**, not paired-year weather realizations:
   free-running model years do not reproduce the observed weather sequence.
   Assess seasonal quantity, dry-spell/extreme/stage-share distributions,
   stage Tmean and heat thresholds on exact shared cells and calendars.
   Report domain coverage and both model–observation and future–model-historical
   shifts. Preserve climate-source/model uncertainty rather than treating a
   historical source offset as forced change.
4. Predefine any correction or delta-transfer method before fitting or viewing
   future crop outcomes. Do not silently debias derived nonlinear indices or
   alter rainfall/temperature dependence. Compare uncorrected and source-matched
   exposure support; neither alone establishes causal response transport.

## Response and valuation sequence

Use quantity as the parsimonious candidate; distribution and drought are
competing specifications subject to the completed out-of-sample evidence.
Do not export barred diagnostic coefficients or override failed promotion
gates. Develop a separate explicit research response contract addressing
short-run weather identification versus long-run adaptation, nonlinear heat,
country/space dependence, irrigation, CO2, source construction and joint
support. Retain null soybean and weak incremental timing evidence plainly.

For scenario decomposition, distinguish total joint climate response from a
formal precipitation-held-temperature contrast; explain dependence and
interaction allocation rather than adding moisture specifications. A scenario
contrast is not the GIVE emissions pulse. Production/value weighting, market
cost/inventory conventions and fixed/trend/upper adaptation parameters remain
separate calibration tasks. No new user download approval is needed; ask only
for genuinely consequential unresolved scientific choices after evidence-based
defaults and safe alternatives have been assessed.
