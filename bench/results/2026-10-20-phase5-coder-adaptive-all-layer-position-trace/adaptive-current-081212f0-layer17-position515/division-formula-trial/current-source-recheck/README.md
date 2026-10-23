# Current-source expert-22 parity rerun — Orin — 2026-10-22

The current candidate rebuilt from this worktree reran the independent
`native_expert_parity` check on the retained layer-31, expert-22 activation.
The model is the pinned Coder IQ1_M GGUF at revision
`5348543e0147355ac9cbcb031184a3546350988e`. The exact executable and source
hashes are in `source-identity.sha256`.

With `STRATA_EXP_MODE=0` and the layer-specific `iq3_xxs/iq4_nl` Q8_1 selector,
CPU and CUDA activation Q8_1, gate/up dot outputs, post-SwiGLU hidden Q8_1,
and CPU down projection on the CUDA hidden blocks all matched bit-for-bit.
The expert output also matched across CPU and CUDA (0/7,680 F32 words differed).
The parity executable reported zero failures. This confirms that the earlier
reciprocal-SiLU repair for this captured layer-31 row is present in the current
candidate. It does not resolve the adjacent layer-32 accepted-state divergence:
that service pair still differed at position 518.

The run used `MemoryMax=28G` and passed in 1.06 seconds. Minimum host/admission
availability was 24.45 GiB; all cgroup low/high/max/OOM/OOM-kill counters were
zero. CPU/GPU clocks were observed dynamically; EMC readback was unsupported.
Energy was not attributed. Dumped stage files and supervisor logs are retained
here.
