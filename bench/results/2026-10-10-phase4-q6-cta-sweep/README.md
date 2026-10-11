# Q6_K conversion CTA-size screen — Orin — 2026-10-10

This test-only schedule screen compares the production Q6_K-to-FP16 kernel
(256 threads per CTA) with equivalent one-thread-per-32-value-group kernels
using 128, 256 and 512 threads per CTA. It uses the five real IQ1_M matrix
shapes identified by the request profile. The full output of every schedule
was compared bit-for-bit with production over all 76,349,440 matrix elements;
all comparisons passed. The separate [real-payload CPU oracle check](../2026-10-10-phase4-q6-real-payload/README.md)
covers four rows of each shape.

Each of three separate process runs used a different shape/schedule random seed
(20261011, 20261012, 20261013). Within each run, seven blocks randomized all
five shapes and all four schedules; every sample timed 20 launches after five
warmups. Results below are medians of seven within-process paired blocks for
each matrix/schedule, then medians of the three process-level paired deltas.
The ranges show the three process-level deltas; they are not confidence
intervals. All raw per-block times, randomized orders, stdout/stderr,
supervisor results, physical-memory samples and tegrastats are retained in
`process-reps/`.

The initial one-process pilot is retained under `supervisor/`. It used the same
first seed and schedule but preceded the explicit seed line in stdout; only the
three runs in `process-reps/` are used in the summary above.

| Matrix rows × columns | Production median ms | 128-thread paired delta | 256-thread paired delta | 512-thread paired delta |
| ---: | ---: | ---: | ---: | ---: |
| 6144 × 2560 | 2.366 | +0.733% (+0.312 to +1.105%) | +0.460% (−0.010 to +0.839%) | +0.323% (−0.185 to +0.738%) |
| 640 × 2560 | 0.251 | +0.459% (+0.344 to +0.582%) | +0.056% (−0.320 to +0.078%) | +3.594% (+3.370 to +3.912%) |
| 10240 × 2560 | 3.934 | +0.445% (−0.429 to +0.489%) | +0.066% (−0.747 to +0.126%) | −0.101% (−0.906 to +0.060%) |
| 512 × 2560 | 0.198 | +0.653% (+0.561 to +0.851%) | −0.218% (−0.228 to −0.022%) | −0.472% (−0.565 to −0.246%) |
| 12288 × 2560 | 4.733 | +0.368% (+0.303 to +0.790%) | +0.041% (−0.061 to +0.573%) | −0.118% (−0.238 to +0.586%) |

The profile's measured request window had 432, 208, 176, 168 and 40 calls for
these shapes, respectively (1,024 total). Weighting each shape's paired
within-block times by those counts gives process-level median changes of
`+0.813%, +0.046%, +0.662%` for 128 threads; `+0.531%, −0.283%, +0.310%` for
the 256-thread candidate; and `+0.518%, −0.363%, +0.239%` for 512 threads.
The across-process medians are +0.662%, +0.310% and +0.239%, respectively.
The weighted sum is a diagnostic reconstruction of profiled dequant duration,
not end-to-end latency; it ignores overlap and other request work.

No schedule is consistently faster across processes and shapes. The apparent
differences are small, shape-dependent, and within-run repetition ranges
overlap. No candidate is promoted. This rejects these CTA-size alternatives for
the current candidate pending any new schedule or clock-controlled evidence.

`cuobjdump --dump-resource-usage` on the test executable reports 22 registers
per thread and zero stack, spills, shared memory and local memory for all three
candidate kernels. The production kernel has the same counts. CTA sizes differ,
but occupancy was not measured: Nsight Compute cannot launch on this node with
the current profiling permissions. `tegrastats` reported GPU utilization near
99% during measured batches, but did not report GPU or EMC frequencies. CPU
frequency samples ranged from 729 to 2201 MHz. No energy claim is made. The
lowest physical `MemAvailable` across runs was 29,790,773,248 bytes (27.74
GiB), above the required six-GiB reserve.

The test-only source SHA256 is
`b174499662f2ab110f89228e191f97f1f48c9d59bd3ce882e378b42302244134`; the
linked executable SHA256 is
`1c857a8593b930f424009403bb78d7946f3c2668eb371efc00e017b3b9cf93a3`. The
Q6_K source shard is identified in the [candidate profile manifest](../2026-10-10-phase4-candidate-request-profile/identities.json).
Production code and default dispatch were not changed.

Reproduce on Orin with the pinned ggml source available at
`/tmp/strata-orin-build/_deps/strata_llamacpp-src`:

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_GGML_DIR=/tmp/strata-orin-build/_deps/strata_llamacpp-src
cmake --build build/integration/operator-tests --target q6_k_schedule_sweep --parallel 1
python3 tools/integration/run_control.py \
  --output bench/results/NEW-q6-cta-sweep/rep1/supervisor --timeout 300 -- \
  build/integration/operator-tests/q6_k_schedule_sweep \
  ~/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  20261011
```
