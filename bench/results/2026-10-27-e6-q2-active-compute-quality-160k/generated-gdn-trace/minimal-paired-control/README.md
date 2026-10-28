# E6 160K minimal paired control

## Outcome

This is the ordinary staged Strata-versus-strict-NInfer comparison for the
held-out Q2_0 retrieval workload, with no optional diagnostic captures. The
prompt was 163,840 tokens. Both arms generated the same 47 token IDs, returned
the exact expected retrieval/arithmetic answer, and had identical expert
residency. The final state was not equal: `gdn`, `tail`, `pooled`,
`pooled_full`, and `kv` differed. `L`, `ple`, `dead`, and `ple_prev` matched.
The harness therefore correctly reports failure; matching text is not state
parity or release qualification.

This confirms the long-context persistent-state mismatch also occurs on the
ordinary path without diagnostic sidecars. It separates the underlying mismatch
from the additional run/capture sensitivity seen in localization experiments,
but a single pair does not establish repeatability or locate its source. The
two backends' exact answers and token IDs also do not demonstrate equivalent
internal state.

The supervisor sampled 3,057 records over 53.95 minutes. Minimum available
memory was 6.64 GiB, peak swap 4.55 GiB, and sampled cgroup OOM-kill counters
were zero. Clocks were observed without control; energy was not measured.
Reported engine usage was 1,532,500 ms prompt time and 11,303 ms decode time for
Strata, with 47 tokens; these single diagnostic timings are not a performance
comparison.

## Identity and reproduction

The run used workload `heldout-retrieval-arithmetic-163840`, prompt content
SHA256 `8377a1053405efb5ca733be15d3e3a70d7586195a88c1db8b4655d6375a7cd94`,
prompt token-ID SHA256
`6d38b36ee0a8a2c33930db06c0db110cb510b446738640bf26891808990fc302`, the
parent E6 model/config, and Release CUDA binary SHA256
`fbd40926be198adc92de9a1b7b7b5d32b431445bef4e909c10de99e027c078e4`. No
optional captures were enabled. Raw logs, result JSON and supervisor telemetry
remain local-only. This is correctness diagnosis, not a performance result.
