# Layer-39 expert-50 residency intervention

## Result

A supervised current-binary two-live target-only diagnostic tested a temporary
Coder IQ1_M expert profile that moved model layer 39 / expert 50 from baseline
rank 7,781 to rank 0. The intervention did not restore full output parity:
slot 0 matched its isolated serial control for all 72 tokens; slot 1 first
differed at output index 66, matching the onset in the prior baseline cell.
This is a failed rescue attempt. The harness did not capture paired committed
state for this run, so it says nothing about terminal state parity or whether
this profile prevented the specific owner switch observed in the earlier
position-104 capture.

The single diagnostic completed successfully under `run_control.py`; minimum
physical/admission availability was 17.757 GiB with no sampled cgroup pressure
events. GPU clocks were read-only and dynamic; EMC readback was denied. This is
correctness evidence only, not a performance, energy, or quality result.

## Identity

- Repository head: `45e79101cbae7ebc94162b2b415cc7547a019436`.
- Candidate binary SHA256: `1f44e7e3713faf9d1e1fee688a69ce5960e21d40c1d0d6071e9831dea53316d6`.
- Base model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
  `5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M shards as recorded in
  `run/result.json`.
- Temporary profile SHA256:
  `41b086e8b40e3da49e6dfae0a634677c407727ed0c64ebaf7956b29136384c38`.
  The 512 KiB derived profile is under `/tmp` and is not a model or default.
- Two 68-token prompts, 72 generated tokens per serial control and batch row,
  MTP off, two live rows, 1,500 requested cache slots, Q8_1 CPU selector forced
  to `all`, default pool-worker count, 1,024 context.

The compact machine-readable result is `run/result.json`; raw server logs and
supervisor samples are local under `run/` and `supervisor/` and were not added
to Git. Reproduce the profile and run from the repository root with:

```sh
python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/make_expert_first_profile.py \
  --layer 39 --expert 50 --output /tmp/strata-coder-layer39-expert50-first.bin
python3 tools/integration/run_control.py \
  --output bench/results/2026-10-24-phase5-coder-layer39-expert50-residency-intervention/supervisor \
  --timeout 2400 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/run_q8all_target_batch.py \
    --output bench/results/2026-10-24-phase5-coder-layer39-expert50-residency-intervention/run \
    --generated-tokens 72 --expert-profile /tmp/strata-coder-layer39-expert50-first.bin
```

The original layer-39 capture tied expert 50's CPU/GPU output delta to one
local branch perturbation. This profile-level test shows that protecting that
one expert's ranking alone does not recover the complete two-live output. The
broader multi-live state/output cause remains open; see the
[diagnostic series](../../2026-10-23-phase5-coder-two-live-target-q8all/README.md).
