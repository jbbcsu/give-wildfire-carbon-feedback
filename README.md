# GIVE Wildfire-Carbon Feedback Extension

This repository contains a research extension to the Rennert et al. (2022) GIVE
social cost of carbon dioxide replication package. The extension audits how GIVE
handles aggregate CO2 pathways, adds exploratory wildfire-carbon feedback pathways
upstream of the carbon cycle, and produces the manuscript, Supplementary
Information, figures, slide deck, teaching notes and interactive site developed for
the project.

## Scope

The central scientific claim is limited: GIVE uses exogenous emissions,
socioeconomic and population pathways and does not internally generate a
warming-to-wildfire-to-CO2 feedback. Because the RFF-SP CO2 pathway is aggregated,
the extension does not assume that all wildfire carbon is absent from the baseline.
The preferred scenarios therefore add only residual net-persistent wildfire CO2
that is not already embedded in the baseline pathway.

Gross fire cases are included as stress tests and mechanism checks, not as central
double-counting-safe estimates.

## Repository Contents

- `WildfireGIVE.jl`: Julia module that adds wildfire CO2 pathways to GIVE.
- `run_temperature_feedback_scc.jl`: deterministic endogenous-feedback checks.
- `run_temperature_feedback_mcs.jl`: paired Monte Carlo SCC runs.
- `run_sectoral_diagnostics.jl`: sectoral marginal-damage diagnostics.
- `run_regional_damage_map_diagnostics.jl`: regional damage-map diagnostics.
- `process_usda_val_martin.jl`: NetCDF processing for USDA/Val Martin/Pierce/Heald fire-projection data.
- `make_png_pdf_figures.R`: figure builder for manuscript and Supplement outputs.
- `source_data/`: cleaned input summaries used by the extension.
- `manuscript/`: manuscript draft, SI, rendered PDFs/HTML and figure files.
- `slides/`: PowerPoint deck and QA artifacts.
- `interactive_site/`: local interactive website for explaining the analysis.
- `teaching_module/`: notes for walking through the research process.
- `replication/`: compact replication notes and example outputs.

The original Rennert et al. replication archive and MimiGIVE packages are not
duplicated here. A reproducer should download the original archive separately from
Zenodo and place this extension inside the extracted project directory as
`wildfire_extension/`.

## Main Manuscript Files

- `manuscript/wildfire_carbon_feedback_ncc_draft.md`
- `manuscript/wildfire_carbon_feedback_ncc_draft.pdf`
- `manuscript/methods_appendix.md`
- `manuscript/methods_appendix.pdf`

## Data Notes

The repository includes cleaned summary data needed for the current figures and
diagnostics. It intentionally excludes extracted full-text literature files and
local PDF copies of copyrighted articles.

The raw USDA fire-projection archive used in the SI can be downloaded from the
USDA Forest Service Research Data Archive entry `RDS-2018-0021`
(`https://doi.org/10.2737/RDS-2018-0021`) and processed with
`process_usda_val_martin.jl`.

## Quick Start

From the root of the extracted Rennert et al. replication archive:

```bash
/Users/jbb/Dropbox/GIVE/tools/julia-1.6.4/bin/julia \
  --project=/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo \
  wildfire_extension/run_temperature_feedback_scc.jl \
  wildfire_extension/output/wildfire_temperature_feedback
```

For the current 100-draw paired Monte Carlo:

```bash
wildfire_extension/run_temperature_feedback_mcs.sh \
  100 \
  wildfire_extension/output/wildfire_temperature_feedback_mcs_100_paired \
  20260503 \
  all
```

Regenerate figures:

```bash
Rscript wildfire_extension/make_png_pdf_figures.R \
  /Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo
```

Render the manuscript and SI:

```bash
pandoc wildfire_extension/manuscript/wildfire_carbon_feedback_ncc_draft.md \
  -o wildfire_extension/manuscript/wildfire_carbon_feedback_ncc_draft.pdf

pandoc wildfire_extension/manuscript/methods_appendix.md \
  -o wildfire_extension/manuscript/methods_appendix.pdf
```

## Current Status

Current manuscript results are based on a completed 100-draw paired validation run.
The 10,000-draw production run has not been completed and should be run before any
submission-ready numerical claims are finalized.

## Authorship And AI Disclosure

The project uses an AI coding assistant as a research-programming aid. The human
author specifies the research question, makes modeling decisions, reviews outputs
and takes responsibility for scientific interpretation. The SI includes an
AI-assisted research programming disclosure.
