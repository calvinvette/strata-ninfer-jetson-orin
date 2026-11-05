# Mixed-codec one-token Strata/NInfer check

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. This is a small E5
functional check after all seven mixed IQ/Q2_0 tuples gained CUDA resident
routes. It is not an answer-quality suite or a performance experiment.

## Controlled arms

Both backends used the same model artifact, token-ID prompt `1,2,3`, matching
model pack and expert profile, the same respective `--expert-cache` setting,
`--prefill 64`,
512-token context, one generated token, greedy sampling and MTP-2. The only
backend difference was `--expert-backend strata` versus strict
`--expert-backend ninfer`. `STRATA_PREFILL_CPU_SHARE=0` was set in both arms to
keep prompt expert ownership fixed.

| Artifact | Strata outputs | Strict NInfer outputs | NInfer tuple dispatch | Minimum available RAM |
| --- | --- | --- | --- | ---: |
| Coder IQ1_M, 256 experts | `5`, `5` | `5`, `5` | All seven, layers 0, 1, 2, 12, 17, 21, 47 | 19.28–19.62 GiB |
| ISTA IQ3_S, 512 experts | `4` | `4` | All seven, layers 0, 1, 2, 12, 17, 21, 47 | 18.96–19.11 GiB |

All six supervised commands exited successfully. The pre-existing cgroup
OOM-kill count remained one in every run; none of these runs incremented it.
The raw commands, memory samples and logs are retained in the per-arm
subdirectories. No throughput, latency or energy effect is inferred from these
single-request checks; clocks were uncontrolled and CPU prefill sharing was
explicitly disabled.

## Limits and next gate

These runs compare one generated token for one manual token-ID prompt per
artifact, not natural prompts, held-out tasks or useful-answer quality. They
do not compare accepted-prefix state or final persistent-state fingerprints.
`STRATA_STATE_HASH=1` and `STRATA_PROMPT_BOUNDARY_STATE_HASH=1` were tried in
separate direct one-shot CLI invocations, but this path emitted no fingerprint;
use the service capture path or another validated state-dump path before
claiming state parity. Earlier exploratory invocations with CPU prefill sharing
left at its default and with diagnostic environment hooks produced varying
one-token outputs; they are not used as controlled evidence here. The fixed
CPU-share-off pairs were repeatable for Coder across two processes per arm.

The result supports a narrow claim about the direct one-shot CLI path only:
with fixed ownership, strict NInfer traversed the complete mixed-codec model
and matched Strata's one-token output for these exact prompts on both artifacts.
It does not establish service parity. A later service `GEN` path comparison on
the same Coder prompt IDs returned different first tokens and persistent state
for Strata and strict NInfer; see the [state diagnostic](state-parity-8token-recheck/README.md).
E5 remains open for localization and correction, held-out quality, longer
state parity, cancellation and recovery. E6/E7 performance and release gates
remain open.

### Exact layer-0 owners and PCIe-share follow-up

At layer 0, position 2 of the service request, the ten routed experts were
`143,175,252,25,54,240,35,204,19,246`. A fresh owner trace found four
primary-VRAM/foresight rows (25, 54, 35, 19) and six CPU rows (143, 175, 252,
240, 204, 246); it found no PCIe or peer rows. Thus the `queued NInfer ...
resident grouped dispatch at layer 0` log only describes the resident group,
not all ten routed experts. Forcing `--pcie-frac 1.0` left the same six misses
on CPU: this `--mmap-experts` configuration has no pinned device complement,
which the planner requires for PCIe ownership. The companion CPU-output
capture verifies execution ownership. This is a source/configuration coverage
limit, not an NInfer operator result. Minimum available RAM was 20.74 GiB and
the pre-existing cgroup OOM-kill count did not increase. Details and hashes are
in the [owner/PCIe diagnostic](layer0-ten-expert-oracle/pcie-frac-1/README.md)
and [ten-row oracle report](layer0-ten-expert-oracle/README.md).

### First-logit follow-up on the direct CLI path

A matched Coder IQ1_M direct-CLI pair repeated prompt IDs `1,2,3` with
`STRATA_PREFILL_CPU_SHARE=0` and the same 391-slot runtime cache. Both backends
selected token `5`, but all 248,320 captured logit values differed (relative
L2 `1.66e-2`, maximum absolute delta `0.2055`). Token `5` led token `4` by
`0.0759` for Strata and `0.0458` for NInfer. This result is limited to the
direct CLI invocation: it does not reproduce the service `GEN` result, where
the same token-ID prompt first differed (`4` versus `5`). It is not state or
quality parity. The top-ten summary and dump hashes are in
[`comparison.json`](../2026-11-05-e5-coder-natural-prompt/direct-cli-cpu-share-off/comparison.json);
the 993,280-byte float dumps remain in `/tmp/e5-coder-logits-cpu-share-off/`.
Both supervised commands passed; minimum available RAM was 20.86 GiB for
Strata and 21.23 GiB for NInfer, with no cgroup OOM-counter increment.
