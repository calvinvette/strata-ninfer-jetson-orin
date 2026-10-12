# Phase 4 Q8_1 NEON Q2_0 API screen

This three-pair screen checks whether the opt-in Strata-contract Q8_1 NEON
quantizer's operator improvement changes a Q2_0 serving request. It is a screen,
not the seven-pair held-out confirmation required to promote a product result.

## Setup

- Host: Orin AGX, ARM64, CUDA 12.6 / SM87; clocks were observed dynamically and
  not controlled. EMC clock reads were unavailable due to permission denial.
- Model: `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-Orin-validation`, Q2_0 GGUF plus the
  existing `q2-ple-pack`, profile and tokenizer under
  `~/models/strata-orin-validation/`. The model files were not copied into Git.
- Serving: expert cache 3,000, prefill chunk 64, context 8,192, speculation 4,
  prompt cache disabled, prefill CPU share 0, and existing 3-GiB workspace
  reserve. The baseline and candidate used the same binary; the candidate set
  only `STRATA_Q8_1_NEON=1`.
- Workload: a held-out synthetic blue case-file prompt, exactly 512 formatted
  tokens, eight generated tokens. The same prompt was used in each randomized
  baseline/candidate pair. Each fresh process warmed with a different 512-token,
  one-output-token prompt.
- Admission: outer process memory cap 28 GiB and the normal six-GiB minimum
  `MemAvailable` floor. No clock changes or services were stopped.

## Results

| Pair | Baseline request (s) | NEON request (s) | Paired delta | Baseline prompt (ms) | NEON prompt (ms) | Text matched |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 0 | 22.390 | 22.800 | +1.829% | 20,513.8 | 20,992.9 | Yes |
| 1 | 22.771 | 22.646 | −0.545% | 20,910.4 | 20,730.6 | Yes |
| 2 | 22.482 | 22.487 | +0.019% | 20,529.7 | 20,620.9 | Yes |
| Median | 22.482 | 22.646 | +0.019% paired median | 20,529.7 | 20,730.6 | 3/3 |

All API harnesses passed with 512 prompt tokens and eight completion tokens.
Generated text matched byte-for-byte in every pair. Median prompt time was
0.444% slower for NEON. Minimum observed `MemAvailable` was 18.04 GiB; the
lowest admission sample was 9.28 GiB, above the six-GiB floor. No request
failure or memory-floor violation occurred.

This is consistent with a small CPU quantization component in a GPU-dominated
request; the total-request differences are within the variation visible across
these three pairs. The operator result does not translate into an observed
end-to-end improvement in this cell. Keep the scalar default and the NEON
candidate opt-in. Do not infer performance or quality for other prompts,
contexts, cache sizes or concurrent CPU/GPU loads.

Raw per-process telemetry, requests, engine logs and clock samples are retained
under `campaign/block-{0,1,2}-{baseline,candidate}/`. The exact workload tokens
are identified by SHA256
`149ebdf69bedc11f93d7788cc0ad1dabc77b659c33e26194d63b752945641d5a`; built
Orin binary SHA256 was
`66cf3491ee06a30f340d8210084626fad78c730ccc819d9f15f167f4c0291a62`.

## Limits

Three pairs are exploratory; no confidence interval is claimed. The generated
response was short and deterministic under this harness, which establishes
parity only for this prompt and setup. Energy was not measured. EMC clocks were
unavailable. The prompt was constructed for a repeatable 512-token case rather
than drawn from a natural task distribution. A held-out prompt/context screen
and seven-pair confirmation would be needed before claiming a serving benefit;
the current result does not warrant that effort for this candidate absent a
stronger measured bottleneck.
