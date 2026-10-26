# Q2_0 staged-miss workload screen

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, CUDA 12.6, SM87. Source
commit: `09087eabfa7bb7788ca00a71e0eff52fe2b896a9`. The tested `strata`
binary SHA256 is
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

## Decision

The 6-GiB staged profile showed a workload-specific performance signal at
1,069 prompt tokens, but its generated output hashes differed from CPU-miss
control in all three pairs. A 557-token workload also differed in all three
pairs. No independent task-quality oracle was applied to those generations, so
the 1,069-token performance result does not advance to seven-pair confirmation
or qualify a broader profile. This is a screen with a useful next diagnostic,
not a quality or release result.

The 1,069-token cell crossed the 5% median screen threshold on prompt and decode
throughput, and improved TTFT and client completion. Its outputs did not match.
The 557-token cell raised decode TPS but had essentially unchanged TTFT and
less than 5% client improvement; its outputs also did not match. The 512,
172-token and 2,048-token cells showed no useful TTFT/client effect. E6 remains
open.

## Method

Each arm used a fresh supervised server process, followed by one warmup and one
measured request for each of five fixed natural-generation shapes. We randomized
arm order in three process pairs, with order `CPU, NInfer`, `NInfer, CPU`,
`CPU, NInfer`. Prompts used temperature 0. The control used CPU miss fallback
(`--pcie-frac 0.0`); the treatment used strict NInfer staged misses
(`--pcie-frac 1.0`). Both used the same Q2_0 model, expert profile, 3,000-slot
GPU cache, 6-GiB resident budget, separate 3-GiB workspace reserve, 8K context,
MTP-2, 128-token prefill and 8 workers. All other settings and model files were
held fixed.

The initial exploratory seed placed NInfer first in all three pairs. It is
excluded from the effects below. The balanced-order run was repeated before
interpreting results. All six processes passed their API and exact token-count
checks and used the same startup residency-map SHA256:
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`.
Strict NInfer dispatch was observed. In the measured 557- and 1,069-token
requests, respectively, 1,519 (4.9%) and 1,367 (4.4%) of 30,720 routed experts
were read by the GPU from the staged tier.

The supervisor recorded at least 11.42 GiB available physical/admission RAM,
above the 6-GiB floor, and zero cgroup `high`, `max`, `oom` or `oom_kill`
events. GPU clocks were observed between 306 and 1,300.5 MHz (median 918 MHz);
clocks were not changed. EMC readback was denied, and energy was not attributed.
These are descriptive three-pair medians, not confirmation intervals.

## Results

Positive TPS changes mean faster NInfer throughput. Positive TTFT and client
changes mean slower NInfer latency. Hashes compare each measured treatment
response with its paired control; equal token counts do not imply equal output.

| Prompt + output | Prompt TPS | Decode TPS | TTFT | Client total | Measured output hashes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 512 + 64 | −7.80% | −6.22% | +8.30% | +7.91% | 3/3 equal |
| 2,048 + 128 | −5.57% | +2.16% | +5.80% | +2.92% | 3/3 equal |
| 172 + 64 | −4.78% | −3.69% | +5.56% | +3.65% | 3/3 equal |
| 557 + 64 | −0.40% | +7.99% | +0.21% | −2.54% | 0/3 equal |
| 1,069 + 64 | +7.04% | +8.54% | −6.56% | −7.60% | 0/3 equal |

The pair-by-pair values, raw requests, residency maps, engine logs, memory and
clock telemetry are in [`balanced-order/`](balanced-order/). Recreate the
screen with:

```bash
python3 bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/run_staged_workload_screen.py \
  --out bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/balanced-order
```

The seed and execution order are stored in `balanced-order/matrix.json`.
[`balanced-order/analyze.py`](balanced-order/analyze.py) regenerates its CSV
and JSON summaries from the saved per-arm results.

## Output divergence diagnostic

An isolated fresh-process reproduction of the 1,069-token cell is in
[`mismatch-reproduction-1069/`](mismatch-reproduction-1069/). The two arms had
identical warmup output hashes. The CPU-miss measured output then differed from
its warmup, while NInfer's measured output matched its warmup; the pair's
measured hashes therefore differed. Captured text confirms wording differences
within the same 64-token completion. The CPU-miss completion also differed
between the isolated reproduction and the five-workload sequence, while its
warmup hash remained the same. This points to request-history or execution
variation that needs investigation; the capture does not establish a cause or
which output is better.

The next gate is a held-out task-quality/state check for staged misses,
including request-history controls and persistent-state comparison. Do not run
performance confirmation or describe the 1,069-token cell as a qualified gain
until this difference is explained or bounded.

## Request-history and state fingerprint follow-up

A direct temperature-zero engine diagnostic repeated the exact 1,069-token
prompt twice per backend with prompt caching enabled and MTP draft counters at
zero. On both CPU-miss and strict-NInfer staged routes, the second request
reused 1,062 prompt tokens and read seven. Its 64 generated token IDs differed
from the first request, and the final GDN, PLE, tail, pooled, pooled-full, KV
and PLE-previous fingerprints changed. Two fresh-engine repeats per backend
produced identical tokens and state. A same-service cache-off repeat also
changed token IDs between requests, identically on both backends; state hashing
is suppressed by the current runtime when prompt caching is zero. Across every
diagnostic condition, CPU-miss and NInfer produced identical tokens at matching
request ordinals, and all nine final-state fields matched where available.
This demonstrates shared process/request-history variation but does not
identify its cause. It does not explain why the original multi-workload screen
had cross-arm mismatches.

Raw IDs, decoded text, per-request engine metrics and state fingerprints are in
[`state-fingerprint-diagnostic/results.json`](state-fingerprint-diagnostic/results.json);
engine logs are retained alongside it. The [fresh-engine repetitions](state-fresh-engine-diagnostic/)
and [same-service cache-off repetitions](state-cache-off-diagnostic-rerun/)
retain their raw token IDs and logs. Next, add an opt-in final-state fingerprint
for cache-off requests, then replay the complete five-workload order under both
miss routes with warmup and prompt-end/final-state capture. Preserve exact
tokens and direct persistent-state evidence. The original 1,069-token screen
remains unqualified and requires a held-out task oracle before confirmation.

Recreate this diagnostic with the same binary and model files using:

```bash
python3 bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-fingerprint-diagnostic/run_state_fingerprint_diagnostic.py \
  --out bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-fingerprint-diagnostic-rerun

python3 bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-fingerprint-diagnostic/run_state_fingerprint_diagnostic.py \
  --fresh-each --out bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-fresh-engine-rerun

python3 bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-fingerprint-diagnostic/run_state_fingerprint_diagnostic.py \
  --prompt-cache 0 --out bench/results/2026-10-26-phase-e6-q2-staged-workload-screen/state-cache-off-rerun
```
