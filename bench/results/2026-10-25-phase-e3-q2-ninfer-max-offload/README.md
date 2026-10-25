# Q2_0 NInfer max-offload screen

Date: 2026-10-25, Jetson AGX Orin, CUDA 12.6, SM87. This three-pair screen
raised the existing staged-miss selector from `--pcie-frac 0.55` to `1.0`,
selecting all eligible misses for strict NInfer execution. It tests whether
more of the nonresident expert work can move off the CPU while preserving the
existing 1-GiB pinned complement and memory policy. It is a screening result,
not quality qualification or a performance confirmation.

## Fixed setup

Both arms used the same current-source executable, Q2_0 model and PLE, 8K
context, 3,000 resident GPU slots, 1-GiB pinned complement, prefill 128, eight
workers, MTP-2, and the same 55-token prompt / 29-token response. The control
used CPU misses (`--pcie-frac 0`); the candidate used strict NInfer and
`--pcie-frac 1.0`. Each fresh service ran one warmup and one measured request.
The six processes had the same resident-map SHA256
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`. Pair order
was randomized with seed `20261025`.

## Results

| Pair | CPU-miss client total | NInfer staged client total | NInfer change | CPU TTFT | NInfer TTFT | NInfer change | Measured response hashes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 9.019 s | 8.819 s | −2.22% | 6.016 s | 5.835 s | −3.01% | different |
| 2 | 8.875 s | 8.815 s | −0.68% | 5.885 s | 5.815 s | −1.19% | different |
| 3 | 8.940 s | 8.822 s | −1.32% | 5.916 s | 5.853 s | −1.08% | different |

Median paired changes were −1.32% client completion latency and −1.19% TTFT
(negative means faster). Engine prompt latency changed by a median −1.15%;
decode latency changed by −0.68%. The staged arm selected 265 expert entries
per measured request (1.9% of 13,920 routed entries), up from 106 entries
(0.8%) at `pcie-frac 0.55`. All outputs had the expected 29-token count, but
the NInfer response hash differed from the CPU-miss response in every pair and
the harness does not retain response text. No independent quality oracle was
run. This does not establish quality parity.

The screening improvement is below the predeclared 5% useful-effect gate and
has only three paired blocks. No seven-pair confirmation is justified. Because
only 1.9% of routed entries were newly selected, this higher fraction does not
move enough work to qualify a serving gain. Keep the CPU-miss fallback and do
not promote the staged policy.

## Resources and artifacts

The campaign was supervised with the six-GiB physical-memory floor and
read-only clock sampling. Minimum available physical/admission memory was
17,407,037,440 bytes (16.21 GiB), above the floor; cgroup OOM counters remained
zero. GPU frequency was observed at 306 MHz; EMC readback was unavailable and
energy was not attributed. The run lasted 248.8 seconds. Raw configurations,
logs, residency maps, paired JSON and supervisor telemetry are retained beside
this report. The runner is [`run_max_offload_screen.py`](run_max_offload_screen.py).

This is an Orin-only result. It does not change the backend default or E6's
unmet performance exit. The same full-offload experiment at a 1,000-slot GPU
cache selected 226 entries (1.6%) and improved median client latency by only
0.72%; see the [1,000-slot screen](../2026-10-25-phase-e3-q2-ninfer-cache1k-max-offload/README.md).
