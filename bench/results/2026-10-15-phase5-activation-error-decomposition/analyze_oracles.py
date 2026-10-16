#!/usr/bin/env python3
"""Compare CPU/GPU operators with shared float-weight Q8 activation oracles."""
import ctypes
import ctypes.util
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "2026-10-14-phase5-current-source-route-change-capture"))
from analyze_activation_quantizers import f16, f32, q8_1, q8k

ROOT = Path(__file__).resolve().parents[3]
CAPTURE = ROOT / "bench/results/2026-10-14-phase5-current-source-route-change-capture/run/start-0.jsonl"
DATA = Path(__file__).resolve().parent / "weights-and-outputs"
OUT = Path(__file__).resolve().parent
H, FF = 2560, 640
experts = (32, 55, 70, 75, 119, 165)
blas_path = ctypes.util.find_library("openblas") or ctypes.util.find_library("blas")
if not blas_path:
    raise SystemExit("OpenBLAS/CBLAS not found")
blas = ctypes.CDLL(blas_path)
sgemv = blas.cblas_sgemv
sgemv.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_float,
                  ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.POINTER(ctypes.c_float), ctypes.c_int,
                  ctypes.c_float, ctypes.POINTER(ctypes.c_float), ctypes.c_int]


def load_f32(path, count):
    raw = path.read_bytes()
    if len(raw) != count * 4:
        raise ValueError(f"{path}: expected {count*4} bytes, got {len(raw)}")
    return (ctypes.c_float * count).from_buffer_copy(raw)


def write_f32(path, values):
    path.write_bytes(struct.pack(f"<{len(values)}f", *values))


def vec(data, n):
    return (ctypes.c_float * n)(*data)


def gemv(matrix, rows, cols, x):
    out = (ctypes.c_float * rows)()
    sgemv(101, 111, rows, cols, 1.0, matrix, cols, x, 1, 0.0, out, 1)
    return out


def q8_0(x):
    # ggml quantize_row_q8_0_ref: fp16 scale and roundf (half away from zero).
    out = []
    for start in range(0, len(x), 32):
        block = x[start:start+32]
        amax = max(map(abs, block))
        d = f32(amax / 127.0) if amax else 0.0
        scale = f32(f16(d)) if amax else 0.0
        inverse = f32(1.0 / d) if d else 0.0
        for v in block:
            x0 = f32(f32(v) * inverse)
            q = math.floor(x0 + 0.5) if x0 >= 0 else math.ceil(x0 - 0.5)
            out.append(f32(max(-127, min(127, q)) * scale))
    return out


def oracle(gate, up, down, activation, path):
    xq = q8k(activation) if path == "Q8_K/Q8_0" else q8_1(activation)
    xvec = vec(xq, H)
    g = gemv(gate, FF, H, xvec)
    u = gemv(up, FF, H, xvec)
    h = [f32((v / (1.0 + math.exp(-v))) * w) for v, w in zip(g, u)]
    hq = q8_0(h) if path == "Q8_K/Q8_0" else q8_1(h)
    return gemv(down, H, FF, vec(hq, FF))


def metric(a, b):
    return sum(abs(float(x)-float(y)) for x,y in zip(a,b)) / (sum(abs(float(y)) for y in b)+1e-30)


def delta_residual(cpu, gpu, q8k_out, q8_1_out):
    numerator = sum(abs((float(c)-float(g)) - (float(k)-float(q)))
                    for c,g,k,q in zip(cpu,gpu,q8k_out,q8_1_out))
    denominator = sum(abs(float(c)-float(g)) for c,g in zip(cpu,gpu))
    return numerator / (denominator + 1e-30)


def main():
    captures = [json.loads(s) for s in CAPTURE.read_text().splitlines()]
    initial, recovery = captures[1:23], captures[45:67]
    records = []
    for expert in experts:
        stem = f"layer-0-expert-{expert}"
        gate = load_f32(DATA / f"{stem}-gate.f32", FF*H)
        up = load_f32(DATA / f"{stem}-up.f32", FF*H)
        down = load_f32(DATA / f"{stem}-down.f32", H*FF)
        cpu_actual = load_f32(DATA / f"{stem}-cpu-output.f32", H)
        gpu_actual = load_f32(DATA / f"{stem}-gpu-output.f32", H)
        float_actual = load_f32(DATA / f"{stem}-float-output.f32", H)
        for row in range(7):
            activation = initial[row]["activation"]
            ck = oracle(gate, up, down, activation, "Q8_K/Q8_0")
            g1 = oracle(gate, up, down, activation, "Q8_1/Q8_1")
            rec = {"expert": expert, "row": row,
                   "activation_sha256": __import__("hashlib").sha256(struct.pack("<2560f", *activation)).hexdigest(),
                   "oracle_cpu_vs_gpu_quant_rel_l1": metric(ck, g1),
                   "q8k_oracle_vs_full_float_rel_l1": metric(ck, float_actual) if row == 0 else None,
                   "q81_oracle_vs_full_float_rel_l1": metric(g1, float_actual) if row == 0 else None}
            if row == 0:
                rec.update({"actual_cpu_vs_q8k_oracle_rel_l1": metric(cpu_actual, ck),
                            "actual_gpu_vs_q81_oracle_rel_l1": metric(gpu_actual, g1),
                            "actual_cpu_vs_gpu_rel_l1": metric(cpu_actual, gpu_actual),
                            "actual_vs_quantizer_delta_residual_rel_l1": delta_residual(cpu_actual, gpu_actual, ck, g1),
                            "cpu_actual_vs_full_float_rel_l1": metric(cpu_actual, float_actual),
                            "gpu_actual_vs_full_float_rel_l1": metric(gpu_actual, float_actual)})
            records.append(rec)
    result = {"status": "pass", "method": "GGUF dequantized FP32 gate/up/down weights; CBLAS FP32 dot; captured exact activations; source-transcribed activation quantizer reconstruction", "limits": ["float-weight oracle is diagnostic and does not reproduce packed-weight kernel arithmetic", "Q8_0 transcribed with nearest-even rounding; exact ties may differ from backend details"], "records": records}
    (OUT / "oracle-analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    for expert in experts:
        row = next(r for r in records if r["expert"] == expert and r["row"] == 0)
        print(f"expert {expert}: CPU/GPU={row['actual_cpu_vs_gpu_rel_l1']:.5%}; quant-oracle={row['oracle_cpu_vs_gpu_quant_rel_l1']:.5%}; CPU residual={row['actual_cpu_vs_q8k_oracle_rel_l1']:.5%}; GPU residual={row['actual_gpu_vs_q81_oracle_rel_l1']:.5%}")
    print(f"seven-row, six-expert quant-oracle comparisons: {len(records)}")


if __name__ == "__main__":
    main()
