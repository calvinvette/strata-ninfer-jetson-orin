# Q2_0 direct 172-token isolation probe: unsupported

This proposed control attempted to run the same 172-token prompt used as the
warmup in the state follow-up, without a preceding request. The
`stage_buffer_parity.py` harness rejected it before engine startup because its
supported measured-prompt minimum is 512 tokens. The supervised command exited
with parser status 2; initial physical availability was 26.45 GB. No model
request ran and no correctness or timing result is claimed.

The raw supervisor output is retained. The existing three-pair [512/64
no-warmup pageable/pinned screen](../2026-10-11-phase3-q2-stage-pin-screen/README.md)
is the available direct-request control. The open finding is whether a
different warmup completion affects later state parity; this unsupported
short-prompt probe does not resolve it.
