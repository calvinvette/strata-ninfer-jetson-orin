# Graph experiments: phased build and study plan

Created: 2026-10-28. Status: planning only; no JP7 performance results.
Integration branch: `feat/graph-experiments`.
Starting source: `33b3eb7daa57c025e24d085e9d4a9ea23f7d388e` from `feat/ninfer-expert-e0`.
See [quick status](../integration/QUICK_STATUS.md), [detailed status](STATUS.md),
[study protocol](STUDY.md), [references](REFERENCES.md), and [workflow](WORKFLOW.md).

## Scope and assumptions

Target NVIDIA Jetson AGX Orin 32 GB, ARM64/SM87, CUDA on an actually verified JetPack 7.x installation.
Assume the ongoing NInfer work will yield a useful candidate, but measure it before accepting that premise.
The frozen starting commit is a planning ancestor, not the eventual baseline.
Import the final qualified NInfer commits before G0, record that merge and pin source/binary identities.
Do not infer JP7 installation, a particular minor version, codec support, or NInfer speedups from this plan.

Maestro HIP/SYCL builds are removed from this campaign's gates, including shared-file changes.
CUDA/Orin builds, CPU-side mathematical oracles, service regressions and disabled-feature controls remain.
Existing HIP/SYCL source and historical evidence remain available; upstream portability is deferred.
An architectural break is permitted behind explicit model/runtime format versions and opt-in paths.
Do not silently reinterpret existing packs, caches or server requests.

Single physical RAM authority: retain 6 GiB physical headroom plus the existing separate workspace reserve.
The graph, checkpoints, drafts, embeddings, experts and workspaces compete for the same RAM.
Do not assume CUDA free bytes are an additional pool.

## Branches and phase gates

Git cannot have both `feat/graph-experiments` and `feat/graph-experiments/foo`.
Use the sibling component refs below, each descending from the integration branch.
Created refs are scaffolds, not evidence of implementation. Merge required predecessors before starting work.

| Phase | Component branch | Depends on | Deliverable / completion gate |
| --- | --- | --- | --- |
| G0 | feat/graph-g0-baseline | Final NInfer candidate + verified JP7 | Frozen manifests, functional controls, same-day performance and quality baseline |
| G1 | feat/graph-g1-prefix-cache | G0 | Content-addressed fragments, canonical assembly, complete hybrid prefix checkpoints |
| G2 | feat/graph-g2-speculation | G0; G1 for repeated sessions | Repository/session suffix proposer, target verification, MTP fallback |
| G3 | feat/graph-g3-prefetch | G0; G2 traces | Versioned graph index, exact n-gram lookups and predictive expert prefetch |
| G4 | feat/graph-g4-state-compression | G0; G2 rollback contract | Checkpoint/replay and buffered mixed-precision GDN state |
| G5 | feat/graph-g5-expert-compression | G0; G3 cost traces | Shared numerical bases/deltas, direct versus materialized execution |
| G6 | feat/graph-g6-memory-encoder | G1–G4 evidence | Graph memory tokens plus literal retrieval, learned draft head |
| G7 | feat/graph-g7-architecture | G6 passes interventions | QSA memory bank, state generation and fragment-composition research |
| G8 | feat/graph-g8-combined-study | Qualified components | Held-out combined ablations, Pareto profiles and reproducibility package |

G1, G2, G3 are the first implementation priorities, in that order.
G4 can proceed independently after baseline/rollback contracts; G5 precedes the more speculative architecture work.
A failed phase is a useful result; do not force every component into G8.

## G0: new baseline before experiments

1. Inventory actual hardware, JetPack/CUDA/driver/compiler, power/observed clocks, storage and installed packs.
2. Merge the agreed final NInfer source; pin hashes. Compile CUDA SM87 with bounded jobs; run existing functional tests.
3. Audit the current long-context state variation with same-backend repetitions and randomized backend order.
   Match logical accepted positions, capture settings and allocation policy. Unresolved state noise must not be
   attributed to a new feature. Block exact-state claims for affected cells; a quality-bounded profile requires
   a separately preregistered numerical/behavioral contract.
4. Establish the new default control and each supported backend/quant pair. Log actual backend execution and
   fallback counts; a fallback is not a NInfer measurement. Strict unsupported cells remain unsupported.
5. Run historical-shape bridge cells, realistic long agent sessions, capacity screening and confirmation.
6. Freeze a baseline manifest and result IDs. No graph optimization is enabled in the baseline.
   JP6 results remain historical; optional matched-toolchain comparisons are separate campaigns.

## G1: prompt fragments and full hybrid checkpoints

Build stable fragment IDs from exact bytes/tokenization context with collision verification.
Separate content identity from state identity: model/pack/adapter revisions, complete preceding token prefix,
positions, template, numerical settings and cache format belong in state keys.
Canonicalize only semantically reorderable sections. Never reorder instruction precedence or silently discard
model-visible session IDs. Test IDs at beginning/end, fragment permutations, boundary tokenization,
cross-fragment n-grams, truncation, edits, model changes and explicit invalidation.

Checkpoint all required GDN, convolution, QSA KV/indexer, position, n-gram and speculative state.
Start with exact complete-prefix reuse and a bounded cache; standalone fragment KV is not interchangeable.
Compare no cache, tokenization/lookup-only caching, and full-state restore. Include serialization,
restore, eviction and expert displacement in latency and RAM. Gate on continued-generation and
accepted-prefix state checks, cancellation/recovery, and stale-cache rejection.

## G2: graph/suffix proposals, then state-conditioned ranking

Start with a single proposed continuation from repository text and prior session outputs.
Compare no speculation, current MTP, lexical suffix, and suffix-to-MTP fallback.
Record candidate source, acceptance by position, committed tokens/round, proposal/verification/replay costs.
Use target verification with correct rejection/resampling for stochastic sampling; greedy parity alone
does not establish distribution preservation. Explicitly restore/commit all hybrid state.

Only after a cheap proposer pays off, train a small ranker using existing hidden outputs, recent exact
tokens, n-gram features and optional GPU-resident recurrent sketches. Maintain sketches using the actual
GDN delta-rule update; the simplified scalar-decay-plus-outer-product equation is not the full recurrence.
Measure sketch maintenance, avoid copying full state to CPU every token.
Separate train/dev/test repositories and sessions. No held-out patch or future tool output in the graph.

## G3: graph-guided residency and prefetch

Keep compact graph indices separate from contiguous numerical payloads.
Track repository/versioned symbol relationships, fragment IDs, exact n-gram row addresses,
expert co-selection/transitions and cost statistics. Known prompt lookups are calculated exactly;
future generated-token and expert accesses are predictions.
Original router remains authoritative; every miss has a correct fallback.
Collect routing frequency/weight, reuse distance, co-activation, bytes read, exposed stall,
wasted prefetch, reconstruction time and eviction cost by task phase.
Compare byte-budgeted LRU/frequency policies with cost-aware graph prediction.
Hold total memory fixed, then separately allow freed memory to become expert residency.
Do not credit a graph algorithm for simply allocating more RAM.

## G4: recurrent-state storage and rollback

First compare full snapshots with checkpoint plus bounded replay/update logs.
Separate active-state, speculative rollback, and parked-prefix compression.
Start FP32 control, FP16 sensitivity, INT8 plus protected channels, and INT8 checkpoint with
higher-precision buffered updates. INT4 is a later aggressive screen, never assumed safe.
Implement the exact GDN recurrence and convolution history in independent oracles.
Audit long-horizon error accumulation, saturation/outliers and rollback after partial acceptance.

DCT/Fourier/FFT is exploratory: measure spectral energy and reconstruction error before a kernel.
Feature ordering has no guaranteed spatial smoothness. Include transform/decode/update cost and metadata.
Entropy coding is initially restricted to parked snapshots; no per-token Huffman decoding assumption.
Do not store per-token-per-layer full histories by default.

## G5: numerical expert templates

Estimate redundancy in the actual pruned/quantized artifacts using activation-weighted calibration.
Compare original expert, shared base plus low-rank delta, direct factor execution and cached reconstruction.
Sweep rank/grouping/precision and materialization capacity in bytes, with oracle output and task tests.
Keep routing/top-k fixed. A cap controls materialized residency, not selectable experts.
Record reconstruction amortization and avoid counting encoded and reconstructed copies as free.
Extracted symbolic triples are not a lossless expert representation.

## G6: graph-to-memory encoder and draft head

Version nodes/edges with source provenance and invalidate affected neighborhoods after edits.
Cache query-independent encodings; perform bounded query-dependent selection.
First interface: learned memory tokens with explicitly trained positions and n-gram masking/handling,
plus exact source retrieval for identifiers, literals, tool arguments and critical instructions.
Teacher sees full relevant text; student sees memory plus literal excerpts.
Initially freeze target weights and train encoder/projector; adapters are a separately labeled arm.
Specify training hardware/cost before execution; no assumption that Orin can train the full target.

Distill continuations and tool calls; score exact identifiers, source locations, held-out tests and multi-step
task completion. Compare text RAG, exact-prefix restore, graph memory, and equal-budget constant/shuffled
memory. Change one required graph fact and check that behavior changes; perturb irrelevant edges and check
stability. A better score without graph sensitivity does not qualify the graph encoder.
A separate draft head shares the encoder only after independent memory/draft ablations.

## G7: architecture research, gated on G6

Explore a bounded explicitly gated QSA memory bank, then low-rank generated GDN initialization.
Use G6's processed memory as a teacher for coherent state targets; include convolution and QSA consistency.
Measure recurring per-token memory-read overhead against prefill savings.
Study reordered fragment composition with both recurrent and attention repair; CacheBlend/EPIC are
precedents, not proof for this hybrid. Sweep repair fraction and fragment order.
Graph-conditioned expert deltas/hypernetworks are last: train against expert outputs and coding tasks.
Record new model/checkpoint/cache schemas and retain a clean rollback to the baseline.

## G8: interactions and release/research record

Confirm components independently, then test prefix × speculation, speculation × state compression,
prefetch × expert compression, and memory tokens × drafting under one physical memory budget.
Use matched total bytes and an allocation-reoptimized arm as distinct comparisons.
Publish unsuccessful cells and quality failures, not only winners.
Report TTFT, raw processed-token prefill rate, committed TG, time/energy per successful coding task,
memory, storage and confidence intervals. Separate first token from first visible answer.
Prepare a reproducible paper package only after measured claims and attribution review.
