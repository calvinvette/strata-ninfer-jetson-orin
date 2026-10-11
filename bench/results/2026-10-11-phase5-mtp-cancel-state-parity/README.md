# Excluded MTP cancellation-state attempt

This attempt did not reach cancellation and is retained as a failed setup. The
512/64 prompt ended naturally after 11 generated tokens (6/12 MTP drafts
accepted), before the client reached its eight-delta cutoff. The harness then
waited for a cancellation marker that could not arrive and was stopped by the
supervisor. No persistent-state comparison was made. The replacement uses the
prepared 2,048/128 workload and now fails immediately if a stream finishes
before the requested cancellation point.
