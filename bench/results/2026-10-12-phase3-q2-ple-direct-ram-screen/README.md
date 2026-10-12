# Q2_0 PLE direct versus RAM-mode screen

Date: 2026-10-12. Device: Jetson AGX Orin. This three-pair randomized screen compared `--ple-io direct` with `--ple-io ram` on the current candidate binary and the same Q2_0 512-token/one-output workload, 5,000 expert-cache slots, 4,096 context, and 3,072 MiB workspace reserve. Owner tracing was disabled. The six-GiB supervisor sampled memory and read-only clocks; clocks remained dynamic.

All six runs passed and emitted token ID 32 with 5,000 resident expert-cache slots. Minimum host availability was 17,118,593,024 bytes (15.94 GiB). The median prefill-stage times were 15,323.6 ms direct and 15,925.6 ms RAM mode; paired RAM-minus-direct changes were −1.53%, +10.76%, and +12.76%. The PLE-stage counter was 0.3 ms in each arm.

The RAM mode did **not** lock the table in any run. It logged `mlock failed (Cannot allocate memory; raise ulimit -l)` and then faulted the pages in, leaving them reclaimable. The launch shell reported a 3,929,184 KiB soft and hard `RLIMIT_MEMLOCK`. Thus this tests RAM-mode page touch with reclaimable pages; it does not qualify a locked-RAM transfer mode. Startup table-load times were 9.1–9.6 seconds and are not included in the prompt-stage measurements. No timing benefit is claimed and no default changed.

[`analysis.json`](analysis.json) records the three pair results. [`campaign.json`](campaign.json) and each pair directory retain commands and supervisor telemetry. The Q2_0 model remains under `~/models`; its source revision, pack identity and profile identity are recorded in the [Q2_0 admission artifact report](../2026-10-11-phase3-q2-admission/artifact-identities.json). This is a short screen, not a confirmation; locked RAM remains unsupported with the current per-process memlock limit.
