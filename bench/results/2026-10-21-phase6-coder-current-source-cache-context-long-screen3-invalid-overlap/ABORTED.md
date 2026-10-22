# Invalid prefill cell: overlapping model checksum read

The 1,500/3,000 cache × 8K/16K long-prompt screen was stopped in its first
cell after the supervisor observed 5.78 GiB available host memory, below the
required 6-GiB floor. The cgroup recorded no `high`, `max`, OOM, or OOM-kill
events. During that run, an agent-started checksum helper used `Path.read_bytes`
on the two roughly 29-GB GGUF shards, creating a large concurrent memory
consumer outside the supervised cell. The recorded floor breach is therefore
confounded and this cell is not evidence that the 3,000 cache is infeasible.
The incomplete request and telemetry are retained here and excluded from all
analysis. The checksum helper was terminated; available memory recovered to
28 GiB before any rerun. The rerun uses the already recorded shard hashes and
will not read model files during measurement.
