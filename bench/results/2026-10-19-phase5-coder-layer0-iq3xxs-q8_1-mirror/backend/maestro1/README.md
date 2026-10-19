# maestro1 HIP and SYCL build evidence

The exact source overlay recorded in the parent artifact was synchronized to
maestro1 and built with the validation checkout's ROCm and oneAPI toolchains.
The exact-source overlay is retained as
`../../source-overlay-exact-source.diff` with its digest in
`../../source-overlay-exact-source.sha256`.
The HIP build linked `strata` and `native_expert_parity`; the separate SYCL
build linked `strata`. The final `strata --help` command exited 0 for both
backends. The HIP `native_expert_parity --help` invocation exited 134 because
that utility does not implement a help option and tried to open `--help` as a
GGUF path; this is not a device-runtime test. No HIP or SYCL accelerator
execution is claimed.

Builds used two jobs with compiler temporary files under the isolated
`/dev/shm/phase5-iq3xxs-q8_1-maestro1` workspace. The SYCL build's final link
first failed because the host root filesystem had only 114 MiB free; it passed
after `TMPDIR` was redirected into that workspace. The source was not changed
between attempts. Earlier four-job attempts were interrupted after cgroup
memory events were observed, so they are retained for transparency and are not
counted as validation. The final two-job rebuild observed no cgroup pressure
or OOM events.

The recorded binary hashes are in `logs/hip-binaries-exact-source.sha256` and
`logs/sycl-binary-exact-source.sha256`. `logs/*build*exact-source.txt` contains
the exact-source build transcripts, while initial/interrupted attempts and
the no-space retry are retained alongside them. These are x86_64 compile/link
checks only. maestro1 is not Orin and its results say nothing about Orin
performance or GPU runtime behavior.
