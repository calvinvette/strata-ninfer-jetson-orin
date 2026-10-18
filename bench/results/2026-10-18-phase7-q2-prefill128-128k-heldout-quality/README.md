# Q2_0 selected-profile 128K held-out retrieval, arithmetic and recovery — Orin — 2026-10-18

The selected Phase 6 Q2_0 MTP-off profile passed one held-out 128K retrieval-
plus-arithmetic task and same-service recovery. The independently tokenized,
uncached prompt contained 120,141 tokens. It placed three new codes at 10%, 50%
and 90% of the prompt. The service returned them exactly once and in order and
reported `SUM=1980`. An independent suffix oracle computed
`417 + 638 + 925 = 1980`; a separate capacity reviewer verified the configured
context, actual prompt count, runtime settings, memory guard, and cgroup events.
The same service then returned `RECOVERED`.

The model was Q2_0 from the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` snapshot
`5348543e0147355ac9cbcb031184a3546350988e`. The configuration was Q2_0 GGUF,
FP16 KV, MTP off, 131,072 context, 3,000 expert slots (3,955 MiB), prefill
chunk 128, eight workers, prompt cache disabled, adaptive swaps disabled and a
3,072-MiB workspace reserve. Model shards, PLE pack, expert profile and
tokenizer remained under `~/models/strata-orin-validation/`; hashes and
source revisions are in [`artifacts.json`](artifacts.json).

The request ran under `MemoryMax=28G` and the six-GiB physical host/admission
guard. Across 5,528 one-second supervisor samples, minimum host availability
was 14.64 GiB and minimum effective-admission availability was 11.41 GiB.
Maximum observed cgroup use was 16.59 GiB; `low`, `high`, `max`, `oom` and
`oom_kill` event counters stayed zero. Engine prefill took 5,751.5 seconds at
20.9 tokens/s. The client retrieval request took 5,761.4 seconds; it generated
47 tokens at 4.9 tokens/s. Same-service recovery took 4.4 seconds.

CPU clocks ranged from 729.6 to 2,201.6 MHz, GPU clocks from 306 to 1,300.5
MHz, and `tj` from 46.906 to 55.75 °C. EMC clock readback was denied. No clock
controls were applied. Raw `tegrastats` rail readings are retained, but energy
is not process-attributed. This is one synthetic task and one profile cell,
not a broad quality score, repeated performance result or general 128K support
claim. The first launch attempt failed before starting a model because its
runner path was wrong; it is retained in `supervisor/`. The successful measured
run is in `attempt2-run/` and `attempt2-supervisor/`. Phase 7 remains open.

## Reproduction

Run from the repository root with the model and prepared PLE/profile files at
the paths in `config.json`:

```sh
python3 bench/results/2026-10-18-phase7-q2-prefill128-128k-heldout-quality/prepare_workload.py \
  --tokenizer /home/calvin/models/strata-orin-validation/pack/tokenizer \
  --output /tmp/q2-128k-workload.json

python3 bench/results/2026-10-18-phase7-q2-prefill128-128k-heldout-quality/review_workload.py \
  --workload /tmp/q2-128k-workload.json \
  --tokenizer /home/calvin/models/strata-orin-validation/pack/tokenizer

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-128k-quality-supervisor --timeout 21600 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-15-phase7-q2-quality-64k/run_quality_task.py \
  --config bench/results/2026-10-18-phase7-q2-prefill128-128k-heldout-quality/config.json \
  --workload /tmp/q2-128k-workload.json \
  --warmup-workload bench/results/2026-10-18-phase7-q2-prefill128-128k-heldout-quality/warmup-workload.json \
  --output /tmp/q2-128k-quality-run

python3 bench/results/2026-10-15-phase7-q2-quality-64k/review_arithmetic.py \
  /tmp/q2-128k-quality-run/result.json
python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-128k-quality-run/result.json \
  --workload /tmp/q2-128k-workload.json \
  --supervisor /tmp/q2-128k-quality-supervisor/result.json \
  --memory /tmp/q2-128k-quality-supervisor/memory.jsonl \
  --context 131072 --output /tmp/q2-128k-quality-run/independent-review.json
```

The run's raw memory JSONL and `tegrastats` logs are gzip-compressed in the
retained results directory; decompress them before passing them to reviewers.
`SHA256SUMS` covers the retained artifacts.
