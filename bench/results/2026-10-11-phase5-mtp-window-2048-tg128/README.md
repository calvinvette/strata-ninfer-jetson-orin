# Invalid MTP long-workload screen — excluded

This screen is retained as a failed setup and **must not be interpreted as an
MTP performance result**. Its source config was generated from the prior
MTP-off arm, which intentionally omitted the `--mtp` draft-weight path. The
window arguments changed, but the draft model was not restored; engine logs
report `drafts accepted 0 of 0`. Four such process arms finished, and one
additional arm was interrupted after the configuration error was found. No
paired comparison is qualified.

The campaign record marks every arm `invalid_setup` and records the reason. The
replacement screen uses the original base config containing the explicit MTP
model path, with the same selected 2,048-prompt/128-output workload.
