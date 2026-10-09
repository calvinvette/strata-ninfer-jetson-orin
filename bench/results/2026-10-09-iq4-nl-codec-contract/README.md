# Independent IQ4_NL codec diagnostic — Orin, 2026-10-09

The existing scalar CPU decoder and CUDA F32/BF16 dequantizers pass 14 synthetic
cases against an independent arithmetic/rounding oracle. There are 3,726,080
represented values per implementation. Exact bits include signed zero; packed
inputs and output guards are preserved. No production source, default, codec,
allocation policy or dispatch is changed. No NInfer implementation is promoted.
This is Phase 2 contract preparation while Phase 1 backend qualification remains
pending, not completed Phase 2 or a performance result.

## Contract and oracle

IQ4_NL has 32 elements in an 18-byte block: a little-endian FP16 scale and 16
packed bytes, low nibble elements0–15/high nibble16–31, indexed through the
pinned nonlinear table. Format data comes from ggml `3cf03257` (MIT); existing
notices remain. The original integration oracle states the table independently,
interprets FP16 using FP64 significand/exponent arithmetic, and rounds to BF16
by searching adjacent represented values and comparing distances, with even
codes on ties. It does not use production half/BF16 helpers. Seven known-value
anchors check subnormal/unit/maximum half values, both tie directions, a negative
tie and signed zero before testing the codec.

Criteria were recorded in [OPERATOR_CONTRACTS.md](../../../docs/integration/OPERATOR_CONTRACTS.md)
before the GPU run: exact CPU and CUDA F32 bits, exact BF16 nearest-even bits,
unchanged input and guards. Finite FP16 times a seven-bit integer fits exactly
in F32, justifying the criterion independently of observed candidate errors.

The exhaustive case covers all 63,488 finite FP16 scales and all sixteen codes
in both halves. Other cases cover row0=2 slicing, rows1/3, columns32/256/288/640/
2560/10240, and a full synthetic 2560x640 down matrix at row0=3. The real verified
artifact inventory has `blk.0.ffn_down_exps.weight` shape[640,2560,256] in fastest
axis order; the full single-expert case matches its matrix shape. Synthetic
blocks vary scales and code order across rows and block boundaries.

Nonfinite scales, invalid-shape behavior, FP16 output, real tensor payloads,
other codecs, NInfer RowSplit conversion, kernel speed, model quality and
accepted-prefix state are excluded. The launched operator remains the existing
Strata route; BF16 storage equality does not imply format interchangeability.

## Reproduce and inspect

Use the already pinned llama.cpp checkout; no downloads or dependency fetching:

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_GGML_DIR=/tmp/strata-orin-build/_deps/strata_llamacpp-src
cmake --build build/integration/operator-tests --target iq4_nl_codec_contract --parallel 2
python3 tools/integration/run_control.py --output build/integration/NEW_CODEC_RUN \
  --timeout 180 -- build/integration/operator-tests/iq4_nl_codec_contract
```

Without an explicit ggml path, CMake leaves this codec target unconfigured;
weighted RMS remains available. Missing GPU returns77 (skip, not pass).
The first diagnostic link failed because the existing dequant translation unit
also references IQ dispatch functions. Its log is retained. The standalone
build now includes the existing IQ translation unit and explicitly pinned ggml
headers; both final compilation and the bounded GPU run succeed. These linked
IQ paths are not exercised or qualified by this diagnostic.

The run preserves the six GiB sampled physical/cgroup floor; sampled minimum
MemAvailable is 26,472,456,192 bytes (~24.66 GiB). CUDA12.6 Release SM87 uses the
existing fast-math kernel build option and a nondefault nonblocking stream.
Clocks/services/JetPack are unchanged. Tegrastats is raw; no energy or latency
comparison is claimed. Source/header/binary digests are in `identities.json`;
models and compiled binaries are not published. Both private CTest targets are
registered; the raw supervisor result is the authoritative executed codec pass.
