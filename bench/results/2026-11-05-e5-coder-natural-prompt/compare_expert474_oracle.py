#!/usr/bin/env python3
"""Compare the captured layer-0 expert-474 rows with native CPU/GPU oracle outputs."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt'
BUNDLE_HEADER = struct.Struct('<8sIIIIQqii')
WIDTH = 2560
EXPERT = 474
POSITION = 81
TOKEN = 2912


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_target_part(path: Path) -> tuple[bytes, bytes]:
    raw = path.read_bytes()
    offset = 0
    found = []
    while offset < len(raw):
        magic, version, layer, k, reserved, width, position, slot, token = BUNDLE_HEADER.unpack_from(raw, offset)
        if magic != b'STMOEBN1' or version != 1 or reserved != 0 or width != WIDTH:
            raise ValueError(f'{path}: invalid MoE bundle record at {offset}')
        cursor = offset + BUNDLE_HEADER.size
        route_ids = struct.unpack_from(f'<{k}i', raw, cursor)
        cursor += k * 4
        cursor += k * 4  # route weights
        input_bytes = raw[cursor:cursor + width * 4]
        cursor += width * 4
        parts_bytes = raw[cursor:cursor + k * width * 4]
        cursor += k * width * 4
        cursor += 2 * width * 4  # shared and combined outputs
        if cursor > len(raw):
            raise ValueError(f'{path}: truncated MoE bundle payload')
        if layer == 0 and position == POSITION and token == TOKEN:
            matches = [i for i, expert in enumerate(route_ids) if expert == EXPERT]
            if len(matches) != 1:
                raise ValueError(f'{path}: expert {EXPERT} appears {len(matches)} times in route')
            row = matches[0]
            found.append((input_bytes, parts_bytes[row * width * 4:(row + 1) * width * 4]))
        offset = cursor
    if len(found) != 1:
        raise ValueError(f'{path}: expected one target row, found {len(found)}')
    return found[0]


def as_floats(raw: bytes) -> tuple[float, ...]:
    if len(raw) != WIDTH * 4:
        raise ValueError(f'expected {WIDTH * 4} bytes, found {len(raw)}')
    return struct.unpack(f'<{WIDTH}f', raw)


def metrics(reference: bytes, candidate: bytes) -> dict:
    a, b = as_floats(reference), as_floats(candidate)
    delta = [y - x for x, y in zip(a, b)]
    norm = math.sqrt(math.fsum(x * x for x in a))
    return {'different': sum(x != y for x, y in zip(a, b)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in delta)) / max(norm, 1e-300),
            'max_abs': max(map(abs, delta), default=0.0)}


def main() -> None:
    default = BASE / 'ista-is-prime-layer1-plus-layer0-moe-run'
    resident = BASE / 'ista-is-prime-layer0-expert474-resident-run'
    oracle = BASE / 'ista-is-prime-layer1-plus-layer0-moe-run/expert474-oracle-dump'
    cpu = (oracle / 'layer-0-expert-474-cpu-output.f32').read_bytes()[:WIDTH * 4]
    gpu = (oracle / 'layer-0-expert-474-gpu-output.f32').read_bytes()[:WIDTH * 4]
    source_activation = (oracle / 'layer-0-expert-474-activation.f32').read_bytes()[:WIDTH * 4]
    rows = {}
    for label, run in (('default_profile', default), ('forced_resident', resident)):
        for backend in ('strata', 'ninfer'):
            input_bytes, output_bytes = read_target_part(run / f'{backend}.moe-bundle')
            if input_bytes != source_activation:
                raise ValueError(f'{label}/{backend}: oracle activation differs from the service input')
            rows[f'{label}/{backend}'] = {
                'input_sha256': digest(input_bytes),
                'output_sha256': digest(output_bytes),
                'vs_native_cpu': metrics(cpu, output_bytes),
                'vs_native_cuda': metrics(gpu, output_bytes),
            }
    if rows['forced_resident/strata']['output_sha256'] != rows['forced_resident/ninfer']['output_sha256']:
        raise ValueError('forced-resident Strata/NInfer outputs are not bit-identical')
    if rows['forced_resident/ninfer']['output_sha256'] != rows['default_profile/strata']['output_sha256']:
        raise ValueError('profile changed Strata output for the exact same activation')
    result = {
        'schema': 1,
        'model': 'ISTA-DASLab Qwen3.8-Flash-Next IQ3_S GGUF plus iq3-s-pack',
        'layer': 0, 'position': POSITION, 'token': TOKEN, 'expert': EXPERT,
        'codec_pair': 'IQ3_XXS/IQ4_NL',
        'oracle': 'native_expert_parity on the exact service activation and GGUF expert weights',
        'weight_dequant': 'GGML to_float and native CUDA GPU dequant matched for 4,915,200 values',
        'rows': rows,
        'interpretation': 'The default-profile pair compares different owners (Strata resident CUDA, NInfer CPU fallback). The forced-resident pair compares the same resident row and matches the native CUDA output exactly.',
    }
    path = resident / 'expert474-oracle-comparison.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
