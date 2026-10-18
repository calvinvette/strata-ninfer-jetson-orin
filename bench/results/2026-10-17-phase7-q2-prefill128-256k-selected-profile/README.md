# Q2_0 selected-profile 256K capacity, retrieval and recovery — Orin — 2026-10-18

The selected Phase 6 Q2_0 MTP-off profile completed one near-limit retrieval
and same-service recovery cell at 256K configured context. The uncached prompt
contained 240,286 actual tokens. The service returned all three planted markers
exactly once and in order, generated 41 tokens, and then returned `RECOVERED`
on the same service. The independent capacity reviewer passed the request,
profile, marker positions, recovery, 28-GiB scope and cgroup event checks.

This is the `Q2_0` variant from the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` snapshot
`5348543e0147355ac9cbcb031184a3546350988e`, not the separate IQ1_M run. The
model shards, PLE pack, expert profile and tokenizer remained under
`~/models/strata-orin-validation/`; shard and pack hashes are included in
[`artifacts.json`](artifacts.json), matching prior selected-profile reports.

The configuration matched the selected profile except for context: Q2_0 GGUF,
FP16 KV, MTP off, 262,144 context, 3,000 expert slots (3,955 MiB), prefill
chunk 128, eight workers, prompt cache disabled, adaptive swaps disabled,
3,072-MiB workspace reserve, memory-mapped experts, and 0.55 PCIe fraction.
The run used a 28-GiB cgroup limit and preserved the six-GiB physical
host/admission floor. Across 31,442 one-second memory samples, minimum host and
effective-admission availability were both 11.64 GiB. The cgroup recorded no
`low`, `high`, `max`, `oom` or `oom_kill` events. CPU and GPU clocks were sampled
read-only and varied dynamically; EMC readback was denied. No clock controls
were applied. Raw `tegrastats` rails are retained, but energy is not
process-attributed and is not used as an energy result.

Engine prefill time was 32,851.9 seconds (7.3 tokens/s); client retrieval time
was 32,861.9 seconds. The 41-token answer took about 9.7 seconds, and same-
service recovery took 4.3 seconds. The workload was synthetic multi-position
retrieval, not arithmetic or broad long-context quality testing. This is one
functional capacity point after two unsuccessful attempts (a short timeout and
a later supervisor signal 15), not a repeated performance result, 256K sustained-service qualification,
general support boundary, or comparison against another quantization or engine. The
long latency and missing process-energy attribution remain material limits.
Phase 7 remains open.

## Reproduction

Run from the repository root with the model and prepared PLE/profile files at
the paths already supplied in `config.json`:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output /tmp/q2-prefill128-256k-supervisor --timeout 36000 --interval 1 \
  --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-q2-prefill128/run_recall_case.py \
  --config bench/results/2026-10-17-phase7-q2-prefill128-256k-selected-profile/config.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-256k-selected-profile/workload.json \
  --warmup-workload bench/results/2026-10-17-phase7-q2-prefill128-256k-selected-profile/warmup-workload.json \
  --output /tmp/q2-prefill128-256k-run

python3 bench/results/2026-10-17-phase7-q2-prefill128-16k-selected-profile/review_capacity.py \
  --result /tmp/q2-prefill128-256k-run/result.json \
  --workload bench/results/2026-10-17-phase7-q2-prefill128-256k-selected-profile/workload.json \
  --supervisor /tmp/q2-prefill128-256k-supervisor/result.json \
  --memory /tmp/q2-prefill128-256k-supervisor/memory.jsonl \
  --context 262144 --output /tmp/q2-prefill128-256k-run/independent-review.json
```

The retained raw JSONL memory samples and `tegrastats` logs are gzip-compressed
to reduce repository size; decompress them before passing them to the reviewer.
`SHA256SUMS` covers the retained files. The successful request artifacts are in
`attempt3-run/` and its supervisor data is in `attempt3-supervisor/`; the prior
interrupted attempt is preserved in `attempt2-supervisor/`.
