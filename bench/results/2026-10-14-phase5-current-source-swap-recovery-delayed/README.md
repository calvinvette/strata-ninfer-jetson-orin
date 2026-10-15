# Current-source delayed-swap recovery control — Orin — 2026-10-14

This is the control for the paired [adaptive-swap recovery diagnostic](../2026-10-14-phase5-current-source-swap-recovery/README.md).
It uses the same current native binary, Qwen3.8-Flash-Next Coder IQ1_M
configuration and 512→2,048→512 sequence, with MTP off and window 4 in fresh
services. Adaptation is accepted-only but scheduled at cadence 100,000, so the
run logged no adaptive choice or apply events.

All per-request MTP0/MTP4 outputs and state fingerprints matched. Within each
service, the first and recovery short outputs were identical and all nine
persistent fields matched. The scope passed in 377.11 seconds with 13.43 GiB
minimum host/admission availability and zero sampled cgroup pressure/OOM
events. This is a no-swap control on one diagnostic sequence, not a general
recovery or quality qualification.

Reproduce with the same command as the paired report, substituting this output
path and `--adapt-every 100000`. Raw service traces and supervisor samples are
retained here. `SHA256SUMS.txt` verifies them.
