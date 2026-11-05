# IQ3_XXS/Q2_0 mixed resident expert route

Date: 2026-11-05. Jetson Orin AGX, SM87, CUDA 12.6. The implementation
uses an IQ3_XXS gate/up D3 dot and the shared grouped Q2_0 D4 path at 2560/640.

Coder IQ1_M layer 12/expert 5 real weights dispatched once. Gate/up and all
720 hidden Q8_1 bytes matched Strata bitwise; the final output was also
bit-identical for the captured Coder activation row. That activation was
captured at another layer, so this is not a layer-12 activation oracle. See
[`ninfer-parity.log`](ninfer-parity.log).

A strict one-token Coder service request logged the new layer-12 route after
IQ2_S/Q2_0 at layer 1. It then stopped at layer 21 (IQ3_S/Q2_0), which was
still unsupported in this build. That rejection was expected for the partial
selector at the time; the completed selector later traversed the model. Minimum
available memory was 21.48 GiB and the pre-existing cgroup OOM-kill counter
stayed at one. Raw evidence: [`service-strict/`](service-strict/).

This tuple occurs at three layers in each mixed artifact. It is now implemented
and directly checked at one Coder layer; the later full strict traversal is
recorded in the [IQ4_XS closeout](../2026-11-05-e4-iq4xs-iq4nl/README.md).
No performance or quality benefit is claimed.
