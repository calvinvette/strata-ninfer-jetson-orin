# Direct GDN state at the first verifier-input divergence layers — Orin — 2026-10-20

These two randomized same-service pairs captured raw pre/post verifier GDN
state at model layers 12 and 34, position 511, in three identical 512-token
requests. They follow the corrected all-layer input trace, which first found
adaptive input divergence at layer 34 from initial to intermediate and at
layer 12 from intermediate to recovery. Each pair compared the adaptive cap-8
schedule with delayed adaptation, with prompt cache disabled, 12 generated
tokens per request and `STRATA_NATIVE_CPU_Q8_1_DOT` set to the recorded
selector. Both orders were randomized independently.

The accepted-prefix comparator parsed all three raw pre/post records per arm
and matched each raw post-state FNV hash to the corresponding service
`STATE_HASH_GDN` hash at that layer ordinal. The direct captures show:

| Layer | Arm | Initial → intermediate | Intermediate → recovery |
| ---: | --- | --- | --- |
| 12 | Delayed control | pre and post exact | pre and post exact |
| 12 | Adaptive cap-8 | pre and post exact | pre exact; post differs in 785,976/786,432 recurrent and 10,240/30,720 convolution values |
| 34 | Delayed control | pre and post exact | pre and post exact |
| 34 | Adaptive cap-8 | pre exact; post differs in 786,332/786,432 recurrent and 10,240/30,720 convolution values | pre exact; post differs in 786,424/786,432 recurrent and 10,240/30,720 convolution values |

Both requests in each transition had identical generated token IDs. Thus, at
each layer the recorded state entering the update matched, while the state
leaving the update followed the already-different input activation. The layer
12 result aligns with the intermediate-to-recovery activation split; layer 34
aligns with the initial-to-intermediate split. The delayed control remained
exact at both layers. This confirms the raw changed states and service hash
join; it does not establish why upstream adaptive execution produced the
different inputs or prove that a particular migrating expert caused them.

All four arms passed under `MemoryMax=28G`. Minimum host/admission availability
was 14.09/14.09 GiB; `high`, `max`, `oom`, and `oom_kill` counters were zero.
No performance claim is made. The reports and paired raw captures are retained
in the `layer12/` and `layer34/` directories. The analysis is reproducible
with:

```sh
python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-gdn-state-layers12-34/compare_state_prefix.py \
  --run-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-gdn-state-layers12-34/layer12 \
  --layer 12 --gdn-ordinal 9

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-gdn-state-layers12-34/compare_state_prefix.py \
  --run-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-no-cache-gdn-state-layers12-34/layer34 \
  --layer 34 --gdn-ordinal 26
```

The `layer12-prompt-cache6-check/` directory is an earlier configuration check
from the same runner before explicitly setting `--prompt-cache 0`. It is
retained but excluded from the conclusions above.
