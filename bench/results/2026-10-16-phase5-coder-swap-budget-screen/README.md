# Coder IQ1_M adaptive swap-budget recovery screen — Orin — 2026-10-16

This three-block randomized mechanism screen compares the delayed-adaptation
control with accepted-only adaptive swap caps of 1, 8 and 96 blobs per apply.
Each fresh MTP-off Strata service ran the same uncached 512-token, 2,048-token,
512-token sequence and generated 16 tokens per request. The final short response
and persistent state fingerprints were checked directly; first-layer MoE inputs,
expert IDs and route ownership were captured. This is a Strata recovery-parameter
comparison, not a Strata-versus-NInfer speed comparison.

The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. The campaign inherited the
pre-existing `~/models/strata-orin-validation/IQ1_M/` paths from the Phase 6
configuration; prior artifact manifests identify those shards with the exact
same full-file SHA256 values as the downloaded `Coder-GGUF/IQ1_M/` snapshot:
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The per-run service binary SHA256 was
`fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b`.
The prompts, options and source are recorded in `run_one.py`,
`run_campaign.py`, and the per-run `analysis.json` and `requests.json` files.

All 12 arms completed. The three delayed controls reproduced their first short
response exactly on recovery and had no changed state fingerprints. Cap 8
reproduced the delayed-control recovery tokens exactly in all three blocks; its
own first and final short outputs also matched. However, five persistent-state
fingerprints differed from the delayed control in each block, so this is output
agreement, not exact state recovery. Cap 1 and cap 96 differed from delayed
control at all 16 recovery token positions in every block; each showed 14 token
changes against its own first short output and seven changed state fingerprints.

The first seven captured layer-0 activation rows and expert IDs matched between
the initial and recovery short requests for every arm. Cap 8 had no owner flips
or later activation differences in any block. Cap 1 had no first-seven owner
flips but had 15 later activation differences; cap 96 had 18 first-seven
CPU-to-VRAM owner flips and 15 later activation differences. The targeted
adaptive byte and residency checks passed at all 11 apply points in every active
arm. The continuation follow-up below shows that the cap-8 state mismatch is
behaviorally observable on the next request, so cap 8 does not pass recovery.

The 2,221 one-second supervisor samples showed minimum host and admission
availability of 14.34 GiB, above the six-GiB floor. GPU clocks ranged from 306
MHz to 1.3005 GHz and CPU clocks from 729.6 MHz to 2.2016 GHz. EMC clock readback
was unsupported and energy was not measured per request. Dynamic clocks and the
small three-block sample make this a mechanism result, not a performance claim.

The first launch attempt did not start inference: the campaign harness held the
same advisory lock that `run_control.py` needed. The lock was free afterwards;
the harness now uses a separate campaign lock. That preflight record is retained
in `campaign/` and excluded. The completed retry is in `campaign-retry1/`.

This does not close Phase 5. The schedule was generated with seed `20261016`.

## Continuation follow-up — 2026-10-16

The delayed-control versus cap-8 pair was repeated in three blocks, with one
additional identical 512-token request after the original short/long/short
sequence. The output/state comparison is in `continuation-summary.json`; raw
requests, accepted-prefix hashes, capture, logs, clocks and memory samples are
under `continuation-campaign/`.

All three pairs produced the same pattern: the first short output matched, the
long output differed at three of 16 positions, the recovery short output matched,
and the extra continuation differed at all 16 positions. At the extra request,
all seven captured state fingerprints differed from delayed control. This
confirms that matching the immediate recovery text concealed state divergence
that changed the next response. All six services passed supervision; minimum
host/admission availability was 14.33 GiB across 1,196 samples, with zero
sampled cgroup memory events. All 15 adaptive byte and residency checks passed
in each cap-8 service. Clock observations remained dynamic; energy was not
attributed per request.
