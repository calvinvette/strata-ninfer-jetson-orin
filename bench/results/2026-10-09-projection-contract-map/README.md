# Projection contract map — 2026-10-09

All 48 Strata Coder layers (108 selected projection tensors) are incompatible
with direct reuse of the pinned NInfer two-parent GDN/attention projection
profiles. This is a source-header/contract decision, not a failed numerical
kernel, implemented converter or rejection of all possible NInfer adaptation.
The tool preserves per-layer symbols, formats, logical matrix dimensions,
required parents and individual reasons. Its required-profile invocation exits2
while retaining the report; no model process or execution route is started.

The source inventory is the independently identified GGUF cohort from the
[paired controls](../2026-10-09-paired-api-controls/README.md). Selected projection
formats comprise 62 Q6_K, 19 Q5_K, 14 IQ4_XS and 13 Q4_K tensors. The distribution
filename IQ1_M does not describe these tensors. Source GGUF encoding also does
not prove the prepared runtime's split-plane or activation contract.

## Shape and arrangement differences

| Family | Strata source projections | Pinned NInfer two-parent profile | Decision |
| --- | --- | --- | --- |
| GDN, 36 layers | QKV [10240,2560] plus gate/Z [6144,2560] | QK [4096,5120] Q4G64_F16S plus value/Z [12288,5120] Q5G64_F16S | Hidden width, codecs and parent arrangement differ |
| Full attention, 12 layers | Q/gate [12288,2560], K/V each [512,2560] | Query/key and gate/value each [7168,5120], RowSplit Q4/Q5 group64 | Hidden/KV widths, codecs and head arrangement differ |

Dimensions here are [output rows,input columns], reversed from the GGUF
fastest-axis-first inventory. Strata's `qsa_layer` copies each head's first half
from its interleaved Q/gate projection (`cudaMemcpy2DAsync`); a blind contiguous
Q/gate split would permute heads incorrectly. GDN uses separate QKV and gate/Z
source parents. NInfer's documented arrangement is QK plus concatenated value/Z.
Both pinned NInfer profiles require contiguous BF16 activations/outputs. Header
shape agreement alone cannot establish that represented-type contract.

The checked map covers these two-parent signatures only. Other single-parent
specializations, other operators/codecs, persistent state, runtime weight planes,
conversion fidelity/cost and performance are explicitly excluded. A future
adaptation must separately qualify parent rearrangement, head layout, dtype,
codec and independent operator math before timing. The existing independent
IQ4_NL codec diagnostic does not qualify these projection codecs.

## Reproduce

```sh
python3 tools/integration/projection_contracts.py \
  --inventory bench/results/2026-10-09-paired-api-controls/evidence/coder-tensor-inventory.json \
  --output build/integration/NEW_PROJECTION_MAP.json --require-direct-profile
```

Omit `--require-direct-profile` to produce an informational report with exit0;
the recorded layer decisions remain incompatible. Output creation is exclusive,
so earlier evidence is preserved. Missing/ambiguous families, missing projection
tensors, duplicate symbols and invalid dimensions fail instead of guessing.
A matching shape or a misleading format label still cannot prove RowSplit
planes. Tests cover these failures and the required CLI's report retention;
the full integration harness passes 46 tests. No production/backend source is
changed by this preparation. Pinned references and source identities are retained
in `identities.json`, with NInfer revision b07248f2 recorded in the full map.
