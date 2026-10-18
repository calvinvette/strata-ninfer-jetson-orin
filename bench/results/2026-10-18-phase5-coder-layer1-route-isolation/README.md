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

## Position-keyed current-source rerun

The route diagnostic was then extended to record each row's absolute position
and input token ID, and the CPU output diagnostic now records the same key. The
new format versions are dispatch v3 and CPU output v2. A supervised fresh
three-arm rerun used the resulting binary (SHA256
`320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932`) in
randomized order `cpu_default`, `cpu_mirror`, `gpu_layer1`. It used the same
model revision, prompt and profile intervention. All three cells passed the
request and capture checks, returned the same 16 token IDs, and matched the
same route row to exactly one combined-output row at position 511/token 271.
Each CPU-owned expert output row also matched its route slot and absolute key.

This establishes the row join that the earlier capture lacked. At that joined
row, CPU default and CPU mirror had bitwise-identical input activations and
routes, yet all 2,560 combined-output values differed (maximum absolute
difference `0.00021168`, relative L1 `0.00402`). The GPU-profile arm routed all
ten experts to GPU and its joined combined output matched CPU mirror bitwise;
however, its layer-1 input activation differed from the CPU controls. Thus the
CPU default/mirror comparison is a direct same-activation numerical difference
for this one row. Each of the seven captured CPU expert vectors also differed
at all 2,560 elements between default and mirror; their per-expert relative L1
deltas ranged from `0.00804` to `0.01757`. The GPU-owner comparison remains
confounded by upstream activation change. Final persistent-state fingerprints
still differed among arms despite identical completion IDs. These findings
narrow the unresolved path; they do not establish a quality conclusion or a
performance result.

Minimum host/admission availability was 14.22/14.22 GiB (CPU default),
14.40/14.40 GiB (CPU mirror) and 14.44/14.44 GiB (GPU profile), above the
six-GiB floor. Per-arm telemetry, exact artifacts and the source-diff digest
are under `position-keyed-three-arm/`. Reproduce the join and comparisons with:

```sh
/home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_position_keyed.py
```

## Captured expert numerical oracle

The same saved activation and the seven IQ2_S/Q2_0 expert blobs were checked
with the CUDA `native_expert_parity` tool. It compares the service CPU paths
against GGML's float dequantized reference, and with
`STRATA_NATIVE_CPU_Q8_1_DOT=1` it requires the Q8_1 CPU output to match the
CUDA output bitwise. For every expert, the service default vector matched the
tool's default CPU vector exactly; the service mirror vector matched the
tool's Q8_1 CPU vector exactly; and the Q8_1 CPU vector matched CUDA bitwise.
The Q8_1 relative L1 error against the float reference was lower for all seven
experts: default ranged from `0.01077` to `0.01463`, while Q8_1 ranged from
`0.00953` to `0.01198`. These are single-activation operator comparisons, not
full-service quality or performance evidence. The GPU-profile service arm
still has a different captured input activation at this layer.

The oracle run used a 28-GiB supervisor and retained its stdout summaries,
activation bytes and memory/clock log. A first wrapper attempt stopped before
running the parity tool because it compared parsed decimal JSON values with
float32 values without rounding the JSON inputs to float32; that harness check
was corrected, and the supervised retry passed all seven experts. Reproduce
the oracle check on Orin with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase5-coder-layer1-route-isolation/position-keyed-three-arm/oracle/supervisor-retry \
  --timeout 900 --interval 1 --sample-clocks -- \
  /home/calvin/.local/python/bin/python3 \
  bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_native_expert_oracle.py
```

The native Release CUDA service and parity utility rebuilt with one job. The
21-test accepted-prefix, verifier, KV, GDN, draft and graph CTest selection
passed 21/21 on the updated binary under a 28-GiB scope; minimum host/admission
availability was 24.57/24.57 GiB and sampled cgroup `high`, `max`, `oom` and
`oom_kill` counters were zero. The direct service runs and oracle retry also
passed under 28-GiB scopes, with minimum availability above 14 GiB and 24.52
GiB, respectively. This validates the keyed diagnostic in ordinary and batch
verifier builds; the tests do not close other Phase 5 state, graph-pool or
performance gates.
