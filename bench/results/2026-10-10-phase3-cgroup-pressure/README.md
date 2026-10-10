# Phase 3 cgroup pressure and PLE rerun — 2026-10-10

## Bounded cgroup pressure probe

`run_pressure.py` started `hold_memory.py` in a transient user scope with
`MemoryMax=6G`. The child touched and held 4 GiB for 15 seconds, then exited
successfully. The host sampler collected 64–65 samples depending on the run;
the repeat's minimum `MemAvailable` was 23,821,824,000 bytes. This remained
well above the 6 GiB ordinary-campaign floor. The files retain the exact
command, scope output and host samples.

This confirms a bounded real allocation under a cgroup cap while physical
headroom remains ample. The cgroup's own `memory.current` high-water was not
captured (the transient scope was not present at the sampler's selected path),
and this did not run Strata inside the pressure scope. It does not close late
workspace pressure or service recovery under active cgroup pressure.

## Strata under an active cgroup cap

The candidate engine then ran the existing IQ1_M native path inside a transient
12 GiB scope, with `run_control.py` enforcing the normal 6 GiB effective
availability floor. Startup completed, chose file-backed experts, sized the
expert cache to 1,410 slots under the cap and completed profile fill. During
the 512-token prefill the supervisor observed cgroup availability reach
6,409,375,744 bytes, then terminated the command as its next sample crossed
the floor. At that point host `MemAvailable` remained 22,215,254,016 bytes;
the cgroup scope reached 6,475,526,144 bytes current of 12 GiB. This is a
supervisor pressure abort, not an engine allocation failure or a completed
request.

A fresh run with the same binary, pack, profile, flags and workload outside the
12 GiB scope passed, completed the 511-token prompt and generated one token.
Its minimum host availability was 8,180,158,464 bytes (7.62 GiB). This shows
fresh-process recovery after the supervisor ends a cgroup-limited engine. It
does not demonstrate in-process recovery, state parity, or that the bounded
12 GiB scope supports this workload. Raw outputs and cgroup/host samples are in
`../2026-10-10-phase3-cgroup-engine/`.

## PLE artifact rerun

The first rerun of `ple_parity` against the downloaded Q2_0 shard and generated
Q2_0 pack exits 2 during preflight because the old oracle requires a
26,214,400-byte PLE value span while this pack indexes 13,107,200 bytes of BF16
values. The raw failure is retained below and in the original
[Q2_0 PLE attempt](../2026-10-10-phase3-q2-ple-test/README.md). The reader was
then adapted to the source key blocks and BF16 values; the resulting test
passes all seven stages. See the [artifact-aware PLE
report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md).

The real-table reader was separately run with 64 rows from that shard and
reported bit-identical mmap/direct reads. The selected Phase 3 CTest set was
rerun: all 10 tests passed, including `ple_reader_selftest`, VMM lifecycle,
segmented expert cache, pin fallback, and memory admission/refusal checks. See
`ple-rerun/ctest.txt`, `ple-rerun/reader.txt`, and `ctest/output.txt` for raw
outputs.
