# Phase 8 closeout — bounded Q2_0 integration profile

Phase 8 is complete for one documented, opt-in Orin AGX integration profile.
This closes the integration-release gate for that bounded scope; it does not
close Phases 5 or 6, promote defaults, or qualify features excluded below.

| Gate | Evidence and result |
| --- | --- |
| Documented profile and identities | [`RELEASE_PROFILE.md`](RELEASE_PROFILE.md) pins the Q2_0 model shards, pack, source, binary, runtime settings, memory floor, reproduction command and rollback path. Models remain under `~/models/`. |
| Current CUDA/ARM64 functional runtime | The 2026-10-22 current-candidate smoke passed exact 7,498-token ingestion, three-marker retrieval in order, and same-service recovery. It retained 17.84 GiB minimum host and 8.71 GiB admission availability over 317 samples, with zero cgroup memory events. The [smoke record](../../bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/README.md) includes the candidate binary hash and test commands. |
| Default-path regression | The current candidate passed all 130 runnable CUDA CTests; two optional IQ-fixture tests skipped, and no test failed. Python integration discovery passed 163/163. The CTest run retained at least 21.4 GiB host availability and had zero sampled cgroup memory events. |
| HIP and SYCL source portability checks | Fresh maestro1 Release builds compiled and linked the shared diagnostic sources with two jobs; both `strata --help` checks returned zero. This is x86_64 build/CLI evidence only, not accelerator execution. See the [backend record](../../bench/results/2026-10-22-phase5-maestro1-q8-selector-backend-build/README.md). |
| Rollback | The pinned-control/current-candidate API comparison passed its seven documented scenarios. Restore the pinned executable together with its compatible invocation and configuration; the pinned binary does not accept every Q2_0 candidate-profile option. |
| Opt-in changes and attribution | Native-expert arithmetic selectors and the graph-cap override are opt-in; defaults were not changed. NInfer source remains an immutable reference. No upstream pull request was opened, and Strata portability PR #1621 remains separate. |

The selected configuration is Q2_0, FP16 KV, MTP off, 3,000 exact expert
slots, 8K context, prefill chunk 128, eight workers, prompt cache and adaptive
swaps off, and a 3,072-MiB workspace reserve. It is an experimental
qualification target for this Orin/model cell, not a general support claim.

## Exclusions

- Adaptive CPU/GPU migration remains excluded because long accepted chains
  change persistent state and later output.
- MTP remains off. The MTP2 cancellation cell passes at five captured prefixes,
  but broader accepted-state, multi-live batch correctness, and graph/MTP
  interaction gates remain open.
- Phase 6's measured interactions cover specific workloads and cohorts only.
  Named tegrastats rails include board idle/background energy and are not
  process-attributed; no general Pareto choice or default promotion follows.
- Other quantizations, boards, concurrency levels, changed defaults, and
  JetPack/CUDA upgrades are outside this profile.

Reopen Phase 8 if the selected model, source, binary, configuration or excluded
feature set changes, or if new evidence contradicts this bounded profile. The
overall integration plan remains active for unresolved Phase 5 and Phase 6
gates; this closeout does not mark those gates passed.
