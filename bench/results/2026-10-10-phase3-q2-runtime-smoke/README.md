# Q2_0 runtime admission smoke — Orin — 2026-10-10

The artifact-aware Q2_0 PLE oracle and table reader pass are documented in the
[PLE report](../2026-10-10-phase3-q2-ple-artifact-aware/README.md). This follow-up
attempted a separate 512-token/one-output native-pack request under
`run_control.py` with the six-GiB physical availability floor. It did not reach
prefill and does not qualify Q2_0 model execution, service behavior or
performance.

The first attempt was rejected by the CLI because a native pack requires
`--native`, `--spec >= 2` and an explicit prefill chunk. The supported spec2
retry loaded the Q2_0 pack and native projections, then rejected
`data/expert-profile-coder.bin`: it has 48×256 entries while this model has
48×512 experts. The no-profile retry loaded the pack and PLE table but failed
before prefill because the supplied Q2_0 MTP GGUF had not been converted to
runtime files. `tools/mtp_rt.py` was then tried with `gguf` 0.19.0 installed in
the local `~/models/strata-orin-validation/pack-venv`; that reader rejects
GGML tensor type 42 in this artifact. No repository dependency or source was
changed, and generated models/runtime files remain under `~/models`.

All three supervised attempts stayed well above the six-GiB floor; their
minimum available memory readings were 28.23 GiB, 25.28 GiB and 24.64 GiB.
The first unsupported configuration and both artifact-compatibility failures
are retained under `run/supervisor*` and `mtp-convert/`. The failure is a useful
integration boundary: Q2_0 PLE block compatibility is established, while the
model's expert profile and MTP runtime conversion need matching Q2_0 support
before a model request can be qualified. No timing or correctness conclusions
are drawn from these setup failures.
