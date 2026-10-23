# maestro1 HIP/SYCL rebuild for the current CPU expert selector — 2026-10-22

The current `src/kernels/cpu/native_expert.cpp` (SHA256
`7e218ba3be5fd1e59c55f51965625b874b26d82568cf741ce039a66369788955`) was
copied into the isolated Strata validation source snapshot on maestro1. Both
existing HIP and SYCL builds rebuilt and linked `strata` with one job. The
HIP build rebuilt the CPU expert source and linked the service; SYCL rebuilt
the same CPU expert source, library and service. Both `strata --help` checks
passed after supplying the toolchain runtime library paths. Build output and
binary hashes are retained under `logs/`.

The first SYCL build attempt failed because `icpx` scratch defaulted to the
full `/tmp`; the retry used the writable validation `TMPDIR` and succeeded.
An initial help attempt omitted runtime libraries and was repeated with the
ROCm/oneAPI library paths. No accelerator device or model was exercised.
maestro1 is x86_64 build evidence only, not Orin performance evidence.

## Follow-up after adding the reciprocal-SiLU experiment selector

The refreshed CPU expert sources were copied into the same isolated source
snapshot and verified by SHA256: `native_expert.cpp`
`582f9e9bfe18f930f04962ffa2c166f76576c89f625d5ed5a5782cae33234dc0`, and
`native_expert.hpp`
`5dbd51a09db94b22801f26c17d584f395591bacc4823f2596765b8a811d281c3`. The
HIP service rebuilt and linked; its current binary hash is
`4e59797ae37d125ebcc7fccd4c6d0831c02e53cbfd26c861f25030ea088d8117`, and
`strata --help` returned 0.

The current SYCL target compiled all 20 build steps and linked after adding the
installed oneMKL library directory to `LIBRARY_PATH`. Its binary hash is
`09bb41c00196c41ca15cf4fb41a53d03a21592b521a3aa8c69a0482a11a1cd4c`. A
current `strata --help` attempt aborted with exit 134 and no diagnostic text,
so startup is unsupported/unqualified for this exact snapshot. No SYCL device
or accelerator runtime was exercised. This remains x86_64 build evidence only.

## Expert-specific selector rebuild

After threading model expert IDs into the multi-token native expert jobs for the
expert-22-only experiment, the refreshed shared sources matched these local
SHA256 values: `native_expert.cpp`
`ecf3720044912cdc3ff4ec7579b48d3397657cf2ca5853b178af6c0f0c7dfde3`,
`native_expert.hpp`
`622e4466139407f8ba8d1dfc4cd3e90791656116af24fa7f224a51b1da180b21`,
`pool.cpp` `3af253b65e7db288d29b666c3df51f13f7ae8a31d5cf9ca9ce4b1a8298f4d8e7`,
`pool.hpp` `8f8dd3635625b51134e7ac9572ad3af05a0c594d99289438a6d541cdc9d64529`,
and `expert_source.cpp`
`a24607c850e8096a75ad9646acb41d33e0163ae1cbf8d90259b83a2490d37121`.
Current HIP linked as `2f276bc3b05620087df2d7199630a6b5cda01726e2daf18942234b9cd0a90b76`
and `strata --help` returned 0. Current SYCL compiled and linked as
`de638d6d018296332522f88059f9be32dd7fe416eba4efbd84b690b2f6f5af59`; its
`--help` attempt again aborted with exit 134 and no diagnostic. There is no
SYCL runtime/device qualification here.

## Full current-worktree backend rebuild

To verify all latest shared CPU expert and capture changes, a clean source
snapshot excluding build products and model data was copied to maestro1's
scratch volume. The seven touched shared source/header files matched the local
worktree byte-for-byte; hashes are in `current-source-sha256.txt`. Fresh HIP and SYCL
Release builds both completed with two parallel jobs. `strata --help` returned
zero for both binaries when their respective ROCm/oneAPI runtime paths were
loaded. SHA256: HIP `48bb73fe59de60146bc55b9af2676276ad41a639c01f6b8c1c9edf615eeccb6f`;
SYCL `1d17ee99c46d622e35c52d64f170cd0d0c934dbfd8322c462850beaa19e11dc8`.
The fresh logs and toolchain build trees remain on maestro1 scratch. The Intel
environment emitted advisory setup warnings; the help process still exited 0.
No accelerator runtime, model execution or performance was tested. This is
x86_64 compile/link and CLI-startup evidence only.


## One-token native oracle output dump — 2026-10-22

`native_expert_parity` now emits a reconstructed single-token CPU output when
`--dump-f32-dir` is used. The 1-vs-N-token check requantizes the one-token
gate/up result before its down projection, then checks the complete output. The
current Orin CUDA target rebuilt successfully; the real Coder expert-11
checks passed on both captured activations, including the 1-vs-3-token output
check. The focused `native_expert_parity_iq2_s_q2_0_cpu_q8_1_windows` CTest passed
(1/1), and the Q8_1 1–8 window contract passed on the same model. The one-token
CPU result matches the three-token diagnostic result bit-for-bit.

The changed source SHA256 is
`b22cc3722da428c5881dd9c265b829e167f2fcd2864b4a4938556ad4943ded30`; the Orin
CUDA diagnostic binary SHA256 is
`5450b245c313ef81e95647d4bbc0b707447a827f4c0bc1a18d6e85a382a6280b`. The same
source hash was copied to maestro1's isolated source snapshot; its HIP
`native_expert_parity` target rebuilt and linked with two jobs (HIP binary
SHA256 `4f8fc9018b7520dd2e465683b1541df880c14f0a83dd0072bc764f2f91e89552`). The
HIP CPU-only Q8_1 selector contract passed. This source file is in the
CUDA/HIP-only parity target; the SYCL-only configuration does not build that
target. These are build and diagnostic checks, not accelerator-runtime or
performance evidence. Full output and hash records are in `logs/`.
