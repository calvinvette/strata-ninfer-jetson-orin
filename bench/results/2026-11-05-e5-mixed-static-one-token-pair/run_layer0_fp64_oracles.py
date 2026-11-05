"""Run the independent FP64/native CUDA oracle for all ten layer-0 service rows."""
from __future__ import annotations
import array
import hashlib
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
CAPTURE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/state-moe-layer0'
MODEL = Path('/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
ORACLE = ROOT / 'build/integration/e0-cuda-build/native_expert_parity'
PROFILE = Path('/tmp/e0-coder-iq1m-layer1-first-profile.bin')
LAYER, POSITION, TOKEN, HIDDEN, K = 0, 2, 3, 2560, 10
HEADER = struct.Struct('<8sIIIIQq8i')


def read_f32(path: Path) -> array.array:
    raw = path.read_bytes()
    values = array.array('f')
    values.frombytes(raw)
    if len(values) * 4 != len(raw):
        raise ValueError(f'{path}: partial float32 value')
    return values


def metrics(reference: array.array, candidate: array.array) -> dict:
    if len(reference) != len(candidate):
        raise ValueError('oracle vector length mismatch')
    deltas = [float(b) - float(a) for a, b in zip(reference, candidate)]
    norm = math.sqrt(math.fsum(float(x) ** 2 for x in reference))
    return {
        'count': len(reference),
        'different': sum(a != b for a, b in zip(reference, candidate)),
        'relative_l2': math.sqrt(math.fsum(x * x for x in deltas)) / max(norm, 1e-300),
        'max_abs': max(map(abs, deltas), default=0.0),
        'invalid_candidate': sum(not math.isfinite(x) for x in candidate),
    }


def read_input() -> tuple[array.array, str]:
    raw = (CAPTURE / 'strata.all-input.bin').read_bytes()
    offset = 0
    found = []
    while offset < len(raw):
        h = HEADER.unpack_from(raw, offset)
        if h[0] != b'STMOINP1' or h[1] != 1 or h[5] != HIDDEN:
            raise ValueError(f'invalid service input record at {offset}')
        start = offset + HEADER.size
        for row in range(h[3]):
            if h[2] == LAYER and h[6] + row == POSITION:
                if h[7 + row] != TOKEN:
                    raise ValueError('prompt token identity mismatch')
                lo = start + row * HIDDEN * 4
                found.append(raw[lo:lo + HIDDEN * 4])
        offset = start + h[3] * HIDDEN * 4
    if len(found) != 1:
        raise ValueError(f'expected one activation row, found {len(found)}')
    values = array.array('f')
    values.frombytes(found[0])
    return values, hashlib.sha256(found[0]).hexdigest()


def read_parts(backend: str) -> dict[int, list[array.array]]:
    raw = (CAPTURE / f'{backend}.layer0.parts').read_bytes()
    offset = 0
    rows: dict[int, list[array.array]] = {}
    while offset < len(raw):
        h = HEADER.unpack_from(raw, offset)
        if h[0] != b'STMPART1' or h[1] != 1 or h[2] != LAYER or h[4] != K or h[5] != HIDDEN:
            raise ValueError(f'invalid {backend} expert-parts record at {offset}')
        start = offset + HEADER.size
        for row in range(h[3]):
            pos = h[6] + row
            if pos == POSITION:
                if h[7 + row] != TOKEN:
                    raise ValueError('expert-parts token identity mismatch')
                row_values = array.array('f')
                lo = start + row * K * HIDDEN * 4
                row_values.frombytes(raw[lo:lo + K * HIDDEN * 4])
                rows[pos] = [row_values[i * HIDDEN:(i + 1) * HIDDEN] for i in range(K)]
        offset = start + h[3] * K * HIDDEN * 4
    if POSITION not in rows:
        raise ValueError(f'{backend}: no parts for position {POSITION}')
    return rows


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    owner_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None
    output.mkdir(parents=True, exist_ok=False)
    activation, activation_hash = read_input()
    route = json.loads((CAPTURE / 'strata.layer0.route').read_text().splitlines()[3])
    experts = route['ids']
    if route['layer'] != LAYER or route['position'] != POSITION or route['token_id'] != TOKEN:
        raise ValueError('route record identity mismatch')
    strata_parts = read_parts('strata')[POSITION]
    ninfer_parts = read_parts('ninfer')[POSITION]
    if owner_dir is None:
        raise ValueError('pass the output directory from run_layer0_owner_pair.py')
    owner_maps = {}
    owner_hashes = {}
    for backend in ('strata', 'ninfer'):
        owner_path = owner_dir / f'{backend}.owner.jsonl'
        owner_raw = owner_path.read_bytes()
        owner_hashes[backend] = hashlib.sha256(owner_raw).hexdigest()
        owner_lines = [json.loads(line) for line in owner_raw.decode().splitlines() if line]
        if len(owner_lines) != 2 or owner_lines[0].get('format') != 'strata-moe-dispatch-v3':
            raise ValueError(f'{backend}: malformed owner trace')
        owner_row = owner_lines[1]
        if (owner_row['layer'], owner_row['position'], owner_row['token_id']) != (LAYER, POSITION, TOKEN):
            raise ValueError(f'{backend}: owner trace does not match captured service row')
        owner_maps[backend] = dict(zip(owner_row['ids'], owner_row['route_kind']))
        if owner_row['ids'] != experts:
            raise ValueError(f'{backend}: routed expert IDs changed from the captured row')
    if owner_maps['strata'] != owner_maps['ninfer']:
        raise ValueError('Strata and NInfer owner maps differ')
    profile_bytes = PROFILE.read_bytes()
    magic, version, layers, n_experts, ranked, _ = struct.unpack_from('<4s5I', profile_bytes)
    if (magic, version, layers, n_experts) != (b'STRP', 1, 48, 256):
        raise ValueError('unexpected expert profile identity')
    profile_pairs = [struct.unpack_from('<HH', profile_bytes, 24 + i * 4)
                     for i in range(ranked)]
    cache_match = re.search(r'expert cache (\d+) slots',
                            (CAPTURE / 'strata.log').read_text(errors='replace'))
    if cache_match is None:
        raise ValueError('could not identify actual loaded cache slots')
    loaded_slots = int(cache_match.group(1))
    if len(experts) != K or any(len(row) != HIDDEN for row in strata_parts + ninfer_parts):
        raise ValueError('captured service row geometry mismatch')
    activation_path = output / 'captured-service-activation.f32'
    with activation_path.open('wb') as stream:
        activation.tofile(stream)
    rows = []
    for rank, expert in enumerate(experts):
        dump_dir = output / f'tmp-expert-{expert}'
        dump_dir.mkdir()
        cmd = [str(ORACLE), str(MODEL), '--expert', str(expert),
               '--activation-f32', str(activation_path), '--dump-f32-dir', str(dump_dir), str(LAYER)]
        run = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, check=False)
        if run.returncode:
            raise SystemExit(f'expert {expert} oracle failed ({run.returncode}):\n{run.stdout}')
        prefix = dump_dir / f'layer-{LAYER}-expert-{expert}'
        gpu = read_f32(Path(str(prefix) + '-gpu-output.f32'))
        fp64 = read_f32(Path(str(prefix) + '-float-output.f32'))
        row = {
            'route_rank': rank, 'expert_id': expert,
            'profile_rank': profile_pairs.index((LAYER, expert)),
            'resident_in_loaded_profile': profile_pairs.index((LAYER, expert)) < loaded_slots,
            'owner_kind': {-1: 'CPU', 0: 'primary VRAM/foresight', 1: 'PCIe', 2: 'peer/helper GPU'}[
                owner_maps['strata'][expert]],
            'service_strata_vs_ninfer': metrics(strata_parts[rank], ninfer_parts[rank]),
            'strata_service_vs_native_cuda': metrics(gpu, strata_parts[rank]),
            'ninfer_service_vs_native_cuda': metrics(gpu, ninfer_parts[rank]),
            'strata_service_vs_fp64': metrics(fp64, strata_parts[rank]),
            'ninfer_service_vs_fp64': metrics(fp64, ninfer_parts[rank]),
        }
        rows.append(row)
        shutil.rmtree(dump_dir)
    result = {
        'model': 'Coder IQ1_M', 'layer': LAYER, 'prompt_position': POSITION,
        'prompt_token_id': TOKEN, 'activation_sha256': activation_hash,
        'profile_sha256': hashlib.sha256(profile_bytes).hexdigest(),
        'actual_loaded_profile_slots': loaded_slots,
        'owner_trace_sha256': owner_hashes,
        'owner_maps_equal': owner_maps['strata'] == owner_maps['ninfer'],
        'routed_experts': experts,
        'owner_counts': {name: sum(row['owner_kind'] == name for row in rows)
                         for name in ('CPU', 'primary VRAM/foresight', 'PCIe', 'peer/helper GPU')},
        'independent_reference': 'native_expert_parity: GGML GGUF weight dequantization, native CUDA grouped oracle, FP64 full projection cast to float32',
        'fp64_limit': 'FP64 projection uses unquantized activation/intermediates; its delta includes Q8_1 quantization and is descriptive, not a declared tolerance',
        'rows': rows,
    }
    (output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
