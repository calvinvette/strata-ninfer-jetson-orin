# 1,024-token vision admission refresh — Orin — 2026-10-12

The current candidate repeated the bounded 1,024-token vision smoke with the
IQ1_M model, same 2,048×2,048 fixture, and CUDA vision encoder as the Oct 11
run. The model
request returned HTTP 200 with 1,049 prompt tokens and 48 completion tokens;
the response described the fixture. The API request took 55.38 seconds. The
six-GiB supervisor passed with minimum host `MemAvailable` of
7,978,848,256 bytes (7.43 GiB), leaving 1.43 GiB above the floor. No cgroup
OOM or OOM-kill event occurred.

The candidate engine SHA-256 is
`bdde041e60d8593dac593a846d471c117fee2c5397b01dfd99c9502253dd0f7d`; the
vision executable SHA-256 is
`69d6a171c0ff29504a5971116f7a9299dc7abf0ae1f6caa1563f009684e96825`; and the
fixture SHA-256 is
`c594b1e0f86f7f0b4a653e291e85ff37b3b894b2f517d7a4129d83f9eab65b8d`. The
owner parser observed 55 allocations and 54 frees; the expected service-lifetime
weight arena (1,475,120,640 requested bytes) remained live at log end. The main
engine trace covers service and request allocations together. The separate
vision process was not interposed in this repeat; the older 16-token CUDA
runtime probe is lower-bound attribution only and does not price this
1,024-token request.

The full API response, engine/server logs, owner summary, command config and
supervisor samples are retained here. This is an admission and functional
refresh for one fixture, not vision-quality or image-complexity qualification.
The small 1.43-GiB margin makes this cell sensitive to different cache/system
state. Dynamic clocks were observed without control; energy was not measured.
Models and build products remain outside Git.
