# E6 160K state-layer hash probe

This paired Q2_0 run used the ordinary staged Strata and strict NInfer paths,
with optional per-GDN-ordinal and per-QSA-layer fingerprints enabled. Both
requests reached the exact expected 47-token answer. The probe did not produce
a valid final comparison: enumerating every QSA layer's active KV bytes after
generation exceeded the server's 60-second no-progress watchdog, and both
engines were stopped with exit code `-6` while the post-request fingerprint was
still being collected. No QSA layer fingerprints or complete final result were
produced.

Before the expensive QSA pass, the engine emitted all 36 per-GDN-ordinal raw
byte fingerprints. Ordinal 0 matched between the two arms; ordinal 1 was the
first mismatch, and the other 34 also differed. This is a diagnostic hint only:
the overall comparison is invalidated by the watchdog, and fingerprints do
not quantify the numerical differences. The result motivated the succeeding
GDN-only probe, which completed normally.

The run took 54.59 minutes. Minimum available memory was 6.52 GiB, peak swap
was 0.73 GiB, and sampled OOM kills were zero. The QSA-layer hashing setting
is too expensive for this workload under the current watchdog and should not
be reused. Raw logs and telemetry remain local-only.
