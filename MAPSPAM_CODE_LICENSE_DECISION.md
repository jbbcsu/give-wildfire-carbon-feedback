# MapSPAM code and license decision record

## Decision

The MapSPAM 2000 four-character `stat_code` country problem is resolved for
country assignment, but welfare weights remain disabled.  The fail-closed rule
is now:

1. accept an exact current UN ISO-alpha3 `stat_code` directly;
2. for an `AAXX` `stat_code`, require its `AA` prefix to equal the first two
   characters of the row's documented `admin2_fips`, map `AA` through the
   official NGA GEC-to-GENC entity crosswalk, and require the resulting
   three-character code to exist in the current UN M49 table;
3. retain `TWN` in a separate non-UN bucket; and
4. reject every other code, every row-level prefix disagreement, every missing
   national value, and every unregistered fallback rather than guessing or
   renormalizing.

This is a country assignment only.  It does not assert that old administrative
boundaries are current, does not replace the MapSPAM surface with modern
boundaries, and does not enable value weights or an SCC calculation.

## Primary-source evidence

The archived MapSPAM readme labels `stat_code` as ISO3 but also identifies
`prod_level` as an administrative-level-2 FIPS code.  The source data contain
196 four-character `stat_code` values across 14 two-letter prefixes, contrary
to the ISO3-only label.  NIST FIPS PUB 10-4 defines a two-letter geopolitical
entity code and four-character first-order-division codes.  NGA states that
GEC was formerly FIPS PUB 10-4 and publishes a GENC/GEC crosswalk:

- MapSPAM 2000 archive and codebook: <https://doi.org/10.7910/DVN/A50I2T>
- NIST FIPS PUB 10-4: <https://www.govinfo.gov/app/details/GOVPUB-C13-1ea099540271ff42b09274b9839d02a4>
- NGA reference documentation: <https://geonames.nga.mil/geonames/GNSHome/reference.html>
- current UN M49 codes: <https://unstats.un.org/unsd/methodology/m49/>

The ten-file Dataverse release contains no MapSPAM-specific country-code lookup
beyond the readme and codebook. Thus, identifying these particular
four-character fields as legacy FIPS/GEC administrative codes is an inference,
not an undocumented claim attributed to MapSPAM. It is supported by the exact
FIPS `AAXX` structure, row-level agreement with the independently documented
`admin2_fips` prefix, the NGA crosswalk, and the perfect direct-code check
reported below. The audit rejects the rule if any of those checks disagrees.

The official NGA page's current `GENC_ED3U25_GEC_XWALK.xlsx` link returned HTTP
404 on 2026-08-26.  The official ED3U11 workbook documented by the NGA GNS user
guide remained available and was pinned by byte length and SHA-512.  It maps
all 14 MapSPAM prefixes unambiguously:

| GEC prefix | Current ISO3 | MapSPAM four-character codes | Maize production (metric tonnes) | Soybean production (metric tonnes) |
|---|---|---:|---:|---:|
| SF | ZAF | 9 | 11,191,531.2 | 198,233.9 |
| NI | NGA | 31 | 7,036,476.0 | 473,185.4 |
| KE | KEN | 7 | 2,679,664.7 | 2,503.3 |
| TZ | TZA | 19 | 2,346,374.4 | 2,139.3 |
| ZI | ZWE | 8 | 1,698,133.1 | 142,007.5 |
| CG | COD | 9 | 1,352,582.0 | 5,246.1 |
| UG | UGA | 39 | 1,107,664.5 | 121,680.7 |
| TO | TGO | 5 | 479,849.3 | 0.0 |
| BY | BDI | 15 | 123,647.7 | 784.5 |
| CT | CAF | 16 | 100,891.3 | 0.0 |
| RW | RWA | 10 | 66,130.0 | 13,051.4 |
| GB | GAB | 9 | 25,952.6 | 2,135.6 |
| MR | MRT | 5 | 8,323.0 | 0.0 |
| LI | LBR | 14 | 0.0 | 2,996.1 |

Every one of the 49,222 four-character rows has the same country prefix in
`stat_code` and `admin2_fips`.  As an independent internal consistency check,
550,377 three-character rows have an NGA-mappable `admin2_fips` prefix, and all
550,377 agree exactly with their published three-character `stat_code`; 1,531
direct `SRB` rows have no GEC prefix in the selected 2019 crosswalk and remain
valid through current UN ISO3 matching.  Of the 196 four-character codes, 104
also appear as exact administrative codes in the 2019 NGA crosswalk.  The other
92 use older administrative codes (13,326 rows, versus 35,896 exact-current
administrative-code rows), but their country prefixes remain defined; no
modern administrative-boundary claim is made.

The complete per-`stat_code`, per-crop quantities are written only to the
ignored local audit
`data/interim/welfare_weights/mapspam_gec_resolution.audit.json`.  No raw or
derived MapSPAM table is committed.

## Remaining value coverage

Country resolution raises production with both an authoritative country map
and a nonmissing published 1999-2001 FAOSTAT constant-dollar value from 94.279% to 98.050%
for maize and from 98.630% to 99.058% for soybean.  The still-unweighted
remainder is:

| Remaining bucket | Maize share | Soybean share |
|---|---:|---:|
| Current ISO3, but no baseline value | 1.281% | 0.770% |
| GEC-mapped country, but no baseline value | 0.658% | 0.172% |
| `TWN`, GENC-valid but absent from current UN M49 | 0.012% | 0.0002% |
| Unresolved four-character country code | 0.000% | 0.000% |

The four-character-code blocker therefore needs no user choice.  The later
nearest-year or other missing-value rule is still a modeling choice and must be
pre-registered before weights are built.

## License interpretation and conservative operating rule

The selected 99,610,984-byte production archive is Harvard Dataverse datafile
3666788.  Dataverse versions 1.0 through 2.0 explicitly say CC BY 4.0.  Current
versions 2.1 and 2.2 contain IFPRI's December-2019 terms, whose license section
says materials default to CC BY 4.0 unless a non-CC license is stated.  No
dataset-specific non-CC statement was found.  In contrast, the current
MapSPAM website terms say materials downloaded from that website are CC BY-NC
3.0 and retain an older SPAM 2005 citation:

- Dataverse dataset metadata and terms: <https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/A50I2T>
- MapSPAM website terms: <https://mapspam.info/terms/>

These are differing official distribution statements, not a basis for silently
choosing the more permissive one for redistribution.  The project therefore
uses only the exact Dataverse object for internal academic analysis, cites the
dataset DOI, keeps raw and gridded derivatives ignored, and leaves
redistribution disabled pending written IFPRI clarification.  This conservative
rule does not prevent running an internal audit or reporting aggregate research
results, but it is not legal advice and it does not authorize publishing the
underlying gridded data.

No user decision is required at this stage.  IFPRI clarification is desirable
before any data or gridded derivative is released; code and provenance can be
published without embedding the data.
