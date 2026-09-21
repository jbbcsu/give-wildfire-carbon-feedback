# Current precipitation-agriculture evidence hierarchy

This note integrates the independently audited results available through
September 21, 2026. It is designed for direct manuscript use but does not change any
model-selection or SCC gate.

## What can now be said

1. **Future rainfall patterns change in ways annual totals do not summarize.**
   On fixed rainfed-maize area across five direct daily ISIMIP3b ESMs, late-
   century SSP5-8.5 minus SSP1-2.6 seasonal rainfall is positive in three
   models and negative in two (-67.679 to +20.124 mm). Wet days fall and the
   longest dry spell and Rx1day rise in all five; Rx5day rises in four. Under
   SSP3-7.0, rainfall is positive in two models, while wet days still fall and
   longest dry spells rise in all five. These are eight-year scenario
   contrasts, not forced responses or yield effects. Source:
   `FIVE_ESM_MAIZE_AREA_WEATHER_RESULTS_20260921.md`.

2. **Rainfall quantity has a stable U.S. non-irrigated association, but not a
   causal global coefficient.** A roughly 105--114 mm within-range rainfall
   reduction is associated with fitted non-irrigated corn/soy losses under two
   weather sources, while reported-irrigated intervals include zero. Pooled
   distribution and drought predictors add out-of-sample information, but
   geographic and temperature-control tests are not uniformly stable. Source:
   `US_NASS_EVIDENCE_SYNTHESIS_RESULTS_20260919.md`.

3. **The global historical empirical screen promotes no response family.**
   Maize quantity improves point prediction over heat-only and zero-change
   comparators, but paired intervals cross zero; soybean quantity loses to the
   zero-change comparator and has insufficient folds. Distribution is point-
   worse than quantity for both crops, and scPDSI is unstable or worse. Source:
   `GLOBAL_RESPONSE_EVIDENCE_DECISION_RESULTS_20260919.md`.

4. **The future drought feature pipeline now reaches crop windows.** Monthly
   observationally standardized SPEI-1/3/6 maps reproducibly into fixed maize
   and soybean seasons, three stages and preplant windows for the GFDL pilot.
   This is a completed climate-to-exposure bridge, not a yield response. Source:
   `GFDL_FUTURE_SPEI_CROP_WINDOW_RESULTS_20260919.md`.

5. **A quantity-only structural crop benchmark can be monetized, but it is not
   the final precipitation result.** Four-corner welfare evaluation assigns the
   temperature/precipitation interaction without double counting. In the
   central global-market benchmark, precipitation is beneficial under the
   admissible SSP1-2.6 cases and a small loss under admissible SSP5-8.5 cases;
   temperature dominates joint maize losses. Source:
   `FOUR_CORNER_WELFARE_ATTRIBUTION_RESULTS_20260919.md`.

6. **Economic market geography is a first-order structural uncertainty when
   local crop responses are severe.** CARAIB is stable between global and
   country markets, but EPIC IPSL/SSP1-2.6 falls from roughly 106 billion to
   10.6--10.7 billion USD2005 when supply is pooled before equilibrium. The
   separate-country extreme is dominated by one small market. Source:
   `GLOBAL_MARKET_WELFARE_SENSITIVITY_RESULTS_20260919.md`.

## What cannot yet be said

- There is no validated global causal yield response to precipitation quantity,
  distribution, drought or their interactions.
- The structural four-corner results do not represent within-season timing,
  dry spells, extremes or SPEI/PDSI effects; they use period-mean precipitation
  quantity perturbations.
- The GFDL SPEI pilot covers 2015--2020 on a 512-cell boundary sample and cannot
  identify scenario ordering or later-century drought damages.
- No result supplies matched annual baseline and CO2-pulse climate paths.
- Trend and upper adaptation trajectories and costs remain uncalibrated.
- No current monetary result is a total-agriculture replacement; stacking it on
  GIVE's existing agriculture function would double count climate effects.
- No agriculture result is authorized for GIVE export or SCC calculation.

## Evidence-led primary and sensitivity hierarchy

| Layer | Primary use now | Prespecified alternatives | Current decision |
|---|---|---|---|
| Climate exposure | Direct daily quantity and pattern features | Published positive monthly emulators; SPEI/scPDSI | Report exposure changes; do not infer yield |
| U.S. validation | Non-irrigated quantity benchmark | Direct distribution and PDSI as competing models | Predictive/associational only |
| Global empirical response | Quantity + temperature research comparator | Distribution and drought | None promoted |
| Structural crop response | CARAIB and EPIC as separate benchmarks | Calendar, ESM, scenario, irrigation | Do not ensemble or select by damage |
| Welfare | Global and country markets as structural sensitivities | Three elasticity pairs; two supply mappings | No preferred geography from magnitude |
| Attribution | Four-corner welfare Shapley | Report joint response without attribution | Never add driver effects twice |
| Adaptation | Fixed management benchmark | Trend and upper cases | Latter two await calibration |
| SCC | Paired annual marginal-damage interface | None | Closed |

## Highest-value next work

The precipitation priority is no longer generic feature construction. The next
decisive evidence is a response model that passes an untouched spatial or
temporal validation and can be paired with the now-complete five-ESM
later-century crop-window pattern matrix. The full temperature-inclusive SPEI
matrix remains a large acquisition; the project recovered 25.944 GiB by
evicting a checksum-reproducible NOAA grid cache, but still preserves the
130-GiB free-space floor. Resident-input work should:

1. preserve quantity, direct-pattern and drought representations as competitors;
2. test whether any response transports outside the currently exposed outcomes;
3. keep irrigation regimes explicit and avoid interpreting zero modeled rain
   sensitivity as zero water scarcity or irrigation cost;
4. maintain four-corner attribution whenever nonlinear welfare is evaluated;
5. reject nonpositive crop-model aggregates rather than clipping; and
6. treat all current monetary values as structural sensitivities, never SCC.

## Publication framing

The defensible standalone contribution is the comparison of annual amount,
within-season distribution and drought representations across an auditable
climate-to-crop-to-welfare chain, including transparent null results and
failure gates. The structural quantity-only benchmark is informative precisely
because it shows what a conventional mean-climate crop emulator captures—and
what it misses. The paper should not be framed around a positive SCC number
until the response and paired-climate gates genuinely pass.
