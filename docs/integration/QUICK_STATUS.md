# Quick status: graph experiment campaign

Updated: 2026-10-28. Planning committed; component branches are scaffolds.
Target: Orin 32 GB / CUDA SM87 / verified JetPack 7.x. No new baseline or experiment has run.
Integration: `feat/graph-experiments`, forked from NInfer `33b3eb7d`.
[Plan](../graph-experiments/PLAN.md) · [Study](../graph-experiments/STUDY.md) · [Status](../graph-experiments/STATUS.md) · [References](../graph-experiments/REFERENCES.md)

| Branch | Experiments / state | PP / TG / TTFT | Next |
| --- | --- | --- | --- |
| main | Inherited runtime/history | Historical only | No campaign changes |
| feat/ninfer-expert-e0 | Ongoing NInfer; long-context state variation open at fork | Not the JP7 baseline | Finish/qualify candidate |
| feat/graph-experiments | G0–G8 planning and coordination | not_run | Pin final NInfer + actual JP7 |
| feat/graph-g0-baseline | G0: JP7 inventory, final NInfer pin, baseline; not_run | not_run | Await hardware baseline |
| feat/graph-g1-prefix-cache | G1: Canonical fragments; hybrid checkpoints; not_run | not_run | Wait G0 |
| feat/graph-g2-speculation | G2: Suffix/MTP; state-conditioned ranker; not_run | not_run | Wait G0 |
| feat/graph-g3-prefetch | G3: N-gram/expert graph residency; not_run | not_run | Wait G0/G2 traces |
| feat/graph-g4-state-compression | G4: Replay; mixed precision; buffered updates; not_run | not_run | Wait G0/rollback contract |
| feat/graph-g5-expert-compression | G5: Shared bases; direct/materialized factors; not_run | not_run | Wait G0/G3 |
| feat/graph-g6-memory-encoder | G6: Memory tokens; literal retrieval; draft head; not_run | not_run | Wait G1–G4 |
| feat/graph-g7-architecture | G7: QSA bank; state generation; fragment repair; not_run | not_run | Wait G6 |
| feat/graph-g8-combined-study | G8: Interactions; held-out Pareto study; not_run | not_run | Wait qualified components |

Required quants: Coder IQ1_M, Coder Q2_0, original ISTA IQ3_S.
Optional: original IQ2_XS and IQ3_XXS, subject to verified artifact/backend support.
All runtime gates here are CUDA/Orin; maestro HIP/SYCL builds are deferred.
Keep 6 GiB physical headroom plus workspace reserve. No additive host/GPU memory accounting.
Metrics require run/baseline IDs and linked evidence; no projected gains appear as measurements.
Update after every experiment batch/blocker and at session end; keep this file <=60 lines.
Earlier quick-status detail remains in [the pinned pre-campaign version](https://github.com/calvinvette/strata-ninfer-jetson-orin/blob/33b3eb7daa57c025e24d085e9d4a9ea23f7d388e/docs/integration/QUICK_STATUS.md)
and [integration history](STATUS.md).
