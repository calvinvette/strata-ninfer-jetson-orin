# Independent Q6_K codec diagnostic — Orin, 2026-10-09

The existing scalar CPU decoder and CUDA F32/BF16/FP16 conversions pass 15
cases against an independent oracle. Each route agrees in exact represented
bits for 42,565,632 values. Packed inputs and output guards remain unchanged.
The [contract was hashed before the first GPU run](q6-codec-contract-before-run.md);
its identities are retained. The shared independent FP16/BF16 oracle is original
test code and is not included in production. No NInfer code is copied into the
diagnostic, and no production route/default or codec is changed.

## Contract and execution

Pinned ggml revision `3cf03257f219afbe7334045ff7c6a06ac68c627d` defines Q6_K blocks
as 256 signed quants per210 bytes, with low fields at0–127, high two-bit fields
at128–191, signed int8 subscales at192–207 and little-endian global FP16 scale
at208. Fixtures begin with logical signed quant/subscale arrays and pack each
logical element to the mandated locations. Expected values come from those
retained arrays and an FP64 half/exact-product oracle; they are not reconstructed
by either decoder. Independent pack-placement anchors run first.

The predeclared exact-bit criterion is valid because 11-bit half significands,
7-bit subscales and 5-bit non-power-of-two quant magnitudes need at most23
significant bits; even the ±128/−32 power-of-two endpoints fit exactly in F32.
Nearest BF16/FP16 is selected by adjacent-value distance and ties to even. The
FP16 maximum/overflow boundary is checked. Synthetic finite inputs can correctly
convert to infinity in FP16; that does not qualify real-model quality.

The 15 cases cover every63,488 finite FP16 scale and all quant/subscale lanes,
all256 signed subscales × all64 signed quant values, row0=2 slicing, rows1/3,
columns256/512/768/2560/6144/10240, and the full synthetic10240×2560 GDN QKV
matrix at row0=1. A nondefault CUDA stream is synchronized before comparison.
Q6_K uses real inventory shapes but synthetic payload. IQ4_NL runs as a separate
regression in the same CTest command: 14 cases/3,726,080 exact values.

The bounded supervisor passes in15.89 seconds. Minimum sampled MemAvailable is
26,097,229,824 bytes (~24.30 GiB), with the six GiB physical/cgroup floor intact.
Build is CUDA12.6 Release SM87; the private test kernel library uses fast math,
and model processes remain under the standard supervisor lock. Clocks, services,
and JetPack were not changed. Tegrastats is raw, with no energy claim. No model
weights or profiler binaries are included.

## Boundaries

This validates selected format decoders and output rounding only. It does not
validate a real tensor payload, all codec adapters, the projection arithmetic,
BF16-vs-F16 model quality, persistent state, NInfer kernel equivalence, or speed.
The profiled Q6_K materialization is a later experimental target: any cache or
kernel change must first establish actual physical backing/lifetime, then compare
held-out unprofiled requests and the accepted numerical/state gates.
See [projection contracts](../../../docs/integration/OPERATOR_CONTRACTS.md) and
[request profile](../2026-10-09-request-profile/README.md).

## Reproduce

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_GGML_DIR=/tmp/strata-orin-build/_deps/strata_llamacpp-src
cmake --build build/integration/operator-tests --target iq4_nl_codec_contract q6_k_codec_contract --parallel 2
python3 tools/integration/run_control.py --output build/integration/NEW_CODEC_RUN \
  --timeout 240 -- ctest --test-dir build/integration/operator-tests \
  -R '(iq4_nl|q6_k)_codec_contract' --output-on-failure -V --parallel 1
```

No fetch occurs. Missing GPU is CTest skip77, not a pass. Logs retain all initial
cases, commands, physical samples, declared criteria and source digests. The
CTest command that actually passed is authoritative for this checkpoint.
