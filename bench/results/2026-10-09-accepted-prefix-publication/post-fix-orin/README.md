# Post-fix Orin run

Run date: 2026-10-09. Host: `orin1`, ARM64, Linux 5.15.148-tegra, Orin
(nvgpu). Candidate binary, prompt, model root, source, harness and configuration
identities are recorded in `identities.json`. Models remain under the user's
`/home/calvin/models/strata-orin-validation` directory and are not included.

The supervised paired run completed with status `pass`, return code 0 and a
6 GiB physical-memory floor. Sampled minimum available memory was
9,207,517,184 bytes. Spec 1 and spec 4 emitted equal 32-token ID sequences and
matched all nine recorded state fields. Spec 4 offered 27 drafts and accepted
23. This is one clipped-output model-state case, not a general MTP, EOS,
cancellation, pipeline or performance qualification.

`results.json` is the harness result; both engine logs preserve request output
and state fingerprints. `supervisor.json`, `memory.jsonl` and `tegrastats.txt`
retain the guard and raw host telemetry. Energy was not measured; tegrastats rail
samples are not whole-board energy. Verify the evidence files with
`sha256sum -c SHA256SUMS`.
