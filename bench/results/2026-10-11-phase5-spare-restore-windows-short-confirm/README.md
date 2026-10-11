# MTP accepted-prefix state confirmation — Orin — 2026-10-11

The rebuilt candidate ran the same 512-token prompt for eight output tokens in
fresh processes with MTP disabled and with MTP windows 2, 3 and 4. The prompt
hash, model/pack, 3,903 actual expert slots, FP16 KV and CPU-sharing-disabled
policy were held fixed. Each run used the six-GiB physical-memory supervisor.

All three MTP arms matched the MTP-off token IDs, all five shared accepted
commit boundaries, and all nine final persistent main-model fields. Drafts
accepted/offered were 4/4, 5/8 and 6/12. Minimum host `MemAvailable` was 14.42
GiB, with no supervisor floor breach. This is a short correctness matrix, not
performance or quality qualification.

The structured result, per-arm engine logs and supervisor telemetry are
preserved in `experiment/` and `supervisor/`. The longer MTP-off/window-4
follow-up is reported in the sibling
[32-token chain](../2026-10-11-phase5-spare-restore-long-chain/README.md).
