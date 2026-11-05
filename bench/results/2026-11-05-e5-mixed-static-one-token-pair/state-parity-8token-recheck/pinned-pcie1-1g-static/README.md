# Eight-token Coder state pair with pinned PCIe misses

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a matched
functional/state check, not a timing or answer-quality comparison.

## Setup and owner coverage

Strata and strict NInfer used Coder IQ1_M, prompt token IDs `1,2,3`, greedy
decoding, MTP-2, the same static 391-slot profile/cache, `--pcie-frac 1.0`,
`--resident-budget-gib 1`, and `STRATA_RESIDENT_HEADROOM_GIB=6`. Cache adaptation
was disabled with `--adapt-every 0 --adapt-swaps 0`. Both arms emitted eight
accepted tokens and offered no accepted speculative drafts.

At layer 0 / position 2, both arms selected the same experts:
`143,175,252,25,54,240,35,204,19,246`. Four rows were primary-VRAM/foresight
owned and six were PCIe owned. The CPU-output capture contained no rows for
that dispatch. The per-expert CUDA oracle for the same activation is recorded
in the [one-token staged check](../../layer0-ten-expert-oracle/pcie-frac-1-pinned1g/README.md).

## Tokens and persistent state

Both arms generated the exact same sequence:
`4,5,6,24218,10,4838,1665,15`. All eight accepted-prefix trace entries were
captured, but the persistent-state hashes already differed after the first
committed token (`gdn`, `ple`, `tail`, `dead`, `pooled_full`, `kv`) and remained
different through the final state. `pooled` also differed from the second
boundary onward. Thus pinned PCIe execution makes this synthetic output
sequence agree, but does not provide exact persistent-state parity. This
single token-ID prompt is not a task-quality gate and does not establish a
state-drift tolerance.

The guarded pair retained at least 19.29 GiB available RAM, above the 6 GiB
floor; the pre-existing cgroup OOM-kill counter stayed at one. Clocks and
energy were not measured. Timing is excluded because state tracing is enabled.
The service logs (`strata-engine.txt`, `ninfer-engine.txt`), token/state
comparator result, owner summary and supervisor record are included here.
