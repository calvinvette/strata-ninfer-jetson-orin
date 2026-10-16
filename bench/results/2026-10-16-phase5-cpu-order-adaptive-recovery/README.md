# CPU-order expert arithmetic under adaptive swaps — Orin — 2026-10-16

This Phase 5 mechanism test repeats the accepted-only short→long→short recovery
sequence with Strata's opt-in `--expert-cache-cpu-order` path. It asks whether
using CPU-order arithmetic for GPU cache hits removes the previously observed
recovery drift. The model, profile, prompts, cache size, adaptation cadence,
service binary and capture harness were held fixed from the current-source
route-change experiment; only the CPU-order flag was added.

Two fresh services each processed the same 512-token short prompt, the same
2,048-token swap-inducing prompt and the short prompt again, generating 16
tokens per request with accepted-only adaptation every four tokens. Both
independent services produced identical token IDs and all nine logged state
fields request-by-request. Within each service, recovery still differed from
the initial short request at 14 of 16 token IDs. The GDN, PLE, tail, pooled,
full-pooled, KV and PLE-previous fingerprints also differed; the dead-state
fingerprint matched. Thus CPU-order arithmetic alone did not remove the
recovery drift in this sequence.

The captured layer-0 path retained the same route transition pattern as the
prior run: all first seven aligned initial/recovery rows had identical
activations and expert IDs, with 18 of 70 owner assignments changed. The next
15 aligned rows had different activations. Adaptive refill-byte verification
and device residency-table verification passed at every logged apply point.
This test does not prove that expert arithmetic is irrelevant: the flag is an
experimental GPU path, and this sequence does not establish bitwise CPU/GPU
operator equivalence or trace every propagated numerical difference.

The CPU-order path was markedly slower in this workload. Across the two
services, the 512-token prompt took 28.2–29.2 seconds to ingest and 10.9–17.9
seconds to generate 16 tokens; the 2,048-token prompt took 74.9–76.7 seconds to
ingest and 16.6–22.9 seconds to generate 16 tokens. These are diagnostic
observations from two repetitions, not a randomized paired performance
comparison against the default path, and no performance case is made for the
flag.

The 28-GiB supervised run returned 0 after 405.2 seconds. Across 384 memory
samples, minimum host availability was 14.26 GiB and minimum admission
availability was 9.36 GiB. Sampled cgroup `high`, `max`, `oom` and `oom_kill`
counters were zero. CPU clocks ranged 729.6–2,201.6 MHz and GPU clocks
306–1,300.5 MHz; clocks were observed dynamically, not controlled. EMC
readback was denied and energy was not request-attributed.

The artifact is the `IQ1_M` variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. Model and pack identities match
the earlier [route-change capture](../2026-10-14-phase5-current-source-route-change-capture/README.md).
The current service binary SHA256 is
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`; the
expert profile SHA256 is `a514661124d5305effe9c1bcecff7dc069af398b2b19ff9d11628a2cad0a8915`.
The tokenized short and long prompt hashes are recorded in `run/results.json`.

Reproduce from the repository root on the same Orin setup with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/cpu-order-recovery-supervisor --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-16-phase5-cpu-order-adaptive-recovery/capture_same_service_routes.py \
  --output /tmp/cpu-order-recovery-run --captures 128 --recovery-start-row 2592
```

The harness adds only `--expert-cache-cpu-order` to the established route
capture configuration. Raw outputs, state fingerprints, captured dispatches,
service logs, supervisor telemetry and hashes are retained in this directory.
This is a negative mechanism result, not a Phase 5 closeout; the broader state
cause, graph lifetime gates and quality impact remain open.
