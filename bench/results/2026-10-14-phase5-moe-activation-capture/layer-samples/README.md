# Q2_0 actual-activation parity across model depth — Orin — 2026-10-14

This follow-up samples one short Q2_0 service request at layers 0, 12, 24 and
47. Each service returned `READY` from the 15-token prompt and captured two
finite verifier rows at the selected layer. Each service and standalone parity
run was supervised under a 28-GiB cgroup limit with the six-GiB host floor;
all eight commands passed and sampled cgroup OOM/limit counters stayed zero.
The lowest host/admission availability was 16.868 GiB in the layer-47 service
smoke and 24.488 GiB in parity.

For each layer, the first captured activation was replayed through the CPU and
GPU expert operators for one expert actually routed in that row. Three selected
experts had final route kind 0 (primary VRAM); layer 24's selected expert had
route kind -1 (CPU). The pair comparison always runs both implementations on
the exact same captured FP32 activation, regardless of which route served it.

| Layer | Expert | Captured owner | CPU/GPU relative L1 | Bitwise words differing / 7,680 | Both routes vs float reference |
| ---: | ---: | --- | ---: | ---: | ---: |
| 0 | 2 | VRAM | 1.03e-7 | 5,691 | 1.21e-2 |
| 12 | 20 | VRAM | 7.87e-8 | 5,160 | 6.95e-3 |
| 24 | 439 | CPU | 6.35e-8 | 4,638 | 7.74e-3 |
| 47 | 60 | VRAM | 9.40e-8 | 5,514 | 1.19e-2 |

The route and activation are from the same service row, and the raw activation
file is a lossless little-endian float32 serialization. The parity program's
three operator rows repeat that vector for its width-invariance check. This
expands the real-input operator sample beyond layer 0 and finds small CPU/GPU
differences at all four sampled depths. It does not trace complete routed
outputs through the verifier transaction, demonstrate that unlike owners were
combined within one token, explain adaptive-swap persistent-state drift, or
qualify the short task beyond the exact `READY` response.

Reproduce one layer by selecting it on the bounded service smoke, then replay
the recorded activation and an expert listed in that row:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py --output layer-12-supervisor \
  --timeout 1200 --interval 1 -- \
  python3 bench/results/2026-10-14-phase5-moe-activation-capture/run_capture_smoke.py \
  --config bench/results/2026-10-14-phase5-moe-activation-capture/config.json \
  --output layer-12 --layer 12

systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py --output parity-12-supervisor \
  --timeout 1200 --interval 1 -- \
  build/integration/candidate/native_expert_parity \
  /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf \
  --expert 20 --activation-f32 layer-12/activation.f32 12
```
