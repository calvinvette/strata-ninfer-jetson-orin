# Held-out prompt full-task check

After the seven-pair short-generation confirmation showed different output
prefixes, each prefill setting was checked on the same 1,069-token held-out
prompt with a 512-token allowance and one fresh service. Both responses ended
naturally after 315 tokens (chunk 32) and 321 tokens (chunk 128), and both
exceeded 200 words (266 and 268 words). However, both started with “A computer
processes…” rather than starting with the processor as the prompt requested.
They therefore fail the task-specific opening check; a long answer alone does
not pass the task.

This does not show a quality difference between settings: each condition has
one response, and both fail the same explicit criterion. It confirms that
neither short-prefix behavior nor the large prefill throughput gain qualifies
the settings for promotion. The seven-pair performance data remain useful for
the held-out prompt-path effect, but output parity and task completion gates
are unresolved. Minimum host/effective availability was 13.24 GiB for chunk
32 and 13.30 GiB for chunk 128 under the 28-GiB supervisor; no OOM events were
observed.

The chunk-32 first invocation ran both grid cells but stopped after its first
rubric failure, as the harness is designed to do. The chunk-128 cell was then
run independently and retained in `../quality-candidate-retest/`. An initial
chunk-32 startup lock failure from the separate performance campaign is
retained in `../attempt-01-board-lock/` and did not start a model.
