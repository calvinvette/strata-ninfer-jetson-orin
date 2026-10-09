# Reference snapshot

Root `AGENTS.md` and `docs/integration/` govern this repository. This directory is
an unchanged reference snapshot of NInfer, not part of the active Strata build.
`UPSTREAM_AGENT_GUIDANCE.md` is retained historical documentation, not active
instructions. In particular its old desktop target and unlimited build-parallelism
guidance do not define this Orin integration project.

Do not edit reference files to implement an optimization. Promote the relevant
code and tests into the active tree with source attribution and qualification.
An intentional reference refresh must update `reference/ninfer-import.json` and
document its revision, exclusions and validation status. Retain license notices.
