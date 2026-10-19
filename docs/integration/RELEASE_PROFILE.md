# Bounded Orin integration profile

This record describes one reproducible, opt-in integration profile for the
Jetson Orin AGX. It is an experimental qualification target for this repository,
not a general Strata support statement or a default configuration. Phases 5 and
6 remain open, so speculation/state migration and broader parametric and energy
qualification are excluded.

## Qualified cell

| Item | Value |
| --- | --- |
| Board | Orin AGX, ARM64, L4T R36.4.4, CUDA 12.6 |
| Source | `0b28cd634fa3a7ba9da514df0200d96baea330e4` |
| Candidate binary SHA256 | `320963c6572a13065e7704b3f98d477c8e29119ea45a96114f532008134e9932` |
| Model | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, revision `5348543e0147355ac9cbcb031184a3546350988e` |
| Quantization | Q2_0, two GGUF shards plus the matching local PLE pack |
| Profile | 8K context, FP16 KV, MTP off, 3,000 exact expert slots, prefill chunk 128, eight workers, 3,072 MiB workspace reserve, prompt cache and adaptive swaps off |
| Memory guard | `MemoryMax=28G`; preserve at least six GiB host availability |

The model and pack stay under `~/models/strata-orin-validation/`. The two Q2_0
GGUF shard SHA256 values are `69820c02ec7d0b45ef2ebb19d6620299db749fe2aded7f39f93c6b88b199b720`
and `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
The matching PLE pack dense SHA256 is
`a43d7d0b69525335f4b000d5197a1d3aefcd3c0014fc3e12b3455e0a5d827ba2`; the
expert profile SHA256 is
`b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`.
The full artifact and tokenizer identity is in the [Phase 7 artifact
manifest](../../bench/results/2026-10-17-phase7-q2-prefill128/sustained-512/artifacts.json).
Do not substitute the IQ1_M quantization: the Phase 7 IQ1_M measurements are a
separate cohort.

## Evidence and reproduction

The [current-source profile smoke](../../bench/results/2026-10-18-phase8-current-source-q2-profile-smoke/README.md)
processed an uncached 7,498-token retrieval prompt, returned three planted
markers exactly once and in order, then returned `RECOVERED` on the same
service. The independent reviewer passed. The run retained 324 one-second
supervisor samples, with 17.69 GiB minimum host availability, 8.69 GiB minimum
admission availability, and zero cgroup pressure or OOM events. It is one
functional cell; its timings are not a performance comparison.

Reproduce from the repository root with:

```sh
bash bench/results/2026-10-18-phase8-current-source-q2-profile-smoke/run.sh
```

The selected profile is also qualified by the bounded Phase 7 evidence linked
from [STATUS.md](STATUS.md) and enumerated in the [Phase 7 closeout](PHASE7_CLOSEOUT.md).
Those results cover specific prompts, contexts and service checks; they do not
establish general quality, concurrent serving performance, or 256K sustained
service.

## Default regression and rollback

The unchanged default path has a current-source CUDA regression record at
[`phase8-current-source-regression`](../../bench/results/2026-10-18-phase8-current-source-regression/README.md).
The prior pinned control was restored and smoke-tested on Orin; see the
[rollback record](../../bench/results/2026-10-18-phase8-rollback-smoke/README.md).
Rollback requires restoring the pinned binary together with its compatible
invocation and configuration. The pinned executable does not accept every
candidate-profile option. The maestro1 HIP and SYCL results are x86 build and
CLI checks only, not Orin accelerator-runtime or model-execution evidence.

## Exclusions

- Adaptive CPU/GPU migration remains unqualified because tested swaps changed
  persistent state and later continuation output.
- MTP is off in this profile. Accepted-prefix checks cover bounded prompts and
  settings; they do not close the broader Phase 5 state, graph-lifecycle,
  cancellation and quality gates.
- The Phase 6 interaction, Pareto and process-attributed energy work is
  incomplete. Rail measurements include board idle/background activity and
  must not be described as process energy.
- IQ1_M, other quantizations, other boards, larger model families, and changed
  defaults are outside this profile.

No defaults are changed by this record. Requalify after changing the source,
binary, model snapshot, quantization, memory settings, or any profile option.
