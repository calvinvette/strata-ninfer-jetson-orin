# Generated positions 521–522 verifier and QSA state trace — Orin — 2026-10-20

This randomized same-service `short-short-short` pair captured positions 512,
521 and 522 for the initial, intermediate, recovery and continuation requests.
Each request used the same 512-token prompt, generated 12 tokens, and ran with
prompt cache disabled. The arms were cap-8 adaptive migration and delayed
control. The artifact was the pinned Coder IQ1_M GGUF (revision
`5348543e0147355ac9cbcb031184a3546350988e`) and PLE pack; candidate binary
SHA256 `081212f0e855640747b3d2595d8f8837df7d99a4eb778dc22b7bc7f2d6e76c9d`;
seed 20261127. Both arms ran under the 28-GiB supervisor and passed. Minimum
host/admission availability was 14.13 GiB adaptive and 14.29 GiB delayed;
sampled cgroup memory events were zero.

Generated token IDs matched across all four requests in both arms. Delayed
control had exact accepted state, GDN state and verifier inputs at all selected
positions. In adaptive mode, accepted-prefix and aggregate GDN fingerprints
first differed at zero-based indexes 10 and 11 between the initial and
intermediate requests; intermediate-to-recovery remained exact. Position 512
was bit-identical in the all-layer CUDA-side verifier MoE inputs. At position
521, verifier inputs first differed at layer 40 and then through layer 47; at
522, the first difference was layer 41 and continued through 47. Raw layer-14
GDN pre/post state was bit-identical at all three positions, and every captured
post-state hash matched the service's layer-14 fingerprint.

The per-QSA accepted-state hashes narrow the changed recurrent fingerprints to
QSA layers 43 and 47 at positions 521 and 522. The layer-39 dispatch has
identical expert IDs but changes CPU/GPU ownership for IQ2_S/IQ4_NL experts 66,
135 and 90 between the initial and intermediate requests. This owner change
precedes the first differing layer-40 input; it is a candidate boundary, not a
causal proof. A targeted layer-39 Q8_1 mirror pair is running as the next
operator-level check.

The all-layer trace records host activation validity explicitly. Selected
position 521/522 activation differences are valid; unknown host buffers are
excluded from comparisons. The pair is correctness localization only and makes
no performance claim. Raw captures, supervisor telemetry and all comparison
JSON files are retained in this directory.
