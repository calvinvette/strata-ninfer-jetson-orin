# Q2_0 eager/captured MTP state parity — 128 generated tokens — Orin — 2026-10-12

This extends the existing eight-token eager/captured check to 128 generated
tokens at a 512-token formatted prompt. Both modes used the same Q2_0 model,
MTP runtime pack, binary, prompt, 3,000-slot expert cache, FP16 KV, 64K
configured context, prefill 512, and `STRATA_PREFILL_CPU_SHARE=0`. The eager
route used `--no-capture`; captured used the default graph route. Each mode ran
fresh sequential processes with MTP off and windows 2/3/4. The 28-GiB
supervisor applied the six-GiB availability floor.

Both modes passed the accepted-prefix harness's internal MTP-vs-no-MTP
checks. Cross-mode comparison found identical token IDs and all nine recorded
final state fields for MTP off and each active window. Every shared accepted-
prefix boundary also matched across modes:

| MTP mode | Drafts offered / accepted | Shared eager/captured boundaries | Token and state parity |
| ---: | ---: | ---: | --- |
| Off | 0 / 0 | 128 | Pass |
| 2 | 75 / 52 | 76 | Pass |
| 3 | 116 / 69 | 59 | Pass |
| 4 | 159 / 74 | 54 | Pass |

The run completed in 373.47 seconds. Minimum host availability was 15.27 GiB
and minimum effective cgroup admission headroom was 9.83 GiB; OOM counters
remained zero. Clocks were observed without control. EMC readback was denied,
and energy was not measured. This is a single same-day correctness comparison,
not timing evidence or task-quality qualification.

The captured run is retained in
[`../2026-10-12-phase5-q2-accepted-prefix-128/`](../2026-10-12-phase5-q2-accepted-prefix-128/);
its prompt SHA256 matches this eager run:
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`.
Both use candidate executable SHA256
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`.
Eager raw logs and state traces are in `run/`; supervisor telemetry is retained
in `supervisor/`.

This supports longer-chain eager/captured correctness for the tested prompt and
configuration. Other prompts and formats, cancellation/termination across graph
modes, quality, and randomized performance remain open Phase 5 gates.

Reproduce the eager arm from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-12-phase5-q2-eager-chain-128/supervisor \
  --timeout 10800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-12-phase5-q2-eager-chain-128/config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-12-phase5-q2-eager-chain-128/run \
  --tokens 128 --prompt-tokens 512 --windows 0 2 3 4 --run
```
