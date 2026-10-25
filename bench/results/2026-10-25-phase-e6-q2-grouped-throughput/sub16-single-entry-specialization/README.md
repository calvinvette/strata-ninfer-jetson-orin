# Q2_0 NInfer follow-up: four-entry weight reuse

Date: 2026-10-25. Jetson AGX Orin, CUDA 12.6, SM87. This is an opt-in
operator/service experiment for the E6 Q2_0 expert path. It does not qualify a
release profile.

## Candidate

The NInfer-derived grouped kernels originally decoded one expert row for each
routed entry, using a 32-lane warp for each row. This candidate processes up to
four entries together so each lane decodes a Q2_0 weight chunk once and applies
it to several Q8_1 activations. Two 16-lane rows share each warp. A dedicated
single-entry schedule handles decode groups. Strata remains the default; the
candidate is selected only with `--expert-backend ninfer`.

The model is the Coder Q2_0 first GGUF shard at layer 0, expert 32. The
independent activation and FP64 output fixtures are the Phase 5 artifacts named
in the reproduction command below. The test binary also builds 3-, 64- and
128-token grouped cases with top-10 expert routing.

## Operator results

| Shape | Strata median | NInfer median | NInfer / Strata | Parity |
| --- | ---: | ---: | ---: | --- |
| One resident entry, seven interleaved × 1,000 | 24.754 µs | 24.270 µs | 0.980× | relative L1 `0`, pass |
| 64 tokens × top-10, seven paired blocks × 50 | 3,945.485 µs | 4,369.008 µs | 1.107× latency | relative L1 `0`, pass |
| 128 tokens × top-10, seven paired blocks × 50 | 7,958.770 µs | 8,910.264 µs | 1.120× latency | relative L1 `0`, pass |

The standalone model-derived D3/D4 result had relative L2 `2.13101098e-7`,
maximum absolute error `1.45426081e-8`, and no unwritten outputs. The grouped
3/64/128-token fixture checks all had relative L1 zero and no unwritten
outputs. These tests establish operator/fixture parity, not task quality.

The candidate source SHA256 is
`3891bf2de2d8bae370841df86011787d9e145833f06961b3a00040d377305d3a`. The
server SHA256 is
`daaf67ff7b764f0bd8413bee1d4e027132d4f2f978472795a82404fddeb5d420`; the
operator harness SHA256 is
`6334fb6015e115ea8978f870aa6e25a2cb122761fd098a23a318b3bc1e1fd2bb`.

Tuning retained the 128-thread, eight-row-per-block launch. A first 32-lane
four-entry variant measured 3.797× and 3.858× NInfer/Strata latency at 64/128
tokens. Changing to 256 threads and sixteen rows per block measured 1.137× and
1.147×; it was reverted. Those diagnostics are retained in the adjacent
candidate directories.

## Same-residency service screen

The 8K Q2_0 profile used a 3,000-entry startup residency map, prefill 128,
`--spec 2`, eight pool workers, no prompt cache, and strict NInfer dispatch.
Three randomized same-day pairs each ran one warmup and one measured `1+1`
request per arm. All six maps had the same SHA256
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`, and all
six generated outputs had SHA256
`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`.

| Pair | NInfer / Strata client total (s) | NInfer / Strata client TTFT (s) | NInfer total change | NInfer TTFT change |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 9.141 / 8.897 | 6.049 / 5.890 | +2.74% | +2.70% |
| 2 | 9.432 / 9.060 | 6.358 / 6.013 | +4.11% | +5.73% |
| 3 | 9.143 / 9.027 | 6.105 / 5.987 | +1.28% | +1.97% |

Median paired changes were +2.74% client total and +2.70% client TTFT; positive
means slower. NInfer was slower in all three pairs. This screen did not meet the
predeclared 5% useful-effect threshold. Seven-pair confirmation was not run.
Minimum available physical/admission memory was 17.73 GiB, above the 6 GiB
floor. GPU frequency was sampled at 306 MHz; EMC readback was denied. Energy
was not attributed. The operator improvement did not yield an end-to-end win.

## Kernel profiling diagnostic

An Nsight Systems trace of the complete parity/timing harness recorded median
CUDA kernel times of 9.792 µs for NInfer grouped D3 and 8.992 µs for grouped
D4. The corresponding native Q2 medians in that same trace were 9.504 µs for
gate/up and 9.440 µs for down; NInfer's quantizer median was 2.752 µs versus
3.264 µs for the native SwiGLU quantizer. This trace contains several shapes,
repeated timing blocks and profiler overhead, so these are broad per-launch
diagnostics, not a matched single-shape timing comparison. The ordinary paired
operator and service results above remain the performance evidence.

Nsight Compute collected hardware counters for the one-entry grouped shape
(one group; D3 grid 160 × 128 and D4 grid 320 × 128). It reported 64 and 55
registers per thread and achieved occupancy of 53.46% and 61.91% for D3 and D4,
respectively. A second capture isolated the 64-token/top-10 grouped launches
(D3 grid 160 × 10 × 128; D4 grid 320 × 10 × 128). Achieved occupancy was
65.41%/73.39%, close to the respective theoretical 66.67%/75%; memory
throughput was 69.86%/70.96%, and compute throughput 52.21%/79.06%. The grouped
capture therefore shows no large occupancy deficit, but it does not explain
the remaining operator gap. Both reports' replayed kernel durations are
profiler-only and must not be compared with ordinary timings. The full parity
harness passed during both captures. The raw Nsight Systems trace is
intentionally excluded from the repository; its summarized kernel statistics
are recorded above. Raw [one-entry Nsight Compute](decode-one-entry-basic.ncu-rep)
and [64-token Nsight Compute](grouped-64-exact-basic.ncu-rep) reports, plus
supervisor summaries, are stored beside this report.

## Entries-per-tile sweep

Using the same 16-lane Q2 schedule, I tested tiles of two and eight entries
around the retained four-entry tile. Each grouped value is the median of seven
paired blocks with 50 invocations per arm; lower NInfer/Strata is better. All
cases passed the independent D3/D4 and grouped-output parity checks with no
unwritten results.

| Entries per tile | One-entry NInfer / Strata | 64-token NInfer / Strata | 128-token NInfer / Strata | Decision |
| ---: | ---: | ---: | ---: | --- |
| 2 | 0.984× | 1.234× | 1.236× | Reject: repeated weight loads cost more |
| 4 | 0.980× | 1.107× | 1.120× | Retain: best grouped result |
| 8 | 1.043× | 1.096× | 1.117× | Reject: grouped improvement is only about 1% and decode regresses |

The two-entry run used source SHA256
`8668380b781846376b5501b3ce5bfd76ac1ae8d1b789ca2c6f51c2c11ad5679b`, server
SHA256 `a0e0edc94e7586a96e548bc8f92917f05299d9d2b6d1c22994137cbcd12b6881`, and
parity binary SHA256 `5aca9bb41d3bc6285dd0c3821643492ade1b07814b894e6b8e5ba149f5c7b6db`.
The eight-entry run used source SHA256
`5bacff8cc4952955b3b75123fc6af938065c4a1e24d220f484d601c7a90e10db`, server
SHA256 `2fee37e9c6353f33c888f18c0bc73ee7fb4b62500ec32c4888b51f31abd3c80f`, and
parity binary SHA256 `7ae2880f6bfa1a54f4b25187bb04a38454acebf5e5742578f73486fd5d06bbf8`.
The retained four-entry build remains
`daaf67ff7b764f0bd8413bee1d4e027132d4f2f978472795a82404fddeb5d420` for
`strata` and `6334fb6015e115ea8978f870aa6e25a2cb122761fd098a23a318b3bc1e1fd2bb`
for the parity harness. Raw supervised runs are in the adjacent `entries2/`
and `entries8/` directories. Neither alternative crossed the 5% useful-effect
threshold, so no additional service screen was run.

After restoring the four-entry source, I rebuilt `strata` and the parity
harness and confirmed their hashes matched the retained artifacts above. A
fresh seven-block operator run again passed all parity checks and measured
NInfer/Strata ratios of 1.118× and 1.119× for 64 and 128 tokens (one-entry
ratio 0.980×). This repeat confirms the four-entry path's grouped result is
still about 12% slower; it is not a new service confirmation.

## Reproduction

Build the tested CUDA targets with bounded parallelism:

```sh
cmake --build build/integration/e0-cuda-build \
  --target strata ninfer_q2_expert_parity --parallel 2
```

Run the supervised parity and operator test:

```sh
python3 tools/integration/run_control.py \
  --output <supervisor-output> --timeout 300 --interval 1 --sample-clocks -- \
  build/integration/e0-cuda-build/ninfer_q2_expert_parity \
  ~/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  0 32 \
  bench/results/2026-10-15-phase5-activation-error-decomposition/weights-and-outputs/layer-0-expert-32-activation.f32 \
  <independent-fp64-reference> <output-fixture>
```

Run the three-pair service screen under the same memory supervisor:

```sh
python3 tools/integration/run_control.py \
  --output <supervisor-output> --timeout 1200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-25-phase-e6-q2-grouped-throughput/run_service_paired_screen.py \
  --out <paired-screen-output>
```

The recorded commands, API outputs, engine logs, resident maps and supervisor
summary are stored beside this report. The E6 [combined throughput report](../README.md)
contains the earlier packed-dot comparison and the full 1K–256K capacity
screen.
