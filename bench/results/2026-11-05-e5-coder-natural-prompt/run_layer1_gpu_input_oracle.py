"""Check all layer-1 GPU expert rows on the two captured service inputs."""
from __future__ import annotations

import array
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path.insert(0, str(ROOT))
from tools.integration.compare_moe_bundle import read_bundle

CAPTURE = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/moe-cpu-owner-pos41'
MODEL = Path('/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
NATIVE_ORACLE = ROOT / 'build/integration/e0-cuda-build/native_expert_parity'
NINFER_ORACLE = ROOT / 'build/integration/e0-cuda-build/ninfer_iq_expert_parity'
LAYER, POSITION, HIDDEN = 1, 41, 2560


def read_f32(path: Path) -> tuple[float, ...]:
    values = array.array('f')
    with path.open('rb') as stream:
        values.fromfile(stream, path.stat().st_size // 4)
    return tuple(values)


def metrics(a: tuple[float, ...], b: tuple[float, ...]) -> dict:
    delta = [float(y) - float(x) for x, y in zip(a, b)]
    return {
        'count': len(a), 'different': sum(x != y for x, y in zip(a, b)),
        'relative_l2': math.sqrt(math.fsum(d * d for d in delta) /
                                 max(math.fsum(float(x) * float(x) for x in a), 1e-300)),
        'max_abs': max((abs(d) for d in delta), default=0.0),
    }


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    bundles = {backend: read_bundle(CAPTURE / f'{backend}.moe-bundle')[(LAYER, POSITION)][1]
               for backend in ('strata', 'ninfer')}
    ids = tuple(bundles['strata']['route_ids'])
    if ids != tuple(bundles['ninfer']['route_ids']):
        raise SystemExit('service routes changed; cannot compare captured experts')
    rows = []
    for rank, expert in enumerate(ids):
        native_outputs = {}
        row = {'route_rank': rank, 'expert': expert, 'backends': {}}
        for backend in ('strata', 'ninfer'):
            bundle = bundles[backend]
            activation = output / f'{backend}-input-{expert}.f32'
            with activation.open('wb') as stream:
                array.array('f', bundle['input']).tofile(stream)
            dump_dir = output / f'tmp-{backend}-{expert}'
            dump_dir.mkdir()
            native_log = subprocess.run(
                [str(NATIVE_ORACLE), str(MODEL), '--expert', str(expert), '--activation-f32',
                 str(activation), '--dump-f32-dir', str(dump_dir), str(LAYER)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False)
            if native_log.returncode:
                raise SystemExit(f'native oracle failed for {backend} expert {expert}: {native_log.stdout}')
            gpu_path = dump_dir / f'layer-{LAYER}-expert-{expert}-gpu-output.f32'
            native_output = read_f32(gpu_path)
            native_outputs[backend] = native_output
            service_output = tuple(bundle['expert_parts'][rank * HIDDEN:(rank + 1) * HIDDEN])
            ninf_log = subprocess.run(
                [str(NINFER_ORACLE), str(MODEL), str(LAYER), str(expert), str(activation)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                check=False)
            if ninf_log.returncode:
                raise SystemExit(f'NInfer oracle failed for {backend} expert {expert}: {ninf_log.stdout}')
            row['backends'][backend] = {
                'service_output_vs_strata_gpu_oracle': metrics(service_output, native_output),
                'ninfer_vs_strata_same_input_oracle': ninf_log.stdout.strip().splitlines(),
            }
            shutil.rmtree(dump_dir)
            activation.unlink()
        row['strata_input_vs_ninfer_input_gpu_output'] = metrics(
            native_outputs['strata'], native_outputs['ninfer'])
        rows.append(row)
    result = {
        'layer': LAYER, 'position': POSITION, 'token_id': 271,
        'route_ids': ids, 'owner_kind': 'primary VRAM/foresight (0) for all ten rows',
        'profile': 'same 391-slot runtime cache; 256-slot CLI request was raised by memory sizing',
        'rows': rows,
    }
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
