# GDN verifier commit-prefix kernel check — 2026-10-09

The CUDA `gdn_parity` self-test now exercises every recurrence commit length
`n_keep=0..T` for each verify window `T=1..8`. For each case it starts from the
same state and compares the resulting GDN recurrence state bitwise with a fresh
single-token `fused_gdn_step_norm` replay. It also checks output rows retained by
the prefix. All 84 window/prefix cases pass on the native Orin CUDA build.

The test also checks `gdn_conv_commit` for all 44 pairs `T=1..8` and
`n_keep=0..T`. An independent host selection computes the last three entries of
`[history | qkv[0..n_keep)]`; all history words match bitwise, including zero
retained tokens and a 259-channel case crossing the CUDA 256-channel block edge.
The QKV input remains unchanged. Both checks pass on Orin CUDA.

The same test source compiles in the isolated maestro1 HIP build. Its binary hash
is retained, but `rocminfo` reports that the ROCk module is not loaded and no GPU
device is available there, so HIP runtime execution is unsupported. The full HIP
build log and source digest are retained here.

These are kernel-level checks for GDN recurrence and convolution state. They do
not cover Verifier graph orchestration, QSA K/V or indexer state, PLE history,
output publication/clipping, cancellation, or a multi-window model request.
Those state-transaction checks remain open. Production runtime behavior and
default dispatch are unchanged.

Reproduce the CUDA check with:

```sh
cmake --build build/integration/candidate --target gdn_parity --parallel 1
build/integration/candidate/gdn_parity --selftest
```

The maestro1 HIP command used its isolated build root with
`STRATA_BUILD_TESTS=ON` and `--parallel 1`. The only tracked source file changed
for this check is `src/kernels/gdn_parity.cpp`.
