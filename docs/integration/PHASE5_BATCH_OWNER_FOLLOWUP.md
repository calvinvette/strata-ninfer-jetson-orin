# Phase 5 batch owner follow-up

Date: 2026-10-22. This is a targeted correctness diagnostic on Jetson AGX
Orin (ARM64, CUDA 12.6), using the Coder IQ1_M snapshot from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` at revision
`5348543e0147355ac9cbcb031184a3546350988e` and the delayed target-only batch
schedule recorded in the [batch-MTP experiment](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).
It is not a performance result or Phase 5 closeout.

## Finding

The opt-in residual-boundary writer previously skipped batch-recursive rows.
It now writes versioned `STBNDY2` records for serial and target-only one-row
batch captures. The header records the physical slot (`-1` for serial); the
capture remains restricted to `T=1`. The independent parser checks record
version, dimensions, slot and exact payload length.

At position 119, the captured layer-10 residual, branch, injection and pre-read
fields matched bit-for-bit between serial and batch. At layer 11, the MoE input
activation, route IDs and weights, and shared-expert output matched. The
combined MoE output differed (2,560 values; relative L2 0.00443926; maximum
absolute 0.000294242). Only routed expert ranks 4, 5 and 7 changed in their
per-expert parts; experts 205, 110 and 90 respectively changed owner from
primary VRAM in serial to CPU in batch. The weighted part deltas accounted for
the combined-output delta with maximum residual `5.7e-9`. Slot 0 still emitted
the same 96 tokens as its serial control and its queued peer emitted one.
Minimum physical/admission availability was 17.79 GiB and sampled cgroup
memory events were zero. Clocks were observed dynamically; EMC readback was
denied and request energy was not measured.

The same three service parts were then joined to `native_expert_parity` using
their captured activation (SHA256
`45b5242503845f5fef75c96f68db53ff2dab46d9d85347630e27512077424aaa`). The
selected experts use IQ2_S gate/up and IQ4_NL down weights. For all three,
serial service output matched the CUDA operator output bit-for-bit, and batch
service output matched the CPU operator output bit-for-bit. The CPU and CUDA
outputs differed in all 2,560 values per expert; relative L1 was 0.849–1.380%
and relative L2 was 0.844–1.398%. Both paths also passed the tool's float
reference checks (GGML `to_float` weight decode followed by its separate float
expert calculation). This confirms the observed expert-part change follows
the owner-specific arithmetic path on these rows. It does not measure model
quality or imply that one arithmetic path is preferable. The supervised
oracle run completed in 2.1 seconds with 25.62 GiB minimum available physical
memory and zero sampled cgroup memory events; EMC readback was denied and
energy was not measured.

An all-layer committed-state capture under the same delayed target-only
schedule directly measured the persistent-state consequence. All nine sampled
GDN layers through model layer 10 were bit-identical; the first changed
committed state was GDN layer 12. At layer 12, 785,549/786,432 recurrent
values changed (relative L2 0.000332829) and 10,240/30,720 convolution values
changed (relative L2 0.00170454), for 795,789/817,152 combined values
(relative L2 0.00170369, maximum absolute difference 0.0149361). All 27 later
GDN layer states also differed. Across all 36 layers, 21,504,757/29,417,472
floats changed (relative L2 0.00781353, maximum absolute difference 0.370022).
Slot 0 still matched all 96 serial output tokens and the competitor returned
one. Supervision retained 17.66 GiB minimum
physical/admission availability over 63 samples with zero cgroup events.
This shows the selected layer-11 owner-path difference carries into committed
recurrent state in this run; it does not establish a quality impact or a
long-chain bound. The compact per-layer analysis is
`targetonly-layer11-all-gdn-commit-state-analysis.json`; the 224 MiB paired
state dump and full telemetry remain local-only.

The ARM64/CUDA candidate rebuilt with one job and passed the focused
`verify_parity`, `verify_batch_parity` and `spec_verify_parity` tests. Python
integration discovery passed 163/163 tests. On maestro1, HIP compiled/linked
the current verifier and generator with one job, and both HIP/SYCL binaries
passed `--help`; the SYCL build tree reported no work. These are x86 build and
CLI checks only, not accelerator runtime evidence. The exact source and binary
hashes and build logs are in
[`backend-builds-maestro1-phase5-boundary-final`](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/backend-builds-maestro1-phase5-boundary-final/).

A follow-up with a 3,000 MiB expert cache cap passed the supervisor and emitted
the same tokens, but its layer-11 MoE input already differed (relative L2
0.00323); route weights and shared output also differed. It is an unclean
comparison and says nothing reliable about cache size or owner placement.

The result localizes a numerical change to owner-dependent expert arithmetic
for this prompt and schedule. It does not show a quality impact or establish a
performance effect. Phase 5 remains open.

## Reproduction and retained evidence

Run the controlled capture on the configured Orin checkout:

```sh
OUT=bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run-owner-followup
python tools/integration/run_control.py --output "$OUT-supervisor" --timeout 420 --sample-clocks \
  python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/capture_targetonly_gdn_layer12_stages.py \
  --layer 12 --boundary-layer 11 --moe-layer 11 --all-layer-commit-state --output "$OUT"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_residual_boundary.py \
  --capture "$OUT/boundary.stbndy" --layer 11 --position 119 --output "$OUT-boundary.json"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_layer11_moe.py \
  --run "$OUT" --position 119 --output "$OUT-moe.json"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_all_gdn_commit_state.py \
  --serial "$OUT/serial-committed-gdn.stgcmt" --batch "$OUT/batch-committed-gdn.stgcmt" \
  --position 119 --token 16 --output "$OUT-committed-state.json"
```

The compact selected analyses are `targetonly-qsa-boundary119-batchdiag-analysis.json`,
`targetonly-layer11-moe-owners-position119-analysis.json`,
`targetonly-layer11-moe-owners-cache3000-analysis.json`, and
`targetonly-layer11-moe-owner-oracle-analysis.json`,
`targetonly-layer11-all-gdn-commit-state-analysis.json` in the experiment
directory. The oracle join is reproducible with:

```sh
OUT=bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run-owner-oracle
CAPTURE_RUN=bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run-targetonly-layer11-moe-owners-position119
python tools/integration/run_control.py --output "$OUT-supervisor" --timeout 300 --sample-clocks \
  python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/run_targetonly_layer11_moe_owner_oracle.py \
  --run "$CAPTURE_RUN" --output "$OUT"
```

Full activation/output arrays, parity logs and supervisor samples remain
local-only.

## Transfer to another inference backend

For a future Strata/Splash or Strata/NInfer comparison, preserve the serial
capture format while adding a versioned batch slot field. Pair every observation
by request, token, position and physical slot. Capture the exact input
activation, route IDs and weights, each expert's pre-combine result, combined
output and actual execution owner. Compare owner-specific results against an
independent mathematical or codec oracle. A cache-size intervention is useful
only when the upstream activation and all other controls match; output-text
equality alone cannot establish persistent-state parity.
