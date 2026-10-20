# Orin current-source regression checks — 2026-10-19

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
