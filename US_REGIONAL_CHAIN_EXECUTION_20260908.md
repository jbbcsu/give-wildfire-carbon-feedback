# Persistent bounded climate-input chain

The local chain now advances acquisition directly to regional county feature
construction and its climate-source comparison, without waiting for another
agent turn between those stages. It is **not** a running crop-damage or SCC
estimator. The pipeline stops for review after this climate-input chain ends
or a step fails; the larger research project remains unfinished.

Launch only after confirming no other analysis driver/child is active:

```sh
.venv/bin/python scripts/run_us_paired_regional_chain.py --max-hours 6
```

It resumes the registered54cutouts, at most2unfinished server requests and one
bounded local child. Each data/test/build job retains the existing1024MiB
sampled-RSS,64MiBowned-output and130GiBfree-space limits. Parent controllers
are small standard-library scheduling processes, not unmonitored data-array
workers. The duration bounds the acquisition-loop run; an active bounded
step is allowed to finish. No process detaches, no Git operation occurs, and
no raw/restricted data are published. It can only keep running while the host
and process remain active; closing/suspending/restarting the machine may pause
or end it. It is not proof that the assistant model itself is running nonstop.

Stage and process ID:
`data/interim/us_paired_regional_chain_20260908/state.json`.
Check the actual process and latest receipts, not the saved PID alone after a
restart. File locks prevent duplicate chain and acquisition drivers. Uncertain
POSTs and incomplete/failed outputs are preserved and stop automatic progress;
they are not deleted or resubmitted. A pending server response is not a
validated acquisition. Between unchanged pending responses the driver backs
off from30to60to120seconds; quiet pending states remain in local job logs but
are not repeatedly printed as continuation notices.

At the latest completed queue slice before this note,13/54cutouts were
validated,225,210,293regional bytes retained. Some public server jobs spent
several minutes queued. That is an observed remote processing wait, not a
local memory failure; no assumption is made about the server's internal cause.
The driver continues the same job IDs. All prior successful local steps stay
complete and must not be repeated as unfinished.

The regional builder and protocol are separate from the completed narrow
pilot. Three new tests cover candidate-cell pruning, a band-boundary county
and overlap parity. Two mocked scheduler integration tests verify immediate
test/build/test/compare order and that a failed build prevents the comparison.
These do not claim the real regional construction has already completed.
Full construction additionally requires the573previously validated pilot
county-years to agree at the existing numerical tolerance, exact dates and
zero-rain flags. Earlier13county/region tests and their artifacts remain intact.
