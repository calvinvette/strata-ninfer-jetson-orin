# Q2_0 automatic expert-cache allocation retry — Orin — 2026-10-12

The current Q2_0 candidate passed a supervised 512-token prompt plus one
greedy token at a 64K context reservation after the first automatic
expert-cache allocation was injected to fail. The runtime reduced its proposed
cache from 10,776 to 8,082 slots, recorded one smaller-cache retry, loaded the
profile, and completed the request with output token ID 32. The six-GiB
supervisor passed with minimum host `MemAvailable` of 11,023,073,280 bytes
(10.27 GiB); no OOM kill was recorded.

The owner parser counted 278 allocation and 278 free events. Requested device
payload peaked at 14,560,200,448 bytes across observed owners and returned to
zero at process exit; the expert-cache owner itself requested 11,172,556,800
bytes (8,082 slots). Pageable expert staging peaked at 353,894,400 requested
host bytes. These are instrumented request payloads, not a complete physical
memory ledger; graph-pool and driver-private backing are excluded. This
qualifies the existing simulated refusal/retry path for this Q2_0 workload,
not recovery from a physical CUDA OOM or a general cache-capacity limit.

The model is the local Qwen3.8 Flash-Next Q2_0 two-shard GGUF and Q2 PLE pack;
all model files remain under `~/models`. The launch command and exact
supervisor telemetry are in `supervisor/`, with owner attribution in
`owner-summary.json`. Dynamic clocks were observed without control; energy was
not measured.
