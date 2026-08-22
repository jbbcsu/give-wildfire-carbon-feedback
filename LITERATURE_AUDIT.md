# Evidence and implementation audit

## Primary precedent

Wingenroth, Prest, Rennels, Rennert, Errickson, and Anthoff, “Accounting for
Biodiversity Loss Raises the Social Cost of CO2,” RFF Working Paper 24-23:
https://media.rff.org/documents/WP_24-23.pdf

The paper implements a temperature-driven remaining-biodiversity stock and a
country-level nonuse willingness-to-pay function in GIVE. It uses a fixed
non-climate extinction term, an empirically updated temperature coefficient,
unit income elasticity in the preferred valuation, and 16 FUND-region
preference parameters applied to countries.

## Reproduction boundary

The public paper supports the functional architecture, but the search conducted
on 2026-08-21 did not locate a public replication package containing the exact
species-loss draws and regional valuation table. The printed coefficient also
requires verification of its scale before code receives a numeric default.
Accordingly, the code kernel accepts all empirical parameters explicitly and
contains no calibrated SCC values.

## Double-counting boundary

This module values only nonuse/existence value. Market impacts mediated through
agriculture, commercial fisheries, aquaculture, reef tourism, coastal
protection, health, or carbon storage must remain in their own modules. Any
future ecosystem-service expansion requires a service-by-service overlap audit.
