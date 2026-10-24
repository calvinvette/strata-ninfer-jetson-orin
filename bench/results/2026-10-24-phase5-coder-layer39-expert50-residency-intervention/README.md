# Layer-39 expert-50 residency intervention

## Result

A supervised current-binary two-live target-only diagnostic tested a temporary
Coder IQ1_M expert profile that moved model layer 39 / expert 50 from baseline
rank 7,781 to rank 0. The intervention did not restore full output parity:
slot 0 matched its isolated serial control for all 72 tokens; slot 1 first
differed at output index 66, matching the onset in the prior baseline cell.
This is a failed rescue attempt. The first run did not capture paired committed state. A second instrumented
run confirmed expert 50 was GPU-owned in both serial and batch at the sampled
position, so the intended local residency was achieved. But the layer-39 routes
differed and the serial/batch input activations already differed in all 2,560
values (max absolute delta 0.10295, relative L2 0.02819). The branch parts are
therefore not a same-input comparison. This capture shows that the upstream
divergence precedes layer 39 in this run; it does not establish terminal-state
parity or attribute the full output mismatch.

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

The compact machine-readable results are `run/result.json` and
`layer39-position104/analysis.json`. The reusable capture harness is
`capture_layer39.py`. Raw server logs, activation/part dumps and supervisor
samples are local under `run/`, `layer39-position104/` and `supervisor/`; they
were not added to Git. Reproduce the profile and run from the repository root with:

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
local branch perturbation. This profile-level test shows that promoting that
expert keeps it GPU-owned but does not recover the complete two-live output;
the instrumented follow-up also found layer-39 inputs/routes already unpaired.
The broader multi-live state/output cause remains open; see the
[diagnostic series](../../2026-10-23-phase5-coder-two-live-target-q8all/README.md).
