# Fixed-cache mapped versus pread confirmation with rail samples

This same-day Orin run adds synchronized tegrastats rail sampling to the fixed
5,000-MiB expert-cache mapped-versus-pread comparison. It is a single
512-token prompt / 64-token generation cell, not a general transfer-policy
result. The request prompt SHA256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`; the
candidate engine SHA256 is
`c9c70cfdc701431066063cc71bcaa0c2a20703673eba82f2dc28387f5686a2c7`.
The full model, pack, MTP and tokenizer identities are in
`artifact-identities.json`; artifacts remain under `~/models/`.

Seven randomized pairs completed under the six-GiB supervisor. Every request
emitted 64 tokens; output token IDs, all nine persistent-state hashes, 6,519
actual expert-cache slots and 49,629 expert-cache hits matched within each
pair. The supervisor measured a minimum `MemAvailable` of 8,750,534,656 bytes
(8.15 GiB). Pair arm order was randomized and both arms used the same model,
request, engine, cache cap and MTP configuration.

| Measure | Mapped median | Pread median | Paired mapped-minus-pread median (95% bootstrap interval) |
| --- | ---: | ---: | ---: |
| Request time | 27,030.5 ms | 28,226.5 ms | −6.26% (−9.69%, −4.24%) |
| VIN_SYS_5V0 rail energy | 193.94 J | 202.65 J | −5.39% (−8.19%, −0.86%) |
| VDD_GPU_SOC rail energy | 306.17 J | 318.94 J | −3.65% (−6.06%, −1.99%) |
| Whole-device NVMe read-byte delta | 8,084,525,056 B | 8,736,342,016 B | −6.55% (−8.63%, −3.81%) |

Intervals use 100,000 pair-resamples with seed 20261011. Prompt-time medians
were 22,206.9 ms mapped and 22,280.0 ms pread; decode medians were 4,627.0 ms
and 6,023.3 ms. Major-fault medians were 88,955 mapped and 61,809 pread;
minor-fault medians were 183,854 mapped and 210,082 pread. Fault counts do not
track a uniform benefit across arms.

The two largest request-time outliers remain in the data: pair 4 pread and pair
5 mapped. Both requests had a 729 MHz median sampled CPU clock; CPU medians
ranged from 729 to 2,201 MHz overall. tegrastats returned no GR3D or EMC clock
samples. Energy is trapezoid integration of named whole-board rail readings at
sample-arrival times and includes unrelated system activity; rail values are
separate and non-additive. NVMe deltas are whole-device counters, including
unrelated reads and kernel readahead. Process read-byte and leaf-cgroup I/O
counters were unavailable. These limits and the outlier values are retained in
`analysis.json` and the raw `experiment/` data.

This strengthens one fixed-cache transfer cell, but does not qualify a default
change. Different workloads, cache/context interactions, scoped I/O, stable
clocks and broader memory/latency tradeoffs remain open. No serving path changed.

Reproduce from the repository root with the recorded model config and engine:

```sh
python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-transfer-energy-confirmation7 \
  --timeout 1800 -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/file_tier_transfer_parity.py \
  --config /home/calvin/models/strata-orin-validation/strata-orin-validation-8k.json \
  --engine build/integration/candidate/strata \
  --output bench/results/2026-10-11-phase3-transfer-energy-confirmation7/experiment \
  --prompt-tokens 512 --generated-tokens 64 --pairs 7 --run \
  --tegrastats-energy --tegrastats-interval-ms 100 --expert-cache 5000
```
