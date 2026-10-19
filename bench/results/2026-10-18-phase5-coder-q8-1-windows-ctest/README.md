# Q8_1 CPU/CUDA verifier-window parity — Orin — 2026-10-18

This report records an opt-in extension to `native_expert_parity` that runs the
Q8_1 activation path at verifier widths 1 through 8. It keeps one IQ2_S/Q2_0
synthetic expert payload fixed across widths, compares CPU and CUDA outputs
bitwise at each width, and checks CPU gate/up/down row outputs for invariance
to verifier grouping. Since CUDA outputs match the CPU at each width, this
also checks the corresponding CUDA rows. It is an operator contract test; it
does not establish service-level quality, performance, or resolve the Coder
IQ1_M adaptive-state divergence.

## Orin result

On the local Orin AGX candidate built from source commit `58be4d54`, the
supervised `--synthetic-windows iq2_s/q2_0` run passed all eight widths. Every
CPU/CUDA comparison had zero differing output words; width-invariance checks
also found zero differing gate/up/down rows. The run reported zero failures.
The default IQ2_S/Q2_0 parity test, the prior three-token Q8_1 dot test, and the
new widths 1–8 test passed together in CTest (3/3); the full Python integration
suite also passed (163 tests).

The candidate run was bounded at 28 GiB and kept the six-GiB host availability
floor. Raw stdout, stderr, memory samples, tegrastats, and supervisor JSON are
retained below. This synthetic operator check does not read or alter downloaded
models and does not represent a real-model performance measurement.

## Backend build evidence

The current-source HIP build on `maestro1` completed successfully from source
commit `58be4d54`. It built both `strata` and the changed
`native_expert_parity.cpp` into `native_expert_parity`; the `strata --help` and
parity-utility usage checks loaded successfully (the utility returned its
expected usage exit code 2 without arguments). The build log's last visible
progress marker is 314/315; the build command exited successfully and a
subsequent incremental build confirmed `ninja: no work to do`. The HIP `strata`
binary SHA256 is
`e3353dac1e3aa2f10f32aaf328a23231692f521a2c4870f451a612a35fcea1ef`; the
parity utility SHA256 is
`f30303be14b3ab3a5a1f0596098a8ebb0839b4754eabb91b7fd5d0943efb6721`.

The SYCL build completed all 123/123 steps and `strata --help` loaded
successfully. Its binary SHA256 is
`014388aa98996c4e37a86645fa8d9a6a709a3bd52a2dc03f10f3f6f1f189e7a2`; an
incremental build also reported `ninja: no work to do`. The builds used AMD
clang 22.0.0git and Intel oneAPI DPC++ 2026.1.1 on x86_64, one job, Release,
gfx1100 for HIP, tests disabled and conversation tests enabled for the HIP
configuration, and parity disabled for SYCL.

The maestro1 snapshot contains 801 build inputs. Its SHA256 manifest matches
the current checkout, and the source-diff record shows the two files updated
from the prior Phase 8 build snapshot: `CMakeLists.txt` and
`src/kernels/native_expert_parity.cpp`. The manifest and diff are retained in
`maestro1/`, along with compiler versions, configure/build/help logs,
incremental-build records, and output hashes. Both builds used one job on
maestro1's 3.7-GiB x86_64 host; temporary files and build products stayed under
`/mnt/sda2`. No accelerator runtime or model execution was tested there, so
these are compile/link and CLI checks only, not accelerator qualification or
Orin performance evidence.

To verify the source snapshot from the repository root:

```sh
sha256sum -c bench/results/2026-10-18-phase5-coder-q8-1-windows-ctest/maestro1/source-sha256.txt
```

## Reproduction

From the repository root on Orin:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-18-phase5-coder-q8-1-windows-ctest/direct-supervisor \
  --timeout 300 --interval 1 --sample-clocks -- \
  env STRATA_NATIVE_CPU_Q8_1_DOT=1 \
  build/integration/candidate/native_expert_parity \
  --synthetic-windows iq2_s/q2_0

ctest --test-dir build/integration/candidate --output-on-failure \
  -R 'native_expert_parity_iq2_s_q2_0(_cpu_q8_1_dot|_cpu_q8_1_windows)?$'

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

The CTest supervisor outputs and the 163-test Python suite log are retained with
this report.
The direct run's machine-readable memory and clock observations are in
`direct-supervisor/result.json`; `tegrastats` raw readings are not process-
attributed energy measurements.
