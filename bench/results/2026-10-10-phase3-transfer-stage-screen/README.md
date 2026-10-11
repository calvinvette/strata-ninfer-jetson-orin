# Prefetch page-cache fill versus staging — Orin — 2026-10-10

This randomized three-pair screen isolates `STRATA_IO_PF_STAGE` while keeping
the same whole-blob prefetch path enabled in both arms. It used the IQ1_M
validation model and pack, the formatted 512-token prompt
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`, 64 output
tokens, requested expert cache 3,000 (3,903 actual slots), context at least
8,192, and the same candidate binary
`d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`. Pair order
was randomized with seed 20261013. All six arms matched all 64 output token
IDs, all nine persistent-state fingerprints and actual cache slots. The
supervisor minimum physical `MemAvailable` was 14,168,944,640 bytes (13.20
GiB), above the six-GiB floor.

The prefetch-fill control reads predicted experts through workers into the OS
page cache (`STRATA_IO_PF_STAGE=0`). The stage arm reads them into pageable
host buffers for direct handoff (`STRATA_IO_PF_STAGE=1`). Across the three
stage requests, the engine consumed 265–295 prefetched blobs and reported
1,480.6–1,683.5 ms aggregate decode wait across 1,495–1,573 fetches. The fill
control consumed zero staged blobs and reported zero wait fetches. Therefore
the stage path is now observed in the real request, unlike the prior
stage-disabled pread screen.

| Pair | Order | Fill request ms | Stage request ms | Paired delta | Fill scoped reads GB | Stage scoped reads GB |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 0 | fill / stage | 37,566.4 | 34,614.4 | −7.86% | 14.345 | 11.487 |
| 1 | stage / fill | 34,643.5 | 32,864.5 | −5.14% | 11.315 | 10.004 |
| 2 | fill / stage | 63,664.5 | 33,444.5 | −47.47% | 10.117 | 10.042 |

The paired median delta was −7.86% for staging. A 200,000-draw paired
bootstrap median interval (seed 1013, whole-pair resampling) was −47.47% to
−5.14%; with only three pairs and a 63.7-second fill-arm outlier, this interval
is highly sensitive to individual observations. Median total request time was
37,566.4 ms for fill and 33,444.5 ms for stage. Median scoped reads were 11.315
GB and 10.042 GB respectively. This is screening evidence only. Clocks were
dynamic, board rail telemetry is system-wide, and a same-day seven-pair
confirmation plus held-out workload is still required before any path decision.
No default changed.

The first invocation completed pair 0 but hit a harness bug serializing the
three-field randomized arm definitions. The retained `supervisor/` records that
non-model failure; the script was fixed and resumed into
`supervisor-resume/`, retaining pair 0 without rerunning it. The final
`experiment/results.json` records the three valid pairs and all raw engine
logs, scoped-I/O deltas, state fingerprints, owner observations and telemetry.
The resume run's minimum availability is recorded in its supervisor result.

Reproduce on Orin:

```sh
sudo systemd-run --scope --property=IOAccounting=yes -- \
  /usr/bin/setpriv --reuid=1000 --regid=1000 \
  --groups=1000,4,24,27,29,30,44,46,104,116,120,135,136,137,996,999,1001,1002 -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/run_control.py \
  --output bench/results/NEW-stage-screen/supervisor --timeout 1800 -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/file_tier_transfer_parity.py \
  --config build/integration/candidate-protocol/server-config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/NEW-stage-screen/experiment \
  --prompt-tokens 512 --generated-tokens 64 --pairs 3 --seed 20261013 \
  --expert-cache 3000 --compare-prefetch-stage --run
```
