# Q2_0 MTP accepted-prefix and graph regression — Orin — 2026-10-12

This current-binary Phase 5 check compares Q2_0 with MTP disabled and enabled
at windows 2, 3 and 4. It uses a 512-token formatted prompt, eight generated
tokens, 3,000 expert-cache slots, FP16 KV, prefill 512, 64K configured context,
CPU-prefill sharing disabled, and the Q2_0 MTP runtime pack. A 28-GiB
systemd scope and the standard six-GiB availability floor bounded the run;
clocks were observed but not changed.

The no-MTP reference and all three MTP runs generated the same eight token IDs.
Every final persistent-state fingerprint matched. At each common accepted
prefix, all nine state fields matched directly:

| MTP window | Drafts offered / accepted | Commit sizes | Shared prefix checks |
| ---: | ---: | --- | --- |
| 2 | 4 / 4 | 1, 2, 2, 2, 1 | 1, 3, 5, 7, 8 tokens: all pass |
| 3 | 6 / 5 | 1, 3, 3, 1 | 1, 4, 7, 8 tokens: all pass |
| 4 | 6 / 5 | 1, 4, 3 | 1, 5, 8 tokens: all pass |

Minimum whole-board `MemAvailable` was 15.396 GiB; minimum effective
admission headroom was 11.954 GiB. The run lasted 142.52 seconds and recorded
no OOM kill. EMC sampling was denied, and energy was not measured. This is
short-prompt Q2_0 state-parity evidence for these windows and this build; it
does not establish task quality, long-chain drift or performance benefit.

An initial attempt used a Phase 3 Q2_0 config without an `--mtp` path. Although
tokens and state matched, the harness correctly failed its draft-activity gate:
all candidate arms offered and accepted zero drafts. That probe is retained in
`run/` and `supervisor/` and is excluded from the result above. The corrected
config explicitly points to `/home/calvin/models/strata-orin-validation/mtp/rt`;
its output is retained in `run-with-mtp/` and `supervisor-with-mtp/`.

The current candidate binary SHA256 was
`66cf3491ee06a30f340d8210084626fad78c730ccc819d9f15f167f4c0291a62`. The
focused model-independent CTest regression also passed `published_prefix_test`,
`spec_verify_parity`, `captured_graph_trace_test`, `coupled_draft_test` and
`spec_prob_test` (5/5) under the same memory cap. Minimum host availability was
24.439 GiB. Their raw output and telemetry are under
`../2026-10-13-phase5-q2-transaction-regression/supervisor/`.

Reproduction commands from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase5-q2-accepted-prefix/supervisor-with-mtp \
  --timeout 3600 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-13-phase5-q2-accepted-prefix/server-config-with-mtp.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-13-phase5-q2-accepted-prefix/run-with-mtp \
  --tokens 8 --prompt-tokens 512 --windows 0 2 3 4 --run

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase5-q2-transaction-regression/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  ctest --test-dir build/integration/candidate --output-on-failure \
  -R '^(published_prefix_test|spec_verify_parity|captured_graph_trace_test|coupled_draft_test|spec_prob_test)$'
```

Phase 5 remains open for chains longer than 32 tokens, termination cases,
graph/eager interaction, and quality and performance qualification.

## 32-token transaction-chain extension — 2026-10-12

The same configuration and prompt were then extended to 32 generated tokens.
This exercises repeated MTP rounds while retaining a direct no-MTP reference.
All four runs emitted identical token IDs. Every shared accepted-prefix state
and every final state fingerprint matched:

| MTP window | Drafts offered / accepted | Commit events | State parity |
| ---: | ---: | ---: | --- |
| 2 | 17 / 15 | 18 | All 18 boundaries and final state pass |
| 3 | 24 / 19 | 13 | All 13 boundaries and final state pass |
| 4 | 33 / 23 | 12 | All 12 boundaries and final state pass |

The 28-GiB run took 201.17 seconds. Minimum host availability was 15.342 GiB
and minimum effective admission headroom was 11.392 GiB. No OOM kill occurred;
EMC sampling was denied and energy was not measured. This extends direct state
parity to 32-token chains for the same 512-token prompt and fixed cache, but does
not establish long-context quality or graph/eager behavior. Raw traces and
telemetry are under `run-32/` and `supervisor-32/`.

Reproduce the extension with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase5-q2-accepted-prefix/supervisor-32 \
  --timeout 5400 --interval 1 --sample-clocks -- \
  python3 tools/integration/accepted_prefix_parity.py \
  --config bench/results/2026-10-13-phase5-q2-accepted-prefix/server-config-with-mtp.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-13-phase5-q2-accepted-prefix/run-32 \
  --tokens 32 --prompt-tokens 512 --windows 0 2 3 4 --run
```
