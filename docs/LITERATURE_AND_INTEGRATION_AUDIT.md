# Literature and GIVE integration audit

## Decision

Do not add an education SCC at this stage. The physical/educational response is credible enough to warrant a future module, but the monetization and marginal-climate steps do not pass. The output of this audit is a source-pinned, fail-closed integration contract rather than a speculative number.

## Existing coverage

Rennert et al. (2022; DOI `10.1038/s41586-022-05224-9`) describe GIVE's sectoral damage basis without a distinct education, learning, or human-capital-formation endpoint. EPA FrEDI's August 2024 technical documentation likewise lists its current impact sectors without education. Education is therefore omitted as a named bottom-up endpoint. This does **not** imply that adding it to every expanded total is valid: aggregate macro damage functions may already embody human-capital channels, and GIVE labor and energy extensions can overlap parts of the mechanism or adaptation response.

## Literature-first assessment

### Park et al. (2020), United States

`Heat and Learning` (AEJ: Economic Policy; DOI `10.1257/pol.20180612`) uses repeated PSAT takes and student fixed effects to identify learning effects from prior school-year heat. The paper reports nonlinear school-day exposure specifications and evidence consistent with school air conditioning mitigating losses. The AEA lists a replication package, although its page reported migration to ICPSR during this audit.

This is the strongest U.S. response candidate because the exposure is aligned to school days and cumulative learning rather than only test-day performance. It still does not produce a GIVE-ready damage function. Its earnings calculation is explicitly a back-of-the-envelope transfer from teacher-induced test-score gains; the paper notes the assumption that climate-controlled learning produces later-life effects equivalent to teacher-induced gains. That assumption cannot serve as the valuation bridge here. Reported school-AC costs are illustrative local engineering expenditures, not global welfare damages.

### Park, Behrer, and Goodman (2021), international evidence

The Nature Human Behaviour paper (DOI `10.1038/s41562-020-00959-9`) combines achievement data for 58 countries and 12,000 U.S. school districts with weather and academic calendars. Its breadth makes it relevant to transferability. However, the publisher states that custom code is available only from the corresponding author on request, while source datasets are distributed separately. It supplies no separable monetary welfare endpoint.

### Graff Zivin, Hsiang, and Neidell (2018)

The JAERE study (DOI `10.1086/694177`) exploits longitudinal NLSY79 data and child fixed effects. It finds short-run math-performance reductions above 26 C, but its long-run estimate is imprecise and significantly smaller than the short-run relationship. This is direct evidence against treating a short-run cognitive effect as a known persistent lifetime loss.

### Garg, Jagnani, and Taraz (2020), India

The JAERE study (DOI `10.1086/710066`) documents temperature-related reductions in math and reading scores and evidence that agricultural income is a mechanism and social protection moderates the relationship. It strengthens external-validity concerns rather than resolving them: a monetized education module could double count agricultural income losses unless the direct classroom channel is isolated.

## Why the module fails closed

1. **Outcome is not welfare.** Test-score standard deviations are important educational outcomes but are not dollar damages.
2. **Persistence is unresolved.** Short-run or cumulative school-year learning effects do not establish an invariant lifetime earnings effect; the longitudinal evidence warns against that extrapolation.
3. **Overlap is material.** Earnings valuation overlaps labor-productivity damages; GDP or growth valuation overlaps the macro comparator; the India mechanism overlaps agriculture. Cooling capital and electricity can overlap GIVE energy damages.
4. **Climate matching is incomplete.** A marginal SCC requires baseline and one-ton-pulse changes in the same daily school-calendar temperature bins, not a scenario-average warming multiplication.
5. **Global transfer is unvalidated.** School calendars, curricula, enrollment, cooling access, income, and acclimatization vary substantially.

## Executable future interface

The physical module should eventually consume region-year-school-day temperature-bin counts for matched baseline and pulse climate runs, plus enrollment, local calendar, and adaptation state. It should output learning changes by region, cohort, year, and adaptation scenario with parameter draws. Monetization must be a separate optional layer.

Required adaptation cases are:

- **Fixed:** hold observed school cooling access and calendars fixed.
- **Trend:** extrapolate empirically supported cooling adoption, with capital and electricity accounting kept separate.
- **Upper:** impose a transparent high-protection bound, not costless complete adaptation.

The preferred valuation target is published willingness to pay for avoiding learning disruption or directly measured incremental remediation/resource costs. Lifetime-income conversion remains prohibited unless a future study establishes the causal bridge for heat-induced learning changes and the resulting stream is made mutually exclusive with labor and macro damages.

## Claim boundary

This audit supports the statement that heat-related learning is a plausible omitted physical endpoint. It does not support an education SCC, an additive GIVE damage, or a global monetary damage estimate.
