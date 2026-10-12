# MTP cancellation parity at fixed cache capacities

Date: 2026-10-12. Device: Jetson AGX Orin. Model: existing IQ1_M Coder validation pack and its compatible MTP weights. This is Phase 5 transaction/state evidence, not a Q2_0 result or a performance comparison.

The parity harness now accepts `--fixed-expert-cache N`, copies the source config, and applies the same positive slot count to the canceled request and every fresh exact-length reference. The default remains unchanged. The harness also writes its effective engine environment into each generated server config so config-level overrides cannot silently replace state tracing or the requested prefill setting.

Two supervised runs used one visible text delta to trigger cancellation, checked same-process recovery, and compared every accepted-prefix token ID and persistent-state fingerprint at the exact committed length against three fresh references. Both used `STRATA_PREFILL_CPU_SHARE=0`, `STRATA_MTP_BATCH=1`, state hashing, accepted-prefix traces, the existing integer-list prompt, and dynamic clocks. The supervisor retained the six-GiB host-availability floor and sampled clocks without changing them.

| Fixed expert-cache slots | Cancellation/recovery | Fresh references | Minimum host availability |
|---:|---|---|---:|
| 3,000 | pass | 3/3 match cancellation and each other at L=48, 52 | 13.32 GiB |
| 5,000 | pass | 3/3 match cancellation and each other at L=48, 52 | 8.34 GiB |

The prior [5,000-slot run](../2026-10-11-phase5-mtp-cancel-state-parity-ignore-eos-rerun/result.json) recorded matching token IDs but differing persistent state at L=48 and L=52. That discrepancy did not reproduce in the current three-reference 5,000-slot run. It remains unexplained; these results do not establish why it occurred or prove parity for other prompts, prefix lengths, EOS behavior, longer cancellation chains, or pipeline execution. The observed five committed token IDs match across both new cache-capacity runs. No timing or cache-capacity performance claim is made.

Results:

- [3,000-slot harness result](../2026-10-12-phase5-mtp-cancel-state-parity-fixed-cache-3000/run/result.json)
- [3,000-slot supervisor record](../2026-10-12-phase5-mtp-cancel-state-parity-fixed-cache-3000/supervisor/result.json)
- [5,000-slot harness result](../2026-10-12-phase5-mtp-cancel-state-parity-fixed-cache-5000/run/result.json)
- [5,000-slot supervisor record](../2026-10-12-phase5-mtp-cancel-state-parity-fixed-cache-5000/supervisor/result.json)

The integration tests for the cache override pass. Phase 5 remains open for broader transactions and other prefix/termination cases.
