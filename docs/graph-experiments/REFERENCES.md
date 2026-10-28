# Research references and attribution ledger

Checked: 2026-10-28. This is a reading queue and related-work map, not a claim that every
paper has been reproduced or fully reviewed. Titles/landing-page abstracts were checked for
the method papers below. Read full methods, versions, code and licenses before implementation.
Published speedups are not Orin predictions; this plan intentionally does not reuse them as targets.

Calvin Vette proposed the motivating graph, fragment-cache and expert-template questions in project
discussion. Subsequent literature discovery revealed overlapping prior work. Preserve that chronology
as project provenance, not evidence of priority or novelty. Cite relevant prior work regardless of
independent conception. Do not call established methods new or claim a lossless fact-to-expert mapping.

| ID | Reference | Relationship / phase |
| --- | --- | --- |
| R01 | [SuffixDecoding: Extreme Speculative Decoding for Emerging AI Applications](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b7aea253ab34a773967f1e4cdea9e4fb-Abstract-Conference.html), NeurIPS 2025; [arXiv 2411.04975](https://arxiv.org/abs/2411.04975); [authors' site](https://suffix-decoding.github.io/) | G2: suffix-based proposals; adapt carefully to hybrid recurrent rollback |
| R02 | [CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion](https://arxiv.org/abs/2405.16444); [publisher/author page](https://www.microsoft.com/en-us/research/publication/you-only-prefill-once-combining-cached-knowledge-for-large-language-model-serving-with-cacheblend/) | G1/G7: selectively repaired cached fragments; not exact hybrid-state composition |
| R03 | Hu et al., [EPIC: Efficient Position-Independent Caching for Serving Large Language Models](https://proceedings.mlr.press/v267/hu25j.html), ICML 2025 | G7: position-independent attention cache research |
| R04 | [G-Retriever: Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering](https://arxiv.org/abs/2402.07630) | G6: graph retrieval/soft prompting |
| R05 | Ge et al., [In-context Autoencoder for Context Compression in a Large Language Model](https://arxiv.org/abs/2307.06945v4), ICLR 2024 | G6: compact learned memory slots |
| R06 | Di Francesco et al., [On the Token Collapse Phenomenon in Textual Graph Soft Prompting](https://arxiv.org/abs/2610.31572), 2026 preprint | G6: constant/shuffled-token and graph intervention controls |
| R07 | Pan et al., [LeapQuant: Efficient Linear Attention with Accurate Recurrent State Quantization](https://arxiv.org/abs/2609.38166v1), 2026 preprint | G4: windowed low-bit state and high-precision updates |
| R08 | Zhang et al., [DAMP: Decay-Aware Mixed-Precision Recurrent-State Quantization](https://arxiv.org/abs/2608.27513v2), 2026 preprint | G4: protect channels using error and decay |
| R09 | Li et al., [Preserving Updates in Low-Bit Recurrent State Quantization](https://arxiv.org/abs/2610.15709), 2026 preprint | G4: low-rank update preservation and rounding |
| R10 | Gu et al., [Delta Decompression for MoE-based LLMs Compression](https://proceedings.mlr.press/v267/gu25c.html), ICML 2025 (D²-MoE) | G5: shared bases and expert deltas |
| R11 | Chen et al., [MoBE: Mixture-of-Basis-Experts for Compressing MoE-based LLMs](https://proceedings.iclr.cc/paper_files/paper/2026/hash/431d53d513461ff155d5bc8faa9a440c-Abstract-Conference.html), ICLR 2026 | G5: shared numerical basis factors |
| R12 | Geva et al., [Transformer Feed-Forward Layers Are Key-Value Memories](https://aclanthology.org/2021.emnlp-main.446/), EMNLP 2021 | G5/G7 conceptual background; not a symbolic reconstruction procedure |

## Architecture and implementation inputs

Retain the [Qwen technical report](https://github.com/QwenLM/Qwen3.8-Flash-Next/blob/main/tech_report.pdf),
[model repository](https://huggingface.co/Qwen/Qwen3.8-Flash-Next),
[Coder artifacts](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF),
[original artifacts](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF),
[Strata](https://github.com/Niko1221/Strata), and
[NInfer port](https://github.com/calvinvette/ninfer-jetson-orin).
G0 must pin/download metadata and verify actual dimensions and tensor layouts from the selected artifact;
earlier conversation dimensions are hypotheses until checked against that artifact.
The [Reddit discussion](https://www.reddit.com/r/LocalLLaMA/comments/1xebdzl/8_gb_gpu_262k_context_35_bpw_qwenflashnext_coder/)
and [gpu-unlock](https://github.com/Zagitta/gpu-unlock) are contextual inputs, not verified Orin results.
An Orin unlock remains a separate conditional experiment.

## Evidence and publication practice

For each implemented method, add a ledger entry with reference IDs, exact paper version,
code URL/commit, license, copied/adapted files, project-specific differences, author/contributor credits,
and the experiment IDs that test it. Preserve THIRD_PARTY_NOTICES and source headers.
Citation does not replace code-license compliance.
Before publication, import publisher BibTeX and verify author lists; do not synthesize missing metadata.
Keep a claim-to-result table, baseline definitions, training/data splits, negative results and limitations.
Proposed contribution is initially the measured adaptation/integration on this hybrid/Orin workload;
novelty must be assessed against related work after the experiments, not asserted in advance.
