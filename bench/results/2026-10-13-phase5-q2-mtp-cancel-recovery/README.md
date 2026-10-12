# Q2_0 MTP cancellation, state parity and recovery — Orin — 2026-10-12

This Phase 5 run canceled an MTP-enabled Q2_0 stream after the first visible
text delta, then compared the committed state against three fresh exact-prefix
references and checked recovery on the same service. All runs used a fixed
3,000-slot expert cache, the Q2_0 MTP runtime pack, state hashing and accepted-
prefix tracing. The supervisor used a 28-GiB scope and the six-GiB availability
floor.

The canceled request exposed `1` after committing three tokens. Its accepted
prefixes were `L=48` and `L=50`; the second contained one accepted MTP draft.
The same service returned exactly `Hello Orin!` and remained alive. All three
fresh references matched the canceled token IDs and all eleven persistent-state
fields at both lengths. The references also matched one another.

| Check | Result |
| --- | --- |
| Stream cancellation | Pass; 1 visible delta, 3 committed tokens |
| Same-service recovery | Pass; exact `Hello Orin!`, service alive |
| Fresh exact-prefix references | 3/3 pass at `L=48` and `L=50` |

The supervised run took 120.19 seconds. Minimum host availability was 15.341
GiB and minimum effective admission headroom was 12.514 GiB, above the six-GiB
guard. No OOM kill occurred. Clocks were observed without control; EMC sampling
was denied; energy was not measured. This is one short integer-list cancellation
cell for Q2_0 with a fixed cache, not broad termination or quality qualification.
The exact command, configs, engine logs, state traces, and telemetry are retained
in `run/` and `supervisor/`.

Reproduce from the repository root with:

```sh
systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes \
  python3 tools/integration/run_control.py \
  --output bench/results/2026-10-13-phase5-q2-mtp-cancel-recovery/supervisor \
  --timeout 5400 --interval 1 --sample-clocks -- \
  python3 tools/integration/mtp_cancel_state_parity.py \
  --config bench/results/2026-10-13-phase5-q2-accepted-prefix/server-config-with-mtp.json \
  --output bench/results/2026-10-13-phase5-q2-mtp-cancel-recovery/run \
  --cancel-chunks 1 --reference-repeats 3 --fixed-expert-cache 3000
```

The instrumented requested-allocation ledger balanced 311 allocations and 310
frees in the canceled process and in each of the three references. At log end,
the only requested-live allocation in each process was the 1,485,606,400-byte
service-lifetime weight arena; observed host staging had returned to zero. This
is ownership evidence for instrumented allocation sites, not total physical
backing or graph-pool accounting.
