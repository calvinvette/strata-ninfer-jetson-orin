# Q2_0 16K prompt: pageable versus pinned expert staging — Orin — 2026-10-13

This randomized three-pair Phase 3 screen compared the existing pageable and
opt-in pinned expert-stage buffers on an exact 16,384-token Q2_0 prompt with
eight output tokens. Each fresh process used the same candidate binary, 3,000
expert slots, FP16 KV, eight-worker asynchronous prefetch, `prefill 512`,
`spec 2`, a 16,424-token context reservation, and a six-slot prompt cache.
CPU prefill sharing was disabled in both arms. Model files remained under
`~/models/strata-orin-validation/`.

All six requests passed the six-GiB supervisor. Each randomized pair matched
all eight output token IDs and all nine recorded persistent-state fields. The
same final state was observed in every arm. Each process recorded 304
allocations and 303 frees, with the service-lifetime weight arena as the only
requested-live device owner at log end. The stage owner requested exactly
353,894,400 bytes (337.5 MiB) in each arm and recorded 256 allocations and 256
frees. This owner trace is requested payload accounting; graph-pool and
unobserved driver backing are outside it.

Pinned-minus-pageable paired median request-time delta was −2.56%; the
three-pair bootstrap percentile interval was −23.13% to −1.53%. Pair deltas
were −2.56%, −1.53% and −23.13%. Prompt-time delta was −2.58% (interval
−23.21% to −1.47%), and decode-time delta was −4.19% (interval −19.64% to
−1.60%). The third pageable arm was much slower than its pinned mate and the
other pageable runs, so these three pairs are screening evidence only. CPU/GPU
clocks were dynamic and energy was not measured. No default or staging policy
changed; a seven-pair confirmation is needed before deciding whether this
signal persists on a held-out 16K prompt.

The `MemoryMax=28G` supervisor measured minimum host availability of
18,707,402,752 bytes (17.423 GiB) and minimum effective cgroup headroom of
9,391,964,160 bytes (8.747 GiB). OOM and OOM-kill counters were zero. Raw
results, all six owner traces, per-arm configurations, exact workload identity,
and supervisor telemetry are retained. Local engine logs are ignored by Git;
their hashes are in `SHA256SUMS.txt`.
