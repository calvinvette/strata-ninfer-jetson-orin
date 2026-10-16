# Current-source Coder IQ1_M 256K retrieval and recovery — Orin — 2026-10-15

This Phase 7 test uses the `IQ1_M` variant from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned to Hugging Face
snapshot revision `5348543e0147355ac9cbcb031184a3546350988e`. The two model
shards have the same SHA256 identities as the prior Coder IQ1_M checks:

```text
e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad  Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf
316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113  Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf
```

The request workload contains 240,286 formatted prompt tokens at a configured
262,144-token context. It runs the current candidate binary with Q6_K
warp-dequant, accepted-only MTP4, FP16 KV, 3,000 requested expert-cache slots,
eight workers, adaptive routing cadence four and prefill chunk 128. The model
and MTP files remain under `~/models/strata-orin-validation/`. The candidate
binary SHA256 is `57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
This is a context/retrieval test of one model quantization, not a comparison
between quantizations or inference engines.

## Result

Attempt 3 completed within the eight-hour supervisor limit. The harness passed
the 240,286-token retrieval request: all three planted codes were present once
and in order (`MAPLE-ORBIT-731`, `COBALT-HARBOR-284`,
`VELVET-COPPER-956`). The same service then returned `RECOVERED`. This is one
successful 256K functional cell, not a broad support claim or a comparison
between model quantizations or engines.

The uncached retrieval took 28,300.1 seconds (7 h 51 min 40 s); engine timing
reported 8.5 prompt tokens/s and 9.1 generated tokens/s. It generated 41
tokens, with 29 of 33 MTP drafts accepted. The recovery request took 2.38 s
and accepted all 3 of 3 drafts. Total supervisor elapsed time, including
startup and recovery, was 28,366.7 seconds; command exit was 0. The supervisor
status `pass` means the command completed under the memory floor, while the
harness `pass` records the retrieval and recovery checks.

Across 27,042 one-second memory samples, minimum host and admission availability
was 7.44 GiB, above the six-GiB floor. All observed cgroup `low`, `high`, `max`,
`oom` and `oom_kill` event counters remained zero. Read-only clock samples
recorded CPU frequencies from 729.6 to 2,201.6 MHz and GPU frequencies from 306
to 1,300.5 MHz; EMC frequency readback was denied. Across 28,196 tegrastats
samples, `tj` ranged from 49.0 to 56.4 °C. Clocks remained dynamic and
untouched. Energy was not attributed to the request; raw tegrastats power rails
are retained. The full one-second memory sample log is compressed as
`supervisor-attempt3/memory.jsonl.gz`.

Two earlier attempts are retained but excluded from quality and capacity
results. Attempt 1 used prefill chunk 64; its last progress sample was 1,280
prompt tokens at 238 seconds. Attempt 2 used chunk 128; its last progress
sample was 2,048 prompt tokens at 160 seconds. Both were intentionally
interrupted after projecting beyond their five-hour supervisor limit. Attempt
3 uses the chunk-128 configuration with an eight-hour supervisor limit. The
partial pilot outputs are not completed request results.

The active run is in `run-attempt3/` with telemetry in `supervisor-attempt3/`.
Input identities are:

```text
bedfd651f76b67198cd87e1ce8566f42f7f7a3a07c64cd3632f115a54c9f55c2  config-262144-prefill128.json
359807f5b2712ed4b11b0a3c42f6d2649a58c130fcd5972999c32ace560cfbaf  workloads/workload-262144.json
050fd0a48216aaf5fe6765993987b17c7ba8f674b3f125f1f44d175489a797aa  warmup-512.json
```

The supervisor memory log, raw tegrastats observations, request artifacts,
configuration, model hashes and binary identity are retained here. Phase 7
remains open for independent repetitions, broader task quality, sustained
service, concurrency and other support boundaries; this result does not
establish those properties.
