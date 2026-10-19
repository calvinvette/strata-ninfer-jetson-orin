# Current-source HIP and SYCL build — maestro1 — 2026-10-19

The HIP build used the top-level current sources. The SYCL project resolves
`sycl/src/program/generate.cpp` from its migration overlay and resolves the
CPU expert source and header from the top-level tree. The opt-in accepted-prefix
GDN dump diagnostic was added narrowly to both generate sources. The exact
input hashes are in `source-sha256.txt`; the overlay change is retained as
`sycl-gdn-state-capture.patch` in the parent result directory.

| Backend | Build | `strata --help` | Binary SHA256 |
| --- | --- | --- | --- |
| HIP, gfx1100 | Pass | Exit 0 | `57e68fcd425ecd1df18fe3f139f36840e324c848ae08adab3a4d882e50b2bf6a` |
| HIP `native_expert_parity` | Pass | Not run | `a7458267a2998169d6bad7bcb8a6b7819e69820ebc180d3c7bd7daf294cecfff` |
| SYCL | Pass | Exit 0 | `583eef41380bef4f5271df8bd19491a07656ab8a95b5236b06a65c5e5c0fb17f` |

Both backends used two build jobs. The SYCL incremental compile also completed
the 1,430 per-kernel device-link steps. `memory.events` recorded zero
low/high/max/OOM/OOM-kill events. Configure/build logs, CLI output and binary
hashes are retained in this directory. These are x86_64 compile, link and CLI
checks only; maestro1 provides no accelerator execution or Orin performance
evidence.
