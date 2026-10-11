# Q2_0 layer-dump pinned-owner return cleanup — Orin — 2026-10-11

This focused check exercises the optional `--dump-layers` host buffer under
`STRATA_INTEGRATION_TRACE=1`. The Q2_0 native `--spec 2` run reads 511 of the
512 prompt tokens, then rejects speculation because the layer-dump path
disables the token graph used to build the device residency table. The run is
therefore an expected unsupported configuration and writes no layer data.

The owner trace on the pre-fix binary recorded a
`layer-dump-pinned-host` allocation of 2,007,040 bytes but no matching free
before the function returned. A function-scope cleanup guard was added in
`src/program/generate.cpp`. Rebuilding `strata` and repeating the same request
recorded both allocation and free for the same instance and pointer, including
on the early return. The post-fix binary SHA256 is
`3306495d333c87cbf72e0f628b0ce94552e0492cf428b08d2d2fa96c370dcce3`.
The post-fix process returned code 2 for the expected unsupported combination;
minimum host availability was 23,360,598,016 bytes (21.76 GiB). The staged
output file was empty because verification rejected the path before a layer
record could be written.

The [post-fix owner trace and telemetry](fixed/supervisor/) and the
[pre-fix comparison](traced-supervisor/) retain full logs. The native CUDA
`strata` target rebuilt with `-j1`. maestro1 is reachable but currently has no
`hipcc`, `icpx` or `dpcpp` executable in its installed tool paths, so a fresh
HIP build is not claimed. SYCL uses its separate generator source. This test
qualifies cleanup on the tested early return only; successful layer dumping
with a compatible non-speculative runtime remains untested. After the source
change, the focused 15-test accounting/owner CTest set passed under the
six-GiB supervisor, and integration Python unittest discovery passed 91/91.
The CTest raw output is retained in
[`cleanup-fix-ctest/`](../2026-10-11-phase3-cleanup-fix-ctest/supervisor/).
