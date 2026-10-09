# AI-assisted GIVE damage expansion

This standalone synthesis project documents a rapid but fail-closed expansion
of damage-sector coverage in the Greenhouse Gas Impact Value Estimator (GIVE).
It links to, but does not copy or modify, the isolated precipitation,
labor-productivity, fisheries, biodiversity, and wildfire projects.

The paper's contribution is both substantive and methodological: it reports
which omitted damage pathways can be reproduced from published work, which can
be newly estimated with public data, and which remain external benchmarks
because overlap or identification prevents addition to the SCC.

## Evidence classes

1. **Integrated and replicated**: runnable baseline/pulse damage paths, local
   reproduction receipt, and overlap gate passed.
2. **Original bounded estimate**: locally estimated result with explicit claim
   limits, sensitivity analysis, and no promotion beyond its estimand.
3. **Published external benchmark**: peer-reviewed SCC or damage estimate that
   is informative but not added to GIVE until code, inputs, and overlap pass.
4. **Open research gap**: no defensible transferable estimate identified.

Headline totals may use only class 1. Class 2 results are reported separately
until the model-integration gate passes; classes 3 and 4 are never silently
treated as zero or added as scalars.

The authorized target portfolio is baseline GIVE plus the Moore labor and
updated-agriculture replacement, the separately developed wildfire-carbon
feedback, fisheries, and an incremental drought/precipitation agriculture
extension. Municipal drought/water-system damages are a later module. The
remaining RFF-identified gaps are screened in priority order, with surface
ozone and biodiversity among the leading candidates. This is an integration
target, not a claim that every listed partial SCC is presently additive.

See [the sector registry](SECTOR_REGISTRY.md), [main manuscript](manuscript/MAIN_MANUSCRIPT.md),
and [Methods SI](manuscript/METHODS_SUPPORTING_INFORMATION.md).
