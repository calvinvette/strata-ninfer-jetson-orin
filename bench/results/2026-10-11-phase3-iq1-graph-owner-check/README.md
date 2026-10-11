# IQ1_M/MTP graph-owner trace baseline

This is the pre-owner-label baseline for the post-change
[rerun](../2026-10-11-phase3-iq1-graph-owner-check-rerun/README.md). The
six-GiB supervisor and all seven real-model API/cancellation/recovery scenarios
passed; minimum `MemAvailable` was 8,272,568,320 bytes (7.70 GiB).

The runtime driver probe recorded ten successful `cudaGraphInstantiate` calls,
but the integration owner trace recorded only four: three verifier window
graphs and one verifier commit graph. Six MTP captures were unlabelled. That gap
motivated explicit owner events after successful MTP graph instantiation in the
CUDA/HIP and SYCL implementations. This baseline is retained so the coverage
change can be reviewed directly; it does not measure graph memory or qualify
state parity/performance.
