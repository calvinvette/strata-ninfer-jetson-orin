# IQ1_M vision smoke test — Phase 7

This bounded request used the current IQ1_M Q6 warp-dequant, accepted-only MTP4
profile at 8K context, with the locally built CUDA `strata-vision` encoder and
the BF16 Qwen3.8 projector already under `~/models/`. The test image is the
56×56 checked-in RGB grid fixture (SHA256
`821fc92247c54993fb9ba26f3580b09d264b5ac743a5cf24e22fa5ac54573275`). The
encoder was limited to 16 image tokens. The loopback API reported images
enabled and returned HTTP 200; the request used 41 prompt tokens and emitted
48 completion tokens in 12.31 seconds.

The answer described the colored squares as a checkerboard-like grid and
identified the smooth color gradient across rows and columns. These match the
fixture's visible pattern and color progression. This is one small-image
description smoke test, not a grounding accuracy score, high-resolution test,
or repeated-vision soak.

The 28-GiB supervisor retained 11.99 GiB minimum host/effective availability;
cgroup `oom`, `oom_kill`, `high`, and `max` counters stayed zero. CPU/GPU clocks
were observed under dynamic policy; EMC readback was denied and energy was not
measured. The candidate engine SHA256 is
`857a3fab0e70e049933dab1b51931f0c76e83548784671bb77865c7e24ec596e`; the local
vision executable is
`69d6a171c0ff29504a5971116f7a9299dc7abf0ae1f6caa1563f009684e96825`. The
projector hash is `b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0`.
Models and the encoder remain outside Git.

`run_phase7_vision.py` reproduces the API smoke using only Python's standard
library. It preserves the supplied cache setting unless an override is passed.
The API response, owned service config, server logs, supervisor memory samples,
clock observations and tegrastats are retained here.

## 2048×2048 admission smoke at 1024 vision tokens

The same current candidate engine and local CUDA encoder/projector were tested
with the checked-in 2048×2048 fixture (SHA256
`c594b1e0f86f7f0b4a653e291e85ff37b3b894b2f517d7a4129d83f9eab65b8d`). The
encoder warmed at 1024 image tokens. A loopback API request returned HTTP 200
with images enabled; usage reported 1,049 prompt tokens (1,024 image plus 25
text) and 48 completion tokens. The answer started describing the geometric
color pattern but ended with `finish_reason=length`, so this is an admission and
runtime smoke, not a vision-quality pass.

The 28-GiB supervisor sampled memory 91 times and retained 11.76 GiB minimum
host/effective availability. Cgroup `high`, `max`, `oom`, and `oom_kill`
counters were zero. The service exited cleanly. Clocks were observed under the
dynamic policy; EMC readback was unavailable and energy was not measured. The
request, owned config, logs, supervisor samples and tegrastats are in
`run-1024/` and `run-1024-supervisor/`. This does not test higher image-token
counts, multiple images, image grounding accuracy, or sustained vision service.
