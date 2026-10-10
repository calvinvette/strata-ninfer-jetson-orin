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

The same candidate binary, IQ1_M pack/profile, flags and 512-token prompt ran
inside 12, 16, 20 and 24 GiB transient scopes, each with `run_control.py` enforcing
the normal 6 GiB effective-availability floor. The 12 GiB run started, chose
file-backed experts, filled 1,410 expert-cache slots and was terminated during
prefill when the next cgroup sample crossed the floor. Effective availability
reached 6,409,375,744 bytes; host `MemAvailable` was still 22,215,254,016
bytes. Scope usage peaked at 6,475,526,144 of 12 GiB. The 16 GiB run reached
prefill with a larger cache, then was stopped at 5.46 GiB effective
availability while host `MemAvailable` remained 15.61 GiB; scope usage peaked
at 10.54 of 16 GiB. Both are supervisor pressure aborts, not engine allocation
failures or completed requests.

| Scope cap | Outcome | Minimum effective availability | Minimum host availability | Peak scope current |
| ---: | --- | ---: | ---: | ---: |
| 12 GiB | Supervisor abort during prefill | 5.97 GiB | 20.69 GiB | 6.03 GiB |
| 16 GiB | Supervisor abort during prefill | 5.46 GiB | 15.61 GiB | 10.54 GiB |
| 20 GiB | Request completed | 9.58 GiB | 11.55 GiB | 10.42 GiB |
| 24 GiB | Request completed | 8.84 GiB | 8.84 GiB | 9.76 GiB |

The 20 and 24 GiB scopes passed the request. Both completed the 511-token
prompt and generated one token. The smaller cap had 9.58 GiB minimum effective
availability, and the 24 GiB cap had 8.84 GiB minimum effective/host
availability. This is a small screen, not a universal minimum cgroup size or a
supported-capacity claim.

A fresh run with the same binary, pack, profile, flags and workload outside the
12 GiB scope also passed, with 7.62 GiB minimum host availability. This shows
fresh-process recovery after the supervisor ends a cgroup-limited engine. It
does not demonstrate in-process recovery or state parity. Raw outputs and
cgroup/host samples for all cells are in
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
