# Current-build Q2_0 MTP 128-token accepted-prefix parity

This Phase 5 correctness run compared the current candidate on a formatted
2,048-token prompt and 128 generated tokens with MTP off and windows 2, 3 and
4. Each arm used a fresh engine, FP16 KV, 3,000 expert-cache slots, 8K
configured context and the same Q2_0/MTP assets under `~/models/`. The shared
config disabled adaptive swaps, isolating the MTP transaction path. The
accepted-prefix trace compared generated token IDs and all nine persistent
state fields at each shared commit boundary. This is correctness evidence;
tracing makes it unsuitable for timing.

All four arms emitted the same 128 token IDs and had identical final state.
Every shared accepted-prefix state matched: window 2 had 75 boundaries, window
3 had 64, and window 4 had 55. MTP2 offered/accepted 74/53 drafts, MTP3
126/64, and MTP4 162/73. The current candidate binary SHA256 was
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e` and the
prepared prompt SHA256 was
`93cefb75fa4bb48eec0bcbf5771e06a6cce6bbad03c463df644fb45634b3dc15`.

The 28-GiB supervisor passed with minimum physical host availability 16.867
GiB and minimum effective admission availability 8.703 GiB. The six-GiB host
floor and separate three-GiB workspace reserve were preserved. All sampled
cgroup pressure and OOM counters were zero. Clocks were observed without
changes; energy was not process-attributed.

## Accepted-only adaptive swaps enabled

The same current binary, prompt, cache, KV format and 128-token chain were then
rerun with `--adapt-every 4 --adapt-accepted-only` from the Q2_0 MTP quality
config. The harness's new `--use-config-adaptive-swaps` switch preserved that
policy instead of forcing `--adapt-swaps 0`. MTP-off/2/3/4 again emitted
identical token IDs and matched final state; every shared prefix matched
directly at 83/71/61 boundaries for windows 2/3/4. Drafts offered/accepted
were 67/45, 101/57 and 132/67. The supervisor passed with minimum host
availability 16.903 GiB and minimum admission availability 8.812 GiB; cgroup
pressure and OOM counters remained zero.

This is stronger transaction evidence for accepted-only adaptation on this
single current-build Q2_0 prompt and fixed cache. It does not resolve the
separate prompt/cache cases where residency changes affected output, nor cover
other KV formats, cancellation, or timing. The script's default still disables
adaptive swaps so existing investigations remain isolated; its new switch is
opt-in and has unit coverage in `tools/integration/test_accepted_prefix_parity.py`.

Two setup attempts before the valid run are retained separately in
`supervisor/` and `supervisor-no-adapt/` and excluded. The first was refused
before model readiness because the harness forces `--adapt-swaps 0` while the
initial config still enabled `--adapt-accepted-only`. The corrected shared
config removes that accepted-only option. The second attempt reused an existing
output directory and did not launch an engine. The passing run is under
`run-no-adapt/` with telemetry in `supervisor-no-adapt-rerun/`.

Reproduce from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-q2-accepted-prefix128-current/supervisor-no-adapt-rerun \
  --timeout 7200 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-14-phase5-q2-accepted-prefix128-current/config-no-adapt.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-14-phase5-q2-accepted-prefix128-current/run-no-adapt \
  --tokens 128 --prompt-tokens 2048 --windows 0 2 3 4 --run
```

Repeat with the configured accepted-only adaptive-swap policy by using
`--config bench/results/2026-10-14-phase5-q2-mtp-quality/config-mtp4.json`,
writing telemetry to `supervisor-adaptive/`, writing traces to `run-adaptive/`,
and adding `--use-config-adaptive-swaps` before `--run`.

Together the two policies close one long-chain accepted-prefix parity cell for
this Q2_0 prompt and cache. They do not establish parity for other prompts,
cache sizes or KV formats, cancellation, or MTP performance. Phase 5 remains
open.
