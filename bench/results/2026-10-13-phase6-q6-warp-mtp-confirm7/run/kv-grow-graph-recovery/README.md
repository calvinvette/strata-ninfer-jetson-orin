# Accepted-only KV growth and captured-graph recovery

This 16K-context diagnostic extended the incident-log prompt with repeated
`x` markers to exactly 9,000 tokens, between two runs of the same 512-token
suffix. It generated eight tokens per request, used accepted-only adaptation
with swaps delayed to 100,000 tokens,
and set elastic KV initial backing and growth step to 2,048 cells. Separate
fresh MTP-off and MTP4 services used the current candidate binary. Captured
verifier graphs completed before the long request grew KV; no graph recapture
occurred during the grow/trim cycle. Model, MTP and tokenizer identities are in
the [campaign record](../accepted-only-seven-block/model-identity.json).

Both services grew from 2,048 to 10,240 KV cells during the long request, then
trimmed to 2,048 cells before the final short request. Growth gave 101 expert
cache slots to KV in MTP-off and 110 in MTP4; trim returned those slots and
refilled them from the profile. In each service, the short prompt produced the
same eight token IDs and all nine persistent-state fingerprints before and
after the long request. Cross-MTP outputs also matched for all three requests.
However, the 9,000-token request's final persistent state differed between
MTP-off and MTP4 in GDN, tail, pooled-index and KV fields even though generated
token IDs were identical. At the first shared commit boundary with a main-state
difference (four committed tokens), GDN, tail and KV fingerprints differed.
The strict state gate therefore failed; the supervisor status `fail` reflects
this numerical assertion, not an OOM or process crash. Minimum host availability
was 13.423 GiB.

The [full-context KV control](../kv-grow-graph-recovery-no-grow/trace/results.json)
repeated the identical prompts with elastic growth disabled and all 16K KV cells
resident from startup. It passed output and all nine state checks for each
request, across MTP-off/MTP4, and between the short request before and after the
long one. Its minimum host availability was 13.011 GiB, with no OOM events.

These controls localize the tested long-prompt MTP state discrepancy to the
elastic-KV configuration, while confirming short-request recovery and captured
graph reuse through actual growth and trim. The 9- and 10-slot difference in
expert-cache relinquishment is a plausible contributor because different
resident experts can use GPU or CPU arithmetic, but the experiment does not
prove that cause. No quality or performance result follows, and MTP with
elastic KV remains unqualified for this workload pending a cache-matched or
otherwise isolating follow-up.
