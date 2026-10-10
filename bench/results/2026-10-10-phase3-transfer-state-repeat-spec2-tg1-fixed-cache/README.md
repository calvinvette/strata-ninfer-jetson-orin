# One-token MTP-off fixed-cache repeat — Orin — 2026-10-10

This repeats two mapped 512-token/one-output requests with `spec2`, MTP disabled,
and an explicit `--expert-cache 5000`. Both processes selected 6,519 actual
slots, had 369 cache hits, and recorded identical GDN prefill fingerprints.
After the one generated token, token IDs and all nine persistent-state
fingerprints matched exactly. Minimum available physical memory was
10,208,477,184 bytes (9.51 GiB), above the six-GiB supervisor floor.

This is the fixed-residency counterpart to the [auto-cache one-token failure](../2026-10-10-phase3-transfer-state-repeat-spec2-tg1/README.md),
where actual capacity varied from 5,602 to 5,634 slots, cache hits were 345 and
346, and state differed after the same output token despite identical prefill
fingerprints. The contrast strongly implicates changing expert residency in the
failed repeat; it does not establish a general causal result across cache sizes.
The full fixed-cache records are in `experiment/`.
