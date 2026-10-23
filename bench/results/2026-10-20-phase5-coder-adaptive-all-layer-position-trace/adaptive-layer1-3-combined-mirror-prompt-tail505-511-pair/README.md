# Failed prompt-tail state-capture selection — Orin — 2026-10-20

This retained failed cell tested the combined exact-layer CPU Q8_1 selectors
`iq2_s/q2_0@layer=1,iq2_s/iq4_nl@layer=3` while requesting verifier pre/post
GDN state at every position from 505 through 511. The delayed-control service
completed all three requests under supervision, but the runner failed its
capture-contract check: the state hook emitted records only at position 511
because it captures pre/post state only for single-token verifier windows.
Positions 505–510 were handled in multi-token windows. The randomized order put
delayed control first, so no adaptive arm ran. This is a failed/unsupported
instrumentation cell, not evidence about adaptive behavior.

Raw delayed-control all-layer dispatch, verifier MoE/GDN, commit-state and
supervisor files are retained. They must not be used as a paired comparison.
The follow-up run narrows raw pre/post-state capture to position 511 and retains
multi-position route, MoE and GDN intermediate captures across 505–511.
