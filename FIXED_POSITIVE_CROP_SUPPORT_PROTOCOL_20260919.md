# Fixed all-case positive crop-support audit protocol

Status: frozen before execution. This is a coverage audit, not a repaired crop
model, damage estimate or authorization to discard invalid responses.

For every cell/regime on the existing common EPIC-TAMU/CARAIB support, read all
four yield corners from every model/climate/scenario/calendar ledger. Define
three masks before looking at any welfare result:

1. CARAIB-positive: all four corners are finite and strictly positive in all
   eight CARAIB climate/scenario/calendar cases;
2. EPIC-positive: the analogous condition across all eight EPIC cases; and
3. both-model-positive: the intersection of the first two masks.

The denominator remains the unchanged common-support external production and
common-support value proxy. Report cells, production tonnes, hectares where
available, allocated covered value in USD2005, percentages of fixed denominators
and top excluded countries for each model mask, irrigation regime and their
union/intersection. Do not renormalize retained support to 100 percent and do
not recompute welfare in this audit.

Cell value is allocated within each country/regime in proportion to the fixed
external production weights, exactly matching the existing value-proxy
construction. Countries with missing baseline value remain in production
coverage but not dollar coverage. Nonfinite and nonpositive corners are both
exclusion reasons and are counted separately.

An independent validator will reread every source ledger and reconstruct all
masks and weighted summaries. This audit can motivate a separately registered
partial-support sensitivity, but it cannot retroactively validate negative
predictions or make that restricted population global.

One worker remains subject to sampled 512 MiB RSS, 64 MiB output and 130 GiB
free-disk limits; outputs remain ignored.
