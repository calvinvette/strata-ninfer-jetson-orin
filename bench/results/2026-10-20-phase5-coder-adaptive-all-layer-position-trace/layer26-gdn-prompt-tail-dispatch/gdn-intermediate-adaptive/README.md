# Layer-26 GDN intermediates across the two-token verifier window — Orin — 2026-10-20

The adaptive-cap-8 service captured layer-26 GDN intermediates for both rows
of the verifier's two-token window at positions 505 and 506. This required the
opt-in multi-position `STRATA_VERIFY_DUMP_GDN_POSITIONS` filter; the existing
single-token pre/post state hook cannot observe this window. The run used the
pinned Coder IQ1_M artifact and the current candidate, passed supervision in
181.5 seconds, retained 14.31 GiB minimum host/admission availability, and
recorded zero cgroup memory events.

The layer-26 intermediate record is 689,864 bytes and contains two rows per
request. The initial and recovery token IDs match at positions 505 (248045) and
506 (74455). The first changed GDN field is different for the two rows:

| Position | First differing field | Earlier fields | Difference |
| ---: | --- | --- | --- |
| 505 | `x` | none | 2,560/2,560 values; max abs 0.00463; relative L2 0.00208 |
| 506 | `h` | `x`, `qkv` match | 10,238/10,240 values; max abs 0.00141; relative L2 0.00178 |

At position 505 the layer-26 GDN input `x` already differs before its QKV,
convolution, gate and recurrent projections. At position 506, `x` and `qkv`
are identical but the convolved value `h` differs. Since `h` is produced from
`qkv` and the carried convolution history, this points to the state carried
from the preceding row as the immediate difference at position 506. The
position-505 input difference originates before layer-26 GDN; this trace does
not identify the upstream layer or owner operation that first changed it.
Persistent state between the two rows was not captured by this intermediate
format, so this is a field-level localization rather than a complete state
transition proof.

Other fields confirm the propagation. At position 505, all 10,240 QKV values,
10,239/10,240 `h`, all gate/beta/z/y/GDN output values and both MLP vectors
differ. At position 506, gate, beta and z match, while 6,143/6,144 `y` values
and all 2,560 downstream vectors differ. Full counts, hashes and relative-L2
values are in `intermediate-analysis.json`; the raw intermediate capture is
`run/verify-gdn.bin`.

The local CUDA engine rebuilt successfully. Seven focused CTests covering
accepted windows, GDN recurrence, verifier and speculative parity passed.
maestro1 HIP rebuilt `src/core/verify.cpp`, linked and passed `strata --help`;
SYCL's separate verifier overlay had no source change and its CLI check passed.
These are x86 compile/CLI checks only. No accelerator execution was performed
on maestro1.

The layer-26 trace was built on Orin with its exact source build; run the
supervised service and analyzer from the repository root:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
    --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/supervisor \
    --timeout 1200 --interval 1 --sample-clocks -- \
    python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/run_one.py \
      --adapt-every 4 --adapt-swaps 8 --capture-verify-gdn-layer 26 \
      --verify-gdn-positions 505,506 \
      --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/run

python3 bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/compare_layer26_gdn_intermediates.py \
  --run bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/run \
  --positions 505 506 \
  --output bench/results/2026-10-20-phase5-coder-adaptive-all-layer-position-trace/layer26-gdn-prompt-tail-dispatch/gdn-intermediate-adaptive/intermediate-analysis.json
```

Phase 5 remains open.
