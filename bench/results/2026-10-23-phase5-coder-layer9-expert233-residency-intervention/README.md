# Phase 5: layer-9 expert 233 residency intervention

Two supervised two-live Coder IQ1_M target-only runs tested a temporary static
profile that moved layer 9 / expert 233 from rank 3,130 to rank 0. The requested
expert cache remained at 1,500 slots. MTP was disabled, the existing
`STRATA_NATIVE_CPU_Q8_1_DOT=all` selector was used, and both prompts generated
96 tokens. The profile SHA256 is
`41595f87b9947df82a492f4868e267013bf1fec8bae538f797a14e2b04ab64f4`.

In both runs, both batch output sequences matched their isolated serial
controls for all 96 token IDs. At position 83 for slot 1, the model activation
hash matched the unprofiled capture, routes and all expert parts matched, and
expert 233 remained on primary VRAM in both serial and batch rows. The combined
MoE output was bit-identical. At positions 82 and 83, the captured layer-10 GDN
stages and committed state were also bit-identical to serial.

The existing unprofiled diagnostic had expert 233 move GPU→CPU at layer 9 on
the same position-83 activation, with expert-part relative L2 `1.1979e-4` and
combined MoE relative L2 `1.3708e-5`; the two-live target-only slot-1 sequence
in that baseline first differed from serial at output index 66. The intervention
therefore supports this owner transition as a correctable source for that
observed mismatch. It remains a scoped result: the residency ordering can
change other placements, and these two repetitions do not establish general
profile benefit or exclusive causality for all multi-live drift.

The two supervised diagnostic runs took 222.7 s and 299.8 s. Minimum physical
and admission availability was 17.84 GiB and 17.85 GiB, respectively, above
the 6 GiB host floor. EMC clock readback was denied; clocks remained dynamic.
Energy was not measured. Capture timings include substantial diagnostic
instrumentation and are not performance evidence. Raw dumps and logs remain
outside Git under `/tmp/phase5-layer9-expert233-first*`.

The compact results and exact command inputs are in [`analysis.json`](analysis.json).
Reproduction:

```sh
python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/make_expert_first_profile.py \
  --layer 9 --expert 233 --output /tmp/phase5-layer9-expert233-first.bin
python3 tools/integration/run_control.py \
  --output /tmp/phase5-layer9-expert233-supervisor --timeout 2400 --sample-clocks -- \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/capture_position_state.py \
  --output /tmp/phase5-layer9-expert233 --positions 82,83 --layer 10 \
  --stage-layer 10 --moe-layer 9 --expert-cache-slots 1500 \
  --expert-profile /tmp/phase5-layer9-expert233-first.bin \
  --generated-tokens 96 --serial-slot both
```

Phase 5 remains open for broader committed-state transaction, graph/MTP, and
multi-live state/quality qualification.
