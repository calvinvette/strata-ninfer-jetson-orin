# Historical NInfer Orin evidence

Copied from `/home/calvin/workspace/ninfer-jetson-orin` at bootstrap. These files
were local/ignored reports, not files committed at the reference source revision.
Their individual SHA256 values and origin labels are in
[`reference/ninfer-import.json`](../../reference/ninfer-import.json).

- `profiles/bench/phase8*.json`: reconstructed-initial/tuned SM87 controls,
  host-pressure samples, rail-power observations and the llama.cpp comparison.
- `profiles/bench/phase7*.json`: long-context and MTP pressure-limited attempts,
  retained alongside successful controls so failures are visible.
- `profiles/bench/jetson_orin_35b_a3b/*.json`: short/long BF16/INT8 MTP matrix,
  8K/16K/32K capacity reports and memory telemetry.
- [working-tree-plan.md](working-tree-plan.md) and
  [working-tree-plan.patch](working-tree-plan.patch): the local uncommitted plan
  and its diff against `b07248f2`. The original checkout was left unchanged.

Interpret reports using the copied [experiment ledger](../../reference/ninfer/NINFER_JETSON_ORIN_PORT_EXPERIMENTS.md)
and [port status](../../reference/ninfer/NINFER_JETSON_ORIN_PORT_STATUS.md). Absolute
paths and recorded commands refer to their historical environment. They are
evidence, not scripts to run in the new checkout. Not every historical log or
profiler capture is included; the manifest defines the imported subset.

The local plan's deferred JetPack/toolchain ideas are unverified proposals. They
do not change the initial CUDA 12.6/SM87 target or authorize an OS upgrade.
