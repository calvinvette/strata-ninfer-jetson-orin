# Current-source layer-27 owner transition at generated position 515

This is one same-service correctness pair, not a performance measurement. It
uses the current-source Orin CUDA binary and Coder IQ1_M model listed in
`campaign.json`, with `STRATA_NATIVE_CPU_Q8_1_DOT=all`, prompt cache disabled,
and three repetitions of the same 512-token request with 12 generated tokens.
The adaptive arm uses cap 8; the delayed arm retains the CPU owner. Both
supervised arms passed.

At layer 27 / position 515, the adaptive arm's expert 129 owner codes were
CPU, CPU, CUDA (`-1, -1, 0`); the delayed arm remained CPU (`-1, -1, -1`). The
captured verifier activation and route were identical across all repetitions.
The analyzer also joins the owner trace to the verifier activation when the
owner record carries valid activation values. Expert 129's output part, shared
output, and combined MoE output were bit-identical across the three repeats in
each arm. The generated token IDs matched across repeats and between arms.
Committed GDN snapshots for all 36 GDN layers were bit-identical across the
three requests in each arm and had the same raw SHA256 in both arms.

Minimum physical/admission availability was 14,799,085,568 bytes (13.78 GiB)
in the adaptive arm and 14,846,971,904 bytes (13.82 GiB) in the delayed arm.
These values preserve the six-GiB host headroom; see per-arm supervisor records
in the local run outputs for memory-event counters.

Reproduce the compact checks with:

```sh
python analyze_capture.py --campaign campaign.json --output /tmp/analysis.json
```

`analysis.json` is the checked output. `analyze_capture.py` validates capture
formats, token/route joins, the owner transition, selected output hashes and
all-layer committed-state equality. Raw captures and the tested binary/model
remain local and are not tracked. This result does not reproduce the historical
layer-27 expert-175 observation: the current test is expert 129 at generated
position 515, under the stated build and selector. It does not establish a
general CPU/GPU parity guarantee, quality qualification, performance benefit,
or Phase 5 completion.
