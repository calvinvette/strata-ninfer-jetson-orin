# Layer-2 Q8_1 CPU/GPU owner comparison — Orin — 2026-10-19

This three-block diagnostic repeats the matched-capacity owner test on Coder's
layer-2 IQ2_S/IQ4_NL experts. It tests whether the layer-1 result generalizes
when the CPU and CUDA expert calculations retain the small full-expert residual
recorded by the separate operator diagnostic. The Q8_1 selector is opt-in and
scoped to `iq2_s/iq4_nl@layer=2`; no default changed.

The model is IQ1_M from
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, pinned at revision
`5348543e0147355ac9cbcb031184a3546350988e`. The two shard checksums are in
`model-sha256.txt`. The service binary SHA-256 is recorded in
`analysis.json`; its compiled source was commit `58ea8c00`. Models and packs
remained in `~/models/strata-orin-validation/`.

Both profiles share the same first 3,000 ranked expert entries and fill 3,007
slots. The CPU-mirror profile uses seven filler entries; the GPU-target profile
uses layer-2 experts `(174, 62, 69, 130, 143, 151, 28)`. The profile design,
source route digest, profile hashes and filler exclusion check are in
`profile-design.json`. Every arm ran under a 28-GiB cgroup scope with read-only
clock sampling and the six-GiB physical/admission floor.

The result did **not** preserve accepted state or output. In all three
randomized pairs, prompt-end GDN dumps were byte-identical, while the first
accepted-prefix fingerprint already differed in `gdn`, `pooled`,
`pooled_full` and `kv`. The outputs matched for six generated tokens and
diverged at token seven. The supplemental device-side layer-2 capture showed
identical top-10 expert IDs and router weights from the prompt through those
six matching tokens; the first differing device route was at position 518.
The host route capture also matched through seven route records (the prompt
position plus six generated positions). All seven target experts were CPU
owned in the mirror profile and GPU owned in the candidate at the prompt-end
route. These paired results support a numerical/owner-path correctness failure
for this exact layer-2 profile, not a router difference before the output
split.

| Block | Order | Shared output tokens | First commit state fields that differ | Prompt-end GDN equal | Minimum host/admission availability |
| --- | --- | ---: | --- | --- | ---: |
| 1 | GPU target → CPU mirror | 6 | GDN, pooled, pooled-full, KV | Yes | 15.879 GiB |
| 2 | GPU target → CPU mirror | 6 | GDN, pooled, pooled-full, KV | Yes | 16.115 GiB |
| 3 | CPU mirror → GPU target | 6 | GDN, pooled, pooled-full, KV | Yes | 16.113 GiB |

The supplemental exact-device-route pair retained 16 records per arm and matched
IDs and weights through the six-token common output prefix. Minimum host/admission availability
was 16.087 GiB. All supervisors passed; cgroup low/high/max/OOM/kill counters
were zero. Clocks were observed but not fixed, EMC readback was unavailable,
and energy was not measured. This is correctness evidence only: there is no
performance, quality, general migration or adaptive-swap claim. The experiment
also does not establish that any one of the four changed state fields caused
the later token split.

Recreate the profiles and three randomized pairs on Orin with:

```sh
python3 bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/prepare_profiles.py
BLOCKS=3 SEED=20261020 bash bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/run_pairs.sh
OUTROOT=bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/device-route-pair-reproduction \
  bash bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/run_device_route_check.sh
python3 bench/results/2026-10-19-phase5-coder-layer2-q8_1-owner-equivalence/analyze_layer2_owner.py
```

The raw GDN bytes are retained once as two reference parts; each run records the
same digest. JSONL captures and telemetry are losslessly compressed. Identical
captures are stored once under `shared-captures/`, with decompressed SHA-256 and
size in each request record. Verify the retained artifact with
`sha256sum -c SHA256SUMS` from this directory. Phase 5 remains open.
