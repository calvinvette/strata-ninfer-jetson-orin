# Coder layer-1 CPU/GPU route isolation attempt — Orin — 2026-10-18

This supervised three-arm diagnostic used the IQ1_M Coder GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e`, binary SHA256
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`, one
exact 512-token prompt, 16 generated tokens, MTP2, FP16 KV, a 3,000-slot
expert cache, prompt cache off and adaptive swaps disabled. The model stayed in
`~/models/strata-orin-validation/`. All arms ran in separate 28-GiB scopes with
dynamic clocks; no timing comparison is claimed.

The controls used the checked-in expert profile: default CPU execution for
CPU-owned misses, and the opt-in CPU Q8_1 mirror path. The intended intervention
moved the seven experts observed as CPU-owned at the first layer-1 dispatch into
the existing 3,000-slot profile capacity. The corrected GPU-profile run routed
all ten experts on that captured layer-1 dispatch to the GPU. Its profile hash
is recorded in `profile-design.json`.

All three arms used the same prompt hash and returned the same 16 token IDs. The
default and mirror routes had the same IDs and owners on the captured layer-1
dispatch, with seven CPU-owned entries. The GPU-profile route assigned all ten
entries to the GPU. The combined-output captures have matching position/token
keys for 16 rows. Across all 40,960 captured values, CPU default versus mirror
changed all values (maximum absolute difference `0.00072462`, relative L1
`0.00639`); CPU default versus GPU profile changed 10,240 (maximum
`0.00021168`, relative L1 `0.000728`); mirror versus GPU profile changed
35,840 (maximum `0.00072462`, relative L1 `0.00574`). Final accepted-prefix
state fingerprints differed among all three arms, despite identical completion
IDs.

This is **not a successful causal isolation**. The captured layer-1 activation
matches between CPU default and mirror but differs in the GPU-profile arm,
although the captured layer-0 activation, IDs and owners match. In addition,
the dispatch trace records no absolute position or token ID, so its dispatch 1
cannot be directly joined to the combined capture's first position/token row
`511/271`. The data establishes route placement and output/state differences;
it does not establish which layer-1 weighted-combine row caused them. The
profile intervention or another uncontrolled runtime effect changed upstream
state, and the next experiment needs a shared row key plus a narrower
intervention before attributing this to CPU arithmetic or GPU execution.

The first campaign attempt used a capture start row of 1,392. Its three service
requests completed, but the harness failed because no route file was created;
those cells are retained under the top-level arm directories and excluded. A
row-zero retry completed the three harnesses, but its GPU arm used a profile
derived from the wrong capture window and is excluded from the intended
intervention. The final GPU-only rerun uses the corrected profile from
`retry-start0/cpu_default/result/layer1.jsonl`; it passed request and capture
checks. Its result is combined with the valid default/mirror controls above
only for this correctness diagnostic, not for latency analysis.

Minimum host and admission availability was 14.40/14.40 GiB for CPU default,
14.45/14.45 GiB for CPU mirror, 14.45/14.45 GiB for the excluded initial GPU
attempt, and 14.32/14.32 GiB for the corrected GPU-profile run. All remained
above the six-GiB floor; cgroup pressure and OOM counters were zero in the
corrected cells. Clock samples are retained with each supervisor record.

Recompute the checks from the repository root with:

```sh
/home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze.py
```

The machine-readable summary is `analysis.json`. Failed and superseded cells
remain present for audit and are explicitly excluded above. Phase 5 remains
open.
