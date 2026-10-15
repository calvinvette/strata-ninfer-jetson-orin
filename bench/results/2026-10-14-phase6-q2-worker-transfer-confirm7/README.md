# Q2_0 MTP4 worker × expert-transfer held-out confirmation — Orin — 2026-10-14

This seven-block randomized confirmation compared pool workers 4 and 8 with
mapped expert reads and asynchronous pread on a held-out retrieval-plus-
arithmetic task. Each of the 28 cells used a fresh service, a separate exact-
length 512-token warmup, a 512-token measured prompt, 8,192 configured
context, 3,000 requested expert-cache slots, MTP4 (`--mtp-max-t 4`), and a
48-token generation allowance. MTP drafted 25 tokens and accepted 22 in every
measured response, which naturally stopped after 47 output tokens. The worker
and transfer effects are conditional on this MTP4 configuration, not MTP off.

All 28 requests returned exactly
`EARLY=AMBER-QUARTZ-618, MIDDLE=SILVER-MEADOW-243, LATE=INDIGO-LANTERN-907, SUM=1768`.
The codes occurred once near 14.8%, 48.0% and 81.1% of the rendered prompt;
an independent suffix calculation gives `618 + 243 + 907 = 1768`. Output
hashes and actual cache capacity matched across every cell.

| Worker/transfer condition | Samples | Median prompt time | Median decode time | Median request time |
| --- | ---: | ---: | ---: | ---: |
| 4 / mapped | 7 | 20,130 ms | 10,217 ms | 30,347 ms |
| 8 / mapped | 7 | 20,184 ms | 8,631 ms | 28,968 ms |
| 4 / pread | 7 | 15,480 ms | 10,257 ms | 26,000 ms |
| 8 / pread | 7 | 15,944 ms | 12,611 ms | 28,727 ms |

Paired effects (seven independent blocks; bootstrap 95% interval for the
median) were:

| Contrast | Median delta | 95% interval | Interpretation for this workload |
| --- | ---: | ---: | --- |
| 4 versus 8 workers with mapped reads | +4.38% request time | +3.66% to +7.06% | Four workers were slower in all blocks. |
| 4 versus 8 workers with pread | −15.25% request time | −19.55% to +13.24% | Wide interval; no reliable worker effect. |
| pread versus mapped at 4 workers | −15.82% request time | −19.55% to −9.92% | Pread was faster in this tested cell. |
| pread versus mapped at 8 workers | +1.35% request time | −11.11% to +10.08% | Interval includes no change. |
| Worker × transfer difference-in-differences | −20.00 percentage points | −25.96 to +7.57 | Interaction interval includes no change. |

The 4-worker/pread condition had one 44.3-second request outlier; its cause is
unknown. The interaction interval spans zero despite the lower pread median at
four workers, and the 8-worker pread comparison is inconclusive. This supports
only the measured 4-worker/pread cell on this Q2_0/MTP4 prompt and setup. It does not
justify a general worker or transfer default. Page-cache history was shared
across sequential cells, so this does not establish a cold-storage or physical
disk-read advantage. Energy was not request-attributed.

All 28 cells passed under a 28-GiB systemd scope. Minimum host availability
was 16.70 GiB and minimum effective admission availability was 6.91 GiB; all
sampled cgroup pressure, limit and OOM counters stayed zero. Tegrastats
reported junction temperature from 51.6 to 58.3 °C. CPU/GPU clocks were
dynamic; EMC frequency was not available. The candidate executable SHA256 was
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`, and the
workload JSON SHA256 is recorded in `workload/prepared.json`. Model and pack
assets remained under `~/models/`.

The three-block screen that motivated this confirmation was inconclusive; see
[`2026-10-12-phase6-q2-worker-transfer-rerun`](../2026-10-12-phase6-q2-worker-transfer-rerun/README.md).
This report retains both pilot runs and their supervisors. The first pilot
strictly required 48 generated tokens and was marked incomplete when the model
returned the correct 47-token natural-stop answer. The corrected workload
allows natural stop and passed two pilot requests; these pilot cells are not
included in the seven-block timing estimates. The seven-block campaign, all
per-cell API/engine records, randomized orders, memory samples and tegrastats
are in [`confirm7/`](confirm7/). `SHA256SUMS.txt` covers all result artifacts.

Reproduce the confirmation from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output confirm7-supervisor --timeout 5400 --interval 1 --sample-clocks -- \
    python3 tools/integration/pool_worker_screen.py \
      --config bench/results/2026-10-14-phase6-q2-mtp8k-window-screen-final/config-no-adapt.json \
      --workloads bench/results/2026-10-14-phase6-q2-worker-transfer-confirm7/workload/workloads.json \
      --output confirm7 --workers 4 8 --transfer-modes mapped pread \
      --io-threads 8 --repetitions 7 --seed 2026101419 \
      --baseline-workers 8 --timing-only
```

This completes one held-out worker × transfer confirmation for the stated
Q2_0/MTP4 task, but Phase 6 remains open for other factor interactions,
workload domains and MTP-off confirmation. Phase 5 state/graph limits and
Phase 7 support qualification also remain open.
