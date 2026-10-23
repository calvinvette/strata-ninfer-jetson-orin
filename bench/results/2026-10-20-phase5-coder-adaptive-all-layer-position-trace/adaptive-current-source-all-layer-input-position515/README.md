# All-layer verifier input trace at position 515

This follow-up uses the same Coder IQ1_M short/long/short recovery workload and
current candidate binary as the adjacent boundary capture. It records
`STTMOINP1` verifier MoE inputs at generated position 515 for all 48 model layers,
then compares the initial and recovery short requests within each service.
Both arms passed under the 28-GiB per-arm supervisor.

Campaign seed: `2026102231`. Binary SHA256:
`081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`.
Source tree HEAD: `8e7400fdd91d53b5634aab0923c9bf0a8b7294a5`. Model:
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` IQ1_M at revision
`5348543e0147355ac9cbcb031184a3546350988e`. Each arm used the
short/long/short sequence, 12 generated tokens, prompt cache 6, configured
speculation 2, and native CPU Q8_1 dot for all eligible rows.

At this position, delayed control's 48 verifier input tensors were bit-identical
between the initial short request and recovery. Adaptive recovery first differs
at the input to model layer 12; all 2,560 values differ there (relative L2
`0.0006320`). Inputs remain different at every layer 12 through 47. Layer 16
input differs by relative L2 `0.012805`, consistent with the adjacent targeted
capture. The initial short-request verifier inputs are bit-identical between
the two arms at all 48 layers. Adaptive output tokens still matched across the
short requests, while accepted state fingerprints changed; delayed control
recovered exactly.

This locates the earliest difference visible to this capture at layer 12's
verifier input, which is after layer 11. It does not establish which layer-11
operation or state produced that difference, does not inspect embeddings before
layer 0, and does not establish generality beyond this prompt, model, and
position. No runtime source changes were made.

Minimum available host/admission memory was 14.22 GiB for delayed control and
14.32 GiB for adaptive; cgroup memory events were zero. `campaign.json` records
the arm identities and telemetry; `all-layer-input-analysis.json` contains
per-layer value counts, max differences, relative L2 values, and tensor hashes.
`SHA256SUMS` protects both input captures and their analysis.

Reproduction command:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_pair.py \
  --run --seed 2026102231 --continuations 0 --sequence short-long-short \
  --generated-tokens 12 --native-cpu-q8-1-dot all \
  --capture-verify-moe-layer 16 --verify-moe-positions 515 \
  --verify-moe-input-layers all \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-source-all-layer-input-position515
```
