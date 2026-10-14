# Q2_0 8K MTP task-quality check

This Phase 5 quality check used the same exact 8,192-token prompt that passed
the long-chain accepted-prefix comparison, now with a 512-token generation
allowance and MTP off/2/3/4. Each condition ran in a fresh service using the
current Q2_0 binary, 16K configured context, 3,000 expert-cache slots, FP16 KV
and `--adapt-every 4 --adapt-accepted-only`. All local model assets remained
under `~/models/`.

All four conditions stopped naturally at 311 completion tokens (264 words) and
returned byte-identical text (SHA256
`e3696ec3c492bc5595bf12883ca00bf08eb049e6c44745db90ac6f3d5a619366`). The
answer explained fetch/decode/execute, RAM, binary information, input/output
and durable storage, and exceeded 200 words. It failed the prompt's explicit
opening instruction: the response began “A computer processes information”
instead of starting with the processor. The same opening miss in all four
conditions is a shared task failure, not an MTP-specific difference. This
does not qualify the profile for this task.

Every 28-GiB supervisor passed with zero sampled cgroup pressure or OOM events.
Minimum host availability across the four services was 16.618 GiB and minimum
effective admission availability was 13.539 GiB. Clocks were observed without
changes; energy was not process-attributed. The measured elapsed times are
retained as observations only, not a paired performance comparison.

[`quality-analysis.json`](quality-analysis.json) contains each response hash,
rubric result and memory minimum; [`analyze_quality.py`](analyze_quality.py)
reproduces it. Raw API outputs, configs, engine logs and supervisor telemetry
are stored in each condition directory. The prompt and exact token IDs are
represented in the checked-in `workloads.json` and `prompt.tokens` files.

Reproduce by running the included `quality_api_driver.py` once per MTP config
under the same 28-GiB supervisor. For example:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-mtp8k-quality/mtp0/supervisor \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-14-phase5-q2-mtp8k-quality/quality_api_driver.py \
  --config bench/results/2026-10-14-phase5-q2-mtp8k-quality/config-mtp0.json \
  --workloads bench/results/2026-10-14-phase5-q2-mtp8k-quality/workloads.json \
  --cells quality-pp8192-512 \
  --output bench/results/2026-10-14-phase5-q2-mtp8k-quality/mtp0/results.json
```
