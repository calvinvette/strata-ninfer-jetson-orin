# Corrected-kernel 4K/8K context-capacity rerun

Date: 2026-10-25. This reran the planned five natural-generation request
shapes with the corrected grouped SwiGLU binary at 4K and 8K configured
capacity. Each capacity used a fresh Strata-default service and a fresh strict
NInfer service, randomized arm order, one warmup plus one measured request per
workload, and the same 3,000-slot resident map. The model was the Coder Q2_0
artifact; MTP off, FP16 KV, prefill 128, eight workers, and the 6-GiB physical
floor were held constant. This is a single pair per capacity, not a repeated
performance estimate.

All 20 measured outputs matched their paired response hashes. All four
service-startup residency maps had SHA256
`a02fd81e6337273a299b4b834ab1b694c16e5f97512e5dfec9d4fec08cd5ddf7`. Every
eligible API/token-count check passed. The table reports prompt/decode TPS,
client TTFT to first visible content, and full client time as Strata / NInfer.

| Context | Request | Prompt TPS | Decode TPS | TTFT (s) | Client total (s) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 4K | 512 + 64 | 38.8 / 39.2 | 11.1 / 11.2 | 13.34 / 13.20 | 18.94 / 18.79 |
| 4K | 2,048 + 128 | 55.0 / 55.2 | 10.3 / 10.3 | 37.41 / 37.29 | 49.68 / 49.60 |
| 4K | 172 + 64 | 18.8 / 19.4 | 10.7 / 10.3 | 9.33 / 9.06 | 15.15 / 15.06 |
| 4K | 557 + 64 | 40.0 / 12.6 | 11.7 / 11.6 | 14.07 / 44.35 | 19.38 / 49.71 |
| 4K | 1,069 + 64 | 49.1 / 49.0 | 12.0 / 12.0 | 21.93 / 21.97 | 27.14 / 27.15 |
| 8K | 512 + 64 | 39.1 / 38.6 | 11.1 / 11.2 | 13.23 / 13.41 | 18.83 / 18.98 |
| 8K | 2,048 + 128 | 55.2 / 54.9 | 10.2 / 10.3 | 37.27 / 37.45 | 49.64 / 49.70 |
| 8K | 172 + 64 | 20.3 / 19.2 | 10.5 / 10.5 | 8.68 / 9.16 | 14.58 / 15.07 |
| 8K | 557 + 64 | 39.9 / 39.7 | 11.5 / 11.5 | 14.14 / 14.21 | 19.52 / 19.59 |
| 8K | 1,069 + 64 | 48.8 / 48.4 | 11.9 / 11.9 | 22.04 / 22.22 | 27.28 / 27.43 |

The isolated 4K / 557-token NInfer measurement was a large outlier: its warmup
matched Strata timing, but its measured prompt time was 44.19 s versus 13.92 s
for Strata. A randomized three-pair repeat did not reproduce the spike; median
paired TTFT improved 1.08% and client completion 0.67%, below the 5% screen
threshold. See the [repeat screen](../../2026-10-25-phase-e6-q2-557-repeat3/README.md).
Other cells were close, with no consistent end-to-end advantage in this
one-pair capacity screen. Minimum available physical/admission memory was 17.89 GiB; the
6-GiB headroom floor and separate 3-GiB workspace reserve were preserved. The
read-only initial GPU clock sample was 306 MHz; clocks were not controlled and
EMC readback was unavailable. Energy was not attributed. The service binary
SHA256 was
`c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75`.

The complete per-request API checks, output hashes, model arguments, resident
maps and supervised memory/clock logs are in [`4096/`](4096/) and [`8192/`](8192/).
