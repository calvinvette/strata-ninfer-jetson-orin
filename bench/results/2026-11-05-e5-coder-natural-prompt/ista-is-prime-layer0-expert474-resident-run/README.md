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

## Persistent-state capture sensitivity

Under the same forced-resident binary and profile, the light capture
(`moe-bundle layer 0 + moe-exec expert 474`) reproduced persistent-state drift
in two pairs: full hashes first differed at endpoint 50 (`stale`), live hashes
at endpoint 60, and 50/80 shared endpoints matched. A layer-0 bundle by itself
also differed (first full endpoint 32, live endpoint 41; 32/80 matched).
Four fresh trace-free final-only pairs returned identical task tokens and
passed the code oracle. Cross-backend final state matched in only one pair.
Across the four runs, Strata produced two distinct final fingerprints and
NInfer produced four; the two backend orders were balanced 2/2. The differing
pairs changed `gdn`, `ple`, `tail`, `pooled`, `kv` and `pooled_full` hashes.
This is evidence of state instability without accepted-prefix tracing or
layer-dump hooks; it does not attribute the cause to the NInfer kernel because
ownership of all other routed experts was not fixed.

By contrast, the standalone `moe-exec` capture matched all 81 shared state
endpoints, and all-layer MoE bundles at either position 81 or 109 matched all
80 shared endpoints and final hashes. The combined all-layer MoE/GDN capture
also matched every recorded endpoint; at position 109 its 48 MoE layers and
all 36 GDN commit states were bit-identical. All eight cases used the same
binary hash, forced-resident profile hash, model, prompt and output token IDs.
The diagnostic mode therefore correlates with the state result. Its cause is
unknown; the exact-state dump modes are observer-sensitive and are not used as
service parity qualification. The default-profile comparison also changed the
actual owner, so neither profile comparison isolates the full-sequence cause.

The canonical default-profile comparison adds a second view of this behavior.
Four trace-free pairs, balanced across backend order, passed the task oracle and
emitted identical tokens. Both Strata-first pairs had unequal cross-backend
final hashes; both NInfer-first pairs matched. Each backend produced two
distinct fingerprints across the four cross-backend runs. Separate pairs of
back-to-back fresh Strata processes and fresh NInfer processes matched their
tokens and final hashes internally. The Strata self-control had a third
fingerprint relative to the cross-backend campaign; NInfer repeated an earlier
one. This supports immediate same-backend repeatability, but not stable hashes
across campaigns. The cross-backend outcome associates with order in this small
sample but does not establish the mechanism or implicate NInfer, since all routed
expert owners were not fixed. See the [default-profile final-state
repeats](default-profile-final-only-repeats.json).

See the [capture-sensitivity matrix](state-capture-sensitivity.json). This
confirms that exact local kernel parity for expert 474 does not resolve the
long-task state discrepancy or its instrumentation sensitivity.
The four [trace-free final-state repeats](final-only-state-repeats.json) are
the higher-confidence evidence that state divergence is not limited to the
accepted-prefix trace or single-layer capture path.

## Reproduction and evidence

- Default-profile paired capture and state trace:
  [`../ista-is-prime-layer1-plus-layer0-moe-run/results.json`](../ista-is-prime-layer1-plus-layer0-moe-run/results.json)
- Forced-resident paired capture and comparator:
  [`moe-layer0-comparison.json`](moe-layer0-comparison.json)
- Forced-resident run telemetry and command:
  [`../ista-is-prime-layer0-expert474-resident-supervisor/result.json`](../ista-is-prime-layer0-expert474-resident-supervisor/result.json)
- Same-input Strata/NInfer and native CPU/GPU output comparison:
  [`expert474-oracle-comparison.json`](expert474-oracle-comparison.json)
- Persistent-state diagnostic-mode matrix:
  [`state-capture-sensitivity.json`](state-capture-sensitivity.json)
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
