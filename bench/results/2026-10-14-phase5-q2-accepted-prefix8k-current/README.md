# Q2_0 8K accepted-prefix MTP parity

This current-binary Phase 5 check compared MTP off and windows 2, 3 and 4 on
an exact 8,192-token formatted prompt with 32 generated tokens. Each arm used a
fresh service, 16K configured context, 3,000 expert-cache slots, FP16 KV, and
the configured `--adapt-every 4 --adapt-accepted-only` adaptive-swap policy.
The accepted-prefix trace directly compared published token IDs and all nine
persistent-state fingerprints. It is correctness-only evidence; state tracing
perturbs timing.

All four arms emitted identical token IDs and had identical final persistent
state. Every shared accepted-prefix boundary matched: MTP2 had 22 boundaries,
MTP3 had 19, and MTP4 had 15. Drafts offered/accepted were 17/10, 24/13 and
31/17, respectively. The current candidate binary SHA256 was
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`; the exact
formatted prompt SHA256 was
`c2238eb12df1db3bbd274720f47156105780350d21c87630b0e803b680585f67`.

The 28-GiB systemd supervisor passed with minimum physical host availability
16.713 GiB and minimum effective admission availability 9.581 GiB. This stayed
above the six-GiB physical host floor and separate three-GiB workspace reserve.
All sampled cgroup pressure and OOM counters were zero. Clocks remained
dynamic and read-only; energy is not process-attributed.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-accepted-prefix8k-current/supervisor \
  --timeout 10800 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase5-q2-accepted-prefix8k-current/config-mtp4.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-q2-accepted-prefix8k-current/run \
  --tokens 32 --prompt-tokens 8192 --windows 0 2 3 4 \
  --use-config-adaptive-swaps --run
```

This closes one 8K-prompt accepted-prefix state cell for this Q2_0 artifact,
cache and adaptive-swap policy. The short generation is not task-quality or
performance qualification; other prompts, cache and KV settings, cancellation
and MTP performance remain open. Model files remain under `~/models/`.
