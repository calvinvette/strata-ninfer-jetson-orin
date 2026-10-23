# Long-chain adaptive raw GDN state — Orin — 2026-10-22

This same-day Coder IQ1_M experiment captured committed layer-22 GDN state for
the held-out open-response short–short–short chain, 256 generated tokens per
request, seed `2026102251`, binary SHA256
`0a5f9b0dd9ac96320986a67ba9daf5e6abe6ac570500ea77c36a5ca52919996c`, and
workload SHA256 `d24e252ea0b891f9344008421a05fd60b8313b0ce53a6de5b5322a34d9869b47`.
Both arms used the same pinned model and current 28-GiB supervised configuration.

The adaptive trace contains initial, intermediate and recovery requests at
positions 515, 530 and 640. The delayed-control recapture independently ran the
same request sequence and capture positions. All nine raw layer-22 commit
records in each arm were cross-checked against the service's accepted-prefix
GDN hash at ordinal 17. In the adaptive arm, the first/recovery token IDs still
match at position 515, but recurrent state differs in 786,405/786,432 values
(relative L2 `2.60e-4`) and convolution history differs in 30,719/30,720
(relative L2 `7.86e-4`). At positions 530 and 640, token IDs and state have
diverged further. In delayed control, all recurrent and convolution values are
bit-identical between initial, intermediate and recovery requests at all three
positions. This directly confirms adaptive state drift before the first token
ID mismatch in the long chain; it does not identify the upstream operation
that causes it or provide a general numerical tolerance.

The adaptive raw capture was retained from a runner attempt that returned
failure because it also requested position 767. The final verifier record for
256 generated tokens is at position 766; no state record is emitted at 767.
The first paired attempt requested position 768 and was also rejected. Both
attempts correctly rejected the incomplete requested endpoint and did not
launch their delayed arm. To avoid repeating an already completed adaptive
arm, the delayed-control arm was then run directly at the three valid shared
positions. Its supervisor passed. Thus the selected-position raw-state result
is complete and hash-verified across both arms, while neither original
four-point paired campaign is marked as passing. Failed-attempt launch and
supervisor records remain local-only with the raw captures.

The adaptive arm's three request token sequences exactly match the earlier
hash-only 256-token adaptive campaign. Within the new delayed-control recapture,
all three request token sequences are also identical. The earlier delayed
control likewise had exact tokens; no claim is made that separate delayed
service starts produce identical tokens to each other.

The adaptive arm took 768.15 seconds and had 13.98 GiB minimum host/admission
availability. The delayed recapture took 775.43 seconds and had 14.07 GiB
minimum availability. Sampled cgroup low/high/max/OOM/OOM-kill events were zero
in both. Clocks were observed dynamically; EMC readback was denied; energy was
not attributed. The two failed campaign directories and their launcher/error
records are retained for audit.

The compact raw-state comparisons and service-hash checks are in
`adaptive-cap8/result/state-analysis.json` and
`delayed-control-recapture/result/state-analysis.json`. The workload, request
IDs, raw captures, service logs and supervisor telemetry are retained beside
them. No model or build product is stored here.

The capture path is implemented in the archived `run_one.py` harness and the
compact state analyzer is `compare_gdn_commit_state_trace.py`; both source
files and campaign metadata are committed with this report. Python integration
tests pass 163/163, and both scripts pass syntax and CLI-help checks. No C++
source changed in this diagnostic.
