# Strict-NInfer Coder cancellation and recovery — Orin — 2026-11-05

This guarded service test used the current Coder IQ1_M binary, a fixed 391-slot
profile, strict NInfer dispatch, MTP-2, FP16 KV, a 4K context, and adaptive
residency disabled. The stream was closed after five visible deltas (`1 2 3 4`);
the engine reported cancellation after seven tokens had committed across four
accepted-prefix boundaries (lengths 48, 50, 52 and 54). Two fresh strict-NInfer
processes generated the same seven token IDs and matched all 11 persistent-state
fields at each of those boundaries. Their references were repeatable. The
canceled service process then remained healthy and answered the recovery request
with exactly `Hello Orin!`.

The supervisor passed in 66.2 seconds. Minimum host/admission availability was
20.30 GiB; sampled swap peaked at 1.29 GiB, and the pre-existing OOM-kill
counter remained at one. Clocks were observed dynamically, EMC readback was
unavailable, and energy was not measured. This qualifies one MTP-2 cancellation
point for strict NInfer on this Coder profile. Other boundaries, profiles,
models and task-quality effects remain open; no performance conclusion follows.

The compact source, model and profile identities and accepted-prefix state
records are in [`results.json`](results.json). The full raw result and service
logs remain in the adjacent local-only `cancel-ninfer-run/` and
`cancel-ninfer-supervisor/` directories.
