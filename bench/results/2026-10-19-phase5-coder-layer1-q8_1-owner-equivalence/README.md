# Layer-1 Q8_1 CPU/GPU owner equivalence — Orin — 2026-10-19

This diagnostic tests whether changing the owner of selected layer-1 experts
from the CPU Q8_1 mirror to CUDA preserves the same service state. Both arms use
`STRATA_NATIVE_CPU_Q8_1_DOT=iq2_s/q2_0@layer=1`, so remaining CPU-owned experts
at layer 1 use the same CUDA-matching arithmetic as the seven experts moved to
the GPU in the candidate profile. The selector is opt-in; no default changed.

The model is the **IQ1_M** artifact from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Its two shard checksums are in
`model-sha256.txt`. Routed layer 1 uses GGML types 22/42 (IQ2_S/Q2_0), confirmed
by the local native-pack manifest. The Orin service binary is pinned in
`artifact-identity.json`.

The control and GPU-target profiles share the same first 3,000 ranked experts
and both fill 3,007 slots. The next seven control entries are filler experts;
the candidate instead admits the seven layer-1 targets
`205, 101, 32, 11, 95, 18, 165`. The filler *layer/expert pairs* do not appear
in any of the 16×48 captured generated-token routes. Across the three paired
blocks, the seven target experts moved from CPU to GPU in 15 routed assignments.
All other observed owners, expert IDs and token positions matched. The profile
design and generated binary hashes are recorded in `profile-design.json`.

All three randomized 28-GiB supervised pairs passed. Each arm emitted the same
16 token IDs and matched all 16 accepted-prefix state fingerprints in its pair,
including GDN, PLE, KV, pooled, MTP and stale-draft fields.
The exact prompt-end GDN dumps were byte-identical across each pair (117,669,912
bytes per dump). A supplemental supervised pair captured the device-side layer-1
top-k records: expert IDs and router weights matched at all 16 generated
positions, while the seven target experts changed owner as intended. All
accepted-prefix entries had zero accepted speculative drafts, so these runs
test ordinary committed output tokens, not a speculative acceptance case.

| Block | Randomized order | State fingerprints equal at all 16 commits | Minimum host/admission availability |
| --- | --- | --- | ---: |
| 1 | CPU mirror → GPU target | Yes | 16.009 GiB |
| 2 | CPU mirror → GPU target | Yes | 16.032 GiB |
| 3 | GPU target → CPU mirror | Yes | 16.106 GiB |

The supplemental device-route pair also passed, with 16.015 GiB minimum
availability. All scopes had zero cgroup low/high/max/OOM/kill events and stayed
above the six-GiB physical-memory floor. Clocks were observed but not fixed;
EMC readback was unavailable and process energy was not measured. These are
correctness comparisons, not timing or performance results. The state evidence
uses the engine's per-field accepted-prefix fingerprints; it does not claim a
byte-for-byte dump of every persistent state buffer.

The host route-activation callback differs on some all-GPU rows, matching the
known stale-callback limitation recorded in the [all-position route report](../2026-10-18-phase5-coder-layer1-route-isolation/all-16-positions-three-arm-wildcard/README.md).
The supplemental device-side IDs and weights are authoritative for the tested
layer-1 route. This result is limited to the pinned prompt, profile, seven
experts and one IQ2_S/Q2_0 layer. It does not qualify other layers or formats,
adaptive swapping, task quality, or performance, and does not close Phase 5.

One initial device-route harness invocation failed before model startup because
its shell parser passed both arm names as one argument. It is retained under
`device-route-pair/` as a setup failure and excluded. The corrected
`device-route-pair-retry1/` check passed.

The exact 117,669,912-byte prompt-end GDN dump is identical across all eight
arms. To avoid storing eight copies, the raw bytes are retained once as
`prefill-gdn-reference.part00` and `prefill-gdn-reference.part01`; every run's
`requests.json` records the matching SHA-256. `analysis.json` verifies the
reassembled parts against all eight records. Route, CPU-output and supervisor
JSONL files are losslessly gzipped. Identical route/output captures are stored
once in `shared-captures/`, and each run records the shared path, decompressed
size and SHA-256. `compact_evidence.py` performs this verified compaction.

Recreate the profiles and three paired blocks on this host with:

```sh
python3 bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/prepare_profiles.py
OUTROOT=bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/paired-runs-reproduction \
  bash bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/run_pairs.sh
```

The exact device-side route supplement can be repeated with:

```sh
OUTROOT=bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/device-route-pair-reproduction \
  bash bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/run_device_route_check.sh
python3 bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/analyze_owner_equivalence.py \
  --runs bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/paired-runs-reproduction \
  --device-route-dir bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/device-route-pair-reproduction \
  --output bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/analysis-reproduction.json
```

Verify retained files from this directory with `sha256sum -c SHA256SUMS`. Check
the GDN bytes independently with `cat prefill-gdn-reference.part00 prefill-gdn-reference.part01 | sha256sum`.
