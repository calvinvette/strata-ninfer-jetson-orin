# Q2_0 captured/eager × MTP2 screen — 2026-10-14

Three randomized blocks screened the interaction between captured decode and
MTP2, using the current Orin Q2_0 PLE model and pack. Each cell started a fresh
service, ran a distinct 512-token warmup, then one measured synthetic request
with exactly 512 prompt tokens and 16 generated tokens. Prompt caching and trace
recording were disabled. The output text matched byte-for-byte in all 12 cells;
this short deterministic task checks route parity only, not task quality or
accepted-prefix persistent-state parity.

| Block | Captured MTP0 prompt/decode (s) | Eager MTP0 (s) | Captured MTP2 (s) | Eager MTP2 (s) |
| --- | ---: | ---: | ---: | ---: |
| 0 | 19.928 / 4.450 | 11.978 / 3.355 | 8.292 / 3.481 | 15.970 / 3.904 |
| 1 | 10.180 / 3.554 | 8.919 / 3.499 | 12.397 / 3.325 | 9.993 / 3.403 |
| 2 | 11.890 / 3.303 | 11.456 / 3.346 | 9.030 / 3.642 | 11.848 / 3.452 |

Prompt latency varied substantially across conditions and randomized blocks.
The design has only three single-request screening repetitions per condition,
and the model's expert file traffic shares the host page cache. The measured
timings therefore do not support a stable graph, MTP, or interaction effect;
no paired confidence interval or performance claim is reported. On each MTP2
cell the service offered eight drafts and accepted six. Decode timings were
close to the MTP0 controls and do not establish an MTP benefit. Keep capture and
MTP defaults unchanged. A separate held-out, multi-pair confirmation with
controlled cache state is required before promotion.

All 12 supervised cells passed under the 28-GiB cgroup limit. Minimum host
availability was 16.70 GiB; minimum admission availability was 6.66 GiB. The
six-GiB host-availability floor and separate three-GiB workspace reservation
were maintained; cgroup OOM/limit events remained zero. CPU/GPU clocks were
observed dynamically; EMC clock access was denied, and energy was not measured
at process scope. These are Orin measurements, not desktop evidence.

Reproduce on the same checkout with:

```sh
python3 bench/results/2026-10-14-phase5-phase6-graph-mtp-screen/run_screen.py \
  --output /tmp/phase5-phase6-graph-mtp-screen --blocks 3 --seed 202610141
```

Then use `--run` only with the local Q2_0 model and MTP artifacts configured in
the four JSON configs. `run/experiment.json` and per-cell request, supervisor,
memory, clock and tegrastats records preserve the raw observations. The binary
SHA256 was `857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.
Model and pack files remain in `~/models/` and are not included in this result.
