# Current-candidate Q2_0 release-profile smoke — Orin — 2026-10-22

This reran the bounded Q2_0 profile smoke against the current integration
candidate, then repeated the entire CUDA CTest and Python integration suites.
The model, tokenizer, Q2_0 shards and matching packs stayed under
`~/models/strata-orin-validation/`.

The 8K-context profile used FP16 KV, MTP off, 3,000 exact expert slots,
prefill chunk 128, eight workers, prompt cache and adaptive swaps off, a
3,072-MiB workspace reserve, and a 28-GiB process cgroup. After one 512-token
warmup, the service read the exact 7,498-token uncached retrieval prompt and
returned all three planted markers once and in order at positions 6, 30, and
54. It then returned `RECOVERED` on the same service. The independent reviewer
passed. The measured recall request emitted 41 tokens in 284 seconds; this is
one functional profile cell, not a speed comparison.

The supervised request completed in 334.27 seconds across 317 one-second
samples. Minimum host availability was 17.84 GiB and admission availability
was 8.71 GiB. Cgroup low/high/max/OOM/kill counters were zero. CPU and GPU
clocks were observed dynamically; EMC readback was denied, and energy was not
attributed.

On the same candidate binary, the complete CUDA CTest suite passed 130/132
tests with no failures; two optional IQ-fixture tests skipped because their
external fixtures are not present. The external one-layer Q2_0 S2 fixture was
supplied for `pool_test`. The integration Python suite passed 163/163. CTest
retained 21.4 GiB minimum host/admission availability across 163 memory samples
and recorded zero cgroup memory events.

The executable SHA256 was
`c3b356593d55ccc76ccdf19d13edfbf290835313ab513067992ad4a256b63101`; the
runtime source matches integration commit `e6c029d8` (later commits through
the recorded checkout changed documentation and evidence only). HIP and SYCL
compile/link and `--help` checks for the same shared diagnostic sources are
recorded in the [maestro1 build report](../2026-10-22-phase5-maestro1-q8-selector-backend-build/README.md);
those x86 checks are not accelerator runtime evidence. Raw output and
supervisor telemetry remain local-only.

Reproduce with:

```sh
OUTPUT_ROOT=bench/results/2026-10-22-phase8-current-source-q2-profile-smoke/reproduction \
  bash bench/results/2026-10-19-phase8-current-source-q2-profile-smoke/run.sh

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-22-phase8-current-source-regression/supervisor \
  --timeout 2400 --interval 1 --sample-clocks -- \
  env STRATA_TEST_EXPERTS_BIN="$HOME/models/strata-orin-validation/generated-fixtures/q2_0-s2-layer0/experts.bin" \
  ctest --test-dir build/integration/candidate --output-on-failure -j2

python3 -m unittest discover -s tools/integration -p 'test_*.py'
```

This validates one supported, bounded MTP-off profile and the current default
regression surface. It does not qualify adaptive migration, MTP, multi-live
batch decoding, other quantizations or boards, or a general performance or
energy profile.
