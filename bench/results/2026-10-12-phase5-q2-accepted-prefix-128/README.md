# Q2_0 MTP accepted-prefix chain — 128 generated tokens — Orin — 2026-10-12

This extends the direct persistent-state comparison from 32 to 128 generated
tokens. Four fresh sequential Strata services ran the same 512-token formatted
prompt with FP16 KV, 3,000 expert-cache slots, 64K configured context, prefill
512, and CPU-prefill sharing disabled. The arms were MTP off and MTP windows
2, 3, and 4, using the Q2_0 model and explicit MTP runtime pack under
`~/models/strata-orin-validation/`. State hashing and accepted-prefix tracing
were enabled. The prompt fixture SHA256 is
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`; the
candidate executable SHA256 is
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`.

All three MTP arms matched the no-MTP arm's 128 token IDs and final state. At
every common accepted-prefix boundary, all nine recorded persistent-state
fields matched: `L`, GDN, PLE, tail, dead, pooled, pooled-full, KV and
`ple_prev`. The harness comparison passed without failure:

| Window | Drafts offered / accepted | Shared prefix boundaries | State/token parity |
| ---: | ---: | ---: | --- |
| 2 | 75 / 52 | 76 | Pass |
| 3 | 116 / 69 | 59 | Pass |
| 4 | 159 / 74 | 54 | Pass |

The 28-GiB systemd scope completed in 394.75 seconds. Minimum host
`MemAvailable` was 15.41 GiB and minimum effective cgroup admission headroom
was 10.38 GiB; OOM and OOM-kill events remained zero. Clocks were observed
under the dynamic platform policy, not changed. EMC readback was denied; energy
was not measured or attributed.

This extends exact accepted-prefix state parity to 128 generated tokens for
this prompt, model, binary and fixed cache/configuration. It does not cover
long-prefill termination, other prompts or KV formats, graph/eager interaction,
task quality, or performance. Phase 5 remains open for those gates.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-12-phase5-q2-accepted-prefix-128/supervisor \
  --timeout 10800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-12-phase5-q2-accepted-prefix-128/server-config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-12-phase5-q2-accepted-prefix-128/run \
  --tokens 128 --prompt-tokens 512 --windows 0 2 3 4 --run
```

`run/results.json` contains the direct token/state comparison and per-boundary
records; `run/mtp-*.log` contains raw engine traces. Supervisor memory, cgroup,
clock and tegrastats samples are retained alongside the terminal result.
