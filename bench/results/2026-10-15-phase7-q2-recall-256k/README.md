# Q2_0 256K near-limit retrieval and recovery

Date: 2026-10-15, Orin AGX (aarch64, Jetson Linux 5.15.148-tegra), CUDA 12.6,
Strata binary SHA-256
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
The model is the local two-shard Qwen3.8-Flash-Next-GSQ-RCO Q2_0 GGUF set,
with the matching PLE pack, expert profile, tokenizer and MTP runtime under
`~/models/strata-orin-validation`; model files are intentionally not copied to
this repository. This records the exact engine/config/workload digests below.

The experiment expanded the prior Q2_0 context ladder to the plan's 262,144
token configured limit. The exact formatted retrieval prompt was 240,286
reported tokens (target 240,299); the request asked for 48 output tokens and
returned 41. Three planted markers were returned exactly once and in order:
`MAPLE-ORBIT-731`, `COBALT-HARBOR-284`, `VELVET-COPPER-956`. A subsequent
same-service short request returned `RECOVERED`. The runner and supervisor both
reported pass. This is one long-context retrieval/recovery check, not broad
256K capacity or quality qualification.

The supervised service ran with a 28 GiB cgroup limit and the existing 3 GiB
workspace reserve. The monitor sampled once per second for 11,096 samples over
about 3 h 14 min. Minimum host and admission availability were both 7.31 GiB,
above the required 6 GiB host headroom. Peak monitored scope memory was 11.49
GiB; sampled cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters all
remained zero. GPU frequency observations ranged from 306 MHz to 1,300.5 MHz.
Energy attribution and EMC clock readback were unavailable; no clock controls
were changed. Retrieval prompt throughput was 20.8 tokens/s as reported by the
engine; its measured prompt time was 11,557.8 s. Do not compare this single run
as a performance claim.

Reproduction used `config-262144-mtp4.json` and
`workloads/workload-262144.json`, with the 512-token warmup from the 2026-10-14
Q2_0 recall artifact. The config sets accepted-only MTP4, 3,000 expert slots,
FP16 KV, an explicit 3 GiB VRAM reserve, eight pool workers, and no prompt
cache. The workload SHA-256 is
`359807f5b2712ed4b11b0a3c42f6d2649a58c130fcd5972999c32ace560cfbaf`; config
SHA-256 is `a015e36e4222e39b3d367cbbf272f045fab3d7f9cb4fc10fcbc9d743cf9fdc45`.
The supervisor's per-second raw memory samples are retained as
`supervisor/memory.jsonl.gz` (gzip-compressed from the original JSONL); clock
observations, tegrastats, engine log and request results are retained alongside.
See `SHA256SUMS.txt` for artifact digests.

Phase 7 remains open: sustained thermal equilibrium, cancellation, wider
quality tasks, other supported profiles and the plan's full service matrix are
not established by this case.
