# Q2_0 under a 10 GiB cgroup cap with a 256-slot cache request

This is the matched-cap follow-up to the 8 GiB/256-slot request. It used the
same Q2_0 native model, candidate engine, 512-token prompt, one greedy output,
4K context, no MTP, PLE mmap, 3 GiB workspace reserve and six-GiB
effective-availability supervisor, inside a 10 GiB cgroup-v2 scope.

The request passed and emitted token ID 32. Strata admitted all 256 requested
expert slots, completed a 511-token prefill, and generated one token. Minimum
effective availability was 8.45 GiB; minimum host `MemAvailable` was 21.44
GiB. Peak scope `memory.current` was 1,665,077,248 bytes (1.55 GiB). Scope
memory and host availability remain separate quantities.

Combined with the 8 GiB/256-slot failure, this shows that the lower cache
request is supported at 10 GiB while the 8 GiB scope still admits zero slots
and rejects speculative decode. This narrows the observed behavior to a
cgroup-cap difference for this exact model/configuration, without establishing
a general threshold. The separate 10 GiB/3,000-request cell admitted 296
slots; requested and actual cache slots are not interchangeable.

The engine SHA256 is
`3e1e003c2097d58591db30b60412acbd8798e5ab39ce857f1e3e2c0ebd241a5b`.
Artifact identities are in `artifact-identities.json`; model and pack remain
under `~/models/strata-orin-validation/`. Raw command, result and telemetry
are retained under `supervisor/`.

Reproduce from the repository root:

```sh
systemd-run --user --scope -p MemoryMax=10G \
  python tools/integration/run_control.py \
  --output bench/results/2026-10-11-phase3-q2-cgroup10G-cache256/supervisor \
  --timeout 1800 -- build/integration/candidate/strata \
  --pack /home/calvin/models/strata-orin-validation/q2-ple-pack \
  --native /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00001-of-00002.gguf \
  --ple-gguf /home/calvin/models/strata-orin-validation/Q2_0/Qwen3.8-Flash-Next-GSQ-RCO-Q2_0-00002-of-00002.gguf \
  --expert-profile /home/calvin/models/strata-orin-validation/q2-expert-profile.bin \
  --expert-cache 256 --prefill 512 --spec 2 --max-context 4096 \
  --mmap-experts --prompt-cache 0 --vram-reserve-mib 3072 --pcie-frac 0.55 \
  --tokens-file build/integration/workloads/pp512-tg64.tokens --max-new 1 \
  --greedy --ple-io mmap
```
