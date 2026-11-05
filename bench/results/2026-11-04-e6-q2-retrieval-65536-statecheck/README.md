# Q2_0 65,536-token retrieval state check

Date: 2026-11-04. Device: Jetson AGX Orin 64 GB, ARM64, CUDA 12.6. This is a
paired **state diagnostic**, not a performance or task-quality qualification.

## Result

Strata and strict NInfer processed the same held-out 65,536-token retrieval
prompt at a configured context limit of 131,072. Each request generated one
token. Both returned token ID `19910` (`EAR`). Their final fingerprints matched
for all nine recorded state groups: sequence length, GDN, PLE, QSA tail, dead
state, pooled state, pooled-full state, KV state and PLE previous values. The
5,000-entry resident expert maps were byte-identical. The NInfer log records a
strict resident Q2_0 grouped dispatch at layer 0. Both arms had zero MTP drafts.

This one-token check does not test the complete answer. The exact 47-token
answer for this task was already checked in the full-response backend screen;
see the [65K same-map screen](../2026-10-31-e6-q2-fixed-map-ORBIT-screen/README.md).
Combining that answer check with this final-state comparison does not make the
two separate runs an accepted-prefix trace or prove state parity at every token.

| Measure | Strata | Strict NInfer |
| --- | ---: | ---: |
| Prompt tokens | 65,536 | 65,536 |
| Generated tokens | 1 | 1 |
| First token ID | 19910 | 19910 |
| Final state groups equal | 9/9 | 9/9 |
| Resident-map SHA-256 | `337d43f4d672f5abec0db0379a48454c3e70eacd7f1bd356af50c04f20fb0080` | same |
| Prompt time (trace-enabled diagnostic) | 614.590 s | 615.762 s |
| Expert cache hits/lookups | 245/480 | 245/480 |
| RAM/file expert blobs | 45/190 | 42/193 |
| File bytes reported | 211.5 MB | 218.4 MB |

The prompt-time difference is approximately +0.19% for NInfer, but this was one
trace-enabled pair with state hashing and a one-token continuation. It is not a
performance estimate and must not be compared with untraced screens. Dynamic
file-blob counts differed despite identical startup maps; there is no timing
claim from this run.

## Guard and instrumentation

The run completed under `run_control.py` in 1,315.35 seconds. Minimum available
and admission memory was 7.147 GiB, above the 6 GiB floor; sampled swap peaked
at 1.187 GiB. The existing cgroup OOM-kill counter remained at 1. CPU clocks
ranged from 729.6 to 2,201.6 MHz and GPU clocks from 306 to 1,300.5 MHz. Clocks
were observed, not controlled. EMC readback was denied. Energy was not measured;
tegrastats rail readings are not process-attributed energy.

The diagnostic command used the current Q2_0 build, fixed learned 5K map,
8 workers, prefill chunk 128, `--max-context 131072`, `--resident-budget-gib 6`,
no adaptive swaps, PCIe fraction 0, and trace/state-hash instrumentation. The
NInfer arm used `--expert-backend ninfer --expert-backend-strict`; the control
used `--expert-backend strata`. See the captured
[Strata config](statecheck-strata-config.json),
[NInfer config](statecheck-ninfer-config.json), and
[sanitized evidence](statecheck-evidence.json).

An initial attempt used a Strata config for both arms and was stopped before
completion; it is excluded. The checker now selects each backend explicitly
and has focused regression coverage (11 tests passed). The corrected run used
the NInfer config as its base, and its engine log confirms strict NInfer
dispatch. The checker fix was committed and pushed as `8c1bbe5a`.

This closes only one final-state comparison for one one-token continuation after
a synthetic 65K prompt. Broader task quality, multi-model evidence, state at
intermediate accepted prefixes and the E6 performance gate remain open.
