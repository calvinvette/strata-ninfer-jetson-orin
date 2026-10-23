# Layer-39 service-row capture attempt — unsupported dispatch key — Orin

This supervised adaptive run used the correct layer-39 selector, but omitted
the paired campaign's explicit `--prompt-cache 0` setting. The service used
the configured prompt-cache capacity of 6, which shifted dispatch IDs: the
requested dispatch 519 contained position 518, while position 521 was
dispatch 663. `run_one.py` rejected the capture because no row matched both
the requested dispatch and position. The supervisor recorded the command exit
with minimum availability 14.08 GiB and zero memory guard events.

No service-output comparison is claimed from this attempt. The retry uses the
same zero-cache setting as the paired control and its dispatch map.
