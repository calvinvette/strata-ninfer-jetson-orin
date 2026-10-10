# Current candidate request profile — Orin — 2026-10-10

Nsight Systems profiled the current ARM64 CUDA candidate on the exact
`pp512+tg64` API workload. The run used the existing IQ1_M pack and tokenizer,
FP16 KV, 4K configured context, prefill chunk 64, requested expert cache 5,000
(6,519 actual slots), `--spec 4`, MTP max 4 and mapped experts. It completed a
warmup and one measured request under the six-GiB `run_control.py` floor; the
minimum physical `MemAvailable` was 8,177,410,048 bytes (7.62 GiB). Nsight was
2024.5.4.34. The profile is diagnostic, not a performance comparison.

## Request-window attribution

| Window | Client ms | Kernel events | Sum kernel ms | Union intervals ms | Q6_K→FP16 dequant events | Q6_K→FP16 dequant sum / fraction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Warmup | 22,419.5 | 124,246 | 14,169.6 | 14,086.8 | 1,024 | 3,174.2 ms / 22.40% |
| Measured | 17,294.2 | 128,795 | 11,881.1 | 11,794.6 | 1,024 | 2,556.9 ms / 21.52% |

Q6_K-to-FP16 dequantization is again the largest named kernel by summed
duration in the measured request window. The next entries are spin-wait
`wait_flag_ge_kernel` (1,485.6 ms / 12.50%), Q5_K-to-FP16 dequantization
(794.4 ms / 6.69%), prefill MMQ copy16 (684.6 ms / 5.76%) and Q4_K-to-FP16
dequantization (539.7 ms / 4.54%). In the ±50 ms boundary sensitivity check,
Q6_K dequantization ranges from 2,550.4 to 2,556.9 ms for the measured request;
that check is not a confidence interval. The warmup value is unchanged by the
same boundary check.

Summed kernel time includes concurrent streams and spin waits; it is neither
GPU utilization nor a request critical-path fraction. The near-equality of
summed and union kernel intervals does not isolate useful work from waits. The
trace lacks request NVTX markers; alignment uses the Nsight session epoch and
the median sampled wall/monotonic offset, whose spread was 0.00191 ms, but
absolute alignment error is not independently bounded. CPU IP sampling is
disabled, so this does not attribute ARM CPU quantization, routing or pool
work. Whole-process CUDA API and memory-operation CSVs include startup and
teardown and are not request-local costs.

The measured API request completed 512 prompt and 64 generated tokens; it
reported 87 drafts and 34 accepted. The warmup reported 81 drafts and 36
accepted. These are workload counters, not a state or quality qualification.
CPU clocks varied; GPU/EMC frequency values were unavailable. No energy claim
is made. This profile selects Q6_K dequantization for mathematical/packing
contract review and operator measurement. It does not establish a kernel
optimization opportunity or authorize a dispatch change.

## Retained evidence and reproduction

The supervised request, raw memory samples, tegrastats, engine log, API request
records, capabilities, three Nsight CSV summaries and request-window summary
are in this directory. `identities.json` gives source/binary, model, prompt,
tokenizer, config, profiler and analysis identities. The `.nsys-rep` and SQLite
export remain in ignored `build/integration/nsys-candidate-pp512-tg64/`; their
sizes and SHA256 values are recorded in `identities.json`.

The exact capture command is the `command` array in `supervisor/result.json`.
For an export from that retained raw report:

```sh
nsys stats --report cuda_gpu_kern_sum,cuda_api_sum,cuda_gpu_mem_time_sum \
  --format csv --output NEW_STATS --force-export=true PROFILE.nsys-rep
python3 bench/results/2026-10-09-request-profile/analyze_windows.py \
  --sqlite PROFILE.sqlite --requests requests.json --memory supervisor/memory.jsonl \
  --output NEW_WINDOW_SUMMARY.json
```

Profiler overhead, concurrent kernel execution, approximate request-window
alignment and unlocked clocks limit interpretation. Use unprofiled paired
controls for performance confirmation.

## Source-tensor and conversion contract follow-up

The profiled symbol is `dequant_kernel<(int)14,H16>` in
`src/kernels/cuda/dequant_bf16.cu`, reached through `Gemm::native`'s ordinary
`dequant_f16` path. It is distinct from `iq_dequant_f16` and the native Q6_K
matrix-vector kernel. Joining the GGUF shard headers to Nsight's launch grids
shows that the observed grids correspond to these Q6_K tensor shapes (GGUF
stores `[input, output]`; the matrix is `[output, input]`):

| Grid X | Model matrix | Q6_K tensors in artifact | Calls across warmup + measured |
| ---: | ---: | ---: | ---: |
| 1920 | 6144 × 2560 | 40 | 864 |
| 200 | 2560 × 640 | 26 | 416 |
| 3200 | 2560 × 10240 | 22 | 352 |
| 160 | 2560 × 512 | 21 | 336 |
| 3840 | 2560 × 12288 | 5 | 80 |

For this kernel, `gridX = rows * (cols / 32) / 256`; the table matches each
launch geometry exactly. Each request window has half of the listed calls.
CUDA kernel records do not carry source tensor addresses, so this establishes
the set of compatible source shapes and observed launch counts, not a per-layer
call assignment. `output.weight` is also Q6_K in this artifact but does not
match these grids; its active head path is separate.

On 2026-10-10, the current CUDA `dequant_bf16_test` binary was run against both
IQ1_M shards. It passed all six supported quantization types found, comparing
F32 and BF16 conversion against the independent CPU artifact decoder on the
first four rows of a real tensor of each type. Q6_K's selected tensor was
`output.weight` (4 × 2560 values in the tested row slice). This is real-payload
format evidence, but not a test of the five profiled Q6_K tensor shapes or of
the `H16` output path. The separate Q6_K codec report tests F16 conversion
against synthetic blocks; a real-payload, profiled-shape F16 oracle remains
open. The test binary SHA256 is
`f1dc3a5819ee68d809f50aa9b5cadff4f17d2e664adce8d7b07c1839f3d0b7bf`.
