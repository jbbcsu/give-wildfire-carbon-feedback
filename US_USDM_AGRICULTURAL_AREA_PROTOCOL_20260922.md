# U.S. USDM agricultural-area weighting protocol

**Frozen:** 2026-09-22, before full weekly-shapefile acquisition, construction
of 2008 agricultural-area weights, or inspection of agricultural-area response
estimates.

## Goal and claim boundary

Replace the official REST service's whole-county drought shares with a spatial
reconstruction closer to Kuwayama et al. (2019): weekly USDM polygons
intersected with agricultural land identified in the 2008 Cropland Data Layer
(CDL), accumulated from October of the preceding year through September of the
harvest year. This is a historical fidelity sensitivity. It does not project
future USDM categories, identify a causal yield effect, define a global damage
function, or authorize an SCC input.

## Frozen sources

- [Official 2008 national 30 m CDL archive from USDA NASS](https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php), retained in ignored
  raw storage with URL, size, upstream headers, checksum, license, and raster
  profile.
- [Official weekly USDM shapefile archives](https://droughtmonitor.unl.edu/DmData/GISData.aspx) for every Tuesday from 26 September
  2000 through 24 September 2013 (679 maps), retained in ignored raw storage
  with deterministic URL, byte count, SHA-512, ZIP integrity, CRS, and severity
  fields. [Official USDM metadata](https://droughtmonitor.unl.edu/DmData/Metadata.aspx)
  documents the vector cleaning, categorical polygons, cumulative convention
  for tabular statistics, and approximate four-mile pre-2004 horizontal error.
- TIGER/Line county polygons only for assigning agricultural support to county
  identifiers; geometry vintage differences must be reported.

## Agricultural mask uncertainty

The article says that it aggregated "agricultural land cover categories" but
does not enumerate the CDL codes in the accessible main text. No exact code set
will be guessed or selected to improve coefficient agreement. After inspecting
the actual 2008 raster attribute table, two outcome-blind masks will be frozen
and reported together: a cultivated-agriculture mask (crop-specific categories
plus fallow/idle cropland) and a broad-agriculture mask that additionally
includes code 176, `Grassland/Pasture`. Generic metadata codes 171 and 181 are
absent from the actual 2008 raster and are therefore not used. Neither mask is
called an exact author replication unless the original code list becomes
available.

## Bounded spatial computation

The production route must remain below 640 MiB RSS and avoid expanding the
multi-gigabyte national raster in memory. Agricultural support is reduced
county by county into a sparse equal-area grid. Weekly USDM vector polygons,
whose `DM` field stores mutually exclusive D0--D4 classes, are applied
sequentially; only one map is resident at a time. This differs from the USDM
tabular-statistics convention, which reports cumulative D0-or-worse through
D4-or-worse percentages. Raw archives remain ignored.

The first national pass uses approximately 4 km equal-area cells because early
USDM polygon metadata report roughly four-mile horizontal uncertainty. This is
a computational approximation, not an exact 30 m overlay. A predeclared
multi-resolution audit will compare 4 km, 1 km, and native-30 m results on
outcome-blind sentinel counties spanning agricultural area and drought-boundary
complexity. Advancement requires small, reported exposure error; otherwise the
coarse national result is rejected.

## Validation

- Category areas must be mutually exclusive, bounded in [0,1], and sum with
  no-drought area to one for each county-week within numerical tolerance.
- October--September integration must be gap-free and reconcile to 365/7 or
  366/7 weeks.
- Reconstructed Table 2 means and support counts are compared with the
  published values, but no mask or resolution is selected by proximity alone.
- Whole-county REST shares are an independent arithmetic comparator, not a
  substitute for agricultural weighting.
- Response models reuse the corrected outcome, classifier, fixed effects,
  trends, weather hierarchy, and inference without term or sample tuning.
- Calendar-year and whole-county results remain visible as labeled
  sensitivities. Nulls, sign changes, and worse fidelity are reported.
