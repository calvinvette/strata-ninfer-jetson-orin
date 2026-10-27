# E6 active staged-compute held-out retrieval/state check at 160K — state parity failed

Date: 2026-10-27 (Orin AGX). Source: `2b0c2eb6` (the source tree was unchanged from that pushed checkpoint); binary SHA-256: `44c358706192a57ced038cff0478cec05ae3c7476258c7a90e5b1f1ef9a4374e`.

This one-run-per-arm diagnostic compared Strata grouped compute with strict NInfer grouped compute, staging enabled in both. Profile: Qwen3.8-Flash-Next GSQ-RCO Q2_0; 3,000 expert slots, 6-GiB resident budget, 3-GiB workspace reserve, MTP-2, prefill 128, 8 workers, 256K configured context, `pcie-frac=1`. The exact-length 163,840-token held-out prompt planted three retrieval codes and required their ordered return plus suffix sum `1768`.

| Check | Strata grouped | Strict NInfer grouped | Result |
|---|---|---|---|
| Exact expected answer | Pass | Pass | Same exact text |
| Generated tokens | 47 | 47 | Token IDs identical |
| Resident map | Same 3,000-slot map | Same 3,000-slot map | SHA-256 `a02fd81e…` in both |
| Persistent state | Captured | Captured | **Failed:** `gdn`, `tail`, `pooled`, `pooled_full` and `kv` differ; `L`, `ple`, `dead` and `ple_prev` match |
| Minimum available RAM | 6.79 GiB sampled | — | Above 6-GiB floor |
| Peak swap used | 1.71 GiB sampled | — | Swap observed |
| Paired diagnostic elapsed | 54.2 min | — | Sequential, traced; not a throughput measure |

The exact text and token IDs do not qualify the request because five persistent-state fields differ. The supervisor stopped after the checker returned failure; it did not trigger the memory floor, and OOM counters were zero. This is a failed correctness cell at 160K prompt length, not an unsupported memory cell. The available-memory margin was narrow. Do not claim state-equivalent active NInfer at this length until the divergence is diagnosed and the comparison passes. Clocks were observed without controls; energy was not measured.

Reproduce by generating the fixture with `python3 tools/integration/prepare_ninfer_long_retrieval.py --tokens 163840 --output <new-output-dir>`, then running `tools/integration/ninfer_q2_retrieval_check.py` under `tools/integration/run_control.py` with `--compare-staged-backends --run`, Q2_0 config at `--max-context 262144`. The 2K report contains the complete invocation.

Raw fixture, config, traces, residency maps and supervisor samples remain local in this directory; model files and build products remain outside Git.

The follow-up raw-`o` capture confirms that the first generated-token
discrepancy exists before GDN output normalization: at position 163840, raw
`o` differs by relative L2 `3.13e-8` (max absolute `1.49e-8`), with normalized
`y` at `3.31e-8`. Both remain below `9e-8` through position 163876, then jump
at 163877 (`o`: `5.11e-4`; `y`: `1.41e-3`), matching the first large split in
other captured GDN intermediates. The paired run took 53.96 minutes, minimum
available memory was 7.20 GiB and peak swap was 5.98 GiB. Exact answer, token
IDs and residency still matched while the same five persistent-state fields
did not. A no-capture 2K control passed all output and state checks (182.2
seconds, minimum available memory 11.55 GiB). These measurements localize the
divergence but do not identify its arithmetic cause or which backend is
correct. See the [expanded localization note](GDN_STATE_LOCALIZATION.md) and
[compact raw-output summary](generated-gdn-trace-summary.json).

An independent FP64 recurrence replay over the captured `h`, gate and beta
inputs matched raw `o` at all 46 generated positions. Worst relative L2 was
`3.52e-7` for Strata and `3.58e-7` for NInfer, below the registered `1e-5`
operator bound. At position 163877, the recurrence inputs already differed
substantially (`h`: 10,233/10,240 values; gate and beta: 48/48 each), which
explains why their raw outputs separate there. The first differences in this
trace's layer-2 `x`, gate and beta inputs appeared at position 163844. The
replay starts from a separate same-task prompt-boundary capture, so it does not
establish a same-run trajectory.


A corrected accepted-prefix GDN-array diagnostic found exact equality at GDN
layer 0, a tiny first difference at layer 1 (relative L2 `6.87e-10`), then
amplification at layer 2 (`3.41e-6`) and layer 3 (`4.41e-3`). The all-layer
relative L2 was `3.60%`; the originating operation remains unknown. See the
[GDN localization note](GDN_STATE_LOCALIZATION.md).

A generated-token trace of layer-2 GDN intermediates then recorded 46 positions
(163840–163885). At the prompt boundary (163839), the separately captured
layer-2 state was bitwise equal. At the first generated token, only `y` differed
in the trace (579/6,144 values, max absolute delta `5.96e-8`, relative L2
`2.50e-8`); captured `gdn_out` and FFN values were exact. Differences appeared
in `x`, `gate`, `beta` and FFN intermediates at position 163849, then in `qkv`,
`h`, `z` and `gdn_out` at 163877. Final answer, token IDs and residency still
matched, while the same five persistent-state fields did not. Minimum available
RAM was 6.70 GiB and peak swap 4.72 GiB. This localizes the first observed
generated-side difference but not its underlying arithmetic cause or which
backend is correct; it is not performance evidence. See the [expanded
localization note](GDN_STATE_LOCALIZATION.md) and [compact trace
metrics](generated-gdn-trace/generated-token-trace-summary.json).

A subsequent 160K pair captured the fused grouped-residual read at model layer
2 / position 163844. All five outputs (`xn`, `lo`, `rs`, `inj_out`, `mixed`)
matched bitwise, while the request again returned the exact answer, all token
IDs and the same residency with differing `gdn`, `tail`, `pooled`,
`pooled_full` and `kv` state. The pair took 53.97 minutes; minimum available
RAM was 7.09 GiB, peak swap 6.36 GiB and OOM counters were zero. This does not
match the GDN `x` delta at the same position in a separate paired trace. Since
the GDN capture copies the fused read's `mixed` input as `x`, capture both in
the same run next to resolve the between-run discrepancy. Raw read captures
remain local; the compact comparison is in the localization note.
