# Invalid all-layer verifier input diagnostic

Both supervised workload arms passed, but this capture is **invalid and
excluded from analysis**. The first version of the opt-in layer-multiplexed
input hook used the per-layer destination offset when reading from the
single-layer source activation buffer. The independent parser found non-finite
values at layer 6. The source-offset bug is fixed and the valid rerun is recorded
in the sibling `adaptive-no-cache-verifier-input-all-layers-corrected/` folder.
Retain this failed diagnostic to preserve the audit trail; do not use its input
values as evidence.
