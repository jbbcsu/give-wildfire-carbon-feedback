# GDHY annual spatial-support audit

Status: verified source-structure audit, 2026-08-26. This note does not
authorize a causal response, damage estimate, or SCC input.

## Source identity and integrity

The local source is the publisher-hosted PANGAEA archive for the aligned
GDHY v1.2+v1.3 dataset:

- landing page: <https://doi.org/10.1594/PANGAEA.909132>
- archive: <https://store.pangaea.de/Publications/IizumiT_2019/gdhy_v1.2_v1.3_20190128.zip>
- local and current remote SHA-256:
  `731d03171ff9a5afb4837f51d6941fb58085ee69c62e767810e9395756648c76`
- byte size: 15,989,683
- license reported by PANGAEA: CC BY 4.0

The ZIP integrity test passed. All 360 extracted NetCDF files match their ZIP
members byte for byte by SHA-256. The maize-major and soybean files open on a
360 x 720 grid, contain one `float32` variable named `var`, and use
`-999000000.0` as the fill value. The current official remote archive streamed
on 2026-08-26 has the same SHA-256 as the local archive. The support changes
below are therefore present in the official archive and are not evidence of a
damaged local download or extraction.

The audit is reproducible with:

```bash
./.venv/bin/python scripts/audit_gdhy_annual_support.py \
  --archive data/raw/gdhy_v1.2_v1.3_20190128.zip \
  --extracted-root data/raw/gdhy_v1.2_v1.3 \
  --series maize_major --series soybean \
  --year-start 1981 --year-end 2016 \
  --expected-archive-sha256 731d03171ff9a5afb4837f51d6941fb58085ee69c62e767810e9395756648c76 \
  --expected-archive-size-bytes 15989683 --expected-member-count 360 \
  --out outputs/gdhy_annual_support_audit.json
```

Selected extracted-member SHA-256 values are:

| series/year | SHA-256 |
|---|---|
| maize_major/2010 | `5a04c0eae5a99e7a13e88669e33be08eaa626adb790452e7a76a87198955855c` |
| maize_major/2011 | `0e8ddfad772b42e9c2dfde6b8870129943f921ed1e010a4d4485c90622a3ac04` |
| maize_major/2014 | `f468259f0ecdecf5a5f8c8b90b07a802304e477cc19348821185332327af4cdb` |
| maize_major/2015 | `726be420856f22e9dca11422b6913853e0edf0b9b0c63f509d0ca97a0cde326f` |
| maize_major/2016 | `d2fbef388e0a1e4e8175eabf50333b0d987a50c89ad199327f14b879ae1df4a7` |
| soybean/2010 | `0b0ddc50991a2e1a156a2189a84ea37e40f27cfc47817193d19dfaeda9a9d0c8` |
| soybean/2011 | `3dba9fe6526e08a3c1990b9313969ec6a166e9e442e750553ad83c4b54a1d70f` |
| soybean/2014 | `f7c72925917a82d5e1d0d2dfcbf9b7d679f35129211d77e2ef9ae9721f9af0c0` |
| soybean/2015 | `77a2538c445b462e5bdc36e0916f4dca0ce7968df8d27e458900bdcdf2e488ed` |
| soybean/2016 | `17cbb6645565ec0177821e4b3b8cd55c3ac8ca7dfb15edf585b449884859f9a4` |

## What the primary sources establish

Iizumi and Sakai's data descriptor states that GDHY grid-cell yields are model
estimates constructed from FAOSTAT country yields, satellite-derived
vegetation/productivity inputs, crop areas, and crop calendars; they are not
direct grid-cell yield observations. It documents different satellite and
reanalysis inputs across versions, an explicit alignment procedure, and
clipping of negative aligned values to zero. The aligned record uses version
1.2 information through 2010 and aligned version 1.3 information from 2011.
The authors caution that spatially incomplete GDHY coverage can understate
aggregated production and recommend validation against other, preferably
observed, yield datasets. See the primary data descriptor:
<https://doi.org/10.1038/s41597-020-0433-7>.

Both the paper and PANGAEA landing page attribute many missing values in the
first and last years to growing seasons that span two calendar years. They
identify those endpoint years as 1981 and 2016. Neither source identified in
this audit provides an explanation for a support drop in the file named
`yield_2015.nc4`.

## Exact local source structure

“Finite” includes positive yields and source zeros; “positive” excludes the
aligned values that the source clipped to zero.

| series | year | finite cells | positive cells | source-zero cells |
|---|---:|---:|---:|---:|
| maize major | 2010 | 15,072 | 15,053 | 19 |
| maize major | 2011 | 12,716 | 12,527 | 189 |
| maize major | 2012 | 12,716 | 12,493 | 223 |
| maize major | 2013 | 12,716 | 12,636 | 80 |
| maize major | 2014 | 12,716 | 12,660 | 56 |
| maize major | 2015 | 10,925 | 10,859 | 66 |
| maize major | 2016 | 12,716 | 12,654 | 62 |
| soybean | 2010 | 6,120 | 6,120 | 0 |
| soybean | 2011 | 5,557 | 5,555 | 2 |
| soybean | 2012 | 5,557 | 5,554 | 3 |
| soybean | 2013 | 5,557 | 5,557 | 0 |
| soybean | 2014 | 5,557 | 5,557 | 0 |
| soybean | 2015 | 4,961 | 4,958 | 3 |
| soybean | 2016 | 5,557 | 5,555 | 2 |

At the documented 2010-to-2011 version boundary, the 2011 finite-support mask
is a strict subset of the 2010 mask: 2,356 maize-major cells (15.63%) and 563
soybean cells (9.20%) disappear, with no newly finite cells. The finite mask is
then exactly identical in 2011, 2012, 2013, 2014, and 2016 for each series.

The 2015 finite mask is a strict subset of that common 2011--2014/2016 mask.
It excludes 1,791 maize-major cells (14.08%) and 596 soybean cells (10.73%),
with no gains; every one of those finite cells reappears in 2016. Of the
maize-major cells absent only in 2015, 1,739 (97.10%) are south of the equator;
all 596 soybean cells are south of the equator. This geography resembles the
cross-calendar-season endpoint mechanism discussed by the data providers, but
the source documentation names 2016 rather than 2015. The cause and year-label
discrepancy are therefore unresolved; it must not be described as a confirmed
calendar mechanism or silently repaired.

## Maize 2012--2016 pair composition after MIRCA support

The unbalanced area-weighted maize basis contains 165,955 potential cell-year
rows (33,191 cells x five years), 60,818 positive yield levels, and 46,434
consecutive positive-endpoint pairs. Requiring a positive GDHY yield in all
five years retains 10,590 cells, 52,950 levels (87.06% of the positive levels),
and 42,360 pairs (91.23% of the unbalanced pairs).

| transition | unbalanced positive pairs | five-year-complete pairs | removed |
|---|---:|---:|---:|
| 2012--2013 | 12,368 | 10,590 | 1,778 |
| 2013--2014 | 12,516 | 10,590 | 1,926 |
| 2014--2015 | 10,783 | 10,590 | 193 |
| 2015--2016 | 10,767 | 10,590 | 177 |

Of 33,191 MIRCA-supported cells, 20,607 have no positive GDHY yield in any of
the five years; 10,590 have positive yields in all five years; and 1,762 have
the pattern 2012=1, 2013=1, 2014=1, 2015=0, 2016=1. Thus, the complete-support
restriction removes mainly valid 2012--2014 pairs from cells lacking a 2015
outcome. It is a sample-composition sensitivity, not a repair of the 2015 gap.

The current filter is deliberately a **complete-positive-yield** filter. It
therefore combines two selection events: source fill-value missingness and
source values clipped to zero. A future missing-support-only sensitivity
should carry `gdhy_yield_raw_t_ha` or an explicit `gdhy_source_finite` flag
through irrigation allocation, define common geographic support using that
flag, and still handle zero yields transparently in the log-response model.

## Recommended treatment

1. Keep the unbalanced, positive, consecutive-endpoint panel as the primary
   diagnostic/estimation sample; never impute the unexplained source gaps.
2. Use the five-year complete-positive panel only as a clearly labeled
   sample-composition sensitivity. It conditions partly on the modeled outcome
   and cannot be described as balanced-panel correction.
3. In the full 1982--2016 work, report sensitivities that (a) exclude the
   2010--2011 version-boundary pair, (b) exclude pairs with a 2015 endpoint,
   (c) use the conservative 1982--2014 window, and (d) use common finite source
   support separately from complete positive support once the finite flag is
   retained.
4. Include crop-by-pair-year controls in causal specifications where they are
   compatible with the identifying variation, and show that response estimates
   are not driven by pair-specific support composition.
5. Ask the GDHY corresponding author or PANGAEA to resolve why the official
   archive exhibits the documented endpoint-like support drop in 2015 rather
   than 2016 before attributing a cause or choosing to relabel any file. Until
   then, retain the official filenames and disclose the discrepancy.

## Exact manuscript-ready disclosure

> We use the aligned GDHY v1.2+v1.3 modeled yield dataset (Iizumi and Sakai,
> 2020; PANGAEA 909132). An integrity check of the current official archive
> (SHA-256 `731d03171ff9a5afb4837f51d6941fb58085ee69c62e767810e9395756648c76`)
> showed changes in finite spatial support at the 2010--2011 version boundary
> and in the source file `yield_2015.nc4`. Relative to 2014, finite 2015
> support falls by 1,791 maize-major grid cells (14.08%) and 596 soybean grid
> cells (10.73%); all of these cells reappear in 2016. The publisher documents
> endpoint missingness from growing seasons spanning calendar years but names
> 2016, not 2015, as the affected end year, so we treat the observed 2015
> discontinuity as unexplained source structure and do not impute or relabel
> it. Primary estimates use all available positive consecutive yield endpoints
> in an unbalanced panel. Complete-positive-support, version-boundary, and
> year-window restrictions are reported only as sensitivity analyses; the
> complete-positive restriction conditions on modeled outcomes, including
> values clipped to zero during GDHY alignment, and is not a data repair.
