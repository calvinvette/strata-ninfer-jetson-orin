# QSA spare-row restore and accepted-prefix parity

The verifier commit graph restored accepted QSA indexer rows by replaying the
accepted prefix. A speculative suffix could complete a later four-cell indexer
block and overwrite the spare pooled row beyond the accepted prefix. That row
is part of persistent indexer state, even though the generated text and the
committed pooled rows matched.

The CUDA and SYCL verifier commit paths now restore `idx_dead` into the spare
row immediately after replay. The row is selected from the last committed
position in the existing commit buffer, so this remains asynchronous and can
run inside the captured commit graph. No additional allocation or host
synchronization is introduced.

The Orin confirmation used the current candidate binary, the Qwen3.8-Flash-Next
IQ1_M pack, fixed 3,903-slot actual expert residency, a 512-token prompt, FP16
KV, prompt caching enabled, and CPU prefill sharing disabled. Every arm ran as
a fresh engine process under `run_control.py` with its six-GiB physical-memory
floor. Models stayed under `~/models/`.

The eight-output-token MTP-off/2/3/4 screen matched token IDs, all five shared
accepted-commit boundaries, and all nine final persistent main-model fields.
MTP accepted 4/4, 5/8 and 6/12 offered drafts for windows 2, 3 and 4. The
32-token MTP-off/window-4 follow-up matched all token IDs, all 14 shared commit
boundaries and final state; window 4 accepted 19 of 39 offered drafts. Minimum
host `MemAvailable` was 14.42 GiB in the short matrix and 14.46 GiB in the long
pair. The supervisor recorded no floor breach. These are correctness screens,
not speed or quality qualification; graph lifetime and other supported KV
formats remain open.

The local CUDA candidate was rebuilt and the focused QSA indexer CTests passed
3/3. The integration Python test suite passed 82/82. maestro1 compiled both
changed HIP objects and both changed SYCL objects; the SYCL compiler emitted
warnings but succeeded. The object build logs and object timestamps are retained
in `backend-builds/`. maestro1 is compile-only evidence.

Raw arm logs, structured results and supervisor telemetry are retained beside
this report. The earlier pre-fix state mismatch is retained in
`../2026-10-11-phase5-mtp-off-window4/`,
`../2026-10-11-phase5-mtp-off-window4-long-chain/`, and
`../2026-10-11-phase5-mtp-rejected-suffix-continuation/`.
