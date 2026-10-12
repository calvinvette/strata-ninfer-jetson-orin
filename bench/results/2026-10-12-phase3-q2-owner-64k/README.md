# Q2_0 64K configured-context owner refresh — Orin — 2026-10-12

The current candidate passed a supervised 512-token prompt plus one greedy
output token with `--max-context 65536`, `--expert-cache 3000`, and the explicit
`--vram-reserve-mib 3072`. The model is the local Qwen3.8 Flash-Next Q2_0
two-shard GGUF at `/home/calvin/models/strata-orin-validation/Q2_0/`, loaded
with the Q2_0 native pack, expert profile and the second GGUF shard as the PLE
table source. The executable SHA-256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

The six-GiB supervisor passed and observed minimum host `MemAvailable` of
18,184,941,568 bytes (16.94 GiB). The owner parser found 278 allocation and
278 free events, with zero requested bytes live at process exit. Peak observed
requested bytes by device were 7,534,843,648 on CUDA device 0 and 354,492,280
on host device `-1`. The device peak included a 4,147,200,000-byte expert
cache and a 1,856,067,072-byte session allocation. Pageable expert staging
peaked at 353,894,400 requested host bytes. These remain requested-payload
observations, not complete physical-backing totals; device and host columns are
kept separate, and graph-pool/driver bytes are not inferred.

The 3,072 MiB reserve was explicit, so this run emitted no automatic cache
reservation events. Its context setting does not mean that 65,536 prompt
tokens were ingested. Dynamic CPU/GPU/EMC clocks were sampled; energy was not
measured. Raw supervisor logs, memory samples, the full parsed owner summary,
and command metadata are retained in this directory.
