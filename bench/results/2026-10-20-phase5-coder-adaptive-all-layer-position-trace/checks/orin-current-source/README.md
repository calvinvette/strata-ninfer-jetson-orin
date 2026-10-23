# Orin current-source regression checks — 2026-10-20

The current working-tree source was rebuilt on Orin AGX with the existing
Release CUDA 12.6 / SM87 build directory at `/tmp/strata-ninfer-orin-phase5-cuda`
using two build jobs. The complete build passed. The `strata` executable
SHA256 is `b672187692408e8abcb48beb6ad80282b01954bae819ec48963ac7c6440e4ec9`;
`native_expert_parity` is
`c7e58a04d3742e2b6129d465c4b334e75c7401d03d4bbb9511b799c599da77c0`.
The exact CTest and integration Python commands were rerun against this build:
the focused accepted-prefix, verifier, GDN, KV, graph lifecycle, three native
expert format-pair and selector-contract selection passed 13/13, and Python
integration unittest discovery passed 163/163. Full logs are retained in
`build-20261020.txt`, `ctest-20261020.txt`, and
`integration-python-20261020.txt`; `SHA256SUMS-20261020.txt` verifies those
logs. The five changed shared-source/header SHA256 values are in
`source-sha256-20261020.txt`.

These regression checks do not resolve adaptive migration's persistent-state
and continuation drift; that Phase 5 gate remains open.

## Earlier current-source check — 2026-10-19

These checks ran directly on Orin AGX against the updated candidate binary:

```text
SHA256 build/integration/candidate/strata:
14afd1a4b953e176a88d7812bddcdf2beb65944bb5795beaf0f37e5834a496aa
```

The focused CTest selection passed 18/18: accepted usage/window commits,
GDN recurrence, verifier parity, speculative verifier parity, batched verifier
parity, all ten native Q8_1 dot/window cases, and the selector contract. Python
integration unittest discovery passed 163/163. Full command output is retained
in `ctest.txt` and `integration-python.txt`.

The run does not claim broad suite completion, task quality or performance. The
separate supervised adaptive/delayed campaigns and their memory/clock records
are in the sibling `../../reproduction-q8-cuda-input-quantizer*` bundles.
