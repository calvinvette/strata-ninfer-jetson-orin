# Segmented ExpertCache VMM owner trace — Orin

Run date: 2026-10-09 on the local `orin1` Orin AGX, ARM64, CUDA 12.6. The
existing `expert_cache_segmented_test` exercised both uniform and sized caches:
96 MiB of mapped backing was created, shrunk to 32 MiB, regrown to 64 MiB and
then 96 MiB, with retained slot bytes checked across both changes. A final
ordinary 8 MiB cache covered the non-segmented path. The supervised test passed
with `STRATA_INTEGRATION_TRACE=1` and the six-GiB floor. Its elapsed time was
1.06 s; the supervisor recorded 26,456,444,928 bytes available at admission.
That short interval is a functional lifecycle check, not a pressure or capacity
measurement.

The parser found 41 observed allocations and 41 matching frees. The segmented
owner peaked at 100,663,296 requested bytes (96 MiB) and ended at zero; the
ordinary owner peaked at 8,388,608 bytes and also ended at zero. Segment events
represent successfully mapped CUDA physical handles and use the driver's
allocation granularity. The virtual address reservation is not reported as
device backing. These requested-byte events are scoped observations, not total
Orin physical-memory accounting.

Raw engine events are in `stderr.txt`; supervisor telemetry is in
`memory.jsonl`, `tegrastats.txt` and `result.json`. The summarized parser output
is `owner-summary.json`. No model was loaded. Energy and clock sampling were not
part of this short test. The native candidate binary SHA-256 is
`0901645481ba3e9274e455c5ad688eebc303e85f3f9807901d88f5a5da9fcf55`; the
segmented test binary SHA-256 is
`4492c8436d0401632975b4926f7aa172cfd9fb081660e4278bff0affba89cf77`. Source
hashes are recorded in `source-hashes.txt`. Verify all retained files with
`SHA256SUMS`.

The changed cache header and source were then built on maestro1 with one job
for the HIP `strata` target. A separate one-job SYCL `strata` build also passed
with the shared header updated; its migrated cache implementation remains
separate and unchanged. The source hashes and executable identities are in
`maestro1/hashes.txt`, and full logs are retained there. The SYCL link emitted
warnings about oneMKL compiler runtime libraries not found by the linker's
warning scan, while completing successfully. These x86 builds establish
compilation only; maestro1 has no AMD or SYCL runtime device.
