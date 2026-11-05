"""Compare staged mixed-codec service expert rows with an independent native CUDA oracle."""
from __future__ import annotations
import array
import hashlib
import json
import math
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
MODEL = Path('/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
ORACLE = ROOT / 'build/integration/e0-cuda-build/native_expert_parity'
HEADER = struct.Struct('<8sIIIIQq8i')
WIDTH, K, LAYER, POSITION, TOKEN = 2560, 10, 0, 2, 3


def metrics(ref: array.array, got: array.array) -> dict:
    if len(ref) != len(got):
        raise ValueError('vector lengths differ')
    sq = math.fsum((float(b) - float(a)) ** 2 for a, b in zip(ref, got))
    norm = math.sqrt(math.fsum(float(a) ** 2 for a in ref))
    return {'count': len(ref), 'different': sum(a != b for a, b in zip(ref, got)),
            'relative_l2': math.sqrt(sq) / max(norm, 1e-300),
            'max_abs': max((abs(float(b) - float(a)) for a, b in zip(ref, got)), default=0.0),
            'invalid': sum(not math.isfinite(x) for x in got)}


def record(path: Path, magic: bytes, multiplier: int):
    raw, offset, found = path.read_bytes(), 0, None
    while offset < len(raw):
        h = HEADER.unpack_from(raw, offset)
        if h[0] != magic or h[1] != 1 or h[2] != LAYER or h[5] != WIDTH:
            raise ValueError(f'{path}: invalid record at byte {offset}')
        if magic == b'STMPART1' and h[4] != multiplier:
            raise ValueError(f'{path}: unexpected K={h[4]}')
        if h[6] <= POSITION < h[6] + h[3] and h[7 + POSITION - h[6]] == TOKEN:
            row, start = POSITION - h[6], offset + HEADER.size
            n = multiplier * WIDTH
            values = array.array('f')
            values.frombytes(raw[start + row * n * 4:start + (row + 1) * n * 4])
            found = values
        offset += HEADER.size + h[3] * multiplier * WIDTH * 4
    if found is None:
        raise ValueError(f'{path}: target layer/position/token missing')
    return found


def main() -> int:
    capture, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    activations = {arm: record(capture / f'{arm}.input.stminput', b'STMOINP1', 1)
                   for arm in ('strata', 'ninfer')}
    if activations['strata'].tobytes() != activations['ninfer'].tobytes():
        raise ValueError('pre-expert service activations differ; cannot use one native oracle input')
    routes, owners = {}, {}
    for arm in ('strata', 'ninfer'):
        rows = [json.loads(line) for line in (capture / f'{arm}.owner.jsonl').read_text().splitlines() if line]
        owner = next(r for r in rows if r.get('layer') == LAYER and r.get('position') == POSITION)
        if owner['token_id'] != TOKEN:
            raise ValueError(f'{arm}: target token mismatch')
        routes[arm] = owner['ids']
        owners[arm] = owner['route_kind']
    if routes['strata'] != routes['ninfer'] or owners['strata'] != owners['ninfer']:
        raise ValueError('backend route IDs or owners differ')
    experts = routes['strata']
    if len(experts) != K:
        raise ValueError(f'expected {K} routes, got {len(experts)}')
    parts = {arm: record(capture / f'{arm}.parts.stmparts', b'STMPART1', K)
             for arm in ('strata', 'ninfer')}
    activation_path = output / 'activation.f32'
    with activation_path.open('wb') as f:
        activations['strata'].tofile(f)
    owner_names = {-1: 'CPU', 0: 'primary VRAM/foresight', 1: 'PCIe', 2: 'peer/helper GPU'}
    rows = []
    for rank, expert in enumerate(experts):
        dump_dir = output / f'tmp-{expert}'
        dump_dir.mkdir()
        cmd = [str(ORACLE), str(MODEL), '--expert', str(expert), '--activation-f32',
               str(activation_path), '--dump-f32-dir', str(dump_dir), str(LAYER)]
        run = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, check=False)
        if run.returncode:
            raise RuntimeError(f'expert {expert} oracle failed: {run.stdout}')
        gpu = array.array('f')
        gpu.frombytes((dump_dir / f'layer-{LAYER}-expert-{expert}-gpu-output.f32').read_bytes())
        a, b = parts['strata'][rank * WIDTH:(rank + 1) * WIDTH], parts['ninfer'][rank * WIDTH:(rank + 1) * WIDTH]
        rows.append({'route_rank': rank, 'expert_id': expert,
                     'owner': owner_names[owners['strata'][rank]],
                     'strata_vs_native_cuda': metrics(gpu, a),
                     'ninfer_vs_native_cuda': metrics(gpu, b),
                     'strata_vs_ninfer': metrics(a, b)})
        shutil.rmtree(dump_dir)
    counts = {name: sum(owner_names[k] == name for k in owners['strata'])
              for name in ('CPU', 'primary VRAM/foresight', 'PCIe', 'peer/helper GPU')}
    result = {'device': 'Jetson Orin AGX SM87, CUDA 12.6', 'model': 'Coder IQ1_M',
              'layer': LAYER, 'position': POSITION, 'token_id': TOKEN,
              'activation_sha256': hashlib.sha256(activations['strata'].tobytes()).hexdigest(),
              'routes': experts, 'owners': [owner_names[k] for k in owners['strata']],
              'owner_counts': counts, 'input_activation_identical': True,
              'oracle': 'native_expert_parity GGML weight decode and native CUDA grouped operator',
              'rows': rows,
              'interpretation_limit': 'The oracle verifies output arithmetic on this captured activation; it is not a performance or quality measurement.'}
    (output / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'owner_counts': counts,
                      'strata_native_max_rel_l2': max(r['strata_vs_native_cuda']['relative_l2'] for r in rows),
                      'ninfer_native_max_rel_l2': max(r['ninfer_vs_native_cuda']['relative_l2'] for r in rows),
                      'strata_ninfer_max_rel_l2': max(r['strata_vs_ninfer']['relative_l2'] for r in rows),
                      'activation_sha256': result['activation_sha256']}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
