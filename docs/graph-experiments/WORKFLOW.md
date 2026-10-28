# Branch, commit and reporting workflow

Use `feat/graph-experiments` as the integration branch. Components use `feat/graph-gN-...`
as listed in [PLAN](PLAN.md). Git refs have no true parent relationship; ancestry records it.
All component scaffolds begin at the completed planning commit. Before implementing a phase,
merge the latest integration branch and its required qualified predecessors; record dependency SHAs.
Do not merge experiments into `main` automatically.

Make small, reviewable commits within each component branch:
1. Contract, parameter manifest and independent oracle.
2. Minimal implementation behind an opt-in control.
3. Functional checks and failure/rollback paths.
4. Screening harness and raw result manifest.
5. Confirmed measurements, limitations and status update.

Commit at every coherent milestone, before changing experiment direction, and before ending a work
session. Commit failed experiments with their diagnosis where useful. Do not commit credentials,
weights, private task data, build products or unbounded state captures.
Use messages such as `graph(g2): add suffix proposal contract` and `bench(g2): record held-out screen`.
Do not squash away experimental provenance when merging components; preserve meaningful commit history.

Update [STATUS](STATUS.md) and the one-page [QUICK_STATUS](../integration/QUICK_STATUS.md)
after every completed/aborted experiment batch, material blocker or phase transition, and before each
session ends. This is an in-repository working rule, not an unattended scheduled automation.
Each dashboard row includes branch, experiment IDs/state, PP/TG/TTFT with baseline and result link,
and next action. Use `not_run` until measured. Keep the dashboard <=60 lines; detailed logs belong
in linked reports. On the integration branch it is authoritative across all components.
After a component report lands, merge or cherry-pick only its reporting commit onto integration;
do not pull unqualified runtime changes merely to update status. Refresh sibling reports when resumed.

Reports live in `bench/results/<YYYY-MM-dd@HH.mm>-graph-gN-<slug>/` (America/Detroit).
Retain exact commands, manifest, raw machine-readable rows, summaries and failures.
Large/proprietary data stays outside Git with a durable URI/hash and access requirements.
Documentation prose distinguishes proposed, implemented, screened, confirmed, rejected and unsupported.

For this campaign, user-authorized CUDA/Orin qualification supersedes inherited all-backend build gates.
Do not schedule maestro HIP/SYCL builds. Record deferred portability at review.
Keep CPU oracles and protocol tests. No runtime source or build-system change is part of the planning setup.
When architecture changes pack/cache formats, version them and document migration/rollback.
