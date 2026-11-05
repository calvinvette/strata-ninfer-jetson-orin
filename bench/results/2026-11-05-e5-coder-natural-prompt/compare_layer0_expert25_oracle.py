"""Compare a resident Coder service row with native CUDA and FP64 references."""
from __future__ import annotations
import array
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
CAP = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/state-moe-layer0'
ORACLE = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/layer0-expert25-oracle/dump'
PROFILE = Path('/tmp/e0-coder-iq1m-layer1-first-profile.bin')
LAYER, POSITION, TOKEN, EXPERT, RANK, CACHE_SLOTS = 0, 2, 3, 25, 3, 391
INPUT_HEADER = struct.Struct('<8sIIIIQq8i')


def f32(data: bytes) -> array.array:
    values = array.array('f')
    values.frombytes(data)
    if struct.pack('=I', 1) != struct.pack('<I', 1):
        values.byteswap()
    return values


def metrics(reference: array.array, candidate: array.array) -> dict:
    if len(reference) != len(candidate):
        raise ValueError('reference and candidate lengths differ')
    deltas = [float(b) - float(a) for a, b in zip(reference, candidate)]
    norm = math.sqrt(math.fsum(float(x) * float(x) for x in reference))
    return {'values': len(reference), 'different': sum(a != b for a, b in zip(reference, candidate)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in deltas)) / max(norm, 1e-300),
            'max_abs': max(map(abs, deltas), default=0.0),
            'invalid_candidate': sum(not math.isfinite(x) for x in candidate)}


def read_input() -> array.array:
    path = CAP / 'strata.all-input.bin'
    raw = path.read_bytes()
    offset = 0
    matches = []
    while offset < len(raw):
        h = INPUT_HEADER.unpack_from(raw, offset)
        if h[0] != b'STMOINP1' or h[1] != 1 or h[5] != 2560:
            raise ValueError(f'invalid MoE input record at byte {offset}')
        start = offset + INPUT_HEADER.size
        for row in range(h[3]):
            if h[2] == LAYER and h[6] + row == POSITION:
                if h[7 + row] != TOKEN:
                    raise ValueError('captured input token ID differs from expected token')
                lo = start + row * h[5] * 4
                matches.append(raw[lo:lo + h[5] * 4])
        offset = start + h[3] * h[5] * 4
    if len(matches) != 1:
        raise ValueError(f'expected one captured input row, found {len(matches)}')
    return f32(matches[0])


def read_parts(backend: str) -> tuple[array.array, array.array]:
    raw = (CAP / f'{backend}.layer0.parts').read_bytes()
    offset = 0
    result = {}
    while offset < len(raw):
        h = INPUT_HEADER.unpack_from(raw, offset)
        if h[0] != b'STMPART1' or h[1] != 1 or h[2] != LAYER or h[4] != 10 or h[5] != 2560:
            raise ValueError(f'invalid expert-parts record at byte {offset}')
        start = offset + INPUT_HEADER.size
        for row in range(h[3]):
            position = h[6] + row
            if position == POSITION:
                if h[7 + row] != TOKEN:
                    raise ValueError('captured expert-parts token differs')
                lo = start + row * h[4] * h[5] * 4
                values = f32(raw[lo:lo + h[4] * h[5] * 4])
                result[position] = (values[RANK * h[5]:(RANK + 1) * h[5]], h[7 + row])
        offset = start + h[3] * h[4] * h[5] * 4
    if POSITION not in result:
        raise ValueError(f'{backend}: missing expert-parts position {POSITION}')
    return result[POSITION][0], result[POSITION][1]


def read_float_file(path: Path, count: int) -> array.array:
    data = path.read_bytes()
    if len(data) != count * 4:
        raise ValueError(f'{path}: expected {count * 4} bytes, found {len(data)}')
    return f32(data)

def read_first_float_row(path: Path, width: int, rows: int = 3) -> array.array:
    data = path.read_bytes()
    if len(data) != width * rows * 4:
        raise ValueError(f'{path}: expected {width * rows * 4} bytes, found {len(data)}')
    return f32(data[:width * 4])


def main() -> None:
    activation = read_input()
    route = json.loads((CAP / 'strata.layer0.route').read_text().splitlines()[3])
    if route['layer'] != LAYER or route['position'] != POSITION or route['token_id'] != TOKEN:
        raise ValueError('route record identity mismatch')
    if route['ids'][RANK] != EXPERT:
        raise ValueError('selected route rank does not contain expert 25')
    profile = PROFILE.read_bytes()
    magic, version, layers, experts, ranked, slots = struct.unpack_from('<4s5I', profile)
    if (magic, version, layers, experts) != (b'STRP', 1, 48, 256):
        raise ValueError('profile header identity mismatch')
    pairs = [struct.unpack_from('<HH', profile, 24 + i * 4) for i in range(ranked)]
    profile_rank = pairs.index((LAYER, EXPERT))
    if profile_rank != 281 or profile_rank >= CACHE_SLOTS:
        raise ValueError(f'expert profile residency mismatch: rank={profile_rank}')
    s, s_token = read_parts('strata')
    n, n_token = read_parts('ninfer')
    if s_token != TOKEN or n_token != TOKEN:
        raise ValueError('captured part token mismatch')
    oracle_activation = read_first_float_row(ORACLE / 'layer-0-expert-25-activation.f32', 2560)
    native_cuda = read_float_file(ORACLE / 'layer-0-expert-25-gpu-output.f32', 2560)
    fp64 = read_float_file(ORACLE / 'layer-0-expert-25-float-output.f32', 2560)
    if activation != oracle_activation:
        raise ValueError('oracle did not use the exact captured service activation')
    result = {
        'model': 'Coder IQ1_M', 'layer': LAYER, 'position': POSITION, 'token_id': TOKEN,
        'expert_id': EXPERT, 'route_rank': RANK,
        'resident_profile': {'rank': profile_rank, 'loaded_slots': CACHE_SLOTS,
                             'ranked_pairs': ranked, 'profile_slots': slots,
                             'sha256': hashlib.sha256(profile).hexdigest()},
        'activation_sha256': hashlib.sha256(activation.tobytes()).hexdigest(),
        'independent_oracle': 'native_expert_parity: GGML to_float dequantization and FP64 full expert projection; native CUDA reference also emitted',
        'ggml_weight_decode': {'differing_values': 0, 'checked_values': 4915200},
        'service_ninfer_vs_strata': metrics(s, n),
        'service_ninfer_vs_native_cuda': metrics(native_cuda, n),
        'service_strata_vs_native_cuda': metrics(native_cuda, s),
        'service_ninfer_vs_fp64': metrics(fp64, n),
        'service_strata_vs_fp64': metrics(fp64, s),
        'native_cuda_vs_fp64': metrics(fp64, native_cuda),
        'interpretation': 'one captured resident expert row; FP64 reference uses unquantized activation/projection, so its delta includes activation/hidden quantization and is not a universal tolerance'
    }
    output = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/layer0-expert25-oracle/comparison.json'
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
