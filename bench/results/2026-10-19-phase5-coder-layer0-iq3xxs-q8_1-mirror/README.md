# Coder layer-0 IQ3_XXS/IQ4_NL Q8_1 mirror — Orin — 2026-10-19

This diagnostic extends the opt-in `STRATA_NATIVE_CPU_Q8_1_DOT=1` CPU route
from IQ2_S experts to the Coder's IQ3_XXS gate/up plus IQ4_NL down pair. The
IQ3_XXS integer dot follows Strata's CUDA Q8_1 formula, including packed grid
signs, scale correction, 32-lane accumulation and XOR warp reduction. Default
dispatch remains unchanged. Source identity, model revision, shard hashes,
activation hashes, and binary hashes are in `artifact-identity.json`; the exact
source overlay from commit `9d3f86aa` is retained with its SHA256.

The local candidate build passed six Q8_1 parity CTests covering IQ2_S/Q2_0,
IQ2_S/IQ4_NL and IQ3_XXS/IQ4_NL, for single-width and widths 1–8. On Orin, the
actual two-row layer-0 dispatch-0 activation for expert 70 was replayed against
the pinned IQ1_M Coder GGUF. The default CPU-vs-CUDA expert relative-L1 delta
for this capture was 1.52%; the opt-in Q8_1 route reduced it to `2.46e-8`
(1,302/5,120 F32 words differed). The first captured row tested at widths
1–8 remained width invariant for the CPU route; CPU-vs-CUDA relative L1 was
`2.44e-8` at every width. The independent IQ4_NL down check had zero Q8_1
scale/code mismatches across 20 blocks and zero CPU/CUDA output-word
mismatches across 2,560 values. These are one expert and captured activations,
not an all-layer parity claim. Raw supervised runs and the retained row-zero
activation are in this directory.

A same-day service comparison used the same rebuilt binary and model for four
requests per arm: 512-token short, 2,048-token long, 512-token recovery and a
short continuation; each generated 16 tokens. The adaptive pair used cadence 4,
swap budget 8 and accepted-only updates. The fixed pair disabled adaptive swaps.
Both used prompt cache 0, spec 2, 8K maximum context, dynamic clocks and a
28-GiB `MemoryMax` scope. That service comparison set
`STRATA_NATIVE_CPU_Q8_1_DOT=1`, so it enabled all supported pairs and does not
attribute its state changes to IQ3_XXS alone. The format-specific follow-up is
recorded in [the IQ3-only service diagnostic](../2026-10-19-phase5-coder-layer0-iq3xxs-only-service/README.md).

| Residency | Requests with differing token IDs (default vs Q8_1) | Persistent-state fields differing | Minimum host/admission availability across pair |
| --- | --- | --- | ---: |
| Adaptive | Short 10/16; long 0/16; recovery 10/16; continuation 0/16 | 6–7 of 9 fields on each request | 14.27 / 12.66 GiB |
| Fixed | Short 0/16; long 3/16; recovery 0/16; continuation 0/16 | 6–7 of 9 fields on each request | 14.27 / 14.27 GiB |

All four supervisors passed, all adaptive blob/residency verification checks
passed, and cgroup low/high/max/OOM counters stayed at zero. The raw request
IDs, accepted-prefix state fingerprints, memory samples, service logs and
tegrastats are under `service-pair/`; `analyze_pair.py` regenerates the paired
summary. The result shows that better IQ3_XXS/IQ4_NL operator agreement does not
make service state identical or establish migration correctness. The opt-in
route is diagnostic only. These are functional checks, not a speed, energy or
answer-quality comparison; no default or supported profile changed.

Reproduce the six focused tests with:

```sh
ctest --test-dir build/integration/candidate --output-on-failure \
  -R 'native_expert_parity_iq(2_s|3_xxs)_.*cpu_q8_1'
```

Reproduce the captured two-row operator check from the repository root with:

```sh
STRATA_NATIVE_CPU_Q8_1_DOT=1 \
  build/integration/candidate/native_expert_parity \
  "$HOME/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf" \
  --expert 70 --activation-f32 \
  bench/results/2026-10-19-phase5-coder-q8-1-real-windows/layer0-dispatch0-nt2-activations.f32 \
  --activation-rows 2 --token-width 2 0
```

This leaves Phase 5 open. Adaptive migration and complete accepted-prefix state
parity remain unqualified.

The exact-source [maestro1 HIP/SYCL build record](backend/maestro1/README.md)
confirms cross-backend compile/link only. Both Strata help commands passed;
the HIP parity utility does not implement `--help`, so that invocation is not
a runtime check. No accelerator runtime result is claimed.
