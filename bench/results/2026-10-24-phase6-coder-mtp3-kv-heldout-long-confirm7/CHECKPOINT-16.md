# Held-out long MTP3 × KV confirmation — 16-cell checkpoint

This checkpoint captures four randomized blocks from an ongoing seven-block
campaign. It is not the final confirmation; the campaign continues in
`campaign/campaign.json`. The model, binary, configuration and workload identity
are retained with the checkpoint. All 16 completed arms passed the API request,
exact retrieval/arithmetic oracle, formatted prompt-token count, actual KV and
expert-residency checks. No completed arm failed or aborted.

## Interim paired results

Eight MTP-off/MTP3 pairs passed the residency and same-local-day audit. The
following estimates are provisional four-block summaries, not the planned
seven-block held-out confirmation. Intervals are paired bootstrap 95% intervals.

| KV | MTP3 decode throughput | TTFT | Total request time |
| --- | ---: | ---: | ---: |
| FP16 | -5.04% (-26.95% to -4.04%) | +0.76% (+0.02% to +1.49%) | +0.81% (+0.05% to +1.87%) |
| INT8 | -4.13% (-4.90% to -3.37%) | +0.92% (+0.49% to +9.89%) | +0.95% (+0.52% to +9.83%) |

The decode MTP-by-KV interaction is +1.10% (95% interval +0.43% to +30.18%),
with a large interval driven by the unusually slow FP16/MTP3 cell in block 0.
That cell remains included. This partial result is inconclusive about a stable
KV interaction and does not support changing a default.

Minimum observed physical availability was 16.96 GiB and minimum admission
availability was 16.94 GiB. The six-GiB floor was preserved. Minimum values
cover only these 16 completed arms.

## Reproduction and checkpoint contents

- Device: local Orin AGX; native ARM64, CUDA runtime.
- Model: Coder IQ1_M with upstream base-checkpoint MTP weights, same 1,500 MiB
  expert cache and 8K context configuration as the screening campaign.
- Workload: `coder-cache-context-heldout-retrieval-arithmetic-near-limit-7501`,
  7,501 formatted prompt tokens and 48 requested output tokens. It is distinct
  from the retrieval task used in the three-block MTP × KV × prompt-length
  screen. The exact prompt and answer oracle are retained in `inputs/workloads.json`.
- Design: MTP off/3 × FP16/INT8 KV, seven randomized blocks, seed 20261024.
  Each arm has a fresh service and 28 GiB memory scope.
- Binary SHA256: `1f44e7e3713faf9d1e1fee688a69ce5960e21d40c1d0d6071e9831dea53316d6`.
- Campaign source HEAD: `7e8a7b5acc824ed9a9ce9bd30ead82fe34d5a994`.

`campaign/checkpoint-16.json` contains the full design and the first 16 passing
arms. Their request records, configs, engine logs and telemetry are retained in
`campaign/block-00` through `campaign/block-03`. `CHECKSUMS-CHECKPOINT-16.txt`
verifies this checkpoint's stable inputs and raw results. Remaining blocks,
final model diagnostics, energy integration and the complete campaign report
will be added after the 28-arm run ends.
