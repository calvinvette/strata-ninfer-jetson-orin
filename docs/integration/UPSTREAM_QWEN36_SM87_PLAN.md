# Upstream Strata + Orin SM87 + Qwen3.6 plan

Status: planning only. No upstream fetch, merge, code change, model conversion or
benchmark was performed for this plan.

## Goal

Bring the current upstream Strata source into a clean integration branch, carry
over the validated Jetson Orin/SM87 support, then build and qualify upstream's
Qwen3.6-35B-A3B engine path on Orin. Keep the existing Qwen3.8-Flash-Next
Q2_0 profile working. Treat Strata's GGUF model and NInfer's `.ninfer` artifact
as separate engines and artifact cohorts.

## Current facts and boundaries

- Upstream Strata now has a separate `qwen35` engine for Qwen3.6-35B-A3B. Its
  [Qwen3.6 guide](https://github.com/Niko1221/Strata/blob/main/docs/QWEN36.md)
  documents Unsloth UD-Q4_K_XL, UD-Q6_K_XL and Q8_0 GGUFs, NVIDIA/AMD builds,
  and measurements on an RTX 3060 and Radeon AI PRO R9700. It does not establish
  Orin/SM87 runtime support.
- The exact local IQ4_NL GGUF is identified by this fork's inspector as
  `qwen35moe`; the upstream model list does not document that quantization for
  Qwen3.6. The first model gate must establish whether upstream's import/setup
  path accepts this exact file. Do not infer support from the architecture
  family or silently substitute a different quant.
- The current integration candidate still requires `qwen4exp`, so it cannot
  load Qwen3.6. Its Q2_0 and Coder performance results remain separate evidence.
- NInfer has an Orin-tested Qwen3.6-35B-A3B v2 `groupwise-int` artifact at
  `~/models/qwen3_6_35b_a3b_v2/qwen3_6_35b_a3b.ninfer`. The user-named
  `~/models/qwen3_6_35b_a3b/qwen3_6_35b_a3b.ninfer` is the newer v3 artifact;
  the retained Orin port rejects v3 framing. The NInfer artifact is not a
  Strata input and is not the IQ4_NL model. See the
  [NInfer Orin experiment record](../../reference/ninfer/NINFER_JETSON_ORIN_PORT_EXPERIMENTS.md).
- The validated Strata Orin source branch is `feat/jetson-orin-arm64` at
  `0be090c8`. The current integration `main` is 831 first-parent commits beyond
  that point and contains substantial additional runtime experiments and
  diagnostics. Do not merge the full integration history into upstream.
- Keep the existing input checkouts and upstream PR #1621 separate. Preserve
  the current dirty benchmark evidence and model files.

## Work sequence and gates

| Stage | Work | Gate to proceed |
| --- | --- | --- |
| 0. Pin and isolate | Record upstream `main` commit, release/engine versions, local support commit and clean-tree identities. Create a separate worktree for the new integration; leave this checkout and the original PR worktree untouched. | Reproducible source identities; no dirty evidence is moved or staged. |
| 1. Compare source seams | Map upstream changes in CMake/platform detection, CUDA and ggml build options, shared-memory accounting, CPU/NEON kernels, serving/setup, tests, and `src/qwen35`. Classify each Orin change as reusable, already upstream, or needing adaptation. | A file-level port list with upstream owners and conflict notes. |
| 2. Build upstream baseline | On Orin, build unmodified upstream for ARM64/CUDA 12.6/SM87 with memory-bounded jobs. Confirm which targets include `qwen35`; record unsupported compiler flags or architecture assumptions. Run a minimal upstream Qwen3.8 control if the baseline can serve it. | Build and CLI evidence before any port patches; no clock/service changes. |
| 3. Port Orin/SM87 support | Apply the smallest coherent patches from the validated Orin branch: ARM64/CUDA build support, SM87 dispatch/build guards, shared physical-memory accounting and six-GiB admission floor, CPU/NEON paths, Jetson-specific runtime probes, and relevant tests. Reuse upstream implementations where they now supersede local code. Keep the 3-GiB workspace reserve distinct. | Every modified shared source file builds for CUDA; HIP/SYCL build checks run where the file is shared. No unrelated experimental diagnostics or reports are copied. |
| 4. Protect Qwen3.8 behavior | Rebuild and rerun the current bounded Q2_0 profile smoke and default regression checks on the merged candidate. Compare model/config identity and memory telemetry to the existing closeout. | Required functional checks pass; no loss of the existing Q2_0 profile or six-GiB headroom. |
| 5. Admit the exact Qwen3.6 GGUF | Run upstream's model import/plan and header checks on `Qwen3.6-35B-A3B-UD-IQ4_NL.gguf`. Confirm architecture, shard/PLE/MTP inventory, quant tensor coverage, pack recipe, tokenizer/template, memory estimate and any conversion requirements. | Exact IQ4_NL route loads without reinterpretation and fits the 6-GiB floor plus workspace reserve. If not, stop and report unsupported; ask before choosing another quant or downloading a replacement. |
| 6. Qualify Qwen3.6 runtime | On the merged Orin candidate, run a short supervised generation and the supported API/CLI checks. Verify exact token counts, fresh-prefill, MTP behavior if enabled, teardown/recovery and minimum physical/admission memory. Check one-live behavior first; concurrency stays opt-in. | No crash, malformed output, or memory-floor violation. Model quality remains a separate evaluation. |
| 7. Measure | Use the established `pp512+tg64` and `pp2048+tg128` workloads, seven independent process blocks, warmups, randomized order, medians and bootstrap uncertainty. Record model revision/checksums, realized cache, storage reads, actual clocks, temperature and energy scope. Run one model engine at a time. | Results are complete or explicitly marked failed/unsupported/pressure-aborted; no cross-quant speedup claim. |
| 8. NInfer reference (separate) | If desired, run the pinned v2 NInfer artifact as a separate Orin reference cohort using its supported local runtime and the same request shapes. Do not feed `.ninfer` to Strata or combine its results with IQ4_NL as if the weights matched. Keep the six-GiB floor; a pressure abort is not a capacity result. | Artifact version/checksum and engine identity verified; separate report and interpretation. |
| 9. Close and publish | Update the upstream-merge map, integration status, Qwen3.6 support notes, build/measurement reports and limitations. Review the focused diff, commit each completed stage, then push the integration branch. Decide separately whether to propose a narrowly scoped upstream PR. | No models, builds, credentials or local agent files in Git; only the planned source and evidence are included. |

## Implementation strategy

Use the clean validated Orin branch as a patch source, not the current
experiment-heavy integration `main`. Rebase or adapt focused changes on top of
upstream only after Stage 1 identifies the exact upstream implementation
points. Preserve upstream's Qwen3.6 model-specific engine and keep Jetson
resource policy at the platform boundary; do not force Qwen3.6 through the
Flash-Next loader or share incompatible pack formats.

All Orin work remains on the single 32-GiB LPDDR authority: never add CUDA
capacity to host RAM, preserve six GiB physical headroom and the separate
workspace reserve, use memory-capped builds, and do not alter clocks, JetPack
or running services for convenience. maestro1 may provide x86 HIP/SYCL build
evidence but no Orin performance evidence.

