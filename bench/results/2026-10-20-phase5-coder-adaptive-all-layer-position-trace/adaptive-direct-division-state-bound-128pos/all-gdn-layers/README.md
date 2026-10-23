# All-layer committed GDN capture — Orin — 2026-10-22

This supervised adaptive-only replay extended the 128-token short→long→short
Coder IQ1_M recovery sequence with committed GDN captures at model layers
0–47 that contain GDN state (36 layers; QSA layers omitted), at positions 515,
534, 557, 558, 574 and 638. The model revision, prompts, service configuration,
and adaptive settings match the parent 128-token campaign. The source build
includes the opt-in `STRATA_VERIFY_DUMP_GDN_COMMIT_LAYER=all` diagnostic
extension to the existing STGCMT1 capture path. The binary SHA256 is
`dcf6617a6a7190155e258b58784b2dc8e63529c3d60893bf2801dd2b512abc5e`; source
SHA256 is `2c521590a591a458dbe91b8e837a1f2e4c94ab99fb47b4ccf058b044ff303722`.

The first short request and its recovery emitted 128 tokens each. All 432
captured records (36 layers × six positions × two requests) matched the
corresponding per-layer service GDN hashes; no record hash mismatched. Position
515 is bit-exact across all 36 layers. At position 534, the earliest changed
committed state is model layer 22: 786,051 of 786,432 recurrent values differ
(relative L2 `1.405e-4`), while its convolution history is exact. All earlier
GDN layers are bit-exact. At positions 557 and 558, layer 22 remains the first
changed GDN layer; its recurrent/convolution relative-L2 deltas are
`2.554e-4`/`1.113e-3` and `2.524e-4`/`7.552e-4`, respectively. The consumed
token IDs match across the initial and recovery requests at all three
positions (3155, 11, and 466). This places persistent-state drift before the
first output-token mismatch at index 47, and narrows its first committed GDN
boundary to layer 22. It does not yet identify which layer-22 input or operator
causes that difference.

After token histories diverge, positions 574 and 638 differ across all 36
GDN layers and are not clean causal comparisons. They are retained as
downstream observations only. This remains one prompt and one adaptive
configuration, not a general migration bound or a performance measurement.

The wrapper completed all three 128-token requests in 598.7 seconds. Minimum
host/admission availability was 14.13 GiB, above the six-GiB floor; cgroup
memory-event counters remained zero. CPU/GPU clocks were sampled dynamically;
EMC readback was unsupported; energy was not measured. The full raw state dump
is 1.4 GiB and remains local. `result/requests.json`, `result/analysis.json`,
the service log, and `supervisor/` contain the run records. The compact
`layer-drift-summary.txt` is the layer-level comparison result.

The targeted Orin rebuild and focused verifier/GDN/accepted-window/graph tests
passed before this run. This diagnostic change is opt-in and does not change
normal inference behavior. maestro1 rebuilt and linked the changed verifier
through the HIP target with one job and passed `strata --help`; the first
attempt hit its full root filesystem `/tmp`, and the retry used the task
scratch directory on `/mnt/sda2`. The SYCL target reported no work because this
CUDA verifier translation unit is not part of that target. No accelerator
runtime was exercised on maestro1. The comparison and service-hash audit
helpers are retained beside this report as `compare_all_gdn_commits.cpp` and
`verify_gdn_service_hashes.cpp`.
