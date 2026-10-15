# Current-source release regression and backend builds — 2026-10-14

This report closes a verification gap after the accepted-window cap and new-
sequence MTP reset landed. The tested source is commit `b99b26a2`. The native
Orin binary SHA256 is in `native/binary-sha256.txt`; its fixture-available CTest
run and supervisor logs are retained in `native/`.

The native CUDA/ARM64 tree rebuilt successfully with two jobs. CTest passed all
117 tests in the available selection; two optional IQ tests skipped because
their fixtures are absent. The two tests requiring `pack/full/experts.bin`
(`expert_parity` and `pool_test`) were excluded, as in the earlier full-suite
report. Minimum physical host and admission availability were both 22.27 GiB.
The 28-GiB cgroup recorded zero `high`, `max`, `oom` and `oom_kill` events.
This is the available regression result, not a pass for the two excluded
tests. The integration Python suite also passed 141/141 tests on this
checkout.

maestro1 compiled and linked the current shared MTP/generation source for HIP
(`strata` and `native_expert_parity`) in seven build steps. Its CLI help check
passed with the ROCm runtime library path set. SYCL's `strata` target required
no rebuild in its existing configured tree; its CLI help check passed. The
SYCL service uses separate generator sources, so that no-op build is not
evidence that it compiled the changed generator path. Hashes for the three
updated source files match between the Orin checkout and maestro1. Logs and
binary hashes are retained in `maestro1/`.

maestro1 is x86_64 with no accelerator execution in this check. These results
establish compile/link and CLI startup only; they do not establish HIP/SYCL GPU
runtime behavior or performance. The native CTest run also does not replace
model-level service and quality results from Phases 5–7.

The native command, run under a 28-GiB systemd scope, was:

```sh
ctest --test-dir build/integration/candidate --output-on-failure -j1 \
  -E '^(expert_parity|pool_test)$'
```

