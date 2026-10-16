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

## Run status

At the latest recorded check (16,162 seconds after request start), attempt 3
was still live at 139,776 of 240,286 prompt tokens. Minimum sampled available
host memory was 7.44 GiB, above the six-GiB floor; the latest memory sample was
8.21 GiB. From the 127,616-token sample 1,456 seconds earlier, the average rate
was about 8.35 tokens/s. Linear extrapolation puts prefill near 7 hours 48
minutes total, roughly twelve minutes inside the eight-hour cap. This estimate
varies with throughput and excludes warmup/recovery overhead. The leaf
supervisor scope used 8.17 GiB at the latest memory sample, and sampled `low`,
`high`, `max`, `oom` and `oom_kill` counters are all zero to date. Read-only clock samples so far show CPU 729.6 MHz–2,201.6 MHz and GPU
306 MHz–816 MHz; `tj` ranged 49.0–52.9 °C. EMC readback remains unavailable.
The profile uses dynamic clocks and does not attribute energy to this request.
The supervisor had not produced a terminal result. Retrieval markers, recovery,
final timing and telemetry summary are therefore pending; this is not a pass.

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

On completion, update this report with the terminal supervisor status, exact
marker and same-service recovery results, prompt/decode timings, actual memory
floor and cgroup counters, clocks and thermal observations. Until then, no
256K Coder support claim is made. Phase 7 remains open.
