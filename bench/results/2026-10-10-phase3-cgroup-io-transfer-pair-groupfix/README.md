# Scoped-I/O cache-capacity mismatch attempt — Orin — 2026-10-10

The systemd scope and user/device-group setup worked and produced leaf-cgroup
read counters for one mapped/pread pair. However, requesting 5,000 expert-cache
units resulted in 6,519 mapped slots and 6,187 pread slots. Output token IDs
matched but six persistent-state fingerprints differed. Since resident cache
capacity was not held equal, this pair is invalid for a transfer comparison and
was excluded. Minimum host `MemAvailable` was 8,747,409,408 bytes.

This exposed that the CLI value is a lower bound, not an exact capacity. The
transfer harness now records effective slots and fails pairs where actual
capacity differs. A rerun requesting 3,000 selected 3,903 slots in both arms
and passed token/state parity; see the
[one-pair capacity-controlled pilot](../2026-10-10-phase3-cgroup-io-transfer-pair-cache3000/README.md)
and the later [seven-pair confirmation](../2026-10-10-phase3-transfer-cgroupio-confirmation7/README.md).
