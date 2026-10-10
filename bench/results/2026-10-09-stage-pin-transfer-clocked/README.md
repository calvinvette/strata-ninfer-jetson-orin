# Clocked paired pageable/pinned staging screen — Orin

Run date: 2026-10-09 on the local `orin1` Orin AGX, ARM64, CUDA 12.6. This
repeat used the trace-corrected native candidate binary (`e1ec9ef6…e820c1f`)
and the same Coder IQ1_M model artifacts, exact 4,096-token formatted prompt,
64-token generation cap, 6,519 actual expert-cache slots, context 8,192,
prefill 64 and spec4/MTP configuration as the fixed-cache screen. Both arms
explicitly enabled file-tier prefetch and staging; only `STRATA_STAGE_PIN`
changed. Three randomized process pairs ran in pinned/pageable,
pageable/pinned, pinned/pageable order.

All three pairs matched generated token IDs and all nine persistent-state
fields. Pageable median prompt time was 99,556.3 ms and pinned was 99,655.2 ms
(+0.10%). Pageable median decode time was 5,782.1 ms and pinned was 5,341.9 ms
(-7.62%). Pairwise decode deltas ranged from -9.24% to +3.94%; the three-pair
sample is too small and variable to establish a product benefit. Median
requested host staging was 122,470,400 bytes pageable and 135,782,400 bytes
pinned. These are requested owner payloads, not measured physical backing.
Pinned staging stays opt-in and is not promoted. No copy-latency isolation or
energy measurement was made.

The six-GiB supervisor observed minimum `MemAvailable` of 8,634,073,088 bytes
(8.04 GiB) across the run. Clock sampling ran concurrently without changing
the system power mode or clocks; `nvpmodel -q` reported MAXN. Observed CPU
frequencies ranged from 729.6 MHz to 2,201.6 MHz and GPU frequencies from
306 MHz to 1,300.5 MHz. EMC frequency could not be read because the debugfs
clock path returned permission denied. Dynamic clocks and unsupported EMC
sampling limit timing interpretation. Energy was not measured; tegrastats raw
rails are retained and are not treated as integrated energy.

The experiment command and supervisor metadata are in `result.json`, with
per-arm output, owner traces and persistent-state snapshots in
`experiment/results.json`. The contemporaneous clock samples are in
`clock-samples.jsonl`; supervisor memory and tegrastats are in `memory.jsonl`
and `tegrastats.txt`. Model and engine identities are recorded in each arm.
Models remain under `/home/calvin/models/`. This is a screening result for one
model and workload, not a general staging qualification.
