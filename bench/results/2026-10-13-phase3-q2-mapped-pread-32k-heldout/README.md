# Q2_0 32K mapped reads versus pread held-out confirmation — Orin — 2026-10-13

This seven-pair confirmation compared bounded mapped expert reads with
asynchronous `pread` on a distinct exact 32,768-token `heldout_blue` prompt
with eight generated tokens. It used the Q2_0 Qwen3.8-Flash-Next model, dense
PLE pack, same candidate binary, 3,000-slot expert cache, 32,808-token context
reservation, eight I/O workers, and disabled host staging in all arms. Model
artifacts remain in `~/models/strata-orin-validation/`; artifact revision,
shard checksums and candidate identity are recorded in the [16K transfer
report](../2026-10-13-phase3-q2-mapped-pread-16k-heldout/README.md). The exact
formatted prompt, IDs and tokenizer hashes are in [`prompt.json`](prompt.json),
and the base settings are in [`base-config.json`](base-config.json).

All seven randomized pairs passed. Generated IDs, actual cache slots, and all
nine persistent-state fingerprints matched in every pair. Median total request
time was 172.811 s mapped and 170.875 s pread. Pread's paired median delta was
−1.12%, but the bootstrap 95% interval ranged from −1.58% to +16.23% because
two pairs reversed by about 16–17%. Prompt-time delta was −0.99% with a
−1.72% to +16.35% interval; decode-time delta was −1.01% with a −4.64% to
+5.98% interval. The result does not qualify a reliable end-to-end benefit, so
keep mapped as the default.

Median process major faults were 270,366 mapped versus 4,126 pread; the paired
median ratio effect was −98.12%. Whole-device NVMe reads had a 14.81 GB mapped
median and 10.41 GB pread median (paired median ratio effect −31.50%). Device
reads include unrelated host activity and kernel readahead. The page cache was
not flushed, so these are shared warm-cache observations, not cold storage
results. Process and cgroup byte counters were unavailable. Fault and device
read differences do not substitute for request latency or establish a general
transfer win.

The campaign ran in a user systemd scope with `MemoryMax=28G`, `IOAccounting=yes`
and the independent six-GiB admission floor. It completed in 2,836.3 seconds;
minimum host availability was 17.17 GiB, minimum effective scope headroom was
7.70 GiB, and OOM-kill counters remained zero. CPU clocks varied from 729 to
2,201 MHz; GPU and EMC request clock readbacks were unsupported in this run.
No clocks were changed. Whole-board rail energy estimates include unrelated
activity, are not additive or process-attributed, and do not establish energy
per request. Full per-arm results and raw tegrastats samples are retained in
`experiment-7pairs/`; supervisor samples and terminal records are in
`supervisor/`. Engine logs are ignored by Git and their hashes are recorded in
[`ENGINE_LOG_SHA256.txt`](ENGINE_LOG_SHA256.txt).

[`analyze.py`](analyze.py) recomputes paired effects, counters, clocks and
headroom; [`analysis.json`](analysis.json) is its output. This held-out cell
confirms that the earlier three-pair 32K screen is inconclusive, not that the
transfer policies are equivalent across prompt lengths, cache sizes or storage
conditions. No transfer default changed.
