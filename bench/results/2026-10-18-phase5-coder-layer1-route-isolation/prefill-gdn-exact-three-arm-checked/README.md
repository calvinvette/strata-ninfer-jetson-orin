# Exact prompt-end GDN comparison — Coder IQ1_M — Orin — 2026-10-19

This supervised three-arm diagnostic captures the raw FP32 GDN state immediately
after the same 512-token prompt, before decode. It uses the pinned Coder IQ1_M
GGUF and MTP revisions documented in `artifact-identities.json`, with default
CPU arithmetic, CPU Q8_1 mirror, and the GPU layer-1 placement profile. The
randomized order was `cpu_mirror`, `gpu_layer1`, `cpu_default`. Every arm
returned the same 16 completion token IDs and used the same prompt SHA256.

The three prompt-end GDN payloads compared byte-for-byte equal: 36 state slices
with 817,152 FP32 values per slice (117,669,888 payload bytes per arm). Their
common payload SHA256 is
`ebde53b87811976399d8916b665dd8aeee976b89ba1c211ed89ff51f62498d81`; all 36
per-slice SHA256 values are retained in `prefill-gdn-exact-analysis.json`.
Combined with the accepted-prefix state trace, this shows that GDN state is
identical at prompt end and first differs during decode in this workload. The
first post-commit GDN slice difference aligns with the first differing route
activation at every generated position: layer 2 for default CPU versus mirror
CPU; layer 9 at position 511, then layer 2 at positions 512–526, for mirror CPU
versus the GPU-profile arm. This narrows the point of GDN divergence; it does
not establish which decode calculation causes it. It also does not compare
prompt-end KV, pooled, or other persistent state byte-for-byte.

Each run passed under `MemoryMax=28G` with 53, 53, and 55 one-second samples.
Minimum host/admission availability ranged from 14.27 to 14.40 GiB and all
scope `high`, `max`, `oom`, and `oom_kill` counters remained zero. Clocks were
dynamic; energy was not measured and EMC readback was unavailable.

CUDA built and ran on Orin. The source also rebuilt the HIP `strata` target on
maestro1 with one job; that is compile/link evidence only. SYCL resolves the
migrated `sycl/src/prefill/prefill.cpp`, which this diagnostic did not change.
The focused route, verifier, multi-row, and expert-oracle CTests passed 6/6.
These checks do not close Phase 5 or establish decode parity across the full
service.

The 117,669,912-byte state files (header plus payload) were compared directly,
then removed from this report to avoid adding roughly 353 MiB of raw state to
Git. The analyzer output retains overall and per-slice SHA256 values and the
direct byte-equality result. Supervisor telemetry, service logs, requests,
build records, and the campaign runner are retained.

Reproduce the supervised capture from the repository root:

```sh
OUTROOT=bench/results/2026-10-19-phase5-coder-prefill-gdn-reproduction \
  DUMP_PREFILL_GDN=1 \
  bash bench/results/2026-10-18-phase5-coder-layer1-route-isolation/run_all16_campaign.sh

python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_prefill_gdn_exact.py \
  --campaign bench/results/2026-10-19-phase5-coder-prefill-gdn-reproduction
```
