# Coder all-position layer-1 route and output trace — Orin — 2026-10-19

This supervised follow-up captured every generated row in a single 16-token
request on the pinned `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`
IQ1_M snapshot, revision `5348543e0147355ac9cbcb031184a3546350988e`. It uses
the same 512-token prompt, MTP2 from `Qwen/Qwen3.8-Flash-Next` revision
`de4b8e4d43b917e7706784d8bb445c9af86a3540`, FP16 KV, 3,000-slot expert
profile capacity, disabled adaptive swaps, and prompt cache off as the earlier
position-keyed campaign. The three arms were default CPU arithmetic, the CPU
Q8_1 mirror, and the layer-1 GPU placement profile. They ran in the order
`cpu_mirror`, `gpu_layer1`, `cpu_default`; this correctness diagnostic makes no
timing comparison.

Each arm captured 768 route rows (16 positions × 48 layers), all layer-1
CPU-owned expert output vectors, and verifier graph-side `ffn_x` and `ffn_y`.
All three supervisor cells passed with identical prompt hashes and identical
16-token completion IDs. Minimum host/admission availability was 14.14–14.43
GiB; the 28-GiB scope peak was 10.87–11.32 GiB; cgroup `high`, `max`, `oom`
and `oom_kill` counters stayed zero. The runs used dynamic clocks. Energy was
not measured, and EMC readback was denied.

Across all 16 layer-1 rows, device-side `ffn_x` was bitwise identical among all
three arms. The host route activation matched device `ffn_x` within `1e-7` for
all default and mirror rows and for 14 of 16 GPU-profile rows. The two
exceptions, positions 511 and 513, are all-GPU rows where the host callback
capture is stale. Default and mirror host route activations match bitwise for
all rows.

All 98 CPU-owned expert output vectors captured in both default and mirror
arms differ between the default activation arithmetic and Q8_1. Their relative
L1 deltas have a 1.372% median and range from 0.485% to 1.757%. The 83 outputs
whose expert remains CPU-owned in both default and GPU-profile runs match
bitwise, confirming that those GPU-profile CPU rows use default CPU arithmetic.
Combined graph `ffn_y` differs between default and mirror at every position.
Mirror and GPU-profile `ffn_y` match at positions 511 and 513, where every CPU
owner has moved to GPU; they differ at position 512 and positions 514–526,
where CPU-default owners remain. Existing direct operator oracles establish
Q8_1 CPU/CUDA bitwise parity for the seven owners at position 511 and selected
real owners at positions 512 and 514. They do not reconstruct the complete
router-weighted/shared-expert sum for every row.

The placement profile changed 15 CPU-owner entries in total, at positions
511–513 and 515. The final state fingerprints differ in `gdn`, `kv`, `pooled`,
`pooled_full` and `tail`; the PLE fingerprints match. This remains a state
correctness failure even though all arms emitted the same token IDs.

Final accepted-prefix state fingerprints still differ among all three arms
despite identical generated tokens. This evidence supports the activation
format path as a cause of combined-output differences, but does not establish
the full state-divergence path, answer quality, or performance. Phase 5 remains
open.

The output-capture dispatch filter now treats the default `UINT64_MAX` as a
wildcard and explicit dispatch values as exact filters. The changed native
source rebuilt for the Orin CUDA and maestro1 HIP `strata` targets. The full
SYCL target reported no work because this file is outside SYCL's migrated
`sycl/src/core/expert_source.cpp` source path. maestro1 provides compile/link
evidence only. The selected CUDA route-window, verifier, native multi-row and
Q8_1 parity CTests passed 6/6; the supervised three-arm service capture passed
3/3. A separate supervised compatibility check using explicit dispatch `1`
still captured only that dispatch's seven CPU expert outputs and passed its
request and capture checks.

Recompute row joins and summaries from the repository root:

```sh
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_all16.py
```

To run a fresh capture without overwriting this result:

```sh
OUTROOT=bench/results/2026-10-19-phase5-coder-all16-reproduction \
  bash bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_all16_campaign.sh
```

`artifact-identities.json`, `campaign.json`, backend build logs and
`sha256.txt` identify the source, executables, model, profile and raw capture
files. The two earlier failed-harness attempts are retained beside this
successful campaign and excluded from analysis.
