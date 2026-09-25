# Source-matched rice weather method

The published global rice response can now be evaluated from a fully specified
primitive weather basis. The implementation uses 14--30 C growing degree days,
degree days above 30 C, three rainfall phases covering the first two months,
next three months, and remaining crop-season months, and the sum of monthly
mean daily minimum temperature. Rainfall squared terms are computed monthly
before phase aggregation, preserving changes in within-phase distribution.

The definitions were checked against the pinned source configuration and
climate-collapse code and against the published Methods Supporting
Information. Tests cover phase arithmetic, rainfall polynomial ordering,
temperature thresholds, monthly Tmin aggregation, same-year and cross-year
seasons, moderator caps, missing days, and invalid inputs.

This closes a reproducible implementation gate for extending the maize
benchmark to rice. It does **not** produce a rice yield projection, damage
estimate, or SCC. The next gate is to construct and independently validate
historical and future rice weather bases on the two rice-calendar systems and
rainfed/irrigated supports. The future calculation must use matched baseline
and marginal-pulse weather rather than scaling a scenario endpoint.

The six-month implementation minimum is a conservative engineering rule that
keeps all three published rainfall phases nonempty; it is not presented as a
new empirical finding. Calendar support outside that rule must be reconciled
to the authors' estimation construction before use.
