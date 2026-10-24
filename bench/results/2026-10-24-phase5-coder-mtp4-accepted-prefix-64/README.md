# MTP4 accepted-prefix state parity — Orin — 2026-10-24

## Result

The current CUDA candidate engine ran the existing deterministic 512-token
formatted Coder IQ1_M prompt and 64 generated tokens in two isolated private
processes: MTP-off and MTP4. Generated token IDs matched exactly. MTP4 offered
84 draft tokens and accepted 35. All nine persistent-state fingerprints
matched at each of the 29 shared accepted-prefix commit boundaries and at final
state: `L`, GDN, PLE, tail, dead, pooled, pooled-full, KV and PLE previous
embedding. The direct accepted-prefix check passed.

This is one bounded transaction case on the same deterministic prompt used by
the earlier MTP3 probe, not independent prompt confirmation. It does not
qualify longer chains, cancellation/recovery, adaptive migration, long-context
state or multi-live decoding, which remains open.

## Identity and reproduction

- Device: Orin AGX, native aarch64, CUDA 12.6 / SM87.
- Source HEAD at run: `061a0853`.
- Model: Coder IQ1_M artifact revision
  `5348543e0147355ac9cbcb031184a3546350988e`, with base-checkpoint MTP weights
  under `~/models/strata-orin-validation/`.
- Prompt: 512 formatted tokens; token-ID SHA-256
  `ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`.
- Output: 64 tokens in both arms; MTP4 84 drafts offered / 35 accepted.
- Binary SHA-256 for both arms:
  `ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.
- The supervised run preserved the six-GiB physical-headroom floor; minimum
  physical and effective-admission availability was 16.98 GiB. GPU frequencies
  were observed dynamically; EMC readback and energy analysis were unavailable.

The successful `run-corrected/results.json` contains both arm IDs, exact state
fingerprints, prefix comparisons, commands and binary hashes. The compact
`supervisor-corrected/result.json` records the memory floor and run status.
Detailed per-token logs and telemetry remain local.

Reproduce with the MTP4 arm config (which supplies the draft-model path):

```sh
python3 tools/integration/run_control.py \
  --output /tmp/mtp4-accepted-prefix-supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
    --config bench/results/2026-10-24-phase6-coder-mtp4-kv-heldout-length-screen3/\
block-00-kv-fp16-workload-coder-mtp4-screen-heldout-short-512-mtp-4/config.json \
    --engine build/integration/candidate/strata \
    --output /tmp/mtp4-accepted-prefix-run \
    --tokens 64 --prompt-tokens 512 --kv-format fp16 --windows 0 4 --run
```

An initial invocation used the MTP-off config for both arms. That config has no
`--mtp` path; the probe correctly rejected it because MTP offered/accepted no
drafts. Its captured summary is retained as `setup-attempt-summary.json` and is
excluded from this passing result. The corrected run used the MTP4 config above.
