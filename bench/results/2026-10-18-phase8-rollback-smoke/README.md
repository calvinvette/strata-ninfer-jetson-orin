# Pinned-control rollback smoke — Orin — 2026-10-18

The pinned Strata control executable is still present at
`build/integration/control/strata`. Its SHA256 matches the original
[`0be090c` control manifest](../2026-10-09-integration-controls/control-manifest.json):
`edbc0a85fc706fd929f9ea5ad1041c3fed25a0cc107356bcc82e59c2431a5249`. The
current integration candidate executable is
`build/integration/candidate/strata`, SHA256
`320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932`, built
from engine source at `0b28cd63`.

Both executables ran the same one-token IQ1_M Coder command from the pinned
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` revision
`5348543e0147355ac9cbcb031184a3546350988e`, with only the executable path
different. The GGUF shard hashes are recorded in the original
[artifact manifest](../2026-10-09-integration-controls/artifacts.json). Each
run used a fresh `MemoryMax=28G` scope, one-second telemetry and the six-GiB
physical-availability floor. Both exited 0 and produced token ID `846` from
input token `248045`. Minimum host/admission availability was 9.16 GiB for the
pinned control and 8.92 GiB for the candidate; all sampled cgroup memory-event
counters were zero. This establishes one executable rollback smoke only. It is
not a service/API, quality, or performance comparison.

The pinned binary does not accept every option in the newer selected Q2_0
profile. Rollback therefore means restoring the pinned control runtime and its
known-compatible invocation/configuration together; do not substitute only the
binary while retaining candidate-only flags. The existing control source
snapshot and CMake build tree remain under ignored `build/integration/`. The
source is the Git commit above; the build used CUDA 12.6, SM87, Release mode,
and llama.cpp `3cf03257f219afbe7334045ff7c6a06ac68c627d`.

The compact independent review is in [`analysis.json`](analysis.json). Raw
stdout, stderr, memory and clock observations are retained in `control/` and
`candidate/`. Re-run both arms with [`run.sh`](run.sh), then verify them with
[`review.py`](review.py). No model or executable is stored in Git.
