# Layer-2 owner equivalence with service expert-row capture — Orin — 2026-10-19

This follow-up records the verifier's per-expert outputs immediately before
router-weighted combination. It revisits the earlier layer-2 owner-placement
counterexample after the IQ4_NL CPU Q8_1 dot was corrected to use the grouped
CUDA service reduction schedule in commit `c3bd1b98`. The earlier results remain
available in the parent report and are not deleted or reinterpreted.

The test used IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. It used the same 512-token Coder
prompt and matched 3,007-slot profiles as the prior owner-placement check. One
profile kept seven layer-2 IQ2_S/IQ4_NL experts on CPU; the other placed those
seven experts on CUDA. Each arm generated 16 greedy tokens. The current-source
binary hash is in `binary-sha256.txt`; the checked-out base commit was
`6eda7595`. The small opt-in capture overlay is retained in
`service-parts-source.diff`, with file hashes in `source-sha256.txt`.

Three paired blocks captured exact device routes, all ten expert output rows,
and the combined layer-2 `ffn_y` for positions 511–526. In every block, the
device expert IDs and router weights, every expert output value, and every
combined `ffn_y` value matched bit-for-bit between owner profiles. All 16
accepted-prefix state fingerprints and all 16 completion IDs also matched in
each block. Thus the prior layer-2 service divergence was not reproduced with
the corrected grouped Q8_1 arithmetic on this current-source binary. This is
fixed-residency correctness evidence for this model, prompt, selector and
layer; it does not qualify adaptive migration, other formats or layers, and it
is not a performance or quality result.

The three confirmation blocks used the CPU-mirror arm before the GPU-target arm
in each block. They are correctness replications, not randomized timing
comparisons. Minimum host and admission availability across all six arms was
16.058 GiB; all six 28-GiB supervisors passed and recorded zero `high`, `max`,
`oom` or `oom_kill` events. Clocks remained dynamic; EMC readback was denied and
energy was not measured. Per-block checks and raw captures are retained under
[`owner-confirm3-retry1`](owner-confirm3-retry1/), with a checksum manifest in
[`SHA256SUMS.txt`](SHA256SUMS.txt). The earlier wrapper attempt and its missing
optional prefill dump are retained under `owner-confirm3/`; the service itself
completed, and the corrected wrapper now supports runs without that dump.

Before capturing the complete service rows, the seven moved experts were also
replayed individually on the exact position-511 input. Every CPU/GPU output
pair had matching SHA256, but that isolated parity check did not establish the
grouped service result; see the [replay record](../weighted-replay-retry1/operator-retry1/replay.json).
The verifier capture closes that gap by checking all routed expert rows at
their actual service boundary.

The added capture is off unless both `STRATA_VERIFY_DUMP_MOE_PARTS_LAYER` and
`STRATA_VERIFY_DUMP_MOE_PARTS_PATH` are set. It allocates one bounded pinned
host buffer, queues copies on the verifier stream after the service's CPU and
GPU expert rows are complete, and appends versioned `STMPART1` records. The
service-parts parser independently checks those records against captured device
routes, combined MoE output, accepted-prefix hashes, supervisor floors and
cgroup events. The regular no-capture path was exercised by the seven focused
current-source CUDA CTests in `ctest-current-source/`.

The CUDA candidate build used two jobs on Orin. The updated shared verifier
source also compiled and linked into the maestro1 HIP binary with two jobs;
`strata --help` exited 0 after loading the ROCm runtime libraries. The SYCL
port has its own migrated `sycl/src/core/verify.cpp` and
`sycl/include/strata/core/verify.hpp`; neither was changed by this CUDA/HIP-only
diagnostic, and the current maestro1 SYCL target had no work to rebuild. No
SYCL runtime or accelerator-execution claim is made.

Reproduce the three confirmation blocks from the repository root with:

```sh
for seed in 20261021 20261022 20261023; do
  DUMP_PREFILL_GDN=0 SEED="$seed" \
    OUTROOT="/tmp/layer2-service-parts/block-$seed" \
    bash bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/run_device_route_check.sh
done
for seed in 20261021 20261022 20261023; do
  python3 bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/analyze_service_parts.py \
    --campaign "/tmp/layer2-service-parts/block-$seed"
done
```

The focused CUDA regression command was:

```sh
ctest --test-dir build/integration/candidate --output-on-failure \
  -R 'verify_batch_parity|native_multi_parity|route_window_parity|native_expert_parity_iq2_s_iq4_nl_cpu_q8_1|q8_1_(scalar|neon)_contract'
```

All seven selected tests passed. This closes the specific fixed-residency
layer-2 Q8_1 owner-equivalence counterexample; Phase 5 remains open for its
other state, speculation, graph, cancellation and workload gates.
