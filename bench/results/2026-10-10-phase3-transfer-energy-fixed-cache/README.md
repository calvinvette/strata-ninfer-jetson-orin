# Mapped versus pread transfer and rail-energy screen — Orin — 2026-10-10

This is the qualified three-pair follow-up to the earlier auto-cache diagnostics.
It used the candidate binary `d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`,
the existing IQ1_M Coder pack, the 8K `spec4`/MTP config, and the exact formatted
512-token prompt (SHA256 `9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`).
Each randomized mapped/pread pair generated 64 tokens. Both arms explicitly used
`--expert-cache 5000`; this selected the same 6,519 slots (12.40 GiB) in all six
processes, with 49,629 expert-cache hits per request. Staging remained disabled.
Full SHA256 and byte-size identities for the GGUF shards, packed tensors, MTP
files, tokenizer, profile and candidate binary are in
[`artifact-identities.json`](artifact-identities.json); model and pack files
remain in `~/models/`.

All three pairs matched all 64 token IDs and all nine persistent-state fields.
The supervisor retained at least 8,701,550,592 bytes (8.10 GiB) of available
physical memory, above the six-GiB floor. Process major-fault medians were
88,302 mapped and 61,802 pread; minor-fault medians were 192,512 and 202,258.
Process `read_bytes` were unavailable. Whole-device NVMe read deltas were
7.83–8.22 GB mapped and 8.42–9.27 GB pread; these include unrelated device reads
and readahead and are not process-attributed.

Median request time (prompt plus decode) was 26,393.6 ms mapped and 27,884.0 ms
pread. The three paired mapped-minus-pread deltas were -7.22%, -4.27% and
-3.41%; the median paired delta was -4.27%. The screen is only three pairs and
does not meet the seven-block confirmation rule. CPU frequencies varied
dynamically (request-level medians 883–1,113 MHz); tegrastats did not report GPU
or EMC frequencies.

The median `VIN_SYS_5V0` system-input-rail estimate was 188.82 J mapped and
198.20 J pread; per-pair mapped-minus-pread energy deltas were -5.34%, -4.73%
and -2.58%. The median `VDD_GPU_SOC` rail estimate was 303.14 J mapped and
314.24 J pread; `VDD_CPU_CV` was 88.30 J and 110.28 J. These are integrals of
separate named tegrastats rails, not process-attributed energy; rail values are
not additive, and other system activity is included. Treat them as screening
telemetry, not a confirmed energy-per-request benefit. The sampler's initial
scope label was overly broad; the reporting code now labels each named rail and
explicitly says rail estimates are separate and non-additive.

The prior failed `spec4` repeat used `--expert-cache auto`, selecting 7,035–7,108
slots between arms; the same-mode auto-cache repeats selected different
capacities as well. Strata documents that GPU-resident experts round differently
from CPU-computed experts. The fixed-cap run held residency constant, matched
expert hits and restored state parity in every pair. The failed auto-cache runs
remain preserved as mismatched-residency diagnostics, not evidence of a
transfer-path state bug. No path or default is promoted from this screen.

Raw pair results, tegrastats samples, engine logs, supervisor memory samples and
commands are retained in `experiment/` and `supervisor/`. Models and build
products remain outside Git.
