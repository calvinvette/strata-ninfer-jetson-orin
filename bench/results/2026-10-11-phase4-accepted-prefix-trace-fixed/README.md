# Accepted-prefix state trace and worker determinism diagnostic — Orin — 2026-10-11

This correctness-only run adds an opt-in `STRATA_ACCEPTED_PREFIX_TRACE` path to
Strata's serving loop. After each verifier commit, it waits for the async commit
to finish and logs the accepted draft count, published token IDs and the full
eleven-field persistent-state fingerprint (`L`, GDN, PLE, QSA tail/dead/pooled
and pooled-full, KV, MTP, stale KV and `ple_prev`). The existing end-of-request
state hash uses the same helper. With the variable unset, this path does not
wait at each commit or copy state for hashing. Hashing every commit adds
synchronization and transfer overhead, so these runs are not timing evidence.

Four independently started IQ1_M Orin server processes ran the same 512-token
measured prompt with an eight-token generation cap, after the same distinct
512-token warmup. Worker settings 8 and 11 each ran twice in randomized order.
All requests completed under the six-GiB supervisor; minimum `MemAvailable` was
9,086,951,424 bytes (8.46 GiB). Every run used 6,519 actual expert-cache slots.
All four runs emitted the same eight token IDs and output-text hash.

The correctness gate failed on persistent state. At the common first committed
boundary `L=512`, all four runs have identical `ple`, `ple_prev` and stale-KV
hashes, while GDN, QSA tail/dead/pooled/pooled-full, KV and MTP hashes each
have four distinct values. Both worker 8 and worker 11 also differ between
their own two repetitions. This shows that the observed state divergence is
present before the later generated prefix and is not explained only by the
worker-count change. It does not identify the source of nondeterminism. The
full per-commit token/state traces are preserved in `experiment/`; `analysis.json`
contains their parsed comparison.

The existing full 64-token worker screen remains a separate failed result: it
had matching output hashes in 14 of 15 runs, but a different hash in one
11-worker run and differing final state fingerprints across worker counts. The
new short trace does not replace that failure. No worker timing is used or
promoted, and no default changes.

A first trace-smoke attempt in sibling directory
`../2026-10-11-phase4-accepted-prefix-trace-smoke/` failed in the harness because
its parser counted both warmup and measured requests. The corrected parser
selects the last request, confirms the trace covers exactly the emitted tokens,
and retains the first attempt for audit.

The native CUDA `strata` target compiled locally. The changed shared
CUDA/HIP `src/program/generate.cpp` also compiled in the full maestro1 HIP build;
the SYCL backend build completed as well, although it has a separate generator
source tree and does not include this source edit. Build logs and binary/source
hashes are retained in this directory. maestro1 provides compile evidence only.

A separate [end-of-request hash control](../2026-10-11-phase4-default-state-hash-control-fixed/)
passed with `STRATA_ACCEPTED_PREFIX_TRACE` unset: warmup and measured API
requests completed, and the refactored legacy final state-hash path emitted
both end-of-request records without accepted-prefix trace lines. Its minimum
availability was 8.51 GiB. The initial reused-prompt setup failure is preserved
at `../2026-10-11-phase4-default-state-hash-control/` and excluded from the
control.

The model, pack, MTP and tokenizer checksums are referenced by
`model-artifact-identities.json`; artifacts remain in `~/models/`. The
reproduction command uses a new empty output directory:

```sh
build/integration/venv/bin/python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase4-accepted-prefix-trace-reproduction/supervisor \
  --timeout 1800 -- \
  build/integration/venv/bin/python tools/integration/pool_worker_screen.py \
  --config bench/results/2026-10-11-phase4-accepted-prefix-trace-fixed/base-config.json \
  --workloads bench/results/2026-10-11-phase4-accepted-prefix-trace-fixed/measured-workloads.json \
  --output bench/results/2026-10-11-phase4-accepted-prefix-trace-reproduction/experiment \
  --workers 8 11 --baseline-workers 11 --repetitions 2 --seed 20261011
```
