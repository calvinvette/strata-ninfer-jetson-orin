# Layer-11 expert-201 same-input oracle

`activation.f32` contains the 2,560-float verifier activation for Coder IQ1_M
layer 11, position 515. Its SHA256 is
`d488e5abb862588a04acd2d6bd95a3cb240ce9dc36d1076e679056de72c24f8a`. The
adaptive pair's initial and recovery layer-11 activation and router metadata
were checked against this input by
`compare_layer25_owner_output_oracle.py`.

The successful `native_expert_parity` run used the pinned IQ1_M GGUF and
`STRATA_NATIVE_CPU_Q8_1_DOT=all`, under `MemoryMax=28G` supervision. It reported
layer 11 expert 201 as IQ2_S/IQ4_NL and zero parity failures. The service's
initial CPU output equals the parity CPU row bitwise; its recovery GPU output
equals the parity GPU row bitwise. Those CPU/GPU outputs differ in all 2,560
values, with relative L2 `4.395e-4`. Raw activation, gate/up/down weights,
float output, and CPU/GPU outputs are retained in `oracle/`; the machine output
and supervisor telemetry are retained in `supervisor-retry-1/`.

The stage-isolation rerun set `STRATA_EXP_MODE=0` to capture the actual CUDA
gate/up stages and enabled hidden-state comparisons. Independent IQ2_S/Q8_1
gate/up dots matched the CUDA stages exactly (`0/1,920` gate and up values
differing). CPU raw hidden values produced from the GPU activation also matched
the CPU raw hidden values bitwise. After SwiGLU and Q8_1 quantization, CPU and
GPU hidden blocks differed in only 3 of 60 blocks: one signed code byte moved
from 32 to 33 at block-in-row 3, code index 7, for each of the three diagnostic
rows. The block `d` and stored-sum fields matched. CPU IQ4_NL down-projection on
the captured CUDA hidden Q8_1 rows then matched grouped CUDA output bitwise
(`0/7,680` values differed). This localizes the measured operator delta to the
post-SwiGLU hidden Q8_1 codes; the exact device-versus-host SiLU rounding at
those three threshold crossings was then isolated by a host replay from the
captured CUDA gate/up values. The CPU expression `(g * (1/(1+exp(-g)))) * u`
reproduces CPU hidden codes exactly and misses the same three GPU codes; the
CUDA expression `(g/(1+exp(-g))) * u` reproduces all GPU hidden codes exactly
with both tested Q8_1 code quantizers. Both formulas used the same host
`std::exp`, so this isolates the tested operation-order difference on these
captured values without establishing CUDA `__expf` equivalence generally.
Results and source/input hashes are in `silu-order-replay.txt` and
`silu-order-inputs.sha256`. This operator-level explanation does not establish
that a runtime arithmetic change repairs accepted-state migration or improves
end-to-end quality; production source was not changed.

The separate Q8_1 input quantizer diagnostic reported identical scales and
codes but different stored-sum fields in 78/80 input blocks (GGML stores
`d*sum(q)`, CUDA stores `sum(input)`). The exact gate/up match and exact down-on-
CUDA-hidden result show that this stored-sum difference was not observed to
contribute to this expert's output delta.

The first parity attempt is retained in `supervisor/`. It did not complete the
operator check: the output directory had not been created, and the utility
accepts the layer as a positional argument rather than `--layer`. The corrected
retry created the directory and used positional layer `11`.

The first exp-mode stage-capture attempt likewise lacked its output directory;
the successful rerun is retained under `stage-supervisor-exp0-retry-1/`.

Reproduction:

```sh
mkdir -p bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer11-position515/expert201/oracle
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer11-position515/expert201/supervisor-retry-1 \
  --timeout 1800 --interval 1 --sample-clocks -- \
  /usr/bin/env STRATA_NATIVE_CPU_Q8_1_DOT=all \
  build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf \
  --expert 201 \
  --activation-f32 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer11-position515/expert201/activation.f32 \
  --dump-f32-dir bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/operator-checks/layer11-position515/expert201/oracle \
  11
```
