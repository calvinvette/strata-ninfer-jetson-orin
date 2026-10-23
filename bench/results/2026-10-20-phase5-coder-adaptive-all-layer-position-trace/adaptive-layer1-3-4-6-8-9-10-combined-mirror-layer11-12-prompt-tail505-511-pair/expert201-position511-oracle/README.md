# Expert-201 position-511 service join — rejected cell

The native expert harness can evaluate expert 201 on the captured layer-11
activation at position 511, but the initial and recovery route at that position
does not contain expert 201. `compare_layer25_owner_output_oracle.py` therefore
rejects the attempted service-row join with “expert 201 is not routed at this
layer/position.” The raw native output files are retained, but this probe is
not evidence about a migrated service row and is excluded from the layer-11
report conclusions. The valid expert-201 service join is position 505.
