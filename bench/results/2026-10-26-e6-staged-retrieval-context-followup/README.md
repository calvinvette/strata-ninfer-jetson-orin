# Staged-miss held-out retrieval context follow-up

Date: 2026-10-26. Hardware: Jetson AGX Orin 32 GB, CUDA 12.6, SM87. Model:
Qwen3.8-Flash-Next GSQ RCO Q2_0. Binary SHA256:
`3a8133abbbe83dce0ec87473d5843f8cb59d9e59ed276198ab008747ff333b90`, from
source `68de59ab2c6736ca328c83afabe2138123cd7051`. Each prompt used the same
held-out retrieval/arithmetic fixture at the stated exact token length. CPU-miss
Strata and strict NInfer staged runs were sequential diagnostics with prompt
cache off and 3,000 residency slots. These are functional/state checks, not
paired performance measurements.

## Results

| Prompt | Expected answer | Token IDs | Residency map | Final state fields that differ | GDN relative L2 | Minimum available RAM |
| ---: | --- | --- | --- | --- | ---: | ---: |
| 4,096 | Exact answer on both | Match | Match | GDN, PLE, tail, pooled, pooled-full, KV | Not dumped; requested length was one token past actual accepted length | 11.45 GiB |
| 8,192 | Exact answer on both | Match | Match | GDN, tail, pooled, pooled-full, KV | 3.159% over 29.4M floats | 11.28 GiB |

Both runs generated 47 tokens, returned all three retrieval codes and the exact
suffix sum, and matched the same startup residency map hash as the 2K
diagnostic (`a02fd81e...ddf7`). The 4K and 8K result JSON records identify
4,551 and 4,588 staged expert reads, respectively. The exact answer and token
IDs remained stable across the 2K, 4K and 8K prompt fixtures. State fingerprints
did not match, and the earlier five-shape workload replay had token-output
mismatches. The held-out task therefore does not close staged-miss correctness
or release qualification.

The 8K GDN comparison covers 36 layers and 29,417,472 floats. It found
28,487,309 differing values (96.84%), global relative L2 `0.03159`, and global
RMS absolute delta `0.007895`. State layer 1 differed by `7.44e-7` relative L2;
state layer 2 by `0.002410`; the largest layer-relative error was `0.05793` at
state layer 26. Compared with the 2K diagnostic, the final global GDN error is
similar in scale, but the first-layer error is smaller. It is not monotonic
with prompt length and does not by itself identify a cause. The 118 MB raw GDN
arrays remain local; sizes and SHA256 values are in
[`8192/evidence/gdn-dump-artifact-hashes.json`](8192/evidence/gdn-dump-artifact-hashes.json).

The 4K harness asked for a GDN dump at `L=4143`, while both engine logs report
actual accepted length `L=4142`; no arrays were produced. The state hashes,
answer, tokens, route counts and memory telemetry remain valid for that run.

## Reproduction and evidence

Each context directory contains the exact workload, config, result JSON,
engine logs, residency maps and `run_control.py` memory/clock/tegrastats
records. Reproduce with `tools/integration/prepare_ninfer_long_retrieval.py`
and `tools/integration/ninfer_q2_retrieval_check.py --compare-cpu-miss-staged
--dump-gdn --run`, wrapped in `tools/integration/run_control.py`. For the 8K
case set `--max-context 16384` and `--dump-gdn-at 8238`.

Minimum available physical/admission memory stayed above the six-GiB floor in
both runs. No clocks or services were changed. Sequential prompt/decode times
are in `run/results.json` and should not be interpreted as an effect estimate.
