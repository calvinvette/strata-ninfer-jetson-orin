# Q2_0 automatic expert-cache allocation retry — Orin — 2026-10-12

Three fresh Q2_0 processes passed the supervised 512-token prompt plus one
greedy token at a 64K context reservation after the first automatic
expert-cache allocation was injected to fail. Each runtime recorded one
smaller-cache retry, loaded the profile, and completed with output token ID 32.
Retry capacities were 8,082, 6,626 and 8,043 slots, reflecting the memory
available when the failed request was retried; these are observations, not a
capacity threshold. Minimum host `MemAvailable` was 10.27, 12.33 and 10.48 GiB.
All runs stayed above the six-GiB floor and recorded no OOM kill.

Each owner ledger balanced 278 allocation/free events and returned to zero
requested live bytes at process exit. The first run’s requested device payload
peaked at 14,560,200,448 bytes across observed owners; its expert-cache owner
requested 11,172,556,800 bytes (8,082 slots). Pageable expert staging peaked
at 353,894,400 requested host bytes. These are instrumented request payloads, not a complete physical
memory ledger; graph-pool and driver-private backing are excluded. This
qualifies the existing simulated refusal/retry path for this Q2_0 workload,
not recovery from a physical CUDA OOM or a general cache-capacity limit.

The model is the local Qwen3.8 Flash-Next Q2_0 two-shard GGUF and Q2 PLE pack;
all model files remain under `~/models`. The launch command and exact supervisor telemetry are in `supervisor/`,
`repeat2/` and `repeat3/`, with corresponding owner summaries alongside them. Dynamic clocks were observed without control; energy was
not measured.
