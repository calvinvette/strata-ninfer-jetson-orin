# Q2_0 int8-KV MTP × workload interaction — Orin — planned

The existing seven-pair MTP3 confirmations at 512 and 7,501 prompt tokens use
different binary hashes. They support separate workload-specific findings, but
not a clean combined interaction estimate. [PLAN.md](PLAN.md) defines the
same-binary 2×2 follow-up and limits the conclusions to its prompts/profile.

The screen and confirmation runner are prepared for source commit
`c55e84756e5497e1e1fd9805e815db5859dfa959` and binary SHA256
`57b2222c370c2b9b2590350f1feb206627b70c393394221fd634c53b37d314e0`.
The runner checks the shared non-MTP configuration, model checksums while the
Orin campaign lock is idle, and binary identity before and after each cell.
`campaign_plan.py` generates randomized paired order; `prepare_confirmation.py`
will create new exact-length prompts for held-out confirmation.

No interaction campaign has run. The current-source Coder IQ1_M 256K run in
`../2026-10-15-phase7-current-source-coder-iq1m-256k/` still owns Orin. The
runner's screen dry run produced six complete pairs (three per prompt length),
and its lock guard correctly refused artifact hashing while that supervised
run was active. Its CPU-only design/oracle tests pass 3/3. Do not launch either
stage until the current supervisor has reached a terminal state.

After Orin is idle, execute the three-pair screen with:

```sh
python3 bench/results/2026-10-16-phase6-q2-int8-mtp3-workload-interaction/run_campaign.py \
  --suite screen --campaign-name screen-1
```

The screen uses the existing 512-token retrieval/arithmetic and 7,501-token
near-limit retrieval prompts. Only after reviewing that screen should new
held-out confirmation prompts be generated and the seven-pair confirmation run.
Both stages must finish on the same binary/artifact set before any
MTP-by-workload effect is reported.
