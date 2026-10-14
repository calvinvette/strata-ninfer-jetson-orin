# Q2_0 accepted-prefix state after streamed decode cancellation — Orin — 2026-10-14

This test canceled a streamed Q2_0 MTP4 request after four nonempty text
deltas, then compared the canceled request's committed prefix with two fresh
requests limited to the exact same generated-token count. The existing
`mtp_cancel_state_parity.py` harness checked committed token IDs and all 11
persistent-state fields at every shared accepted-prefix boundary. Both fresh
references matched the canceled trace and each other. A follow-up short request
on the canceled service returned the exact `Hello Orin!` response.

The exact artifact is `Qwen3.8-Flash-Next-GSQ-RCO-Q2_0`, using its native
two-shard GGUF, `q2-ple-pack` and `/home/calvin/models/strata-orin-validation/mtp/rt`.
The GGUF shard sizes are 37,623,740,192 and 28,800,138,432 bytes; the files,
PLE tables and MTP weights were already local and remain outside Git.
The service used the current CUDA binary (SHA256
`abef7698554590b3e28036844da207c0c58c291167204bee9dff248d80304b32`), 8K
configured context, fixed 3,000-slot requested cache, MTP4 accepted-only
adaptation at cadence 4, and CPU prefill sharing disabled. The rendered prompt
was 48 tokens, despite the integer-list text. The canceled request committed
six tokens at accepted-prefix lengths 48, 50, 51 and 53; two drafts were
offered and accepted. The visible canceled text was a prefix of both exact-
length responses.

| Check | Result |
| --- | --- |
| Stream cancellation observed by engine | Pass after 4 nonempty deltas; 6 accepted tokens committed |
| Same-process recovery | Pass; exact `Hello Orin!` response |
| Fresh exact-length reference 0 | Pass; IDs and all persistent state matched at L=48, 50, 51, 53 |
| Fresh exact-length reference 1 | Pass; IDs and all persistent state matched at L=48, 50, 51, 53 |
| Reference repeatability | Pass; both references matched each other |

The full sequence ran sequentially in one `MemoryMax=28G` supervisor. Minimum
physical host availability was 16.731 GiB and minimum effective admission
availability was 15.910 GiB. The six-GiB floor passed; sampled cgroup pressure,
limit and OOM counters stayed zero. State tracing synchronizes execution, so
latency is not a performance result. The run used the current dynamic clock
profile; raw tegrastats is retained, while energy was not measured.

This adds one short-prompt Q2_0 MTP4 accepted-only decode-cancellation state
cell. It does not cover a long prompt, cancellation after a longer generated
prefix, other MTP windows or KV formats, or task quality. It does not explain
the separate state drift associated with adaptive residency changes. Phase 5
remains open.

Reproduce with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output supervisor --timeout 2400 --interval 1 -- \
    python3 tools/integration/mtp_cancel_state_parity.py \
      --config bench/results/2026-10-14-phase7-q2-recall/config-8192-mtp4.json \
      --output run --cancel-chunks 4 --reference-repeats 2 \
      --fixed-expert-cache 3000
```
