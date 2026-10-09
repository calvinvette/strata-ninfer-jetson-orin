# Phase 1 control harness

This checkpoint implements the control harness outside the runtime. It does not
complete Phase 1 or qualify an optimization. See [status](STATUS.md) for measured
checks and [porting notes](PORTING_NOTES.md) for transferable integration lessons.

## Build and identity

Archive Strata `0be090c8997b24cf5d21557ced40a1b7e93e87d3` into an ignored,
isolated source directory. Configure that source and this branch independently:

```sh
cmake -S SOURCE -B BUILD -DCMAKE_BUILD_TYPE=Release \
  -DSTRATA_ENABLE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DSTRATA_BUILD_TESTS=OFF -DSTRATA_BUILD_CONVERSATION_TESTS=ON \
  -DSTRATA_GGML_DIR=PINNED_LLAMA_CHECKOUT
python3 tools/integration/run_control.py --output NEW_RUN_DIRECTORY -- \
  cmake --build BUILD --target strata shared_memory_budget_test --parallel 2
python3 tools/integration/control_manifest.py --source SOURCE --revision REVISION \
  --build BUILD --binary BUILD/strata --artifact EXPLICIT_ARTIFACT \
  --output NEW_MANIFEST.json
```

Use ggml's pinned revision `3cf03257f219afbe7334045ff7c6a06ac68c627d`.
`STRATA_BUILD_TESTS=OFF` avoids the omitted upstream `tests/` sources. Standalone
conversation tests remain available. Build selected targets before invoking
CTest; a configured-but-unbuilt test is not a pass. Preserve configure/build logs
and the embedded SM87 image list. Binary digests identify the actual builds;
different source directories can produce different hashes even with equal source.

The supervisor writes `result.json`, `memory.jsonl`, `stdout.txt`, `stderr.txt`
and `tegrastats.txt`. A `pass` means successful command exit within the sampled
memory floor, not numerical or performance qualification. Linux cgroup-v2
ceilings are sampled where exposed; absent controllers remain an explicit gap.
Do not run two model processes or unrelated model services during controls.

## Prepare and run API controls

Use an existing Python environment with Strata's tokenizer/server dependencies:

```sh
python tools/integration/prepare_controls.py \
  --tokenizer "$HOME/models/strata-orin-validation/pack/tokenizer" \
  --output build/integration/NEW_WORKLOADS
python tools/integration/benchmark_control.py --variant baseline \
  --base-url http://127.0.0.1:18081 \
  --workloads build/integration/NEW_WORKLOADS/workloads.json \
  --output build/integration/NEW_BASELINE.json --rounds 3
```

Prepare separate local server configs naming the two freshly built executables
and source working directories, with identical explicit model/MTP/profile paths,
prefill64, context4096, native spec4, expert-cache5000, prompt-cache0,
reserve3072 MiB and pcie-frac0.55. Keep model files under `~/models/`. These are
control settings, not new product defaults. Confirm actual READY resources,
including cache slots/bytes, KV and MTP geometry; requested expert-cache5000 is
not an actual slot count.

```sh
python tools/integration/sample_clocks.py --help
python tools/integration/run_paired_controls.py --help
/path/to/existing/strata/venv/bin/python tools/integration/run_paired_controls.py \
  --baseline-config build/integration/baseline-paired-config.json \
  --candidate-config build/integration/candidate-paired-config.json \
  --workloads build/integration/NEW_WORKLOADS/workloads.json \
  --output build/integration/NEW_PAIRED_CONTROLS --blocks 3
python tools/integration/summarize_controls.py \
  --campaign build/integration/NEW_PAIRED_CONTROLS \
  --clock-samples build/integration/NEW_CLOCKS.jsonl \
  --output build/integration/NEW_SUMMARY
python tools/integration/plot_controls.py --help
```

Consult each tool's help for exact options. The paired runner owns each loopback
server under the memory supervisor, randomizes process/workload order and writes
partial results durably. Start the read-only clock sampler before the campaign
and terminate its owned PID afterward; do not change clock profiles to fill a
missing observation. `--prior-campaign` permits compatible independent extensions
without overwriting completed evidence. One warmup and one measured request per
cell per process avoid treating requests in the same process as independent
process replicates. Three pairs are screening; seven are required for confirmation.

Streaming preserves raw SSE events and client first-visible-delta TTFT. Metrics
snapshots retain engine stage times at their published precision, cache/draft
counts and logical reads. Whole-pair bootstrap intervals preserve paired units.
Named rail integration is request-window estimation, not whole-board energy.
Missing telemetry remains explicit. The successful October 9 campaign contains
four pairs, including one extension to obtain three frequency-observed pairs.

The prepared cells are pp512+tg64, pp2048+tg128 and historical prompt lengths
172/557/1069 with tg64. Cache reuse, early EOS, missing timings or count mismatch
fail the control cell. CLI smoke tests are separate: CLI prefill counts exclude
the final prompt token and cannot be labeled API workload results.

## Gates still required

Owner-specific allocations, reservations and graph/workspace peak counters remain
required. Same-day paired controls, streaming TTFT and the first independent
operator tolerance/diagnostic are now recorded in the
[paired report](../../bench/results/2026-10-09-paired-api-controls/README.md).
The known raw-token logit discrepancy was freshly reproduced, not adopted as a
pass. NInfer model cohorts have not been rebuilt or measured here.

The private diagnostic builds separately from production dispatch:

```sh
cmake -S tests/integration -B build/integration/operator-tests \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build build/integration/operator-tests --parallel 2
python tools/integration/run_control.py --output build/integration/NEW_RMS_ORACLE \
  -- build/integration/operator-tests/weighted_rms_contract
python -m unittest discover -s tools/integration -p 'test_*.py'
```

`api_control_block.py --validate-api-only` runs owned-server protocol scenarios.
`inventory_tensors.py` reads explicit GGUF headers without copying model payloads.
`compare_logits.py` compares explicit reference/native dumps diagnostically;
argmax equality is not numerical parity. See each tool's help for inputs.


Owner diagnostics are opt-in; see [coverage and limitations](INSTRUMENTATION.md).
The owned server now saves initial `/metrics` to `capabilities.json`, including
actual KV residency. `--require-kv-streaming` rejects an unexecuted streaming
cell rather than trusting the requested flag. A larger configured reservation
with short requests does not qualify a near-limit context workload.
`compare_logits.py` requires NumPy; use the existing Strata virtual environment.


For the independent IQ4_NL codec diagnostic, configure the private test root
with `-DSTRATA_GGML_DIR=PINNED_LLAMA_CHECKOUT`, build target
`iq4_nl_codec_contract`, and run it under the supervisor. No dependency fetching
is performed. [Evidence](../../bench/results/2026-10-09-iq4-nl-codec-contract/README.md)
records exact-bit qualification boundaries.
