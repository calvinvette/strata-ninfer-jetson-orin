# Coder IQ1_M fixed-residency recovery confirmation — Orin — 2026-10-16

This seven-block confirmation retests the Phase 5 finding that adaptive
CPU/GPU expert migration changes persistent state. Each randomized pair ran the
same four-request sequence in a fresh service: an uncached 512-token request,
a 2,048-token request, the original 512-token request again, and one further
identical 512-token continuation. Each request generated 16 tokens. The two
arms were an effectively delayed-adaptation control (`--adapt-every 100000`)
and the accepted-only adaptive policy that swaps at most eight experts every
four rounds (`--adapt-every 4 --adapt-swaps 8`). This is correctness and state
evidence, not a performance comparison.

Both arms used the exact `Coder-GGUF/IQ1_M/` shard paths for
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`. Shard SHA256 values are
`e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad` and
`316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The runtime binary SHA256 was
`fd9c010cb5e126dfa1f272d6c2864830df25a67c08c5aacc69ea4c98d5c2a29b`; the
recorded source commit is `b2cde9b41b4eab1179a24d80133fc5a236560acb`.
Configuration, model hashes, prompt hashes and per-request raw token IDs and
state fingerprints are retained with the campaign.

All 14 supervised services passed. The output and persistent-state comparison
reproduced in every block:

| Request | Control vs cap-8 token positions different | State fingerprints different |
| --- | ---: | ---: |
| Initial short, 512 tokens | 0/16 | 5 of 10 |
| Long, 2,048 tokens | 3/16 | 7 of 10 |
| Recovery short, same 512 tokens | 0/16 | 5 of 10 |
| Continuation short, same 512 tokens | 16/16 | 7 of 10 |

The delayed control recovered the exact initial short output and all state
fingerprints in all seven services. Cap-8 also returned the same immediate
recovery text as its initial short request, but five state fingerprints
changed every time. The next identical short request then differed at all 16
token positions in every block. Thus matching the immediate recovery answer is
not sufficient evidence that recurrent state was restored. Each cap-8 service
passed all 15 adaptive refill-byte checks and all 15 residency-table checks, so these results do not point to corrupted refill bytes or stale
residency ownership.

The per-run route capture inspected layer 0; its first seven rows showed no
owner flip or activation difference. The earlier [all-layer trace and operator
oracle](../2026-10-16-phase5-coder-swap-budget-screen/README.md#all-layer-route-trace-and-operator-oracle--2026-10-16)
located the first repeated CPU/GPU owner changes at layer 1 and independently
reconstructed their quantization-dependent operator deltas. This confirmation
strengthens the state/continuation evidence but does not establish full
service-level causality or correct the arithmetic difference.

The 28-GiB supervisor retained a 14.069-GiB minimum host-availability floor
and 13.306-GiB minimum admission availability across 2,745 one-second samples.
All cgroup `low`, `high`, `max`, `oom` and `oom_kill` counters were zero. CPU
clocks ranged from 729.6 MHz to 2,201.6 MHz and GPU clocks from 306 MHz to
1,300.5 MHz; EMC clock readback was unavailable. Clocks were observed, not
controlled. Energy is not attributed per request. No timing claim is made from
these instrumented runs.

Keep adaptive cap-8 migration unqualified for exact persistent-state recovery
on this Coder IQ1_M workload. The delayed-adaptation arm is a correctness
control for this sequence, not a generally qualified serving profile. No
default changed; Phase 5 remains open.

Two early preflight attempts are retained under `campaign/` and
`campaign-retry1/`. Neither reached model inference: the first omitted the
workload fixture and the second pointed to an invalid model root. They are
excluded. The successful seven-block campaign is under `campaign-retry2/`.

Reproduce on Orin1 with the same model files under `~/models/`:

```sh
python3 bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/run_campaign.py \
  --output bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/campaign-new \
  --blocks 7 --seed 202610167 --continuations 1 --run
python3 bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/analyze.py \
  --run bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/campaign-new \
  --output bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7/summary-new.json
```
