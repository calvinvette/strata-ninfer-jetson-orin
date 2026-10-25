# Q2_0 NInfer staging at 1,000 resident slots

Date: 2026-10-25, Jetson AGX Orin, CUDA 12.6, SM87. This three-pair screen
reduces the GPU resident cache from 3,000 to 1,000 slots while retaining the
1-GiB pinned complement and selecting all eligible misses (`--pcie-frac 1.0`).
The matched control keeps the same 1,000-slot cache but uses CPU misses. This
tests whether lowering GPU residency exposes enough additional work for staged
NInfer execution to improve a short request.

## Fixed and verified controls

Both arms used the same current-source executable, Q2_0 model and PLE, 8K
context, 1,000 resident GPU slots, 1-GiB pinned complement, prefill 128,
eight workers, MTP-2 and the same 55-token prompt / 29-token response. The
control used `--pcie-frac 0`; the candidate used strict NInfer and
`--pcie-frac 1.0`. Each process ran one warmup and one measured request. All six
services had the same resident-map hash
`6a4a97bef0632a05576d4933ce48b0ea69c71f916926b641075f0e4f8fae548a`.
Randomized pair order used seed `20261025`.

## Results

| Pair | CPU-miss client total | NInfer staged client total | NInfer change | CPU TTFT | NInfer TTFT | NInfer change | Response hashes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 10.320 s | 10.265 s | −0.53% | 6.611 s | 6.582 s | −0.43% | match |
| 2 | 10.287 s | 10.213 s | −0.72% | 6.586 s | 6.566 s | −0.30% | match |
| 3 | 10.316 s | 10.202 s | −1.10% | 6.605 s | 6.557 s | −0.73% | match |

Median paired changes were −0.72% client latency and −0.43% TTFT. The staged
arm selected 226 additional expert entries per measured request (1.6% of
13,920 routed entries), below the 265 entries (1.9%) selected with 3,000 GPU
slots. All measured responses had the same hash as the CPU control and the
expected token count. No independent quality oracle was run.

Reducing residency did not increase staged coverage or produce a useful
latency gain. The observed effect is below the predeclared 5% threshold, so no
seven-pair confirmation or promotion follows. This short-request screen does
not establish behavior on longer outputs or other cache profiles.

## Resources and artifacts

The run used `run_control.py` with the six-GiB physical floor, read-only clock
sampling and no clock control. Minimum available physical/admission memory was
19,607,093,248 bytes (18.26 GiB); cgroup OOM counters were zero. GPU frequency
was observed at 306 MHz; EMC frequency was unavailable and energy was not
attributed. The supervised campaign lasted 242.3 seconds. The runner,
per-process configs, logs, residency maps, paired results and supervisor
telemetry are retained here. Models remain under `~/models/`.

This is a bounded Orin screening result. It changes no default and does not
close E6's performance exit.
