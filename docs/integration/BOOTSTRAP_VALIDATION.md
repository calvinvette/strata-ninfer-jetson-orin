# Bootstrap validation

The bootstrap changes documentation and adds reference material plus offline
planning tools. Active engine, server, setup, CUDA/HIP/SYCL source and build files
are identical to the pinned Strata control. This is source equality, not a fresh
runtime or desktop output-parity claim.

Checks on the Orin host:

| Check | Outcome |
| --- | --- |
| `python3 tools/integration/verify_import.py` | 1,320 imported files match their manifest hashes: 1,272 committed-source files, 46 local reports, local plan and local diff |
| `python3 tools/integration/plan_matrix.py --output /tmp/strata-ninfer-matrix.json` | 162 proposed cells, 936 baseline/candidate run entries; execution disabled |
| `python3 tools/integration/plan_matrix.py --suite mtp_kv_workload --confirmation --output /tmp/strata-ninfer-confirmation.json` | 16 cells, 224 run entries, seven pairs per cell |
| `python3 -m unittest discover -s tools/integration -p 'test_*.py' -v` | Five tests pass: paired reproducibility, full nominated interactions, ordered capacity, confirmation counts, invalid-design rejection |
| New integration Markdown local links and Python/JSON syntax | Pass |
| Staged import blob hashes | All 1,320 match; Git attributes preserve imported line endings and corpus whitespace |
| Original checkouts | Strata stays clean at `0be090c`; NInfer retains its original local plan edit |

The imported engine and tools have not been rebuilt or run here. Existing reports
remain historical evidence of their original binaries. Full backend rebuilding
and actual-model integration validation are future phase gates, not prerequisites
for publishing this source/reference and planning bootstrap.

Imported source/corpora retain their original whitespace; the reference subtree
is exempt from whitespace normalization and checked by content hashes instead.
New integration files retain the repository's normal whitespace checks.
