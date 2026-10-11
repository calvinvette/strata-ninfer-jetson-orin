# Rejected configuration attempt

The first launch paired the Q2_0 model shards with the IQ1_M packed expert
files. The engine rejected that geometry before readiness with
`FileExpertSource: the requested geometry does not match the loaded expert
layout`; no request or graph measurement was made. The supervisor observed
26,005,667,840 bytes minimum host availability, well above its six-GiB floor.
The attempt is retained as a configuration failure, excluded from the Q2_0
result, and superseded by the `q2-ple-pack` configuration in the parent folder.
