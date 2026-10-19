# Per-QSA accepted-prefix state fingerprints — Orin — 2026-10-19

This follow-up fingerprints each of the 12 persistent QSA states at every
accepted generated prefix for the same three Coder IQ1_M arms documented in the
parent report: default CPU, opt-in CPU Q8_1 mirror, and GPU placement profile.
The model is `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` at revision
`5348543e0147355ac9cbcb031184a3546350988e`. The exact prompt and completion
IDs match across arms. Runs were randomized and separately supervised with a
28-GiB cgroup limit; dynamic clocks were observed, not controlled.

At each prefix, the opt-in diagnostic hashes the QSA ring indices and used
key/value cells, including the spare row, independently per QSA state. A
64-bit FNV-1a value is a change locator, not a cryptographic proof of state
identity. The captured state-to-model-layer mapping is in
`analysis-qsa-state.json`; CUDA implementation/build identity and focused CTest
results are retained in `backend-builds/`.

For default CPU versus Q8_1 mirror, the first different QSA fingerprint is
model layer 3 at all 16 positions; the first different host route activation
is layer 2 at all 16. For mirror versus GPU placement, the first position
(511) differs in QSA state at model layer 11 while the first host route
activation differs at layer 9; positions 512–526 first differ in QSA state at
layer 3 and route activation at layer 2. This narrows the location of the
persistent-state difference after the observed activation differences, but the
fingerprints do not reveal which state element or operation causes it.

All three runs passed supervision. Minimum host/admission availability was
14.38/14.38 GiB (default CPU), 14.42/14.42 GiB (Q8_1 mirror), and
14.40/14.40 GiB (GPU profile); each had zero observed cgroup high, max, OOM,
and OOM-kill events. No performance comparison is claimed. The independent
per-layer analysis can be regenerated with:

```sh
python3 bench/results/2026-10-18-phase5-coder-layer1-route-isolation/analyze_qsa_state_all16.py
```

This is diagnostic state evidence for one prompt/model/profile. It does not
establish exact state equality, service-level causality, answer quality, or
resolution of the continuation mismatch. Phase 5 remains open.
