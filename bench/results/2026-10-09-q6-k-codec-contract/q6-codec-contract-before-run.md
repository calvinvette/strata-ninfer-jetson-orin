## Q6_K materialization contract, declared before diagnostic execution

The existing Q6_K scalar and CUDA F32/BF16/FP16 decoders are the next diagnostic,
selected from the pinned request profile's materialization cost. A block has
256 values in210 bytes: low fields128 bytes, high fields64, signed int8 subscales16,
and little-endian FP16 global scale at208. Each consecutive16-value group shares
a subscale; ideal value is `global_scale * subscale[group] * signed_quant` with
signed quants−32..31. Logical fixtures are independently encoded into the
mandated field locations; expected values use the retained logical arrays,
never a production decoder or a second transcription of its unpack loops.

The criterion is exact represented F32 bits and nearest-even BF16/FP16 bits,
plus unchanged packed input and output guards. A finite half significand has
11 bits; a127 subscale has7 and a31 quant has5, so products need at most23
significant bits and fit exactly in F32. Power-of-two extrema−128/−32 change
exponents without increasing that bound. Half conversion is checked by adjacent
represented-value distance, including the IEEE65520 overflow threshold. Some
synthetic scales deliberately overflow FP16; matching signed infinity is then
required, not classified as model-quality qualification. Nonfinite input scales
are excluded. BF16/F32 remain finite for all admitted fixture values.

Coverage is all63,488 finite half bit patterns with signed subscale edges, all256
signed subscale values × all64 quant codes in a separate fixture, rows1/3 with
row0=2, columns256/512/768/2560/6144/10240, and a full synthetic10240×2560 GDN
matrix with row0=1. Tests use a nondefault stream and explicit completion.
Packing/rounding known-value anchors precede execution. Other codecs, real
model payloads, invalid shapes, NInfer conversion, speed and persistent state
remain outside this diagnostic. The original test arithmetic is shared with
IQ4_NL through a private test header, not through production codec helpers.
