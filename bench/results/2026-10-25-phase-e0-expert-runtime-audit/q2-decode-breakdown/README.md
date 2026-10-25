# Q2_0 decode-phase timing screen

Date: 2026-10-25. Host: Jetson AGX Orin, aarch64, CUDA 12.6, SM87. This
screen adds request-phase timing for the exact Q2_0 artifact used in the E2
backend comparison. It is one diagnostic pair, not a new performance estimate.

## Paired setup

Both arms used the same Release binary (`strata` SHA256
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`), Q2_0
model and PLE shard, deployment pack, tokenizer, expert profile, 8K context,
3,000 profile-filled expert slots, FP16 KV, prefill 128, eight pool workers,
`--spec 2 --suffix-draft 0`, mmap expert source, and `--pcie-frac 0.55`. The
NInfer arm added `--expert-backend ninfer --expert-backend-strict`. Each fresh
service ran one warmup and one measured request (`1+1`, temperature 0,
max_tokens 48); the measured completion was 29 tokens. `STRATA_DECODE_TIMING=1`
was enabled in both arms and `STRATA_RESIDENT_HEADROOM_GIB=9` preserved the
required 6 GiB physical headroom plus the separate 3 GiB reserve. Both service
startup logs reported 6,144 MiB physical RAM headroom and about 18 GiB shared
RAM available after loading.

The actual startup residency CSV hashes match:
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`.
Measured output SHA256 also matches:
`18e649c52e8a6a942bfb6c486a4da267fc7ca05faaf55c831ea4b35372df848e`.
Draft counters were zero in both runs. The engine logged the NInfer dispatch in
the candidate. GPU cache hit rates were 57.2% (7,968/13,920) for Strata and
57.4% (7,994/13,920) for NInfer; these are close but not identical route counts.

## Measured request

| Decode window component | Strata | NInfer | Units / interpretation |
| --- | ---: | ---: | --- |
| Verifier window | 103.36 | 109.79 | ms per 1-token window |
| GPU-reach wait | 33.08 | 40.28 | ms/window; wait time, not expert-kernel time |
| Per-layer host work | 66.35 | 65.52 | ms/window |
| └ plan, activation quantization, job setup | 46.01 | 45.37 | ms/window combined |
| └ CPU expert work | 19.88 | 19.67 | ms/window |
| Host staging | 0.02 | 0.02 | ms/window |
| Commit/emit | 0.04 | 0.04 | ms/window |
| Decode rate | 9.1 | 8.6 | tokens/s, engine request summary |
| Client TTFT | 6.102 | 6.034 | seconds, first visible text |
| Client total | 9.191 | 9.298 | seconds |

The warmup request is retained in the raw logs but excluded above. This single
pair had almost unchanged host CPU expert time and job setup, while verifier
wait was about 7.2 ms/window higher for NInfer. It does not isolate GPU expert
kernel time from all other GPU work. The separate E2 operator test directly
measured the current NInfer grouped Q2_0 operator at about 3.5x the Strata
operator latency. Together, these measurements explain why the current resident
substitution has no demonstrated request benefit: it leaves CPU misses intact,
adds slower grouped GPU work, and the remaining window time includes waits and
other GPU work. These are diagnostics, not a speedup ceiling; cache-hit counts
are not time fractions, and overlapping work cannot be summed into a wall-time
budget.

The one-pair client latency observation differs from the three-pair E2 screen's
median result and is not a contradiction: neither individual pair can override
the small randomized screen. The three-pair median remained +3.4% prompt,
+7.3% decode, +4.4% client total and +3.5% TTFT latency for NInfer.

## Limits and files

This is one pair with the timing instrumentation enabled, not a seven-block
confirmation or an instrumentation-neutrality test. No `nsys` capture was made
for this Q2_0 pair, so resident GPU kernel and dense-projection request sums
remain unavailable; the existing E0 Nsight report is for Coder IQ1_M and is
not transferred to this model. Orin GPU clock readback and energy were
unavailable. The logged `files ... MB read` counter is the engine's file-expert
counter, not an independent physical-NVMe measurement. On Orin the `pcie_frac`
setting/counter does not indicate a discrete PCIe transfer.

Raw request/engine JSON, logs and map files are in this directory. The
reproduction used the E2 runner's `start_one` routine with
`STRATA_DECODE_TIMING=1`, headroom 9 GiB, a fresh port and a separate output
directory; `run.jsonl` records both requests and identities.
