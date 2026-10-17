# Current-source Coder IQ1_M image-grounding check — Orin — 2026-10-17

This bounded vision check asked the current-source Coder IQ1_M service to count black circles in a synthetic four-quadrant image and report the exact counts and total. The 224×224 PNG contains red, blue, green and yellow quadrants with one, two, three and four circles. A separate connected-component pass over the generated pixel raster supplied the oracle `TL=1 TR=2 BL=3 BR=4 SUM=10`; the question gave only the required response format, not the counts.

Three fresh services independently returned that exact answer with HTTP 200, `finish_reason=stop`, 80 prompt tokens and 17 completion tokens. Each service shut down cleanly. Median request time was 15.46 s. Minimum host/effective admission availability was 11.76 GiB, above the six-GiB floor; sampled cgroup high/max/OOM/OOM-kill counters were zero. The image encoder was fixed at 16 tokens. No energy was measured.

The profile used the pinned `IQ1_M` variant from `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF`, snapshot revision `5348543e0147355ac9cbcb031184a3546350988e`, with Q6 warp dequant, MTP4 accepted-only adaptation, 3,000 expert slots, FP16 KV, 8K context and eight workers. Model shards, MTP files, projector and other model assets remained under `~/models/strata-orin-validation`. The report pins the current Strata service binary and the local vision encoder separately.

This adds a repeatable exact-grounding pass for one synthetic image and one image-token setting. It is not broad vision-quality or high-resolution support; the separate 2,048×2,048 admission smoke remains non-qualifying because its response was truncated.

`analysis.json` validates all three responses and supervision records. `oracle.json`, `generate_fixture.py` and `fixture.png` retain the independent fixture and expected answer. `run/`, `run-02/`, and `run-03/` contain the responses, service logs and owned configs; matching `supervisor*` directories retain memory, clocks and tegrastats. `artifacts.json` pins source, binaries, model revision and profile. `SHA256SUMS.txt` covers the retained artifacts. Reproduce from the repository root with:

```sh
python3 bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/generate_fixture.py
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/supervisor \
  --timeout 900 --interval 1 --sample-clocks -- \
  python3 bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/run_vision.py \
  --config bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/config.json \
  --output bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/run \
  --fixture bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/fixture.png \
  --vision-exe build/integration/vision-cuda/bin/strata-vision \
  --mmproj /home/calvin/models/strata-orin-validation/mmproj-Qwen3.8-Flash-Next-BF16.gguf \
  --port 18860 --vision-min-tokens 16 --vision-max-tokens 16
bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/run_confirm3.sh
python3 bench/results/2026-10-17-phase7-current-source-coder-iq1m-vision-count/analyze.py
```

Phase 7 remains open for broader vision tasks, profile selection, capacity boundaries, concurrency and the remaining support-matrix gates.
