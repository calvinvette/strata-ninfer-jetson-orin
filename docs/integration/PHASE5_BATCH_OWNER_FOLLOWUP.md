# Phase 5 batch owner follow-up

Date: 2026-10-22. This is a targeted correctness diagnostic on Jetson AGX
Orin (ARM64, CUDA 12.6), using the Coder IQ1_M model and delayed target-only
batch schedule recorded in the [batch-MTP experiment](../../bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/README.md).
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
  --layer 12 --boundary-layer 11 --moe-layer 11 --output "$OUT"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_residual_boundary.py \
  --capture "$OUT/boundary.stbndy" --layer 11 --position 119 --output "$OUT-boundary.json"
python bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/analyze_targetonly_layer11_moe.py \
  --run "$OUT" --position 119 --output "$OUT-moe.json"
```

The compact selected analyses are `targetonly-qsa-boundary119-batchdiag-analysis.json`,
`targetonly-layer11-moe-owners-position119-analysis.json`, and
`targetonly-layer11-moe-owners-cache3000-analysis.json` in the experiment
directory. Full capture arrays and supervisor logs remain local-only.

## Transfer to another inference backend

For a future Strata/Splash or Strata/NInfer comparison, preserve the serial
capture format while adding a versioned batch slot field. Pair every observation
by request, token, position and physical slot. Capture the exact input
activation, route IDs and weights, each expert's pre-combine result, combined
output and actual execution owner. Compare owner-specific results against an
independent mathematical or codec oracle. A cache-size intervention is useful
only when the upstream activation and all other controls match; output-text
equality alone cannot establish persistent-state parity.
