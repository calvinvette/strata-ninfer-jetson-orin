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
| 4,096 | Exact answer on both | Match | Match | GDN, PLE, tail, pooled, pooled-full, KV | 2.645% over 29.4M floats | 11.45 GiB |
| 8,192 | Exact answer on both | Match | Match | GDN, tail, pooled, pooled-full, KV | 3.159% over 29.4M floats | 11.28 GiB |
| 16,384 | Exact answer on both | Match | Match | GDN, PLE, tail, pooled, pooled-full, KV | 2.572% over 29.4M floats | 10.85 GiB |

Both runs generated 47 tokens, returned all three retrieval codes and the exact
suffix sum, and matched the same startup residency map hash as the 2K
diagnostic (`a02fd81e...ddf7`). The 4K, 8K and 16K result JSON records identify
4,551, 4,588 and 4,583 staged expert reads, respectively. The exact answer and
token IDs remained stable across the 2K, 4K, 8K and 16K prompt fixtures. State
fingerprints did not match at any tested length, and the earlier five-shape
workload replay had token-output mismatches. The held-out task therefore does
not close staged-miss correctness or release qualification.

Each numeric GDN comparison covers 36 layers and 29,417,472 floats. At 4K, 28,565,809
values differed (97.11%), global relative L2 was `0.02645`, and global RMS
absolute delta was `0.006622`. State layer 1 differed by `3.32e-6` relative
L2, state layer 2 by `0.003146`, and the largest layer-relative error was
`0.06126` at state layer 27. The first 4K run did not produce dumps because it
requested `L=4143` rather than actual accepted length `L=4142`; a corrected
supervised rerun captured arrays. The raw 118 MB arrays remain local; sizes
and hashes are in
[`4096/evidence/gdn-dump-artifact-hashes.json`](4096/evidence/gdn-dump-artifact-hashes.json).

At 8K, 28,487,309 values differed (96.84%), global relative L2 was `0.03159`,
and global RMS absolute delta was `0.007895`. State layer 1 differed by
`7.44e-7` relative L2; state layer 2 by `0.002410`; the largest layer-relative
error was `0.05793` at state layer 26. Global GDN error is similar in scale to
the 2K diagnostic, but the first-layer error is smaller. Error is not
monotonic with prompt length and does not identify a cause. The raw 118 MB
arrays remain local; sizes and hashes are in
[`8192/evidence/gdn-dump-artifact-hashes.json`](8192/evidence/gdn-dump-artifact-hashes.json).

At 16K, 28,453,384 values differed (96.72%), global relative L2 was `0.02572`,
and global RMS absolute delta was `0.006424`. State layer 1 differed by
`3.19e-6` relative L2; state layer 2 by `0.002676`; the largest layer-relative
error was `0.05513` at state layer 26. The raw arrays remain local; sizes and
hashes are in
[`16384/evidence/gdn-dump-artifact-hashes.json`](16384/evidence/gdn-dump-artifact-hashes.json).

## Reproduction and evidence

Each context directory contains the exact workload, config, result JSON,
engine logs, residency maps and `run_control.py` memory/clock/tegrastats
records. Reproduce with `tools/integration/prepare_ninfer_long_retrieval.py`
and `tools/integration/ninfer_q2_retrieval_check.py --compare-cpu-miss-staged
--dump-gdn --run`, wrapped in `tools/integration/run_control.py`. Set
`--dump-gdn-at 4142` for 4K, `--dump-gdn-at 8238` with `--max-context 16384`
for 8K, and `--dump-gdn-at 16430` with `--max-context 32768` for 16K.

Minimum available physical/admission memory stayed above the six-GiB floor in
all runs. No clocks or services were changed. Sequential prompt/decode times
are in `run/results.json` and should not be interpreted as an effect estimate.
