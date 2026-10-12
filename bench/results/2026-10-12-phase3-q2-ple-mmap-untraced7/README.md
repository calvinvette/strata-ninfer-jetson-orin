# Q2_0 PLE direct versus mmap — seven-pair confirmation screen

Date: 2026-10-12. Device: Jetson AGX Orin. This extends the earlier three-pair timing screen with seven randomized, balanced same-day pairs on the current candidate binary (`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`).

Each independent process used the same Q2_0 model and PLE table, exact 512-token prompt, one greedy output token, requested and actual 5,000 expert-cache slots, 4,096 context, and 3,072 MiB workspace reserve. Only `--ple-io direct` versus `--ple-io mmap` changed. Integration owner tracing was disabled for timing; the six-GiB supervisor sampled host memory and read-only CPU/GPU/EMC clocks. Clocks remained dynamic.

All 14 runs passed, stayed above the six-GiB host-availability floor, emitted token ID 32, and retained 5,000 actual cache slots. Minimum `MemAvailable` was 16,987,193,344 bytes (15.82 GiB). Median prefill-stage time was 15,886.7 ms direct and 15,708.0 ms mmap. The paired mmap-minus-direct median was −0.77%, with a seven-pair bootstrap 95% interval of −1.83% to +0.76%; five pair deltas favored mmap and two favored direct. The PLE stage counter rounded to 0.3 ms in both arms. CPU observations ranged from 729.6 to 2,201.6 MHz; retain the raw clock records for the GPU/EMC observations.

The small apparent difference is not distinguishable from zero and the measured PLE stage is negligible relative to full prefill. This cell does not demonstrate an end-to-end transfer benefit. No default changed. Request-scoped energy and request-attributed disk traffic were not measured; this is not broad workload or cache-size evidence.

[`analysis.json`](analysis.json) contains the paired samples and bootstrap interval. [`campaign.json`](campaign.json) and each pair directory retain commands, telemetry and engine output. The workload token file SHA256 is recorded in the campaign. Model artifacts remain in `~/models/` and are not copied into the repository.
