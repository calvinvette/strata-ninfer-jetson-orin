# Coder adaptive migration with matched Q8_1 arithmetic — Orin — 2026-10-19

This randomized same-service correctness pair tests whether the adaptive-state divergence persists when both services use the same opt-in CUDA-mirroring CPU arithmetic. Both arms set `STRATA_NATIVE_CPU_Q8_1_DOT=all`, which selects Q8_1 for the three implemented native expert pairs: IQ2_S/Q2_0, IQ2_S/IQ4_NL and IQ3_XXS/IQ4_NL. Other expert formats retain the normal ggml CPU path. The current v3 route capture records layer 1, the first owner boundary implicated by earlier all-layer captures.

Both services ran the same IQ1_M Coder artifact, expert profile and four-request sequence: 512-token short, 2,048-token long, the same 512-token short again, and one identical continuation. Each generated 16 tokens. The arms were cadence-100,000 delayed updates and cadence-4 updates capped at eight swaps. Both were supervised at 28 GiB, with FP16 KV, 8K context, 3,000 configured expert slots, prompt cache 6 and accepted-only update policy. The randomized order was adaptive first, delayed control second. The service runs accepted no speculative drafts.

The delayed-control arm returned the same tokens and all nine persistent-state fields at all 16 accepted prefixes of the initial and recovery short requests. The adaptive arm differed at all 16 recovery prefixes, changed seven of nine final persistent-state fields, and returned different token IDs at 10/16 recovery positions. Its continuation happened to return the same 16 token IDs as the delayed control, while all 16 continuation state fingerprints still differed. This demonstrates that equal final text does not establish state parity.

Direct cross-arm accepted-prefix comparison found:

| Request | Token IDs different | State fingerprints different |
| --- | ---: | ---: |
| Initial short | 0/16 | 8/16 |
| Long | 3/16 | 16/16 |
| Recovery short | 10/16 | 16/16 |
| Continuation | 0/16 | 16/16 |

Layer-1 capture found seven matching expert-ID/activation rows between initial and recovery prompts, but 27 owner assignments flipped in the adaptive arm; the delayed arm had zero flips and no later activation differences. The adaptive arm then showed nine later activation differences. The active arm passed all 15 adaptive swap-byte checks and all 15 residency-table checks. Both 28-GiB supervisors passed. Minimum host/admission availability was 14.24 GiB, with zero observed cgroup low/high/max/OOM/kill events. Clocks were observed dynamically; no energy or timing comparison is made.

This result shows that the tested Q8_1 mirror selector does not restore adaptive migration state parity for this sequence. It does not prove that every owner change is causal, because only one layer's routes are captured here and unsupported expert pairs retain default CPU arithmetic. It does not qualify task quality, other prompt lengths, other quantizations, or a serving policy. Phase 5 remains open.

The pinned model is IQ1_M from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision `5348543e0147355ac9cbcb031184a3546350988e`. Binary SHA256 is `b09ed0b5774de235d145bff869950730a78cbf5ddc6b4057098d70b981130eaa`; its source code is commit `b6ea6188`. Full model shard identities, source HEAD and capture details are in [`artifact-identities.json`](artifact-identities.json). Accepted-prefix comparisons are in [`verification.json`](verification.json).

The first run under `pair/` completed its service requests but the copied wrapper failed after completion because it required capture format v2; current source wrote v3. It is retained as a harness failure and excluded. The corrected run under `pair-retry1/` accepts v3 and passed both arms. Reproduce with:

```sh
python3 bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/run_pair.py \
  --output bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/reproduction \
  --seed 202610197 --run
python3 bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/analyze_pair.py \
  --pair-dir bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/reproduction \
  --output bench/results/2026-10-19-phase5-coder-q8_1-adaptive-matched-pair/reproduction-verification.json
```
