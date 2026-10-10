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

The three initial supervised attempts stayed well above the six-GiB floor;
their minimum available memory readings were 28.23 GiB, 25.28 GiB and 24.64 GiB.
The first unsupported configuration and both artifact-compatibility failures
are retained under `run/supervisor*` and `mtp-convert/`. The failure is a useful
integration boundary: Q2_0 PLE block compatibility is established, while the
model's expert profile and MTP runtime conversion need matching Q2_0 support
before speculative requests can be qualified.

## Narrow one-token result

To isolate runtime admission from those unsupported pieces, a shape-correct
full 48×512 expert ranking was generated with `tools/make_profile.py --no-base`
and stored at `~/models/strata-orin-validation/q2-expert-profile.bin`. The
ranking uses the tool's deterministic fill order; it is not based on Q2_0
routing measurements and is not a performance profile. With a fixed 5,000-slot
cache, MTP omitted and `--max-new 1`, the real native Q2_0 model completed the
provided 512-token prompt and emitted token ID 32. The log records 5,000 actual
resident slots, Q2_0 PLE enabled, and a captured one-token verifier window.
Minimum physical `MemAvailable` was 16,870,502,400 bytes (15.71 GiB), above the
six-GiB floor. The provided CLI prompt is processed as 511 prefill tokens plus
the final prompt token in the decode path, consistent with the control
convention.

The same cell was repeated inside transient systemd cgroups:

| MemoryMax | Outcome | Minimum effective availability | Minimum host availability | Peak scope current |
| ---: | --- | ---: | ---: | ---: |
| 20 GiB | Request completed; output token 32 | 7.98 GiB | 15.82 GiB | 12.01 GiB |
| 16 GiB | Supervisor pressure abort during prefill | 5.45 GiB | 15.80 GiB | 10.55 GiB |

The 16-GiB run crossed the six-GiB effective-availability stop threshold
between sampler intervals; host availability stayed ample and the process was
stopped by the supervisor, not by an OOM event. These cells show this exact
workload completing at 20 GiB and being refused at 16 GiB. They do not define a
general minimum cgroup size or a supported capacity profile. Raw telemetry and
outputs are in `run/cgroup-20g/` and `run/cgroup-16g/`.

Finally, the same 5,000-slot, no-MTP, 512-token/one-output cell completed with
`--max-context 8192` and `--max-context 16384`. Minimum host availability was
15.65 GiB and 15.70 GiB, respectively. These are configured context
reservations; the requests still processed only the short prompt. The captured
one-token verifier window and output token ID 32 matched the 4K smoke. This
supports admission at these settings for this artifact and request shape, not
actual 8K/16K ingestion, retrieval quality or long-context serving.

This is one successful allocation/admission smoke, not a quality check, paired
comparison, cache-ranking result, MTP/speculation test, service test, or
performance claim. The build SHA256 is
`d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`; the exact
token file SHA256 is
`c463143cd6cc684c29cba41efe832274e4cc040335b2338cce196d67c47d3cbf`; and the
generated admission profile SHA256 is
`b3e62120218cd96d175a0547530158869177dd2164b22b40f32bea7d7e85fb8c`. The
supervised raw run is `run/supervisor-spec2-no-mtp/`.
