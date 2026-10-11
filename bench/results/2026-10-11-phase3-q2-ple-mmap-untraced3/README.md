# Q2_0 PLE I/O timing screen without owner tracing — Orin — 2026-10-11

Three balanced randomized process pairs compare PLE direct reads and mmap on
the same Q2_0 Coder model and 512-token prompt, with a fixed 5,000-slot cache,
4,096 context and one greedy output token. Owner tracing was fully disabled.
All six supervised requests completed, emitted token ID 32, retained 5,000
actual cache slots and stayed above the six-GiB floor; minimum `MemAvailable`
was 17,266,540,544 bytes (16.09 GiB).

Median whole-prompt time was 13,764.3 ms direct and 13,696.8 ms mmap. The three
paired mmap-minus-direct deltas were +13.27%, −7.37% and −9.31% (median
−7.37%). The medians differ by only 0.49%, and the paired signs are not stable.
The engine's PLE counter was 0.3 ms in every run. These samples do not establish
a PLE transfer benefit; the prompt-time variation is much larger than the PLE
counter and includes the rest of the model prefill.

CPU frequencies ranged from 729 to 2,201 MHz; tegrastats did not expose GPU or
EMC clock frequencies. Request-scoped energy was not measured, and host-wide
disk counters cannot attribute reads to these requests. Treat this as a small
screen, not a confirmation or a reason to change defaults. Exact commands and
telemetry are in each pair directory; [`analysis.json`](analysis.json) contains
the paired values. Model and pack identities are in the sibling [Q2_0
admission report](../2026-10-11-phase3-q2-admission/artifact-identities.json).
