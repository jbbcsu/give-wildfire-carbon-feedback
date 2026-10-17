# Target GIVE labor-overlap audit

Status date: 17 October 2026.

The original GIVE paper checkout at the workspace path
`paper-2022-scc-give-zenodo` was searched for `labor` and `include_labor` in
`src/`, `Project.toml`, and `Manifest.toml`. There were no matches. The damage
aggregator calls found in `src/compute_scc.jl` select the existing mortality,
agriculture, sea-level-rise, energy, DICE, and Howard-Sterner pathways; they do
not select a labor-productivity component.

This establishes the narrow accounting fact needed for the fast-track labor
transfer: the audited original GIVE checkout does not already contain an active
labor-productivity sector. It does not prove that every future or downstream
GIVE configuration lacks labor. Any combined run must repeat this audit against
the exact target commit before adding the labor partial SCC.

Audit command:

```sh
rg -n -i "labor|include_labor" \
  paper-2022-scc-give-zenodo/src \
  paper-2022-scc-give-zenodo/Project.toml \
  paper-2022-scc-give-zenodo/Manifest.toml
```

Result: zero matches.
