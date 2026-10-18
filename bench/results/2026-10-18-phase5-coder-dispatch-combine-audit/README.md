# Coder dispatch/combine capture alignment audit — 2026-10-18

This audit corrects an overclaim in the earlier report at the former `2026-10-18-phase5-coder-dispatch-combine-join` path, committed as `e3551547`. That report incorrectly equated route dispatch 1393/layer 1 with the first post-combine row at position 511/token 271. **That row-level join is not established and the assertion is withdrawn.**

The Oct 16 service runs retained two different capture windows. The CPU-route capture skipped the first 1,392 route rows and records dispatch, layer, row and stream-row indices, but no absolute token position or token ID. The `STGDIAG4` combined capture starts with position 511/token 271 and contains the selected verifier layer's output rows. The CPU output records do match the route IDs and CPU-owner slots at dispatch 1393, but without the skipped route prefix or shared position metadata they cannot be safely aligned to a particular combined-output row. `alignment-audit.json` records the checks and retained source hashes.

The prior evidence remains valid only as separate observations: four CPU-owned expert rows differed between the default and CUDA-mirror routes on the same matched captured activation/IDs/owners, and the paired services separately showed post-combine differences on matching position/token rows. It does not establish that those are the same row or directly connect that route delta to that combined delta.

The new three-arm run in the sibling [layer-1 route isolation campaign](../2026-10-18-phase5-coder-layer1-route-isolation/README.md) initially failed to create its truncated route capture because a single short request did not reach `start_row=1392`. The request itself completed, but those cells are harness failures and are excluded. The corrected rerun captures from row 0 and selects the first layer-1 dispatch so its route record can share the first verifier row's sequence order; qualification still requires explicit position/token checks.

Reproduce this audit from the repository root with:

```sh
python3 bench/results/2026-10-18-phase5-coder-dispatch-combine-audit/audit_alignment.py
sha256sum -c bench/results/2026-10-18-phase5-coder-dispatch-combine-audit/input-sha256.txt
```

The corrected model capture will remain separate until the harness records or independently verifies a shared absolute row key. Phase 5 remains open.
