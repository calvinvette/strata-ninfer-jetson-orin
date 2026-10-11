# Current-binary Phase 3 memory and owner CTests — Orin — 2026-10-11

The current CUDA candidate passed all 22 selected memory, ownership, VMM,
cache, graph, conversation and PLE checks serially. The selection includes the
artifact-aware `ple_parity` test and the `ple_reader_selftest`, which completed
after 52.38 seconds. The complete CTest summary and command are retained in
`supervisor/stdout.txt` and `supervisor/result.json`.

The six-GiB supervisor measured minimum host `MemAvailable` of
26,371,256,320 bytes (24.55 GiB); no cgroup memory events were recorded. This
reconfirms selected software contracts. It does not close Phase 3's remaining
physical-pressure, graph-allocation pricing or transfer/admission gates.
