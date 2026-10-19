# Layer-26 GDN accepted-commit trace — Orin — 2026-10-20

This opt-in same-service run captured committed layer-26 GDN state at selected
accepted endpoints while executing the initial 512-token prompt, a 2,048-token
prompt, and the identical 512-token recovery prompt. The candidate used Coder
IQ1_M, accepted-only adaptive swaps (cadence 4, cap 8), a two-token verifier
window and the existing 8K context profile. Raw arrays remain outside Git at
`~/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-commit-positions-500-514-2026-10-20.bin`.

The initial and recovery requests had the same token IDs at every captured
endpoint. The first captured committed state difference is at position 506:
786,389/786,432 recurrent values differ, with maximum absolute difference
0.00216343 and relative L2 0.00173438; 10,240/30,720 convolution-history
values differ, with maximum absolute difference 0.0184928 and relative L2
0.00166646. At position 508 the convolution history is again bit-identical,
while 786,367 recurrent values differ. Recurrent state remains different at
positions 510 through 514.

The raw state at committed position 510 matches the prior verifier pre-state
capture at position 511 byte-for-byte for both initial and recovery requests.
The prior prefill trace found identical raw state at boundary 505. Thus the
first observed divergence falls in the verifier commit window ending at 506,
after matching prefill and before the position-510 state. The endpoint capture
does not distinguish computations for individual tokens inside that window;
it identifies a narrow transaction boundary, not the cause. Recovery token IDs
matched the initial request throughout the 16-token completion.

The run passed its `MemoryMax=28G` supervisor in 183.19 s. Minimum host and
admission availability were both 14.31 GiB, peak scope memory was 10.90 GiB,
and cgroup low/high/max/OOM/OOM-kill counters remained zero. Clocks were
dynamic, EMC readback was denied, and energy was not attributed to the request.
The paired service log and telemetry are under `run/` and `supervisor/`; exact
state comparison and the verifier cross-check are in `commit-state-analysis.json`.
The capture built on Orin. Eight focused native tests covering accepted windows,
GDN recurrence and verifier parity passed; the integration Python suite passed
163/163. Current-source HIP and SYCL compile/CLI evidence is retained under
`../backend/maestro1-gdn-commit-state-trace-2026-10-20/`.

Reproduce the analyzer on Orin with the retained raw state files:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_gdn_commit_state_trace.py \
  --state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-commit-positions-500-514-2026-10-20.bin" \
  --verifier-state-dump "$HOME/models/strata-orin-validation/experiments/phase5-gdn-state/coder-iq1m-adaptive-cap8-layer26-verifier-pre-2026-10-20.bin" \
  --layer 26 \
  --output /tmp/commit-state-analysis.json
```
