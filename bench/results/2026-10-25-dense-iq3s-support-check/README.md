# Dense Qwen3.8-27B IQ3_S support check

**Status: unsupported by the current Strata candidate; no performance requests
were run.** The requested file is
`~/models/qwen3.8-27b-iq3s/Qwen3.8-27B-UD-IQ3_S.gguf`, 12,040,883,104 bytes
(12.04 GB on disk), SHA256
`d847e2c1e4aa276e4b7b8e9ad7628050e61e165d49ab995407bc36677a6f3864`.

The project’s header-only `tools/strata_inspect.py` identified architecture
`qwen35` and reported: “Strata: not Qwen3.8-Flash-Next (architecture 'qwen35'):
Strata runs only that model.” The inspected file contains a dense 27B model and
is not compatible with the current Flash-Next runtime. The current candidate
binary is SHA256
`ad4b2354fe98f0e4128cf9a9ed70488fef362207dd1f7e94555a8ba35d8985df`.

NInfer's local Qwen3.8-27B artifacts use its separate `.ninfer` format. They
are not this IQ3_S GGUF, so their results would be a different model/artifact
cohort. No engine, model, quantization or workload substitution was made. A
valid performance campaign requires either Strata support for `qwen35` GGUF
or an explicit request to benchmark a compatible engine/artifact instead.
