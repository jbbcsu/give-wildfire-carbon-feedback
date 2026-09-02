# FAO FishStat observed-catch source gate

Status: official workspace acquired and container/metadata validated; record
export, marine filtering, crosswalks, model validation, welfare, damages, and
SCC use remain closed.

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
