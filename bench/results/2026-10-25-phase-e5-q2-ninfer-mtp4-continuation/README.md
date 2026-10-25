# E5 Q2_0 strict NInfer repeated continuation and recovery

Date: 2026-10-25. Host: Jetson AGX Orin, CUDA 12.6, SM87. This compares
MTP disabled with MTP-4 under the same strict NInfer expert backend, static
expert ownership and Q2_0 model.

## Setup and result

Both arms used the same 512-token prompt (SHA256
`ca13a79c83650d0bda01e8db5cc641308e496ff8342cb17471916c8d0a502729`),
8K context, FP16 KV, 3,000 profile-ranked expert slots, prefill 128, eight
workers, strict `--expert-backend ninfer`, and `--adapt-swaps 0`. Each engine
served three requests in sequence: 8 generated tokens, continuation for 8 more,
then a recovery request for 8. The MTP-4 arm used the converted Q2_0 runtime
with batch 1. The MTP-off arm retained all other settings.

Both arms produced identical token IDs for all three requests. At the end of
each request, all nine captured state fields matched: logical position, GDN,
PLE, tail, dead slots, pooled and full pooled state, KV, and previous PLE
tokens. The MTP-4 arm offered 6, 9 and 9 drafts; it accepted 5, 5 and 5,
respectively. Rejected suffix drafts were observed before the later requests,
so continuation and recovery exercised the post-rejection path. The probe passed
with no reported failures.

The detailed result, including per-prefix traces, request metrics and exact
arguments, is in [`evidence/results.json`](evidence/results.json). Supervision
summary is in [`evidence/supervisor-result.json`](evidence/supervisor-result.json).

## Resources and limits

The supervised run lasted 103.8 seconds. Minimum physical/admission availability
was 18,302,013,440 bytes (17.04 GiB), above the preserved 6 GiB floor. Sampled
cgroup memory events remained zero. CPU observations ranged from 729.6 MHz to
2.2016 GHz; GPU observations ranged from 306 MHz to 1.3005 GHz. EMC readback was
denied; clocks were observed, not controlled. Energy was not attributed.

Single-run request durations in this functional probe are diagnostic only. This
does not qualify long-context retrieval/scoring, adaptive residency, performance,
or general replay. The three-request sequence expands same-engine state coverage
beyond the earlier cancellation and accepted-prefix tests; E5 remains open for
held-out task/quality coverage and the remaining support matrix.
