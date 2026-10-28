# E6 160K ordinary-path GDN-layer fingerprints

## Outcome

This is a third no-capture paired 160K Q2_0 retrieval, with only end-of-request
per-GDN-ordinal raw-byte fingerprints added. Both backends produced identical
token IDs, the exact 47-token answer, and identical residency. Final persistent
state still differs in `gdn`, `tail`, `pooled`, `pooled_full`, and `kv`; `L`,
`ple`, `dead`, and `ple_prev` match. The harness correctly reports a state
parity failure.

The GDN fingerprint covers 36 GDN state ordinals. Ordinal 0 is identical
between backends and across the two runs for which per-ordinal hashes are
available. Ordinal 1 is the first differing ordinal between backends; ordinals
1 through 35 differ. Comparing per-ordinal hashes across the two runs shows
that, for each backend, ordinal 0 stays identical while all 35 remaining
ordinals change. This localizes the observed run-to-run byte variation to GDN
state beginning at ordinal 1, but hashes cannot quantify the numerical delta
or reveal why it changes. It also shows why the earlier captured layer-8 split
is not a stable earliest divergence. This does not yet identify a code defect
or justify a backend change.

| Check | Result |
|---|---|
| Prompt tokens | 163,840 |
| Generated tokens | 47 per arm |
| Token IDs / answer | Equal; exact expected answer |
| Residency fingerprint | Equal |
| Final state | Different in `gdn`, `tail`, `pooled`, `pooled_full`, `kv` |
| GDN ordinals | 36 total; ordinal 0 equal; first difference at ordinal 1 |
| Pair runtime | 54.06 minutes |
| Minimum available memory | 6.72 GiB |
| Peak swap | 0.73 GiB |
| Sampled OOM kills | 0 |

The prompt content SHA256 is
`8377a1053405efb5ca733be15d3e3a70d7586195a88c1db8b4655d6375a7cd94`; the
prompt token-ID SHA256 is
`6d38b36ee0a8a2c33930db06c0db110cb510b446738640bf26891808990fc302`. The
binary and model/config identities are the same as the [first minimal
control](../minimal-paired-control/README.md). Hash computation occurs after
generation and adds no per-token diagnostic captures. Raw logs and telemetry
remain local-only. This is a correctness diagnostic, not a performance result.
