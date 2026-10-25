# E5 Q2_0 NInfer MTP-2 cancellation state check

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This is a bounded
functional/state check for the strict NInfer Q2_0 route with static expert
ownership and MTP-2. It is not a performance measurement or broad Phase 5
qualification.

## Setup and identities

The current Release `strata` executable SHA256 was
`527d7833ac398b82368c37b1001ed1adfdd245730b28482a90fef28851161be8`. The target
model was the two-shard Coder Q2_0 artifact and matching Q2 PLE deployment pack;
the MTP runtime was `~/models/strata-orin-validation/mtp/rt`, converted from
`mtp/mtp-q2_0.gguf`. The source MTP GGUF SHA256 was
`a22206a4d74eafbf31063a84610292535fb3b49af9a339963817fd04aed81e4d`; runtime
`dense.bin` and `experts.bin` hashes were `c724dc0b0822ada5d2977bf5bde821605feabaa64ea2e0045b67ca656329070a` and
`09398406be61f1f54c93861f449e48b8df0bfccbc9ec9b2b7636775a6ea9244f`.

The service used 8K context, 3,000 profile-ranked expert slots, prefill 128,
eight CPU workers, `--spec 2 --mtp-max-t 2`, MTP batch mode 1, strict
`--expert-backend ninfer`, and `STRATA_PREFILL_CPU_SHARE=0`. The guard preserved
6 GiB physical RAM headroom and the separate 3 GiB workspace reserve. The exact
engine config is in [`evidence/engine-config.json`](evidence/engine-config.json).

## State, cancellation and recovery

The test used `tools/integration/mtp_cancel_state_parity.py`, canceled after
five non-empty text deltas, then compared the canceled service with two fresh
exact-length reference services. It passed all checks:

- The canceled request committed seven tokens, across accepted-prefix state
  lengths 48, 50, 52 and 54. Three MTP drafts were accepted.
- Each reference reproduced all committed token IDs and every recorded state
  fingerprint (`GDN`, PLE, tail, dead, pooled, KV, MTP, stale and previous PLE
  state) at all four accepted prefixes. The two references also matched each
  other. The visible canceled text `1 2 3` was a prefix of both reference
  completions (`1 2 3 4`).
- The canceled server remained alive and returned `Hello Orin!` to a fresh
  recovery request.
- Engine logs show verifier and MTP prefill/round CUDA graph instantiation in
  this run. This supports the tested captured-path lifecycle, but does not
  count graph replay launches or qualify every window shape.

The complete accepted-prefix and comparison record is in
[`evidence/cancel-state-result.json`](evidence/cancel-state-result.json).

## Memory and limits

The supervised run lasted 78.8 seconds. Minimum `MemAvailable` and minimum
admission availability were both 18,289,954,816 bytes (17.04 GiB), above the
6 GiB floor; cgroup memory events remained zero. Observed CPU clocks ranged
from 729.6 MHz to 2.202 GHz and GPU clocks from 306 MHz to 1.3005 GHz. EMC
clock readback was denied. Energy was not attributed to this run. The supervisor
summary is in [`evidence/supervisor-result.json`](evidence/supervisor-result.json);
raw one-second telemetry and engine logs remain beside the run output locally.

The first attempt used the source `.gguf` as `--mtp`, but Strata requires its
converted runtime directory. It exited before serving any requests and is
retained as [`evidence/initial-source-gguf-failure.json`](evidence/initial-source-gguf-failure.json).
The corrected run used the already existing `mtp/rt`; no model was downloaded
or modified.

This check covers one static Q2_0 profile, one MTP-2 cancellation boundary and
one recovery. It does not test held-out/long retrieval or scoring prompts, MTP-4,
adaptive residency, strict mode against mixed-codec models, or an end-to-end
performance gain. E5 remains in progress; the default backend and settings are
unchanged.
