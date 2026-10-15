# maestro1 accelerator runtime availability audit — 2026-10-15

This read-only audit checked whether maestro1 can supply accelerator runtime
evidence in addition to its retained HIP/SYCL compile and CLI checks. It is
x86_64, and its only enumerated graphics controller is Intel HD Graphics 500
(PCI `8086:5a85`) using the i915 DRM device. `/dev/kfd` is absent, so this host
cannot provide HIP/ROCm device execution.

The bundled Intel oneAPI DPC++ compiler is version 2026.1.1. Running its
`sycl-ls --verbose` reports zero platforms. The OpenCL adapter cannot load
because `libhwloc.so.15` is unavailable; no OpenCL ICD vendor files are
installed. The Level Zero adapter cannot load because `libze_loader` is
absent. Adding the bundle's available UMF 1.1 library directory to
`LD_LIBRARY_PATH` does not expose a SYCL platform. The Intel render node exists,
but a render node alone is not evidence of a usable SYCL device runtime.

This audit made no package, driver, environment, clock or device changes. Raw
read-only command output is in `audit.txt`. It does not invalidate the retained
maestro1 HIP/SYCL compile and `--help` evidence; it establishes that those
checks are not accelerator execution. Phase 8 still needs its Orin CUDA/runtime
and supported-profile release gates; an AMD HIP runtime requires a separate
AMD device, and SYCL runtime execution requires a usable SYCL platform.

The repository checkout and models were not copied to maestro1 for this audit.
