# Failed diagnostic validation: continuation count

This adaptive arm completed four same-service short requests and captured
position 512. The trace writer produced valid activation ownership metadata,
including GPU-only rows with an empty activation vector, and the GDN-state hook
captured four records as requested. The harness then failed because its
expected capture count included the three base requests but omitted the
configured fourth continuation. The delayed arm was not launched, so this is
not a paired result and carries no correctness comparison.

The failed data and supervisor logs are retained. `run_one.py` now includes
configured continuations in verifier-route, input, GDN-state, and boundary
capture count checks. A retry will retain all four rows in the CPU-pool trace
and exercise the fixed validation.
