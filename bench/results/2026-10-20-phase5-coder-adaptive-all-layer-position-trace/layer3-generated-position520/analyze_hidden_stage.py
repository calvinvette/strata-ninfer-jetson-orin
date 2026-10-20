#!/usr/bin/env python3
"""Compare retained CPU/GPU pre-quantized SwiGLU and Q8_1 stage captures."""

import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "operator-checks" / "expert182-q8_1-mirror"
DEFAULT = ROOT / "stage-detail"
UNFUSED = ROOT / "stage-detail-parts"


def read_f32(path: Path) -> tuple[float, ...]:
    data = path.read_bytes()
    if len(data) % 4:
        raise ValueError(f"{path}: f32 byte count is not divisible by four")
    return struct.unpack(f"<{len(data) // 4}f", data)


def compare_float_stage(name: str) -> dict[str, float | int]:
    cpu = read_f32(UNFUSED / f"layer-3-expert-182--cpu-{name}.f32")
    gpu = read_f32(UNFUSED / f"layer-3-expert-182--gpu-{name}.f32")
    if len(cpu) != 3 * 640 or len(gpu) != len(cpu):
        raise ValueError(f"{name}: expected three 640-value rows; got CPU={len(cpu)} GPU={len(gpu)}")
    delta = [a - b for a, b in zip(cpu, gpu)]
    return {
        "different_values": sum(a != b for a, b in zip(cpu, gpu)),
        "values": len(cpu),
        "relative_l2_cpu_vs_gpu": math.sqrt(sum(x * x for x in delta) / (sum(x * x for x in gpu) + 1e-300)),
        "max_absolute_difference": max(abs(x) for x in delta),
        "cpu_rows_repeat_bitwise": cpu[:640] == cpu[640:1280] == cpu[1280:],
        "gpu_rows_repeat_bitwise": gpu[:640] == gpu[640:1280] == gpu[1280:],
    }


def relative_l2(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / (sum(y * y for y in b) + 1e-300))


def dot_oracle(part: str) -> dict[str, float | int]:
    weights = read_f32(UNFUSED / f"layer-3-expert-182-{part}.f32")
    cpu_output = read_f32(UNFUSED / f"layer-3-expert-182--cpu-{part}.f32")
    gpu_output = read_f32(UNFUSED / f"layer-3-expert-182--gpu-{part}.f32")
    if len(weights) != 640 * 2560 or len(cpu_output) != 3 * 640 or len(gpu_output) != len(cpu_output):
        raise ValueError(f"{part}: unexpected weight/output shapes")

    def decode_activation(path: Path) -> tuple[list[float], bytes]:
        raw = path.read_bytes()[:80 * 36]
        if len(raw) != 80 * 36:
            raise ValueError(f"{path}: expected one Q8_1 row")
        values: list[float] = []
        codes = bytearray()
        for offset in range(0, len(raw), 36):
            scale = struct.unpack_from("<e", raw, offset)[0]
            block_codes = raw[offset + 4:offset + 36]
            values.extend(scale * q for q in struct.unpack("<32b", block_codes))
            codes.extend(block_codes)
        return values, bytes(codes)

    cpu_act, cpu_codes = decode_activation(UNFUSED / "layer-3-expert-182--cpu-activation.q8_1")
    gpu_act, gpu_codes = decode_activation(UNFUSED / "layer-3-expert-182--gpu-activation.q8_1")
    oracle = tuple(sum(float(weights[row * 2560 + col]) * cpu_act[col] for col in range(2560))
                   for row in range(640))
    cpu = cpu_output[:640]
    gpu = gpu_output[:640]
    return {
        "oracle": "FP64 sum of GGML-decoded FP32 IQ2_S weights times exact Q8_1 scale/code values",
        "cpu_vs_oracle_relative_l2": relative_l2(cpu, oracle),
        "gpu_vs_oracle_relative_l2": relative_l2(gpu, oracle),
        "cpu_gpu_activation_codes_identical": cpu_codes == gpu_codes,
        "cpu_gpu_activation_code_bytes_different": sum(a != b for a, b in zip(cpu_codes, gpu_codes)),
        "cpu_vs_gpu_relative_l2": relative_l2(cpu, gpu),
    }

cpu_q = (UNFUSED / "layer-3-expert-182--cpu-hidden.q8_1").read_bytes()
gpu_q = (UNFUSED / "layer-3-expert-182--gpu-hidden.q8_1").read_bytes()
fused_gpu_q = (DEFAULT / "layer-3-expert-182--gpu-hidden.q8_1").read_bytes()
if len(cpu_q) != 3 * 20 * 36 or len(gpu_q) != len(cpu_q) or len(fused_gpu_q) != len(gpu_q):
    raise ValueError("expected three 640-value Q8_1 rows")

blocks = len(cpu_q) // 36
result = {
    "scope": "captured expert 182 layer-3 gate/up projections, pre-quantized SwiGLU rows and Q8_1 blocks",
    "rows": 3,
    "values_per_row": 640,
    "cpu_packed_gate_up_reconstruction_matches_native_hidden":
        "0/1920 words differ" in (UNFUSED / "native-expert-parity.txt").read_text(),
    "float_stages": {
        "gate": compare_float_stage("gate"),
        "up": compare_float_stage("up"),
        "pre_quantized_hidden": compare_float_stage("hidden"),
    },
    "independent_q8_1_dot_oracle": {
        "gate": dot_oracle("gate"),
        "up": dot_oracle("up"),
    },
    "cpu_gpu_q8_1_blocks_differ": sum(cpu_q[i:i + 36] != gpu_q[i:i + 36] for i in range(0, len(cpu_q), 36)),
    "q8_1_blocks": blocks,
    "cpu_gpu_q8_1_byte_differences": {
        "d_scale": sum(a != b for i, (a, b) in enumerate(zip(cpu_q, gpu_q)) if i % 36 < 2),
        "stored_sum": sum(a != b for i, (a, b) in enumerate(zip(cpu_q, gpu_q)) if 2 <= i % 36 < 4),
        "codes": sum(a != b for i, (a, b) in enumerate(zip(cpu_q, gpu_q)) if i % 36 >= 4),
    },
    "grouped_v1_gpu_q8_1_matches_default_fused_gpu_q8_1": gpu_q == fused_gpu_q,
}
print(json.dumps(result, indent=2) + "\n", end="")
