# FAO FishStat observed-catch source gate

Status: official workspace and an independent symbol-preserving headless table
export validated; FishStat GUI-menu reconciliation, marine filtering,
crosswalks, model validation, welfare, damages, and SCC use remain closed.

The official FAO FishStat Global Production workspace version 2026.1.0 was
retrieved from FAO's public FishStat directory. The 22,994,754-byte archive
matches its frozen local SHA-512 and passes full ZIP integrity over 639 members.
Its embedded workspace identity names FAO as provider and its capture notes
cite *Global capture production 1950--2024* under CC-BY-4.0.

This source records nominal landings converted to live weight. It includes
commercial, industrial, recreational, and subsistence landings from inland,
brackish, marine, and high-seas areas, but excludes discards, live escapements,
and pre-landing losses. Country attribution generally follows vessel flag, not
the surrounding EEZ. The embedded metadata also distinguish official,
estimated, provisional, low-reliability, missing, not-significant, and
suppressed observations. Missing or suppressed entries therefore cannot be
read as zero.

The validated container is a source gate, not an empirical calibration. Next,
an independently checked export must preserve country/area, species, FAO major
fishing area, year, unit, value, and observation-status flags; separate marine
capture from inland and non-tonnage records; and reconcile country keys before
any comparison with FishMIP. The workspace supplies neither effort/management
identification nor grid/EEZ allocation, trade incidence, welfare, a matched
carbon pulse, damages, or SCC.

The export route is now version-pinned. FAO's official manifest selects
FishStatJ 4.04.11 for macOS; the 146,552,898-byte bundle matches the frozen
local SHA-512, passes ZIP integrity, and its bundled Temurin OpenJDK 11.0.15
runtime executes locally. Read-only class inspection identifies the Derby
capture table `TSD_CAPTURE_QUANTITY`, keys `COUNTRY`, `SPECIES`, `AREA`, and
`MEASURE`, and paired value/symbol columns for every 1950--2024 year. The FAO
manual's supported route is **File > Export selection (CSV file)**, with symbol
export controlled by preferences. A guarded record export and independent
row/value/flag reconciliation are still required; runtime availability alone
does not validate observations.

An independent headless integrity export now reads only a disposable Derby
copy and resolves every one of the 30,918 wide capture records to FAO country,
species, area, environment, and measure references. The deterministic
29,413,192-byte CSV preserves all 2,318,850 annual 1950--2024 value/status
pairs and has SHA-256 `ca58247c4f6044948b01048e4a808d21a4975c9f4171e3d0d1fbc321e46ebb52`.
An independently implemented Python pass reproduces the record, annual-cell,
environment, measure, value, and status counts: 28,305 records are marine,
2,613 inland, 30,164 use tonnes live weight, and 754 use number. Stored zero
values include 1,266,653 `O` missing cells, 281 `Q` suppressed cells, and
32,808 `N` not-significant cells, so zero is not treated as observed absence.
Historical/reference entities leave 158 country ISO3 values and 493 species
common names blank; those are preserved rather than invented.

This headless export is an integrity and feasibility result, not the manual's
supported GUI export. The GUI-menu output must still be generated with symbols
enabled and reconciled against this independent extract. Marine-tonnage
filtering, vessel-flag/EEZ allocation, observed FishMIP validation, welfare,
damage, and SCC gates remain closed.

A separate post-export descriptive audit now reports the shape of the eventual
FishMIP overlap without authorizing the filter. For marine `Q_tlw` records,
reported positive totals rise from 17.316 million tonnes in 1950 to 80.463
million tonnes in 2014 and peak at 87.687 million tonnes in 1996. Active ISO3
support rises from 159 to 195, active species from 546 to 1,772, and active FAO
areas from 15 to 19. Missing-status cells fall from 22,953 to 10,434. No
suppressed `Q` cell occurs in 1950--2014 within this specific slice, while
not-significant `N` cells remain distinct from zero absence. Blank-ISO3
positive tonnage never exceeds 0.474 percent of the annual total (1980), but
the underlying vessel-flag/EEZ and historical-entity crosswalk problem remains.
These are nominal-landing support diagnostics, not effort or biomass trends,
model calibration, allocation, welfare, damages, or an SCC input.

A deterministic concentration audit further shows why a single global scaling
factor is not defensible. From 1950 to 2014, the top-five vessel-flag-country
share falls from 51.34% to 41.07%, while the top-five reported-species share
falls from 37.71% to 24.23%; the corresponding Herfindahl indices fall from
0.0750 to 0.0571 and from 0.0407 to 0.0212. FAO-area concentration remains
high: the top five areas account for 78.71% in 1950 and 70.84% in 2014. These
descriptive changes reinforce the need for explicit country/species/area and
effort structure. They do not reconcile the GUI export, assign catch to EEZs,
calibrate FishMIP, identify welfare, or authorize damage or SCC use.
