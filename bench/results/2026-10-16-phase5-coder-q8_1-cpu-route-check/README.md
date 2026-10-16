# Coder IQ2_S/Q2_0 opt-in CPU Q8_1 route screen — Orin — 2026-10-16

This screen tested an opt-in CPU expert path for the native pair whose CUDA
route already consumes Q8_1: IQ2_S gate/up plus Q2_0 down. `STRATA_NATIVE_CPU_Q8_1_DOT=1`
selects it during model format setup; the default GGML CPU route remains
unchanged. The candidate uses GGML's Q8_1 quantizer and GGUF weight
dequantizers, then a scalar double-accumulating dot. It is a correctness
experiment, not an optimized CPU kernel.

Both arms ran on the same rebuilt service binary, same Coder IQ1_M artifacts,
same prompt sequence, delayed adaptation and a 28 GiB supervisor. The
candidate arm set the environment variable before service startup. Each arm
ran one 512-token prompt, one 2,048-token prompt, the same short recovery, and
one more copy of that short prompt, generating 16 tokens each time.

| Observation | Default CPU route | Q8_1 CPU candidate |
| --- | ---: | ---: |
| Supervised sequence | pass, 207.0 s | pass, 210.1 s |
| Minimum host availability | 14.34 GiB | 14.40 GiB |
| Layer-1 captured rows | 88 | 88 |
| Shared expert assignments | 863 | 863 |
| CPU-owned shared assignments | 549 | same owners |
| Changed owners for shared assignments | — | 0 |
| Cgroup `low/high/max/oom/oom_kill` events | 0 | 0 |

Token IDs matched on the initial short prompt, recovery prompt and continuation.
The long prompt differed at three of 16 positions between arms. Both services
recovered the same short-request token IDs and state hashes as their own initial
short request. Across arms, the initial short tokens still matched while five
state fingerprints differed; the long request differed in seven fields. The
first captured layer-1 input difference occurred at row 42, after earlier
captured inputs and expert IDs matched. The route capture contained 549 CPU-owned
expert assignments, so this run exercised the candidate. A single pair cannot
attribute the long-answer differences or qualify a quality effect.

On the same captured layer-1 expert activation, the scalar candidate output was
within relative L1 `9.33e-4` (short) and `6.36e-4` (long) of CUDA, compared with
`1.68e-2` for the existing Q8_K CPU route on the short capture. These operator
checks support the Q8_1 arithmetic contract. The service screen does not show
that the new route improves the task answer or accepted-prefix state across
CPU/GPU migration. The 3.1 s difference in total time is one unpaired dynamic-
clock observation, not a speed claim. No default or profile changed.

All 16 `native_expert_parity_` CUDA CTests passed, including the new synthetic
candidate test. The shared CPU source compiled and linked as
`strata_kernels_cpu` in maestro1's HIP- and SYCL-configured builds; those are
x86 host-build checks, not GPU runtime evidence. Exact source/object/archive
hashes and restoration checks are in `backend-builds/`.

The model was `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M; layer 1's routed experts
are IQ2_S/Q2_0. The inputs, hashes, token IDs, persistent-state hashes, route
captures, memory samples, tegrastats, service logs and CTest output are retained
in this directory. The large text streams are gzip-compressed. No model or build
artifact is committed. Phase 5 remains open.

Reproduce each arm on Orin1 with the same files under `~/models/`:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/baseline-new/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/run_cpu_q8_1_route.py \
  --adapt-every 100000 --adapt-swaps 96 --continuations 1 \
  --output bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/baseline-new/result

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/candidate-new/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/run_cpu_q8_1_route.py \
  --adapt-every 100000 --adapt-swaps 96 --continuations 1 --cpu-q8-1-dot \
  --output bench/results/2026-10-16-phase5-coder-q8_1-cpu-route-check/candidate-new/result
```
