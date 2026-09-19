# Methods SI insert: precipitation quantity benchmark and drought bridge

Status: reproducible supplement text for later merge. The calculations below
are structural sensitivities and engineering results. They do not authorize an
empirical agriculture replacement, GIVE export, or SCC estimate.

## S1. Separation of estimands

We maintain three distinct objects:

1. a **quantity-only structural benchmark**, in which published process-crop
   emulators map period-mean temperature and precipitation changes to maize
   yield;
2. a **distribution-aware empirical estimand**, in which total precipitation,
   wet-day frequency, dry-spell duration, extremes, and competing drought
   indices predict observed crop outcomes under prespecified validation; and
3. a **marginal SCC path**, which requires matched baseline and emissions-pulse
   climate exposures, annual damages, adaptation assumptions, and GIVE's
   discounting and aggregation machinery.

Results are never transferred between these objects by relabeling. In
particular, a period-mean crop-model sensitivity is not evidence about rainfall
timing, and a scenario difference is not an emissions-pulse derivative.

## S2. Quantity-only physical benchmark

The structural benchmark uses four yield corners from the separately audited
CARAIB and EPIC-TAMU maize emulators:

- `y00`: baseline temperature and baseline precipitation;
- `y10`: future temperature and baseline precipitation;
- `y01`: baseline temperature and future precipitation; and
- `y11`: future temperature and future precipitation.

The experiments compare 1981--2010 and 2031--2060 climate from GFDL-ESM4 and
IPSL-CM6A-LR under SSP1-2.6 and SSP5-8.5, with CO2 and management fixed. The two
crop models, two crop-calendar conventions, and rainfed/irrigated regimes remain
separate. Cell production weights are fixed from MapSPAM common support.
FAOSTAT 1999--2001 value proxies are allocated across supported cells without
filling missing countries or rescaling incomplete coverage, then converted once
to USD2005 using the registered central price scalar.

For a cell yield multiplier `A=yab/y00`, two prespecified supply mappings are
reported: `s=log(A)` (horizontal output) and `s=(1+e)log(A)` (fixed-input cost),
where `e` is the supply elasticity. No negative or zero yield corner is clipped.

## S3. Market equilibrium and welfare

Normalized supply and demand are

`qS(p;s)=exp(s)p^e` and `qD(p)=p^(-d)`,

where `d` is the absolute demand elasticity. Equilibrium implies
`log(p)=-s/(e+d)` and `log(q)=ds/(e+d)`. For a supply-shift increment `h` from
zero, total-surplus change is evaluated in the numerically stable form

`DeltaTS = V0 h exprel(-(1-d)h/(e+d))/(1+e)`,

with `exprel(z)=expm1(z)/z` and baseline covered value `V0`. Damage is
`-DeltaTS`. The registered elasticity pairs are (supply, demand) = (0.08,
0.02), (0.10, 0.04), and (0.50, 0.06).

For the primary structural calculation, fixed covered-value weights `wi` are
pooled into one global maize market before equilibrium:

`Sab = sum_i wi (yab_i/y00_i)^k`,

where `k=1` or `1+e`. The global shift is `log(Sab)`. A country-market version
is retained only as structural sensitivity because isolated inelastic markets
can magnify a small country's crop-model tail into an implausibly large welfare
result.

## S4. Four-corner precipitation attribution

Welfare is first evaluated at all four physical corners, giving benefits
`B00`, `B10`, `B01`, and `B11`. Only then are drivers attributed using a
two-player Shapley decomposition:

- precipitation benefit: `0.5[(B01-B00)+(B11-B10)]`;
- temperature benefit: `0.5[(B10-B00)+(B11-B01)]`; and
- joint benefit: `B11-B00`.

This shares the nonlinear interaction equally and requires precipitation plus
temperature damage to close to joint damage. It avoids applying the market
model to an order-averaged yield contribution as if it were an independent
supply shock.

## S5. Fixed-support sensitivity

The primary diagnostic preserves nonpositive crop-model corners and disables
substantive interpretation when they occur. A separate sensitivity constructs
one mask before welfare calculation: retain a cell/regime only when every
corner is finite and strictly positive for both crop models, both climate
models, both scenarios, and both calendars. The mask is never changed by case.

Excluded value is removed rather than redistributed. The mask excludes 186
cell/regime locations, 0.01751% of common production, and 24.584 million of
109.047 billion USD2005 covered value. This is a partial-support diagnostic, not
a repair of the crop emulator. Results that become calculable only after this
restriction remain ineligible for the main estimate.

## S6. Distribution-aware drought bridge

The climate pipeline computes total rainfall and direct distribution features
from daily data, alongside SPEI at 1-, 3-, and 6-month accumulation scales.
Drought indices are treated as competing moisture-stress representations, not
automatically stacked with their precipitation inputs. A model using raw
precipitation and temperature competes out of sample against a model using
SPEI; combining them requires a separately prespecified attribution design.

The September 19 GFDL pilot maps monthly SPEI to fixed rainfed and irrigated
maize/soy calendars for 2015--2020, three SSPs, five crop windows, and three
accumulation scales. Each monthly index is weighted by its exact day overlap
with a crop window. Irrigation-regime values are calculated first and then
combined using fixed MIRCA-OS v2 area shares. The output comprises 163,350
regime rows and 150,390 combined rows, with 1,066,451 independent checks. It is
an exposure-engineering validation only; it contains no yield response.

## S7. Independent validation and provenance

Builders and validators are separate programs. Validators reconstruct source
hashes, allocations, market aggregation, all four welfare corners, Shapley
arithmetic, closure identities, support counts, and declared output hashes
without importing the builder. The full-support attribution has 96 registered
economic cases, 84 mechanically admissible cases, and 3,081 validation checks.
The fixed-support sensitivity has 96 cases and 1,929 validation checks.

Machine-readable receipts are stored in:

- `data/provenance/four_corner_welfare_attribution_20260919.json`;
- `data/provenance/fixed_positive_crop_support_20260919.json`;
- `data/provenance/fixed_positive_welfare_sensitivity_20260919.json`; and
- `data/provenance/gfdl_future_spei_crop_windows_20260919.json`.

Raw and numerical interim files remain ignored. Each numerical job is limited
to one worker, sampled group RSS of 512 MiB, owned output of 64 MiB, and a 130
GiB free-disk floor. The published Araujo drought archives were not downloaded:
the five GIVE-overlap model archives total 149.18 GiB, exceed the safe local
storage plan, and lack repository archive checksums.

## S8. GIVE release conditions

The agriculture replacement remains disabled until a distribution-aware or
parsimonious quantity response passes untouched geographic and temporal
validation, climate features cover multiple later-century ESMs, fixed/trend/
upper adaptation scenarios are calibrated, monetary coverage is complete, and
matched baseline and emissions-pulse annual damage paths run through GIVE.
Structural benchmark values must not be added to the existing GIVE agriculture
sector. All current provenance receipts therefore retain false flags for
empirical damage authorization, agriculture replacement, GIVE export, and SCC.
