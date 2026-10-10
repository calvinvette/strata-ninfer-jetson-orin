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

## PLE artifact rerun

The current `ple_parity` CTest was rerun against the downloaded Q2_0 shard and
generated Q2_0 pack. It exits 2 during preflight because the oracle requires a
26,214,400-byte PLE value span while this pack indexes 13,107,200 bytes of BF16
values. This is the known representation mismatch documented in the
[Q2_0 PLE attempt](../2026-10-10-phase3-q2-ple-test/README.md), not a numerical
parity failure and not a pass.

The real-table reader was separately run with 64 rows from that shard and
reported bit-identical mmap/direct reads. The selected Phase 3 CTest set was
rerun: all 10 tests passed, including `ple_reader_selftest`, VMM lifecycle,
segmented expert cache, pin fallback, and memory admission/refusal checks. See
`ple-rerun/ctest.txt`, `ple-rerun/reader.txt`, and `ctest/output.txt` for raw
outputs.
