# Graph campaign status

Updated: 2026-10-28. State: planned, no runtime experiments performed.
[One-page dashboard](../integration/QUICK_STATUS.md) is the cross-branch index.
[Plan](PLAN.md), [study](STUDY.md), [workflow](WORKFLOW.md), [references](REFERENCES.md).

## Setup record

- Created integration branch from `feat/ninfer-expert-e0` at
  `33b3eb7daa57c025e24d085e9d4a9ea23f7d388e`.
- Plan, factor domains, workload blocks, source attribution and publication practices recorded.
- Component refs scaffolded from the common planning head; implementation has not started.
- Required cohorts: Coder IQ1_M, Coder Q2_0, original ISTA-DASLab IQ3_S.
  Optional full-model IQ2_XS and IQ3_XXS are capability-gated.
- CUDA/Orin-only campaign qualification replaces maestro HIP/SYCL obligations.
- Expected NInfer gains and JP7 upgrade are assumptions for planning, not observed facts.
- No GPU benchmarks, model downloads, driver changes, training or runtime implementation in this setup.

## Next executable work: G0

1. Bring in the final qualified NInfer commits without rewriting this branch's planning history.
2. Record actual JP7 version, device/toolchain/power/clock/storage inventory and artifact hashes.
3. Build and qualify CUDA; characterize same-backend long-context variation.
4. Run historical bridge cells, then realistic repeated-prefix agent sessions and paired confirmations.
5. Freeze baseline ID and quality/numerical budgets before enabling candidate features.

## Known inherited risks

The fork's latest report reproduces long-context state trajectories that cross backend labels
between paired runs. Exact answer/token parity does not resolve that confounder.
Keep original [integration status](../integration/STATUS.md) and linked raw diagnostics intact.
Do not report a new compression, speculation or numerical effect against an unstable denominator.

## Update log

| Date | Phase | Change | Evidence / metrics |
| --- | --- | --- | --- |
| 2026-10-28 | Setup | Branch and phased study documentation | Documentation only; all PP/TG/TTFT not_run |

Append concise decisions here; put full measurements under the workflow's result directories.
Record failed and unsupported cells as well as successful ones. Promote only qualified component changes.
