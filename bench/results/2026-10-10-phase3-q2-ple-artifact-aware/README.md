# Artifact-aware Q2_0 PLE block oracle — Orin — 2026-10-10

The earlier `ple_parity` run stopped at preflight because its reader accepted
only separated S2 key codes/scales and 32-bit-expanded BF16 values. The pinned
Q2_0 artifact stores the PLE key as native GGUF type 42 blocks and the pack
stores the PLE value as raw BF16. The oracle now validates the source GGUF
`blk.1.ple_key.weight` tensor's name, dimensions, type, bounds and payload
length; it extracts the code and scale planes by byte relayout only, accepts
raw BF16 value bits, and verifies that reassembling the Q2_0 blocks is
byte-identical to the source tensor. This only changes the diagnostic reader;
runtime dispatch and defaults are unchanged.

Source model: `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, revision
`ed59f92082b1e93c0e96d60a8b11aab089b52f09`. The two shards and generated pack
remain in `~/models/strata-orin-validation/`; see the [download and pack
record](../2026-10-10-phase3-q2-ple-test/README.md) for shard identities and
pack-generation details.

The PLE test was rebuilt for native CUDA and run under the six-GiB memory
supervisor using the Q2_0 shard and pack. It passed with 0 failures and a worst
stage relative L1 error of `1.148e-7`; all seven stages were checked for each
of three tokens. It confirmed the source and packed BF16 PLE value bytes match,
the Q2_0 key source-block round trip is byte-identical, and the native Q2_0 key
projection matches the independent S2-view projection exactly at the existing
norm input. The test uses real
PLE table rows and real layer-1 weights, but synthetic hidden state and
convolution history. It is block-level numerical evidence, not whole-model
quality or performance evidence.

The registered `ple_parity` CTest then passed (1/1). The supervised raw run,
including stdout/stderr, telemetry, minimum available memory and command, is
in `run-verified/`; CTest output is `ctest.txt`. The C++ source SHA256 is
`df07fe92e879521b4a7731ac6d0081b6e3c27861f097878b40973466d9fdda7a`.
