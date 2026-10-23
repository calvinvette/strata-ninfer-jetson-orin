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

A sparse layer-10 state sweep found position 82 exact and the first recurrent
state difference at position 83 (input token `11`); convolution state remained
exact. At position 83, the layer-9 stage capture found its GDN fields and MoE
input exact, with the first changed field at the final MoE output (`ffn_y`).
Routes and weights match. Only expert 233's part differs when its owner changes
from primary VRAM in serial to CPU in batch. Its same-input activation is
bit-identical (SHA256
`7ce8c948912b5f39471d5809fae4672f168e0cfc1b1e404be211f3ec600d77b3`). The
expert part delta is relative L2 `1.1979e-4` (maximum absolute `8.94e-6`); the
combined MoE output delta is relative L2 `1.3708e-5` (maximum absolute
`5.87e-7`).

With `STRATA_NATIVE_CPU_Q8_1_DOT=all` also set in the independent
`native_expert_parity` oracle, the serial service part matched the GPU oracle
bit-for-bit and the batch service part matched the CPU oracle bit-for-bit. The
CPU/GPU outputs differ by relative L2 `1.1979e-4` for this activation. This
attributes the first captured perturbation in this cell to the expert 233
owner transition. It does not establish the effect across other activations or
workloads. The initial oracle attempt omitted the selector setting and is
retained under `layer9-moe-position-83/expert233-oracle/` as a mismatched
diagnostic; the matched run is under `expert233-oracle-q8all/`.

The raw stage and MoE captures, compact analyses and checksums are in
`layer9-position-83/`, `layer10-position-83/`, and
`layer10-state-sweep*/`. The sparse sweep bounds the first state change to
position 83; Phase 5 remains open.

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

A cache-residency intervention repeated the position-83 layer-9 MoE capture
with a 3,000 MiB requested expert cache and otherwise identical prompts,
selector, context, batch size and capture position. Expert 233 remained primary
VRAM in both serial and batch; all ten routed expert parts and routes matched
bit-for-bit, as did the combined MoE output (2,560/2,560 values; zero delta).
The 1,500 MiB baseline changed expert 233 from VRAM to CPU only in the batch
row and showed the small owner-specific difference described above. This is a
same-input operator-level correctness intervention at one captured position;
it does not establish full-sequence recovery or a beneficial general cache
policy. The run took 131.2 seconds, retained at least 13.73 GiB physical and
admission availability, and sampled zero cgroup memory events. EMC clock
access was denied; energy was not measured. Data and hashes are in
`layer9-cache3000-position-83/` and
`supervisor-layer9-cache3000-position-83/`.

Reproduce the intervention with:

```sh
python3 tools/integration/run_control.py \
  --output /tmp/layer9-cache3000-supervised --timeout 2400 --sample-clocks -- \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/capture_layer9_moe.py \
  --output /tmp/layer9-cache3000 --expert-cache-mib 3000
python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/analyze_layer9_moe.py \
  --run /tmp/layer9-cache3000
```

Phase 5 remains open.

The full 96-token two-live run at a 3,000 MiB cache cap did not restore
sequence parity: slot 0 matched its serial control, while slot 1 first differed
at output index 60; both produced 96 IDs. At 1,500 MiB, the corresponding
Q8_1-all cell first differed at index 66. Because the cache changes expert
ownership and resulting token history, these onset indices are separate cells,
not a paired causal comparison. The position-83 expert-233 capture does show
that the selected operator output becomes exact when that expert remains on
GPU, but this is insufficient to establish full-sequence recovery. The run
took 338.6 seconds and retained at least 13.84 GiB physical/admission
availability, with zero sampled cgroup events. EMC access was denied and energy
was not measured. Raw streams, logs and result are under `run-cache3000-full96/`;
supervisor telemetry is under `supervisor-cache3000-full96/`.

Reproduce with:

```sh
python3 tools/integration/run_control.py \
  --output /tmp/q8all-cache3000-full96-supervised --timeout 3600 --sample-clocks -- \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/run_q8all_target_batch.py \
  --output /tmp/q8all-cache3000-full96 --expert-cache-mib 3000
```

Phase 5 remains open.

The position-83 3,000 MiB cache capture was repeated with the same activation
hash (`0475d4464b64ecea6ac2acc7524ce05e8852333500dbd746ffbadec6f6570181`).
Routes, owner classes, all ten expert parts and the combined MoE output again
matched bit-for-bit; expert 233 remained on primary VRAM in both arms. Minimum
physical/admission availability was 13.83 GiB, with zero sampled cgroup events;
the run took 104.5 seconds. This repeats the local operator-level intervention
only and does not contradict the full-96-token slot-1 mismatch. Raw data and
supervisor samples are under `layer9-cache3000-position-83-repeat/` and
`supervisor-layer9-cache3000-position-83-repeat/`.

Further state tracing under the 3,000 MiB cache cap found variable outcomes
across fresh two-live runs. In one all-layer sweep, slot 1's state first differed
at layer 25 at position 83 (token 11), while its generated IDs still matched
serial for 96 tokens; the same run first differed at layer 25 again at 96 and
layer 24 at 112. A separate layer-24 sweep was exact at 83/96 and changed at
112. A repeat capturing layer 25 at 83 was exact, as was a same-run combined
state-plus-stage capture at that position. In the combined capture every layer's
committed state and all layer-25 intermediate fields matched. These observations
show the position-83 state delta is not reproducible and must not be treated as
the stable divergence boundary.

At position 127, a separate 3,000 MiB run whose slot-1 output first differed
at index 60 showed its first changed committed state at layer 24, on the same
input token (`11`); the recurrent and convolution parts both differed. A
separate stage capture at that position had exact `x`, QKV, gate, beta and `z`,
with `h` first changed. The two captures share the same serial and batch token
prefix through index 59, but were not simultaneous; this is consistent evidence,
not proof of causality. Raw all-layer state dumps remain local. Per-run hashes,
derived analyses and the small intermediate captures are retained in the
corresponding `position-127-state-cache3000/`,
`all-layer-state-sweep-cache3000/`, `layer24-state-sweep-cache3000/`,
`state-layer25-position83-cache3000-repeat/`, and
`joint-state-stage-position83-cache3000/` directories. Phase 5 remains open.

A same-run state-and-stage capture at position 112 refines the boundary on the
slot-1 stream that first diverges at output index 60. Layer 24 is the first
changed committed GDN state (relative L2 `8.60e-6`); its recurrent section is
`2.149e-4` relative L2 and its convolution section is exact. At the same row,
layer-24 stage `x` and QKV are exact, while `h` is the first changed field
(relative L2 `9.592e-5`); gate, beta and z are exact. A separate capture sweep
on the same first-60-token prefix found layer-24 state exact at positions 83 and
96, then changed at 112. The layer-25 position-83 discrepancy described above
remains non-reproducible. This localizes where the position-112 state delta is
visible, without proving which earlier operation or scheduling event introduced
it. The captured run took 135.0 seconds and retained at least 13.84 GiB physical
and admission availability, with zero sampled cgroup events. Raw state is local
with checksums; analysis, stage records and supervisor telemetry are in
`joint-layer24-position112-cache3000/` and
`supervisor-joint-layer24-position112-cache3000/`.

The related targeted CUDA checks `gdn_parity`, `verify_parity` and
`verify_batch_parity` pass (3/3). Those tests verify kernel/operator fixtures;
they do not cover this full model's request scheduling and integrated batch
commit sequence.

An onset sweep sampled layer-24 committed state and stage fields at positions
96, 100, 104, 108, 110, 111 and 112 in one fresh 3,000 MiB two-live run.
The slot-1 stream first differs from serial at output index 60. Layer-24 state
and all captured stage fields are exact at 96, 100 and 104. At position 108
(input token 13), `h` is the first changed stage (relative L2 `5.127e-4`);
`x`, QKV, gate, beta and z are exact. The committed state at that row differs
in recurrent state (relative L2 `2.960e-4`) and convolution state
(`1.129e-3`). Later deltas persist through position 111, then partially cancel
at 112 while remaining nonzero. The first sampled difference is therefore
between positions 104 and 108 in layer-24 history; this does not identify the
operation or scheduling event that introduced it. All captures share the
same run and target slot. Duplicate input tokens at position 100 required
pairing the intermediate row by verifier slot as well as token and position;
the analyzer now accepts `--batch-slot` for that case. The run took 146.8
seconds and retained at least 13.88 GiB physical/admission availability, with
zero sampled cgroup events. Large state dumps remain local; checksums, seven
state analyses, seven stage analyses and raw stage captures are under
`layer24-onset-sweep-cache3000/`; supervisor telemetry is under
`supervisor-layer24-onset-sweep-cache3000/`.

A supervised retry sampled every position 104–108 with the same cache and
two-live target-only setup. It again matched layer-24 state at 104, but this
run already differed at 105: `x` was the first changed stage (relative L2
`1.252e-3`), so QKV and later fields were also different. At 106, `x` remained
first changed; at 107–108, `x` returned to exact while `h` differed. This does
not reproduce the later onset and `h`-first pattern from the seven-position
sweep. The verifier's internal batch row was 1 for the target request in this
run (confirmed by its input-token header); row IDs are reassigned between runs,
so analyses must pair on the captured token and per-run row mapping. The full
96-token request still first diverged at output index 60. This run took 150.0
seconds, retained at least 14.00 GiB physical/admission availability, and had
zero sampled cgroup events. Large raw state and stage dumps remain local; the
derived per-position analyses are in
`layer24-onset-104-108-cache3000-retry/` and supervisor telemetry is in
`supervisor-layer24-onset-104-108-cache3000-retry/`. The varying onset and
stage indicate this capture is sensitive to run state or scheduling; neither
run identifies the initiating operation.

### Layer-23 boundary capture attempt

The existing `STBNDY2` hook was enabled at layer 23 / position 105 to compare
the QSA output boundary with layer 24's input. In the two-live run, it wrote a
serial record (token 7620) but no batch record: both live rows were grouped in
two-token batch windows, while this diagnostic currently records one-row
windows only. The run still showed the target's sequence divergence, but the
layer-23 tensor comparison is unsupported in this cell. Minimum available
physical/admission memory was 14.04 GiB; the run took 134.2 seconds.

A follow-up submitted only the target request to a two-slot batch server.
Serial and server outputs matched all 96 tokens, and the two boundary files
were byte-identical (SHA256
`435b7d5a9bd6ace5ccebfd628d71d5771fc5cbb8df6291bd69f6bb14b0685c84`). Both
records carried `slot=-1`, showing that the single-live request used the
ordinary serial verifier path; this is not batch-path parity evidence. Minimum
available memory was 14.34 GiB and elapsed time was 95.2 seconds. Both raw
captures remain local under `boundary-layer23-position105-cache3000/` and
`boundary-layer23-position105-cache3000-single-live/`, with supervisor
telemetry in their matching `supervisor-*` directories. The boundary hook
needs a one-row batch window to answer the two-live localization question.

### Accepted-prefix trace follow-up

A supervised repeat enabled `STRATA_ACCEPTED_PREFIX_TRACE` and generated 72
tokens per request with the same Q8_1-all, target-only, two-live profile. It
completed in 233.8 seconds with 17.82 GiB minimum physical/admission
availability and zero cgroup events. Slot 0 matched its serial control for all
72 tokens; slot 1 first differed at token 66, again beyond the six-token shared
opening. This is a correctness run, not a performance measurement.

The batch log contained four accepted-prefix records before/at the two slot
handoffs. Three mapped to slot 0's generated prefixes 0–2, and one to slot 1's
prefix 0. All four token IDs and all 11 persistent-state fingerprint fields
matched their corresponding serial records exactly. This verifies the state
copied into each slot at those admission boundaries. No accepted-prefix records
were emitted during the remaining batched decode: 69 slot-0 and 71 slot-1
generated tokens have no direct batch-state record. Terminal per-slot state
parity therefore remains unassessed; the early handoff matches do not imply
full-request parity. See
[`accepted-prefix-72/analysis.json`](accepted-prefix-72/analysis.json).

Reproduce on the configured Orin checkout with the current candidate:

```sh
python3 tools/integration/run_control.py \
  --output bench/results/2026-10-23-phase5-coder-two-live-target-q8all/supervisor-accepted-prefix-72 \
  --timeout 2400 --interval 1 --sample-clocks \
  python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/run_q8all_target_batch.py \
  --output bench/results/2026-10-23-phase5-coder-two-live-target-q8all/accepted-prefix-72 \
  --generated-tokens 72 --accepted-prefix-trace
python3 bench/results/2026-10-23-phase5-coder-two-live-target-q8all/analyze_accepted_prefix_trace.py \
  --run bench/results/2026-10-23-phase5-coder-two-live-target-q8all/accepted-prefix-72 \
  --output bench/results/2026-10-23-phase5-coder-two-live-target-q8all/accepted-prefix-72/analysis.json
```

### Terminal slot-0 committed state

A follow-up captured all GDN layers at absolute position 138 after 72 generated
tokens, with fresh serial controls for both prompt slots. The supervised capture
passed in 205.6 seconds, retained at least 17.85 GiB physical/admission
availability and recorded zero cgroup memory events. Slot 0's token IDs matched
its serial control for all 72 outputs, including the captured input token at
position 138. Its committed GDN state was exact through layer 4, then first
differed at layer 5: 312,213/817,152 values changed (maximum absolute delta
`2.3674e-6`, whole-state relative L2 `2.2442e-7`; recurrent-state relative L2
`9.4241e-6`). Deltas grow downstream. This is an exact-output but non-exact
terminal-state result for slot 0. Slot 1's first changed output is index 66, so
its state at position 138 is not compared to serial. These captures localize a
numerical difference; they do not identify its cause or imply a quality or
performance result. Raw 449 MiB state dumps remain local. The compact analysis
is in [`position138-slot0-state-retry/slot0-analysis.json`](position138-slot0-state-retry/slot0-analysis.json).
