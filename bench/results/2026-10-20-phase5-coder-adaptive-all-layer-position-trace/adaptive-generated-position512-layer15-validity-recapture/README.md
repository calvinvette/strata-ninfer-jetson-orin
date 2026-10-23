# Failed diagnostic setup: layer-15 raw GDN state requested

This cell is retained as failed. The current-source candidate initialized the
model and emitted its layer-15 GDN intermediate capture, then rejected the
requested raw GDN-state capture because layer 15 is a QSA layer, not a GDN
layer. The service exited before accepting requests, so this run provides no
correctness or performance evidence and does not test the activation-validity
change. The next run moves raw-state/GDN capture to the preceding supported
GDN layer 14 while retaining layer-15 MoE input capture.

The supervisor observed no cgroup OOM events and a 14.86 GiB minimum
host/admission availability during the startup attempt. The incomplete arm and
logs are retained; no second arm was launched.
