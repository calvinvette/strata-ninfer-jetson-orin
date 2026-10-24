#!/usr/bin/env python3
"""Compare host SiLU/quantization candidates against captured CUDA Q8_1 stages.

The input files are binary float32 gate/up rows and CUDA's packed Q8_1 hidden
row (36 bytes per 32 values). This is a diagnostic, not a production CPU path.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import math
import platform
import struct
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def q8_row(values):
    result = bytearray()
    for begin in range(0, len(values), 32):
        row = values[begin:begin + 32]
        amax = max(abs(x) for x in row)
        d = f32(amax / 127.0)
        lane_sum = list(row)
        for offset in (16, 8, 4, 2, 1):
            prior = lane_sum[:]
            for lane in range(32):
                lane_sum[lane] = f32(prior[lane] + prior[lane ^ offset])
        q = []
        for x in row:
            rounded = math.floor(f32(x / d) + 0.5) if x >= 0 else math.ceil(f32(x / d) - 0.5)
            q.append(max(-127, min(127, rounded)) & 0xff if amax else 0)
        result += struct.pack("<e", d) + struct.pack("<e", lane_sum[0]) + bytes(q)
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gate", required=True, type=Path)
    parser.add_argument("--up", required=True, type=Path)
    parser.add_argument("--cuda-hidden-q8", required=True, type=Path)
    parser.add_argument("--cuda-hidden-f32", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    gate_raw, up_raw = args.gate.read_bytes(), args.up.read_bytes()
    if len(gate_raw) != len(up_raw) or len(gate_raw) % 4:
        raise SystemExit("gate/up must contain equal float32 arrays")
    gate = struct.unpack(f"<{len(gate_raw) // 4}f", gate_raw)
    up = struct.unpack(f"<{len(up_raw) // 4}f", up_raw)
    if not gate or len(gate) % 32:
        raise SystemExit("gate/up row count must be a nonzero multiple of 32")
    cuda_q8 = args.cuda_hidden_q8.read_bytes()
    if len(cuda_q8) != (len(gate) // 32) * 36:
        raise SystemExit("CUDA Q8_1 input must contain 36 bytes per 32-value block")
    cuda_h = struct.unpack(f"<{len(gate)}f", args.cuda_hidden_f32.read_bytes())

    libm_name = ctypes.util.find_library("m")
    libm = ctypes.CDLL(libm_name) if libm_name else ctypes.CDLL(None)
    expf, exp2f = libm.expf, libm.exp2f
    for fn in (expf, exp2f):
        fn.argtypes, fn.restype = [ctypes.c_float], ctypes.c_float

    variants = {}
    log2e = f32(1.4426950408889634)
    for name, exp_fn in (("libm_expf", expf), ("host_exp2f_log2e", exp2f)):
        hidden = []
        for g, u in zip(gate, up):
            neg = f32(-g)
            e = exp_fn(ctypes.c_float(neg if name == "libm_expf" else f32(neg * log2e)))
            hidden.append(f32(f32(g / f32(1.0 + e)) * u))
        packed = q8_row(hidden)
        diffs = [i for i in range(len(cuda_q8) // 36)
                 if packed[i * 36:(i + 1) * 36] != cuda_q8[i * 36:(i + 1) * 36]]
        float_delta = [a - b for a, b in zip(hidden, cuda_h)]
        fields = {"d_scale_blocks": 0, "sum_blocks": 0, "code_blocks": 0}
        for block in range(len(cuda_q8) // 36):
            a, b = packed[block * 36:(block + 1) * 36], cuda_q8[block * 36:(block + 1) * 36]
            fields["d_scale_blocks"] += a[:2] != b[:2]
            fields["sum_blocks"] += a[2:4] != b[2:4]
            fields["code_blocks"] += a[4:] != b[4:]
        variants[name] = {
            "different_cuda_hidden_f32_values": sum(a != b for a, b in zip(hidden, cuda_h)),
            "max_abs_hidden_f32_delta": max(map(abs, float_delta)),
            "relative_l2_hidden_f32_delta": math.sqrt(
                sum(x * x for x in float_delta) / (sum(x * x for x in cuda_h) + 1e-300)),
            "different_q8_1_blocks": diffs,
            "q8_1_field_block_mismatches": fields,
            "packed_q8_1_sha256": hashlib.sha256(packed).hexdigest(),
        }

    result = {
        "scope": "captured single layer/expert activation; diagnostic candidates only",
        "python": platform.python_version(),
        "libm": f"{libm_name or 'process C math library'} expf/exp2f",
        "files": {name: {"path": str(path), "sha256": sha256(path)} for name, path in (
            ("gate", args.gate), ("up", args.up), ("cuda_hidden_q8", args.cuda_hidden_q8),
            ("cuda_hidden_f32", args.cuda_hidden_f32))},
        "values": len(gate),
        "variants": variants,
        "limits": [
            "A host libm exp2f result is not the CUDA __expf implementation.",
            "One activation cannot establish parity or quality across prompts, layers, compilers or backends.",
            "The script does not change a serving path or recommend a default."
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
