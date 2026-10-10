# Pinned registration fallback checks — Orin

Run date: 2026-10-09 on the local `orin1` Orin AGX, ARM64, CUDA 12.6. The
existing `pinned_fallback_test` and `pinned_shared_test` passed under
`run_control.py` with the six-GiB floor. CTest completed both tests in 0.34 s;
the supervisor observed a minimum of 26,432,790,528 bytes available. This was
a functional fallback check, not a memory-pressure experiment.

`pinned_fallback_test` wraps only this test binary's `cudaHostRegister` call and
forces failure for whole-arena registration and sliced registration attempts.
It confirms the arena remains valid as pageable memory, reports zero registered
bytes/slices, consumes the seeded CUDA error, and preserves bytes through a
pageable host-to-device copy and device-to-host readback. The test injects
registration failure; it does not inject `cudaHostAlloc` failure into
`FileExpertSource`'s separate expert-stage pool. `pinned_shared_test` also
confirms shared mapping visibility and refuses mismatched pack identity/size.

CTest output is in `stdout.txt`; supervisor memory, tegrastats and execution
metadata are in `memory.jsonl`, `tegrastats.txt` and `result.json`. No model was
loaded. Energy was not measured; raw tegrastats rails are not treated as energy.
Verify retained files with `SHA256SUMS`.
