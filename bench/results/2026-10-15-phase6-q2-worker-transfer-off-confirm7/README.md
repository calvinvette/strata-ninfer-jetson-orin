# Q2_0 MTP-model-off worker × expert-transfer confirmation — Orin — 2026-10-15

This seven-block randomized, held-out confirmation compared four and eight CPU
pool workers with mapped expert reads and asynchronous `pread` on a distinct
512-token retrieval-plus-arithmetic task. Each of the 28 cells used a fresh
service and one measured request after a separate exact-512-token warmup. The
services used the local Strata Q2_0 model shards and PLE pack, 8,192 context,
3,000 requested expert-cache slots, prefill chunks of 512, and 48 allowed
generated tokens. The two native GGUF shard hashes match the existing
Q2_0/Orin-validation artifact identity recorded in
[`2026-10-11-phase3-q2-actual32k`](../2026-10-11-phase3-q2-actual32k/artifact-identities.json).

The Q2 pack requires `--spec 2` for its verifier window. The measured service
configuration contains that option but has no `--mtp` model path or
`--mtp-max-t` option; MTP drafting was therefore disabled. The output naturally
stopped at 46 tokens in every cell. All 28 requests returned the three planted
codes exactly once and in order, plus the correct suffix sum `1428`. Output
hashes and actual expert-cache capacity matched across every cell. The prompt
and independent suffix oracle are retained in `workload/`.

| Workers / transfer | Samples | Median prompt time | Median decode time | Median request time |
| --- | ---: | ---: | ---: | ---: |
| 4 / mapped | 7 | 18,881 ms | 10,035 ms | 30,129 ms |
| 8 / mapped | 7 | 17,447 ms | 8,321 ms | 25,507 ms |
| 4 / pread | 7 | 15,189 ms | 13,304 ms | 29,062 ms |
| 8 / pread | 7 | 15,812 ms | 17,071 ms | 32,774 ms |

Paired contrasts use request time over seven blocks. Intervals are bootstrap
95% intervals for the median:

| Contrast | Median delta | 95% interval | Reading |
| --- | ---: | ---: | --- |
| 4 vs 8 workers, mapped | +17.37% | +9.22% to +21.50% | Four workers were slower in all paired blocks. |
| 4 vs 8 workers, pread | −19.45% | −33.08% to +6.85% | Interval includes no worker effect. |
| pread vs mapped, 4 workers | −11.22% | −14.79% to +14.21% | Interval includes no transfer effect. |
| pread vs mapped, 8 workers | +29.13% | −0.40% to +91.06% | Wide interval; no reliable transfer effect. |
| Worker × transfer difference-in-differences | −43.60 percentage points | −77.21 to −19.39 | The measured transfer effect differed by worker count. |

This is evidence of an interaction on this task, not a default recommendation:
the interaction is imprecise, and the transfer contrasts at either fixed worker
count include no change. Shared page-cache history across sequential services
also prevents a cold-storage or physical disk-read conclusion. The screen is
timing-only (API output/cache checks; no accepted-prefix trace), and it does not
qualify a broader quality or concurrency profile. Energy was not attributed to
individual requests.

The current candidate executable had SHA256
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`, built from
Strata source commit `b99b26a2`. The experiment ran in a 28-GiB systemd scope
with dynamic, read-only clocks and the six-GiB admission guard. Across 2,453
supervisor samples, minimum host availability was 17.34 GiB and minimum
effective admission availability was 6.46 GiB. Maximum sampled cgroup use was
21.77 GiB; `high`, `max`, `oom`, and `oom_kill` counters stayed zero. Tegrastats
junction temperature ranged from 50.2 to 56.9 °C. EMC frequency readback was
denied; no clocks were changed.

The initial setup attempt in `setup-failure/` is retained but excluded: it
omitted the pack-required `--spec 2`, so all 28 services exited before
measurement. The corrected configuration adds only the verifier-window option
and keeps the MTP model absent. Its full 28-cell run passed.

Reproduce the measured screen from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/supervisor \
    --timeout 5400 --interval 1 --sample-clocks -- \
    python3 tools/integration/pool_worker_screen.py \
      --config bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/config-mtp-off.json \
      --workloads bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/workload/workloads.json \
      --output bench/results/2026-10-15-phase6-q2-worker-transfer-off-confirm7/screen \
      --workers 4 8 --transfer-modes mapped pread --io-threads 8 \
      --repetitions 7 --seed 2026101515 --baseline-workers 8 --timing-only
```

Raw randomized orders, per-request API responses, server configurations,
engine logs, supervisor memory samples, and tegrastats are retained here.
`SHA256SUMS.txt` covers all result files except itself. This adds one held-out
MTP-model-off worker × transfer interaction result; Phase 6 remains open for
other factors and workloads.
