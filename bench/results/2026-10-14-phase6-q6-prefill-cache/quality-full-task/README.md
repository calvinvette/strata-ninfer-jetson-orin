# Full-task quality screen for Q6 prefill/cache settings

This quality-only follow-up used the exact 512-token prompt from the
three-block prefill/cache performance screen, with a 512-token output allowance
instead of its 64-token cap. It crossed `--expert-cache` budget arguments
3,000/5,000 with prefill chunks 32/128, using one fresh service per condition.
The model, IQ1_M artifacts, accepted-only MTP4, Q6 warp dequant, FP16 KV, 8K
context, eight workers, and zero prompt-cache setting matched the performance
screen. Temperature was zero. Each answer ended naturally; the checks required
the exact `Processor:` prefix, at least 200 words, fetch/decode/execute, RAM,
binary data, input/output, and the exact arithmetic `17 x 19 = 323`.

| Cache budget | Prefill chunk | Resident slots | Output tokens | Words | Rubric |
| ---: | ---: | ---: | ---: | ---: | --- |
| 3,000 | 32 | 3,903 | 315 | 267 | pass |
| 3,000 | 128 | 3,903 | 340 | 287 | pass |
| 5,000 | 32 | 6,519 | 334 | 282 | pass |
| 5,000 | 128 | 6,519 | 329 | 278 | pass |

All four requests used exactly 512 prompt tokens and reported zero cached
tokens. Minimum host availability and effective admission headroom were both
8.16 GiB under the existing 28-GiB cgroup scope and six-GiB floor. The sampled
cgroup `oom`, `oom_kill`, `max`, and `high` event counters remained zero.
Dynamic CPU/GPU clocks were observed; EMC frequency readback was denied. Power
rails were retained in `supervisor/tegrastats.txt`, but energy was not
calculated or attributed to these requests.

This establishes that each of the four configurations completed this one
task-quality rubric. It does not compare language quality statistically,
qualify other prompts or model cohorts, or validate residency-driven response
variation. The one-request-per-cell output rates are descriptive only; the
performance conclusions remain those of the separate three-block screen.
Nothing is promoted and no default changes.

Raw configs, responses, API metrics, engine logs, host telemetry, clock
observations, and tegrastats are retained here. Model files remain in
`~/models/`.
