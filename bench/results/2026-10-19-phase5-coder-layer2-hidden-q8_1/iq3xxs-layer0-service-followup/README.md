# Layer-0 IQ3_XXS/IQ4_NL Q8_1 follow-up — Orin — 2026-10-19

This follow-up resolves an invalid operator comparison in the first layer-0
investigation and narrows the current finding. The tested service binary SHA256
is in `binary-sha256.txt`; source file hashes are in `source-sha256.txt`. The
model is pinned Coder IQ1_M revision `5348543e0147355ac9cbcb031184a3546350988e`,
with shard hashes recorded in the [earlier artifact identity](../../2026-10-19-phase5-coder-layer0-iq3xxs-q8_1-mirror/artifact-identity.json).
The service binary was built from parent commit `c3bd1b98`; the local parity
harness fix and the updated capture validator are hashed separately.

The parity utility previously called `native_fmt` without the requested layer,
so a selector such as `iq3_xxs/iq4_nl@layer=0` was evaluated as layer `-1` and
silently left the baseline CPU activation format enabled. The utility now passes
its selected layer to `native_fmt`. A corrected replay of all eight CPU-owned
experts from the earlier two-row layer-0 capture (68, 119, 75, 70, 188, 204,
209 and 180) reported zero CPU/grouped-CUDA output-word differences for every
expert; its supervised log is in `operators-layer-aware/`.

A supervised fixed-residency service run captured layer 0, dispatch 0 at
position 511 (token 271) on the pinned Coder IQ1_M model. The captured route had
seven CPU-owned experts (165, 114, 55, 156, 211, 213 and 88) and three
GPU-owned experts. For each CPU row, `compare_captured_dispatch.py` replayed the
actual activation through the corrected parity utility with the layer-0 Q8_1
selector. Each replay matched the service's CPU output bit-for-bit (2,560 of
2,560 F32 words per expert); the same parity utility reported bitwise equality
against the grouped CUDA expert output for all seven rows. The service output
capture serializes F32 as nine-significant-digit JSON, so the verifier rounds
those values back to F32 before comparing.

On those same activations, the default CPU activation format produced a
different expert output from the Q8_1 mirror in every word. Relative L1
differences were 0.795%–1.410%; the Q8_1 CPU result matched grouped CUDA.
This identifies the operator-format change but does not by itself establish its
weighted MoE or recurrent-state effect.

A separate fixed-residency pair captured exact device inputs, top-10 IDs and
float32 weights, CPU expert outputs, and combined layer-0 `ffn_y` for all 16
accepted positions. At position 511/token 271, input, expert IDs, weights and
owner vectors were bitwise identical between default and Q8_1 arms. The seven
CPU experts were the same as in the direct capture. Weighting their output
deltas reconstructed the combined device-output delta across all 2,560 values:
maximum absolute residual `2.414e-8`, relative-L1 residual `1.116e-5`. The
analyzer permits later completion IDs to differ only with an explicit flag; it
still fails unless the selected position's input, token, routes, weights and
owners match exactly.

The 16 generated IDs differed at 10 positions, and every one of the 16
accepted-prefix state fingerprints differed. Thus the measured service change
is explained at the first combined layer-0 output by CPU expert arithmetic
under the changed activation format, within float32 combine rounding. This does
not qualify the Q8_1 route as a serving default, establish broad answer quality,
or prove every later state transition. The selector remains opt-in.

The pair used `MemoryMax=28G`; minimum host/admission availability was
14.365/14.365 GiB for the default arm and 14.373/14.373 GiB for the Q8_1 arm.
Both supervisors passed with zero cgroup pressure/OOM events. Clocks were
observed dynamically, EMC readback was denied, and energy was not attributed.
The four-arm fixed/adaptive service sequence is retained under `service-pairs/`:
all prompt identities matched, but format-scoped Q8_1 changed token IDs and
accepted-prefix fingerprints in the requests summarized there. It remains a
separate functional comparison, not performance or migration evidence.

All six focused IQ2_S/IQ3_XXS Q8_1 CTests passed after rebuilding the corrected
parity utility. The capture runner accepts both `strata-moe-cpu-output-v1` and
current `strata-moe-cpu-output-v2`; its first attempt completed model execution
but rejected v2 during post-run validation, so that attempt is not counted as a
passing capture run. The corrected runner and subsequent supervised capture
passed.

Reproduce the weighted layer-0 pair from the repository root on Orin:

```sh
Q8_1_SELECTOR=iq3_xxs/iq4_nl@layer=0 \
LAYER=0 \
OUTROOT=bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/layer0-weighted-pair \
  bash bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_layer_weighted_pair.sh

python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_layer_weighted_delta.py \
  --campaign bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/layer0-weighted-pair \
  --layer 0 --position 511 --token-id 271 --allow-completion-divergence \
  --output bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/layer0-weighted-pair/analysis-weighted-delta.json
```

The earlier direct capture and corrected parity replay can be checked with:

```sh
python3 bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/compare_captured_dispatch.py \
  --model "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --dispatch-jsonl bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/capture-fixed-mirror-verified/run/layer1.jsonl \
  --cpu-output-jsonl bench/results/2026-10-19-phase5-coder-layer2-hidden-q8_1/iq3xxs-layer0-service-followup/capture-fixed-mirror-verified/run/cpu-outputs.jsonl \
  --output /tmp/layer0-q8-operator-replay
```

The raw dispatch and route captures, CPU outputs, combined outputs, accepted
state traces, supervisor telemetry, analyzer results and source/build hashes
are retained here. Verify them with `sha256sum -c SHA256SUMS`. The layer-0
arithmetic cause is established for the captured position; Phase 5 remains open
for speculation, transaction/replay, cancellation, graph lifetime, other
formats and broader workloads.
