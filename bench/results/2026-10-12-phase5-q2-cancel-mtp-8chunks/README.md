# Preliminary MTP cancellation attempt — excluded

This diagnostic run was accidentally started without the standard cgroup
supervisor. It canceled an MTP-enabled stream after eight visible deltas (11
committed tokens) and passed same-service recovery. It was interrupted before
its three-reference comparison finished; its orphaned reference server was
terminated. Do not use this run for memory admission or state-parity claims.

The authoritative supervised rerun and complete reference comparisons are in
[`2026-10-12-phase5-q2-cancel-mtp-8chunks-supervised`](../2026-10-12-phase5-q2-cancel-mtp-8chunks-supervised/README.md).
