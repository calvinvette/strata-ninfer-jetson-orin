# ISTA IQ3_S layer-0 expert 474 owner and resident-kernel check

Date: 2026-11-05. This diagnostic used the two ISTA-DASLab Qwen3.8-Flash-Next
IQ3_S GGUF shards and `iq3-s-pack`, the current E0 CUDA binary, strict NInfer,
the held-out 50-token `is_prime` prompt, and a 512-token context. Both backends
generated the same 91 tokens and passed the 11-case executable oracle. The
diagnostic captures are instrumented correctness evidence; no timing is used.

## Findings

At model layer 0, sequence position 81, token ID 2912, both backends had the
same route IDs, route weights, and 2,560-value MoE input. Expert 474's output
was the only routed part that differed in the default-profile paired capture:
all 2,560 values differed, with relative L2 `0.0155154` and maximum absolute
delta `0.0008400`. Its route weight was `0.0672556`; the combined MoE output
differed at relative L2 `0.0002492`. The other nine expert outputs, shared
output, and routing matched exactly.

The selected expert's execution owner was not matched in that capture. Strata
had expert 474 in VRAM slot 686 and captured its full 2,176,000-byte weight;
strict NInfer had no resident slot (`slot=-1`, no weight bytes). Replaying the
exact captured input through `native_expert_parity` found Strata's service
output bit-identical to its native CUDA output and NInfer's service output
bit-identical to its native CPU output. This default-profile delta therefore
does not measure the NInfer resident kernel: it compares a GPU-owned Strata row
with a CPU-fallback NInfer row.

To compare the resident kernels, an experiment-only profile moved `(layer 0,
expert 474)` from rank 986 to rank 0. Both backends then reported the expert in
slot 0 with all 2,176,000 weight bytes present. The raw captured input hash was
unchanged from the default-profile capture. For the shared position/token,
routes, weights, input, every routed expert output, shared output, and combined
output were bit-identical between Strata and strict NInfer. The common output
also matched the native CUDA reference, establishing exact parity for this
single resident IQ3_XXS/IQ4_NL row and activation.

The forced-resident service pair still had differing persistent-state hashes;
its first live-field difference moved to generated-token endpoint 60, versus
endpoint 33 in the default-profile paired capture. This profile changes other
expert residency and is not a controlled state-cause ablation. It does show
that exact local kernel parity for expert 474 does not by itself resolve the
long-task state discrepancy.

## Reproduction and evidence

- Default-profile paired capture and state trace:
  [`../ista-is-prime-layer1-plus-layer0-moe-run/results.json`](../ista-is-prime-layer1-plus-layer0-moe-run/results.json)
- Forced-resident paired capture and comparator:
  [`moe-layer0-comparison.json`](moe-layer0-comparison.json)
- Same-input Strata/NInfer and native CPU/GPU output comparison:
  [`expert474-oracle-comparison.json`](expert474-oracle-comparison.json)
- Reproducible bundle/oracle analyzer:
  [`compare_expert474_oracle.py`](../compare_expert474_oracle.py)
- Exact-input CPU/GPU native oracle supervisor:
  [`../ista-is-prime-layer1-plus-layer0-moe-run/expert474-oracle-supervisor/result.json`](../ista-is-prime-layer1-plus-layer0-moe-run/expert474-oracle-supervisor/result.json)
- Native oracle output summary: `IQ3_XXS/IQ4_NL`, layer 0, expert 474;
  GPU dequantization matched GGML `to_float` for all 4,915,200 weight values.
- Forced-resident profile: local-only `/tmp/e0-ista-iq3s-layer0-expert474-first-profile.bin`;
  it is an experiment artifact and is not committed.
- Minimum available physical RAM was 19.72 GiB for the forced-resident pair;
  no cgroup memory event incremented. Clocks were observed but dynamic, EMC
  readback was denied, and energy was not measured.

This is one exact resident expert-row check. It does not qualify other codecs,
experts, prompt/prefill work, broad state parity, or end-to-end performance.
The default profile's per-request owner behavior still needs an explicit
matched-owner measurement in any performance comparison.
