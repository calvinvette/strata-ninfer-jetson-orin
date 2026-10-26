# HIP build of model-layer GDN crossover replay

Date: 2026-10-26. Exact source commit: `32f04b5695fe9aa6afa540f1b84114a3d17a11fa`.
The changed source is `src/kernels/gdn_parity.cpp`; the configured HIP target
compiled and linked with parallelism 1.

| Target | Build | Runtime check | Binary SHA256 |
| --- | --- | --- | --- |
| `gdn_parity` (HIP / ROCm 7.2.53210, `gfx1100`) | Passed | `--selftest` stopped before kernel cases: `no ROCm-capable device is detected` | `5d26345b4a96d9c1c2fb0fd769ed54f358c5890e532ba726c6c01caf25503ded` |

The host therefore supplies HIP compile/link evidence only for this edit. The
Orin CUDA build, 84-case self-test, layer-1 compatibility replay, and new
model-layer-5 replay are recorded in the [E6 layer-boundary report](../../../2026-10-26-e6-q2-staged-retrieval-2k/evidence/layer-boundary-localization/README.md#gdn-state-history-crossover-at-model-layer-5). No HIP device execution or Orin performance result is inferred from maestro1. The configured SYCL parity source is separate (`sycl/src/kernels/gdn_parity.cpp`) and was not changed.

The compressed compiler/linker output is `hip-build.log.gz`. Build tree and
binary remain on maestro1 under
`/mnt/sda2/tmp/calvin/strata-ninfer-build-e0-1f9f116b/`.
