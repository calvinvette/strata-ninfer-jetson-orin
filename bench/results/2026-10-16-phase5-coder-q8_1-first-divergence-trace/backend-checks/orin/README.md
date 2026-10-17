# Orin CUDA build and native-expert tests

The current diagnostic source compiled and linked into the Orin CUDA `strata`
target. The binary SHA256 is
`dfc6394251bbe2713f6039d442e290109513447a770884b58657f7e162d2ed60`; the
source file SHA256 is
`b5d6ce040144278b978ebdd9c88d71dd045ea57e7b8fbdddcfac3826177a8395`.
The build log and CLI help output are retained here.

All 16 registered `native_expert_parity` CTests passed on this binary,
including the opt-in IQ2_S/Q2_0 CPU Q8_1 route parity case. The four-arm
service pair and its actual CPU-row capture used this same binary; see
`../../README.md` for the captured-input evidence and its scope.
