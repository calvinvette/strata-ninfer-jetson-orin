#!/usr/bin/env python3
"""Compare retained CPU/GPU pre-quantized SwiGLU and Q8_1 stage captures."""

import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "operator-checks" / "expert182-q8_1-mirror"
DEFAULT = ROOT / "stage-detail"
UNFUSED = ROOT / "stage-detail-v1"


def read_f32(path: Path) -> tuple[float, ...]:
    data = path.read_bytes()
    if len(data) % 4:
        raise ValueError(f"{path}: f32 byte count is not divisible by four")
    return struct.unpack(f"<{len(data) // 4}f", data)


cpu = read_f32(UNFUSED / "layer-3-expert-182--cpu-hidden.f32")
gpu = read_f32(UNFUSED / "layer-3-expert-182--gpu-hidden.f32")
if len(cpu) != 3 * 640 or len(gpu) != len(cpu):
    raise ValueError(f"expected three 640-value rows; got CPU={len(cpu)} GPU={len(gpu)}")
delta = [a - b for a, b in zip(cpu, gpu)]
relative_l2 = math.sqrt(sum(x * x for x in delta) / (sum(x * x for x in gpu) + 1e-300))

cpu_q = (UNFUSED / "layer-3-expert-182--cpu-hidden.q8_1").read_bytes()
gpu_q = (UNFUSED / "layer-3-expert-182--gpu-hidden.q8_1").read_bytes()
fused_gpu_q = (DEFAULT / "layer-3-expert-182--gpu-hidden.q8_1").read_bytes()
if len(cpu_q) != 3 * 20 * 36 or len(gpu_q) != len(cpu_q) or len(fused_gpu_q) != len(gpu_q):
    raise ValueError("expected three 640-value Q8_1 rows")

blocks = len(cpu_q) // 36
result = {
    "scope": "captured expert 182 layer-3 pre-quantized SwiGLU rows and Q8_1 blocks",
    "rows": 3,
    "values_per_row": 640,
    "cpu_gpu_float_values_differ": sum(a != b for a, b in zip(cpu, gpu)),
    "float_values": len(cpu),
    "relative_l2_cpu_vs_gpu": relative_l2,
    "max_absolute_float_difference": max(abs(x) for x in delta),
    "cpu_rows_repeat_bitwise": cpu[:640] == cpu[640:1280] == cpu[1280:],
    "gpu_rows_repeat_bitwise": gpu[:640] == gpu[640:1280] == gpu[1280:],
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
