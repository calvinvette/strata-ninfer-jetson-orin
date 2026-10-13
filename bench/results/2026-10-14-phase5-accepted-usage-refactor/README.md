# Accepted-only usage transaction boundary — Orin — 2026-10-14

The accepted-only adaptive policy stages routed-expert counts by verifier row.
After `ver.commit(publish_n)`, it must add only the first `publish_n` rows to
the persistent usage counters and retire the staging vector. The row fold is
now the tested `strata::spec::commit_accepted_usage` helper in
`include/strata/spec/accepted_usage.hpp`; the serving loop still calls it only
after the verifier commit succeeds. It validates the commit length, guards the
size multiplication, rejects malformed staging without mutation, and clears a
successful transaction so the next request can use a different window size.
This refactor preserves existing behavior and does not change the default
adaptation policy.

The new `accepted_usage_test` covers commit lengths zero, one, intermediate and
full; mutation of rejected suffix rows; a following transaction with a
different window size; and invalid length/size rejection without mutation. The
five focused CUDA CTests passed: `accepted_usage_test`, `published_prefix_test`,
`spec_verify_parity`, `controller_test`, and `spec_prob_test`.

The rebuilt Orin CUDA binary then passed a fresh IQ1_M service comparison with
accepted-only cadence 4. MTP-off and MTP4 generated identical 32-token output,
final persistent state and all 17 shared commit-boundary fingerprints. MTP4
offered 31 drafts and accepted 15. The six-GiB supervisor passed with minimum
host availability and effective admission headroom both 14,375,444,480 bytes
(13.39 GiB); no clock controls were applied. This is a runtime regression check
for this prompt and configuration, not a broad state-transaction qualification.

The local candidate is SHA256
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`.
The changed generator also compiled and linked in maestro1's HIP-configured
`q8_1-neon/build-hip` tree with one build job. Its generator object is
`763c1dda434f9bc2ebdcdc94d8cf9f84340597c63eb75f81aac381d9eec2517b`, and the
linked executable is
`3057743748ee365248f1cff9978ffb5c0489921f4c0d83c33929f1329ba438c3`. The
separate SYCL generator source was not changed. maestro1 build evidence is
compile/link only.

Two failed/confounded observations are retained and excluded. First, a help
probe accidentally invoked the comparison script as a workload; its partial,
unsupervised MTP-off log is in `accidental-excluded/`. It was stopped when
detected. A supervised rerun overlapped that process, then mismatched at token
21 and its first state boundary; its artifacts are in `overlapped-invalid/`.
That comparison cannot isolate the code change from concurrent service
activity. With the board idle and no other Strata service, the isolated rerun
above passed. No partial or confounded result is included in the passing result.

The isolated runtime command was:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-14-phase5-accepted-usage-refactor/isolated/supervisor \
  --timeout 1800 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/compare_accepted_usage_incident_prompt.py \
  bench/results/2026-10-14-phase5-accepted-usage-refactor/isolated/trace
```

Source and report file hashes are in `SHA256SUMS.txt`; service traces,
supervisor samples, and the overlapped attempt are retained in their
subdirectories.
