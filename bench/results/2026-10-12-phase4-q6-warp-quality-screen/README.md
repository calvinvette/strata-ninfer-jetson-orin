# Q6_K warp dequantization semantic output screen — Orin — 2026-10-12

This screen compares the default Q6_K-to-FP16 dense materialization path with
opt-in `STRATA_Q6K_WARP_DEQUANT=1` on the same Coder IQ1_M model and candidate
binary. The formatted prompt was exactly 512 tokens and requested a 200-word
explanation of computer processing, the exact `Processor:` prefix, fetch/decode/
execute, RAM, binary data, input/output, and `17 x 19 = 323`. Temperature was
zero and each fresh service received one request with a 512-token limit. The
baseline and candidate ran sequentially under separate 28-GiB scopes and the
standard six-GiB host floor. Configurations differ only in the candidate
setting and loopback port.

Both responses finished naturally and passed the entire checklist. The
baseline produced 284 completion tokens and 235 words (SHA256
`12d09b5878f365a8d91d07539a523d6119ab984629722073bd67eca7364e7185`); the
candidate produced 304 tokens and 252 words (SHA256
`72f12493dc4b31f2fd6c8f51eef81a1a76d8243b1d023357e9c8b7845ecf6dc8`). Both
outputs explain the requested stages and concepts in a coherent, factually
consistent way. Their wording diverges in the closing explanation of binary
data and instruction-set interaction. This is a rubric screen, not a general
language evaluation; no default quality budget is established by one prompt.

Minimum available host memory was 13.26 GiB for baseline and 13.22 GiB for the
candidate. Both supervisor records passed above the six-GiB floor with no OOM
kills. CPU/GPU clocks were observed under dynamic policy, EMC readback was
denied, and energy was not measured. Timings are deliberately excluded: this
was one sequential pair, not a randomized performance design.

The prompt bytes SHA256 is
`00e231d1441879f312c9d4d6fb87ee68edc1c2bcc1b99721bf18b2d61dafd454`; the
workload definition SHA256 is
`86ba9e9d7f25316a7dca47042f290c18c1c4dc4b45a50a0e12d7453396bfb578`. The
candidate executable SHA256 is
`1135dd9093a7bbf15c874516bc75886a029d4d149196898b15023ad95907d047`. Raw API
responses, service logs, configs and supervisor telemetry are retained in
`baseline/`, `candidate/`, `supervisor-baseline/` and
`supervisor-candidate/`. Models remain in `~/models/`.

This adds one semantic output check for the Phase 4 candidate, complementing
its exact operator oracle and output-parity timing screens. It does not qualify
other prompts, model formats or long-context task quality, and does not change
dispatch or defaults.
