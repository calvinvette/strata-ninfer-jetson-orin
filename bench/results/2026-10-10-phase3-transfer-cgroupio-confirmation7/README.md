# Mapped reads versus pread with scoped block-I/O accounting — Orin — 2026-10-10

This seven-pair, same-day repeat compares the existing mapped expert-file path
(`STRATA_IO_PREFETCH=0`) with asynchronous whole-blob `pread`
(`STRATA_IO_PREFETCH=1`, eight workers). Host staging was disabled in both
arms. It repeats the 512-token prompt/64-token output workload with requested
cache 3,000, which selected the same 3,903 expert slots in every arm. The
formatted prompt SHA256 is
`9c1407d465d3daa0d7f5512422144432e482886d33717db09678fc89dddb4f4d`; the
candidate engine SHA256 is
`d3e8bcde3a430d7d5bb614fec8ba938398699b9abecd41965bb28fd6d465d721`. Model,
pack and tokenizer identities are the IQ1_M Coder validation cohort recorded
in the prior [seven-pair report](../2026-10-10-phase3-transfer-confirmation7/README.md).

The run was supervised at the six-GiB `MemAvailable` floor and placed in a
temporary systemd scope with `IOAccounting=yes`. A `setpriv` launcher retained
the normal `calvin` UID and Orin device groups inside that scope. The transfer
harness samples the leaf scope's `io.stat` around each request, so the counter
covers the request harness and engine child but excludes unrelated scopes.
Before the model run, an `O_DIRECT` calibration read of 64 MiB increased the
scope's `rbytes` by exactly 64 MiB. The supervisor's minimum physical
availability was 14,172,614,656 bytes (13.20 GiB).

All seven pairs matched all 64 output token IDs and all nine persistent-state
fields. The actual expert-cache capacity was 3,903 slots in all 14 arms.
Randomized pair order, raw outputs, state fingerprints, cgroup and whole-device
read counters, rail samples, memory samples and tegrastats are retained under
`experiment/` and `supervisor/`. Machine-readable per-pair and bootstrap
summaries are in [`paired-summary.json`](paired-summary.json).

| Pair | Order | Mapped request ms | Pread request ms | Paired delta % | Mapped scoped read GB | Pread scoped read GB | Read delta GB |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | mapped / pread | 30,318.8 | 33,022.3 | −8.19 | 8.411 | 10.790 | −2.379 |
| 1 | mapped / pread | 30,879.9 | 63,607.2 | −51.45 | 8.878 | 10.254 | −1.376 |
| 2 | mapped / pread | 31,984.8 | 33,472.9 | −4.45 | 9.449 | 10.283 | −0.834 |
| 3 | mapped / pread | 31,727.1 | 32,879.3 | −3.50 | 9.007 | 10.634 | −1.626 |
| 4 | mapped / pread | 31,722.2 | 33,579.0 | −5.53 | 9.636 | 10.646 | −1.010 |
| 5 | pread / mapped | 31,784.9 | 33,485.3 | −5.08 | 9.632 | 10.369 | −0.736 |
| 6 | pread / mapped | 39,369.7 | 34,357.2 | +14.59 | 9.602 | 10.026 | −0.424 |

The paired median mapped-minus-pread request delta was −5.08%; a 200,000-draw
bootstrap of the median paired delta (seed 1011, resampling whole pairs) gave
−8.19% to −3.50%. Median total request times were 31,727.1 ms mapped and
33,485.3 ms pread. The median paired cgroup-read difference was −1.010 GB
(bootstrap interval −1.626 to −0.736 GB). By arm, median scoped read bytes were
9.449 GB mapped and 10.369 GB pread. Whole-device NVMe read deltas followed the
same direction and were close to, but generally above, the scope counters;
those device values still include unrelated activity.

The pread-side runtime counters also limit the interpretation: in all seven pread arms, prefetch issued about 1,600–1,750 reads but reported zero consumed prefetched blobs, zero dropped blobs, and zero decode wait fetches. Thus this cell did not exercise a measured request-path pread copy stall; the request-time and scoped-I/O differences are observations for this configuration, not evidence that pread serves the expert misses.

The paired result is workload-specific, with dynamic clocks and two large
request-time outliers (one pread and one mapped). CPU clock medians varied from
729 to 1,267 MHz; tegrastats provided no GPU or EMC frequency samples during
the request windows. Named rail integrals were captured but remain system-wide,
non-additive observations rather than process energy. The result supports a
scoped storage-read measurement method and strengthens the mapped-read screen
for this cache/workload. It does not promote a path or change defaults; other
contexts, cache sizes, request shapes and held-out prompts remain untested.

One earlier attempted pair with requested cache 5,000 selected 6,519 mapped
slots and 6,187 pread slots; tokens matched but persistent state differed. The
harness now records and requires equal actual slot counts. That invalid-capacity
pair is retained in the [capacity-mismatch attempt](../2026-10-10-phase3-cgroup-io-transfer-pair-groupfix/README.md)
and excluded from the table. A first scope launch that dropped device groups
also failed before CUDA initialization; see the
[launcher attempt](../2026-10-10-phase3-cgroup-io-transfer-pair/README.md).
The [one-pair capacity-controlled pilot](../2026-10-10-phase3-cgroup-io-transfer-pair-cache3000/README.md)
passed and led to this seven-pair run. These setup and capacity failures were
resolved for the reported run without changing the engine.

The harness parser has four focused unit tests. Run it with the integration
Python environment:

```sh
/home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  -m unittest discover -s tools/integration -p 'test_file_tier_transfer_parity.py' -v
```

On Orin, the experiment was launched through a temporary system scope with
I/O accounting, then dropped to the normal user and device groups:

```sh
sudo systemd-run --scope --property=IOAccounting=yes -- \
  /usr/bin/setpriv --reuid=1000 --regid=1000 \
  --groups=1000,4,24,27,29,30,44,46,104,116,120,135,136,137,996,999,1001,1002 -- \
  /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/run_control.py --output bench/results/NEW-transfer/supervisor \
  --timeout 2400 -- /home/calvin/models/strata-orin-validation/pack-venv/bin/python \
  tools/integration/file_tier_transfer_parity.py \
  --config build/integration/candidate-protocol/server-config.json \
  --engine build/integration/candidate/strata \
  --output bench/results/NEW-transfer/experiment --prompt-tokens 512 \
  --generated-tokens 64 --pairs 7 --seed 20261011 --expert-cache 3000 \
  --tegrastats-energy --tegrastats-interval-ms 100 --run
```
