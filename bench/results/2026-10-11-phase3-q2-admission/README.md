# Q2_0 model cache × context admission screen — Orin — 2026-10-11

This randomized four-cell screen runs the downloaded Q2_0 Coder model through
Strata's current native path. It crosses 3,000/5,000 expert-cache slots with
4,096/8,192 maximum context. Each fresh process loads the Q2_0 pack and native
shards, uses the matching Q2 expert profile, reads the prepared 512-token
`pp512+tg64` prompt, and greedily emits one token with `--spec 2`. MTP is not
enabled. Prompt cache is disabled. The existing three-GiB workspace reserve is
unchanged, and the supervisor preserves the six-GiB `MemAvailable` floor.

All four corrected cells passed and emitted token ID 32. Minimum physical
availability ranged from 15.88 to 18.52 GiB. The runtime reported exactly 3,000
or 5,000 actual cache slots, corresponding to 3.86 or 6.44 GiB of shared RAM
allocated to the GPU. Doubling context increased the requested session-state
backing from 235,034,112 to 343,102,976 bytes (108,068,864 bytes). The owner
summarizer counted unique live allocation identities: peak device requests were
4,427,958,528–4,536,043,776 bytes at 3,000 slots and
7,192,758,528–7,300,843,776 bytes at 5,000; host pinned/pageable owners peaked
at 354,389,880 bytes. Each log had 276 allocations and 276 frees, with zero
observed live owner bytes at process end. These observed owner totals exclude
graph executable/driver pools and uninstrumented allocations. They are not
added to host `MemAvailable`, which remains the single physical-memory authority.

The first `--spec 1` attempt failed at native-pack preflight because this path
requires `--spec T` with `T >= 2`; it did not enter model execution. The failed
preflight is retained in `cache3000-ctx4096/supervisor/`. The four corrected
runs are in each cell's `retry/supervisor/`. The randomized order, commands,
engine digest and per-cell summary are in [`campaign.json`](campaign.json) and
[`analysis.json`](analysis.json). Model shard identities and local pack/profile
checksums are in [`artifact-identities.json`](artifact-identities.json).

This is admission evidence for one Q2_0 model, one prompt and one generated
token. It is not a quality or performance comparison and does not establish a
supported capacity limit. It adds a real-model Q2_0 point to the earlier
IQ1_M cache/context work; broader pressure and graph memory attribution remain
open.
