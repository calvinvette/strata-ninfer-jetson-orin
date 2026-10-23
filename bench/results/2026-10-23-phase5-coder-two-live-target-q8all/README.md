# Two-live target-only batch with Q8_1 selector forced to all

This supervised Orin diagnostic tests whether forcing `STRATA_NATIVE_CPU_Q8_1_DOT=all`
removes the known two-live target-only output mismatch. It does not measure
performance.

The two fresh serial controls and the two-slot batch used the same prompts and
engine settings: Coder IQ1_M, MTP disabled, context 1,024, 1,500 MiB requested
expert cache, prompt cache 6, and 96 generated token IDs per request. Both serial
and batch engines received `STRATA_IQ_MT_MIN=1` and the Q8_1 selector setting.
The binary SHA256 is `afc710def2ad1c0f0905afa015f5cae3e50063b29d7c4fdd62f186ab21a7358d`;
the source checkout was `b40dcf76b972440306b01a4953d32206e8b316ec`. The model is
`ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision
`5348543e0147355ac9cbcb031184a3546350988e`, IQ1_M. Shard checksums are copied
from the repository's existing model manifest; this run did not rehash the
29-GiB model files.

Slot 0 matched its serial token IDs across all 96 outputs. Slot 1 first differed
at output index 66 (zero-based), although both returned 96 IDs. The earlier
default-selector diagnostic first differed near index 60, but it is a separate
selector/configuration cell, so the onset difference does not establish a cause.
Three terminal batch `STATE_HASH` records are present in the raw engine log but
were not joined to prompts; persistent-state parity is therefore unassessed.

A follow-up captured verifier logits at absolute position 133, the row that
emits slot 1's first differing token. The serial and batch rows receive the
same input token ID (`3008`), but all 248,320 logits differ (relative L2
`0.03150`, maximum absolute difference `0.4373`). The top two reverse order:
serial ranks token 2100 at `22.9859` over 5435 at `22.9068`, while batch ranks
5435 at `23.0309` over 2100 at `22.9599`. The output comparison confirms those
are the differing token IDs at index 66. This localizes the first output change
to verifier logits, but not the preceding layer or operation. The capture took
191.5 seconds and retained at least 17.44 GiB physical/admission availability,
with zero sampled cgroup memory events. Capture and comparison commands are in
`capture_divergence_logits.py` and `analyze_divergence_logits.py`; raw rows and
analysis are under `logits-position-133/`.

An all-layer committed-GDN capture at the same position found the first state
difference at model layer 10, on input token `3008`. At that layer 320,613 of
817,152 saved values differ, but the maximum absolute delta is only
`8.94e-8` (whole-state relative L2 `2.72e-9`); all 30,720 convolution values
are exact. At layer 12, whole-state relative L2 has grown to `0.00418` and
817,149 values differ. Thus the earliest captured divergence is in recurrent
state at layer 10, while the logits analysis shows the eventual output-rank
change at position 133. This does not identify the arithmetic operation that
introduced the small state delta. The state run retained at least 17.52 GiB
physical/admission availability with zero sampled cgroup events. The 113 MiB
serial and 225 MiB batch state dumps remain local because of their size; their
SHA256 hashes and the derived layer-by-layer comparison are retained in
`position-133-state/`.

A layer-10 stage capture at position 133 was repeated. For the row with input
token `3008`, both captures agree exactly with serial through `x`, QKV, `h`,
gate, beta and `z`. The first difference is the GDN recurrence output `y`:
2,207/6,144 values, maximum absolute delta `8.94e-8`, relative L2 `7.70e-8`.
The projected GDN output and subsequent captured FFN values are exact. This
matches the tiny recurrent-state difference and rules out a large QKV input or
projection error in this cell. The batch row's internal slot was 0 in the first
capture and 1 in the repeat, while its token identity stayed the same; row
assignment can change, so comparisons pair by absolute position and input
token. The two-row STGDIAG5 payload is field-major; the retained analyzer reads
the row slices from each field block. Raw stage dumps and their hashes are in
`layer10-position-133/` and `layer10-position-133-repeat/`. The separate serial
slot-0 stage capture is retained under `layer10-serial-slot0/`.

The stage evidence still does not distinguish a tiny recurrence arithmetic
difference from a relevant state-history difference entering the recurrence.
It is a correctness localization only; no performance or general correctness
claim follows.

The run took 278.6 seconds. The supervisor sampled dynamic CPU/GPU clocks and
tegrastats, but EMC clock access was denied and energy was not measured. Minimum
physical and admission availability were both 17.54 GiB, above the preserved
6-GiB host floor; sampled cgroup memory events were all zero. These values
describe this one correctness run only.

Reproduce with:

```sh
python3 tools/integration/run_control.py \
  --output /tmp/q8all-target-batch-supervised \
  --timeout 2400 --sample-clocks -- \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/run_q8all_target_batch.py \
  --output /tmp/q8all-target-batch-raw
```

The selected report files are `run/result.json`, the three engine logs in
`run/`, and the supervisor's `result.json`, `memory.jsonl`, and `tegrastats.txt`
in `supervisor-attempt-02/`. The runner refuses to overwrite an output
directory. The logits capture's supervisor record is in
`supervisor-logits-position-133/`; the state capture's is in
`supervisor-state-position-133/`. The runner consumes the already downloaded model under
`~/models/strata-orin-validation/`; it downloads nothing.

This does not establish multi-live correctness, quality, throughput, energy,
or an operator-level cause. Phase 5 remains open.
