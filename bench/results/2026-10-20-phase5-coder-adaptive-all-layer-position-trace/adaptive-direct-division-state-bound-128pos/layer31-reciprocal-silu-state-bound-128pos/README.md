# Layer-31 reciprocal-SiLU mirror: rejected by long-chain recovery

## Question and decision

The prior owner capture at model layer 31, position 519 found that expert 22's
CPU and CUDA rows both match their owner-specific independent oracle, but differ
from each other. This experiment tested whether using the CPU reciprocal-SiLU
expression on all eligible native CPU Q8_1 expert rows at model layer 31 would
improve the short→long→short adaptive recovery chain.

**Decision: reject this as a recovery correction.** The isolated same-input
expert-22 CPU/CUDA oracle passed bit-for-bit under the reciprocal expression,
but the full adaptive service sequence became incorrect earlier. The runtime
selector remains opt-in and off by default; this experiment supplies no speed
claim.

## Setup

- Orin AGX, same current-source binary for both arms, SHA256
  `fe9f7210ec25befa0b87d0a74385fb7208aa9e9d74a05f62272044e9af61a31e`.
- Coder GGUF IQ1_M, pinned repository revision
  `5348543e0147355ac9cbcb031184a3546350988e`; model shard hashes, prompts and
  token histories are in `campaign.json` and each arm's `result/analysis.json`.
- Randomized pair, seed `20261084`, same short→long→short request sequence,
  128 generated tokens, MTP2, native CPU Q8_1 dot selector `all`.
- Treatment selected `STRATA_NATIVE_CPU_Q8_1_RECIPROCAL_SILU_LAYER=31`; control
  delayed adaptive swaps. Raw layer-32 committed GDN state was captured at
  positions 515–519, 534, 557, 558, 574 and 638. Layer-31 verifier inputs,
  expert rows and combined outputs were captured at 515–519.
- Both arms passed service and supervisor checks. Minimum host/admission
  availability was 14.12 GiB adaptive and 14.07 GiB delayed control; sampled
  cgroup memory events remained zero. Frequencies were observed dynamically;
  EMC frequency was unavailable. Energy was not measured.

## Results

The delayed-control recovery matched all 128 tokens and its captured GDN state
was exact. The adaptive reciprocal-SiLU arm first differed at recovery output
index 6 and differed on 121/128 tokens. By contrast, the paired direct-division
adaptive baseline first differed at index 47 (73/128), while its delayed control
was exact. Thus this variant worsened the tested adaptive recovery outcome;
this single seed does not establish a general effect size.

The reciprocal arm already had a large state difference at the first captured
position 515, although the consumed token IDs there still matched: layer-32
recurrent state differed in 786,391/786,432 values (relative L2 `0.001685`),
and convolution history differed in 10,240/30,720 values (relative L2
`0.006613`). Token histories diverged by position 518, so later comparisons
include different inputs. At position 515 the layer-32 GDN input `x` was also
the first differing captured field (all 2,560 values; relative L2 `0.02013`),
showing that the state delta arrived downstream of earlier changed layer
outputs. The existing prefix diagnostics show changed layer-31 router weights,
expert parts and combined output in this candidate run, so the full-sequence
worsening cannot be attributed only to the expert-22 row isolated at position
519 in the baseline capture.

The owner-specific single-row parity check is still useful: with both
`STRATA_NATIVE_CPU_Q8_1_DOT=iq3_xxs/iq4_nl@layer=31` and reciprocal-SiLU layer
31 selected, the independent oracle reported 0/60 differing hidden blocks and
0/7,680 differing output words for that captured activation. The full-chain
result demonstrates why an isolated operator match cannot qualify a
state-transaction correction. See `adaptive-cap8/result/` for captures and
analysis, and the paired direct-division baseline at `../README.md`.

## Next step

Keep the arithmetic selector opt-in and default-off. Resume Phase 5 by
localizing the earlier state/activation changes in the adaptive chain and
checking additional owner-transition contributors with accepted-prefix hashes,
raw committed state and token history. Any candidate must improve the complete
recovery sequence against a same-day delayed control and then repeat on a
held-out seed/prompt before it can be considered a correction. Matching final
text alone is not a gate.
