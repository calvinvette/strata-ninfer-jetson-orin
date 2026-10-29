# E6 same-backend GDN repeatability by prompt length

This screen repeats the held-out Q2_0 retrieval in fresh engine processes under
identical settings, once with strict NInfer and once with Strata, at 2K and 16K
prompt lengths. Every pair returned the exact expected answer and identical
47 token IDs and residency. Each pair passed all nine final-state fields. At
all three sampled accepted positions, all 36 GDN layers were bitwise identical
between the two fresh processes for both backends.

| Prompt length | Backend | Pair runtime | Minimum available memory | Final state / GDN parity | OOM kills |
| ---: | --- | ---: | ---: | --- | ---: |
| 2,048 | NInfer | 180.3 s | 11.44 GiB | exact / bitwise across 3 positions | 0 |
| 2,048 | Strata | 180.1 s | 11.79 GiB | exact / bitwise across 3 positions | 0 |
| 16,384 | NInfer | 476.7 s | 10.98 GiB | exact / bitwise across 3 positions | 0 |
| 16,384 | Strata | 471.0 s | 11.16 GiB | exact / bitwise across 3 positions | 0 |

The comparison positions were prompt boundary and offsets 22 and 45 after it:
2048/2070/2093 and 16384/16406/16429. These exact same-backend controls
contrast with the 160K same-backend pairs, which matched output and residency
but failed final persistent-state parity and showed GDN drift. This supports a
context-length-dependent repeatability problem in the tested 160K path; it does
not locate a precise threshold, prove that length alone is causal, or establish
which backend is responsible. The 16K and 160K workload configurations differ
in configured context capacity, so isolate prompt length from capacity in the
next screen.

Next screen 32K using a fixed configured capacity shared with the 16K fixture,
then advance to 64K if state remains repeatable. Keep same-backend controls,
selected accepted-prefix captures, exact task checks, and the six-GiB physical
memory floor. If the transition appears, repeat around that boundary before
localizing operators. These are correctness controls, not performance results.

Pair details: [2K NInfer](../2026-10-28-e6-q2-active-compute-quality-2k/same-backend-ninfer-repeat/README.md),
[2K Strata](../2026-10-28-e6-q2-active-compute-quality-2k/same-backend-strata-repeat/README.md),
[16K NInfer](../2026-10-28-e6-q2-active-compute-quality-16k/same-backend-ninfer-repeat/README.md),
[16K Strata](../2026-10-28-e6-q2-active-compute-quality-16k/same-backend-strata-repeat/README.md).
Raw captures, comparator JSON, logs, and supervisor samples remain local-only.
