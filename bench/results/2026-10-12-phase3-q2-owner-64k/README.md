# Q2_0 64K configured-context cache admission and owner screen — Orin — 2026-10-12

The current candidate passed a supervised 512-token prompt plus one greedy
output token at `--max-context 65536`, first with `--expert-cache 3000`, then
with `--expert-cache 5000`, retaining the explicit `--vram-reserve-mib 3072`
in both runs. The model is the local Qwen3.8 Flash-Next Q2_0
two-shard GGUF at `/home/calvin/models/strata-orin-validation/Q2_0/`, loaded
with the Q2_0 native pack, expert profile and the second GGUF shard as the PLE
table source. The executable SHA-256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`.

Both six-GiB supervisor runs passed. Minimum host `MemAvailable` was
18,184,941,568 bytes (16.94 GiB) at 3,000 slots and 15,417,085,952 bytes
(14.36 GiB) at 5,000 slots. Each owner parser found 278 allocations and 278
frees, with zero requested bytes live at process exit. Session backing stayed
at 1,856,067,072 requested bytes. The expert-cache owner grew from
4,147,200,000 to 6,912,000,000 bytes; device-0 peak grew by the same
2,764,800,000 bytes, from 7,534,843,648 to 10,299,643,648. Pageable expert
staging stayed at 353,894,400 requested host bytes, and the host-owner peak
stayed at 354,492,280 bytes. These remain requested-payload observations, not
complete physical-backing totals; device and host columns are kept separate,
and graph-pool/driver bytes are not inferred.

The runs were sequential in 3,000-then-5,000 order and measure admission and
requested allocation scaling only. They are not a randomized pair or timing
comparison.

The 5,000-slot/64K-configured cell was then repeated under transient cgroup
caps of 24 GiB and 18 GiB. Both passed the six-GiB guard. Minimum effective
availability was 13,930,741,760 bytes (12.98 GiB) at 24 GiB and
7,160,496,128 bytes (6.67 GiB) at 18 GiB; minimum physical availability was
14.41 and 14.51 GiB, respectively. Both owner ledgers again balanced 278/278
events with zero requested bytes live at exit; device-0 peak was
10,299,643,648 bytes and pageable host staging peaked at 354,492,280 bytes.
No OOM kills occurred. The 18-GiB result leaves about 0.67 GiB above the guard
and is retained as a single near-floor observation, not a capacity boundary.

The 3,072 MiB reserve was explicit, so these runs emitted no automatic cache
reservation events. Its context setting does not mean that 65,536 prompt
tokens were ingested. Dynamic CPU/GPU/EMC clocks were sampled; energy was not
measured. Raw supervisor logs, memory samples, both parsed owner summaries,
and command metadata are retained in this directory, including both cgroup
supervisors and their owner summaries.
