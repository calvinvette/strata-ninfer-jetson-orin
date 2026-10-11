# Q2_0 PLE oracle under a 10 GiB cgroup cap — Orin

The artifact-aware PLE oracle passed in a transient 10 GiB cgroup-v2 scope
under the ordinary six-GiB physical/effective-availability supervisor. The
test checked all seven PLE stages for three tokens, including the real Q2_0
layer-1 weights and PLE rows, byte-identical native-key reconstruction, and
agreement with the independently decoded projection. The worst relative L1
error was `1.148e-7`. Hidden state and convolution history are synthetic, so
this is operator/codec evidence, not whole-model quality evidence.

The cgroup wrapper returned zero in 1.08 seconds. The supervisor sampled a
minimum effective availability of 9.97 GiB and minimum host `MemAvailable` of
24.64 GiB. The 10 GiB scope's observed `memory.current` peak was 32.1 MiB. These
are this short test's measurements, not a capacity bound for full model
requests. The scope and host figures remain separate and are never summed.

The PLE executable SHA256 is
`021239e6fa46ba81b1d1c011b10a71a6386ae420d14cc25cc496a8558efaed30`.
Model and generated pack remain under `~/models/strata-orin-validation/`;
artifact identities are recorded in `artifact-identities.json`. Raw stdout,
stderr, memory samples and tegrastats are in `supervisor/`.

Reproduce from the repository root:

```sh
systemd-run --user --scope -p MemoryMax=10G \
  python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-q2-ple-cgroup10G/supervisor \
  --timeout 1800 -- build/integration/candidate/ple_parity --selftest \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf
```
