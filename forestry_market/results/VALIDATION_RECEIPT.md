# Validation receipt

- Date: 2026-10-17.
- Local runtime: Julia 1.8.5 with MimiFUND's pinned v3.13.0 manifest.
- Local result: central fixed-2% benchmark `-0.0769529710606` 2020 USD/tCO2;
  source hashes, pulse linearity, channel add-up, and four Python tests passed.
- Server: `darecompute-02`, Linux x86_64, Julia 1.10.3, run with `nice -n 10`
  and `ulimit -v 8388608` (8 GiB). The upstream Julia-1.8 manifest was retained
  as `Manifest.julia1.8.toml` in the temporary validation directory and a fresh
  Julia-1.10 manifest was resolved there only. No research source was changed.
- Server result: central benchmark `-0.0769529710606` 2020 USD/tCO2; all
  displayed sector, channel, discount, horizon, and sensitivity values agree
  with the local run. Four tests passed. Differences are below the retained
  decimal precision except the pulse-linearity diagnostic (`~1e-13` absolute).
- Observed server resident memory during the no-precompile run was below 1 GiB.
  The 8 GiB virtual-memory ceiling was required because Julia compilation failed
  under an initial 2 GiB virtual-memory ceiling.
- Release state: external legacy benchmark only. Additive GIVE integration is
  disabled by the target contract and the claim gates in
  `docs/AUDIT_AND_DECISION.md`.
