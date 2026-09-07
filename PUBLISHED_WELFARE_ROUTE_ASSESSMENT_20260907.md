# Published welfare route: assessment and next implementation step

## What exists

Moore et al. translate crop-productivity shocks through GTAP, including trade
and other general-equilibrium effects. Their calibrated agricultural damage
functions summarize specified warming scenarios; those outputs are not a
general matrix mapping arbitrary new rainfall shocks into welfare.
[Moore et al. (2017)](https://www.nature.com/articles/s41467-017-01792-x).

Hultgren et al. instead describe constant-elasticity calorie supply and demand
and changes in producer and consumer welfare. Their main market assumption
permits within-country trade, with broader trading areas as sensitivities.
They link this valuation to a partial agricultural SCC. Section K of their
supplement contains the detailed valuation methods; the main Methods identify
elasticity sources. This establishes a published alternative to developing a
new GTAP emulator; it does not establish that our implementation or inputs are
ready. [Hultgren et al. (2025), Methods](https://www.nature.com/articles/s41586-025-09085-w).

The authors' [Zenodo record](https://zenodo.org/records/14511340) points to a
[GitLab replication package](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package).
Its [README](https://gitlab.com/ClimateImpactLab/cil-ag-replication-package/-/raw/main/README.md)
describes main-figure, table and regression replication and separate impact
data hosted on Box. This inspection has NOT verified a reusable welfare or
marginal-pulse implementation, file sizes, or redistribution licenses. No
repository or data archive was downloaded and no external code was copied.

## Local integration finding

Read-only inspection of the archived native GIVE dependency
`packages/MooreAg/src/core/AgricultureComponent.jl` confirms three welfare
responses per FUND region (`gtap_df`) interpolated against global warming,
followed by agricultural-income scaling. These cannot simply be inverted to
price an arbitrary rainfall response. No wildfire source was read or changed.
The isolated `JointAgriculture` scaling remains a synthetic interface, not an
empirical welfare model.

## Recommendation and executable sequence

Our recommendation, pending detailed replication review, is to evaluate a
published partial-equilibrium valuation as the first transparent alternative
to an unavailable GTAP shock-response interface. This is a modeling candidate,
not a selected production welfare model or a claim of methodological novelty.

1. Read section K and inspect the named replication components. Recover the
   exact yield-to-supply shift, elasticities, baseline quantities/prices,
   units, welfare integrals and trade assumptions. Establish code/data rights
   before reuse; do not clone the bulk archive under the storage reserve.
2. Independently implement the documented equations with explicit synthetic
   labels. Verify zero shock, market clearing, accounting cancellation of
   price transfers, numerical integration and finite-difference derivatives.
   Do not choose elasticities to produce a desired damage magnitude.
3. Map retained crop production/value inputs to the required economic units.
   Revenue weights alone are not welfare. Reject absent inputs and report
   unrepresented crops, livestock and regional support rather than normalizing
   maize and soybean to all agriculture.
4. Keep the full joint-climate response and precipitation decomposition
   distinct. A historical moisture association is not an admissible projected
   productivity shock. Climate transport, response validation, CO2 and
   adaptation accounting must be resolved before empirical valuation.
5. If the welfare layer emits annual regional money values, replace the
   synthetic agricultural-income scaling, not add to it. Preserve matched
   baseline/pulse draw IDs and discount through GIVE only once. Broader-market
   assumptions require region-specific incidence, not just a global total.

This route could remove the need for a new welfare emulator. It does not
remove the still-missing validated climate-to-crop counterfactual or authorize
a numerical SCC. The detailed supplement/equations are the next work item;
there is no need to block independent historical estimation on that review.
