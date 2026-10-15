# Q2_0 64K retrieval and arithmetic quality check

Date: 2026-10-15, Orin AGX (aarch64, Jetson Linux 5.15.148-tegra), CUDA 12.6.
The Strata engine SHA-256 is
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`. The
model is the local Qwen3.8-Flash-Next-GSQ-RCO two-shard Q2_0 GGUF set, with its
matching PLE pack, tokenizer, expert profile and MTP runtime under
`~/models/strata-orin-validation`; model files are not copied into the repo.

At 65,536 configured context, the exact formatted prompt contained 60,079
reported tokens. The model returned three codes placed near 10%, 50% and 90%,
then computed their suffix sum:

```text
EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956, SUM=1971
```

The independent oracle extracted suffixes 731, 284 and 956, computed 1,971,
and verified each code appeared once and in order. A following short request on
the same service returned exactly `RECOVERED`. Both workload runner and oracle
passed. This extends the held-out retrieval-plus-arithmetic task from 32K to
one Q2_0 64K point; it does not establish a broad quality score.

The request used the existing accepted-only MTP4 Q2_0 profile with a 3 GiB VRAM
reserve, 3,000 expert slots, FP16 KV, eight pool workers and prompt cache
disabled. Under the 28-GiB cgroup limit, 2,205 one-second telemetry samples
covered 2,314.6 seconds. Minimum host/admission availability was 15.13/11.50
GiB; cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters stayed at zero.
GPU observations ranged from 306 MHz to 1,300.5 MHz. Engine prefill timing was
2,244.7 s at 26.8 tokens/s; 24/24 offered draft tokens were accepted. Energy
was not request-attributed, and EMC frequency readback was unavailable. No
clock controls were changed.

The first setup attempt failed before service startup because a copied harness
used the parent directory depth from its former nested location. It ran no
model request and is retained under `supervisor/`. The corrected retry is under
`supervisor-retry/` and `run-retry/`. Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-15-phase7-q2-quality-64k/supervisor-retry \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-15-phase7-q2-quality-64k/run_quality_task.py \
  --config bench/results/2026-10-15-phase7-q2-quality-64k/config-65536.json \
  --workload bench/results/2026-10-15-phase7-q2-quality-64k/workloads/workload-65536.json \
  --warmup-workload bench/results/2026-10-15-phase7-q2-quality-64k/warmup-512.json \
  --output bench/results/2026-10-15-phase7-q2-quality-64k/run-retry

python3 bench/results/2026-10-15-phase7-q2-quality-64k/review_arithmetic.py \
  bench/results/2026-10-15-phase7-q2-quality-64k/run-retry/result.json
```

The per-second memory sample stream is retained as gzip-compressed
`supervisor-retry/memory.jsonl.gz`; `SHA256SUMS.txt` covers the retained
artifacts. Phase 7 remains open for wider quality tasks and its remaining
service and support-matrix gates.
