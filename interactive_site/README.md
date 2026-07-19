# Interactive GIVE Wildfire Website

This folder contains a static website for exploring the wildfire-carbon feedback extension.

## Run locally

From this directory:

```bash
python3 -m http.server 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

## What the controls do

The interactive controls are a calibrated emulator, not a live Julia/GIVE rerun.
They start from the paired 100-draw GIVE outputs and scale the wildfire increment
around a selected scenario anchor.

Controls:

- Discount case: selects the GIVE discount-rate case from the paired run.
- Scenario anchor: chooses the calibrated GIVE scenario to scale from.
- Fire response multiplier: scales the fire-carbon response.
- Net persistent share: represents the share of gross fire CO2 that persists as net atmospheric CO2.
- Not-already-embedded share: represents the share assumed not to be already included in baseline CO2 pathways.
- Damage-response amplifier: stress-tests stronger or weaker damage response around the calibrated result.

## Important caveat

The sliders are for teaching, diagnostics and intuition. A publication-grade estimate
requires rerunning the Julia model with the selected parameter distribution.
