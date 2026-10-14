# Q2_0 MTP accepted-prefix parity with compact KV — Orin — 2026-10-14

These two sequential, supervised correctness runs extend Q2_0 MTP state
coverage from FP16 KV to int8 and q4_0 KV. Both used the same 2,048-token
formatted prompt, 128 generated tokens, 8,192 configured context, 3,000
requested expert slots, and the accepted-only adaptive swap policy at cadence
4. Each format was tested with MTP off/2/3/4. All eight arms completed the
requested output length.

| KV format | MTP window | Drafted/accepted | Matching shared accepted-prefix boundaries | Token IDs and final state |
| --- | ---: | ---: | ---: | --- |
| int8 | 2 | 68/44 | 84/84 | Exact |
| int8 | 3 | 99/54 | 74/74 | Exact |
| int8 | 4 | 130/63 | 65/65 | Exact |
| q4_0 | 2 | 67/46 | 82/82 | Exact |
| q4_0 | 3 | 88/53 | 75/75 | Exact |
| q4_0 | 4 | 119/64 | 64/64 | Exact |

For both formats, every MTP arm matched the MTP-off token IDs and all nine
recorded persistent-state fields at final state and every shared commit
boundary. The int8 run retained 17.058 GiB minimum physical host availability
and 8.798 GiB minimum effective admission availability. The q4_0 run retained
16.977 GiB and 9.068 GiB, respectively. Both ran under separate 28-GiB memory
scopes; sampled cgroup pressure, limit and OOM counters were zero. State tracing
synchronizes execution, so these are correctness results only. Clock profile
was dynamic, and energy was not request-attributed.

The tested candidate executable SHA256 was
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`; the
prepared 2,048-token prompt SHA256 was
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`. Model,
PLE, expert-profile and MTP assets remained under `~/models/`.

Raw logs and final parity records are in the [int8 run](../2026-10-14-phase5-q2-kv-int8-mtp-parity/)
and [q4_0 run](../2026-10-14-phase5-q2-kv-q4-mtp-parity/). Each directory has
its own checksum manifest. Reproduce either run from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output supervisor --timeout 5400 --interval 1 -- \
    python3 tools/integration/accepted_prefix_parity.py \
      --config bench/results/2026-10-14-phase5-q2-mtp-quality/config-mtp4.json \
      --engine build/integration/candidate/strata --output run \
      --tokens 128 --prompt-tokens 2048 --kv-format int8 \
      --windows 0 2 3 4 --use-config-adaptive-swaps --run
```

This qualifies accepted-prefix parity for the tested Q2_0 prompt and settings.
It does not establish quality or performance for other prompts or formats, and
does not close Phase 5's cancellation, recovery, graph-lifetime or broader
quality gates.
