# Rejected expert-118 SwiGLU expression trial — Orin — 2026-10-20

This isolated operator trial changed the CPU Q8_1 hidden expression from the
reciprocal form `(g * (1 / (1 + exp(-g)))) * u` to direct division
`(g / (1 + exp(-g))) * u`. It used the exact current layer-16 position-515
activation (SHA256 `3586bf67c17963bfa134911d410a149d8cd782800c81bcb4c7b025f66300a4a2`)
from the pinned Coder IQ1_M snapshot. The temporary source was restored after
the test; the current worktree and parity target use the reciprocal form.

For expert 118, the direct-division CPU output was byte-identical to the
reciprocal-form CPU output and still differed from CUDA in all 2,560 values
(relative L2 `1.35199e-4`). Its stage run found exact Q8_1 input bytes and exact
gate/up dots against CUDA, with 3/60 hidden Q8_1 blocks differing only in
FP16 `d` scale (no sum-scale or code-byte differences). CPU IQ4_NL down on the
CUDA hidden blocks matched grouped CUDA output in all 7,680 words. Expert 39
remained bit-identical across CPU/CUDA. Thus this formula change did not fix
expert 118 and retained the same sampled scale discrepancy.

The three differing blocks are indices 10, 30, and 50. Their serialized CPU
scale is `de16`; the CUDA scale is `dd16`. The block sum-scale and all 32
integer codes match in each block.

A source-faithful CUDA replay, [`replay_cuda_swiglu.cu`](replay_cuda_swiglu.cu),
used the captured CUDA gate/up float rows and the kernel's `__fmul_rn(g /
(1 + __expf(-g)), up)` expression, followed by the same Q8_1 scale, sum and
rounding code. Compiled with CUDA Toolkit 12.6, `-O3 -arch=sm_87
--use_fast_math`, it reproduced all 60 captured CUDA Q8_1 blocks byte for byte.
Compared with the CPU direct-expression hidden floats, this replay differs in
600/1,920 entries (maximum absolute difference `2.98023e-8`, relative L2
`5.12883e-8`). The three scale-byte differences therefore arise after the
captured gate/up dots and before Q8_1 quantization in this sampled row. A
separate accurate-`expf` CUDA replay retained the same Q8_1 blocks and the
same three CPU/CUDA scale differences; changing only the exponential
approximation did not correct this sample. This is a source-based replay of
the captured stages, not a direct dump of the serving kernel's float hidden
buffer, and it does not qualify a general correction.

Rebuild the source diagnostic from the repository root with:

```sh
nvcc -O3 -arch=sm_87 --use_fast_math -I include \
  bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/replay_cuda_swiglu.cu \
  -o /tmp/replay_cuda_swiglu
```

Then run it on the retained stage captures, under the standard memory
supervisor:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  /tmp/replay_cuda_swiglu \
  bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/expert118-hidden/layer-16-expert-118--gpu-gate.f32 \
  bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/adaptive-current-081212f0-layer17-position515/division-formula-trial/expert118-hidden/layer-16-expert-118--gpu-up.f32 \
  /tmp/expert118-hidden.f32 /tmp/expert118-hidden.q8_1
```

The captured CUDA Q8_1 block file and replay output compared equal over all
2,160 bytes. The replay program is diagnostic source only; generated
executables are not retained in the repository.

The parity executable returned failure because its independent reconstruction
still encodes the reciprocal expression; it reported 369/1,920 gate/up
reconstruction words differing from the altered native hidden output. That
failure is retained as evidence against changing the arithmetic contract
without updating and validating the independent oracle. The measured CPU/CUDA
hidden-scale and down-projection comparisons are still recorded in the
supervisor output. Both oracle invocations were supervised with `MemoryMax=28G`
and passed the six-GiB availability floor; the expert-118 parity assertion
itself failed. This experiment is rejected and no source change remains.

An [Orin NEON reciprocal replay](neon-reciprocal/README.md) then tested zero
through three Newton refinements against the same CUDA Q8_1 hidden bytes. One
refinement matched the 60 `d` scales but moved three one-step errors to `s`
(blocks 8, 28 and 48); two or three refinements matched `s` but left three
`d` errors (blocks 10, 30 and 50). All integer codes matched in these refined
variants. A simple ARM reciprocal estimate diverged broadly. No tested NEON
variant reproduced the packed CUDA bytes exactly, so this remains a rejected
local arithmetic substitution.

The current-source [layer-31 expert-22 parity rerun](current-source-recheck/README.md)
also confirms the captured reciprocal-SiLU mirror produces exact CPU/CUDA
hidden bytes and expert output in the rebuilt candidate. That local parity
does not remove the separately observed layer-32 accepted-state divergence.
