#!/usr/bin/env python3
"""Run native CPU/CUDA expert parity on exact layer-39 dispatch activations."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
MODEL = Path.home() / 'models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf'
PARITY = ROOT / 'build/integration/candidate/native_expert_parity'
LAYER = 39
WIDTH = 2560


def metric(left, right):
    a = struct.unpack(f'<{WIDTH}f', left)
    b = struct.unpack(f'<{WIDTH}f', right)
    diffs = [float(x) - float(y) for x, y in zip(a, b)]
    denom = math.fsum(float(y) ** 2 for y in b)
    return {
        'bitwise_equal': left == right,
        'different_values': sum(x != y for x, y in zip(a, b)),
        'max_abs': max(map(abs, diffs), default=0.0),
        'relative_l2': math.sqrt(math.fsum(x * x for x in diffs) / denom) if denom else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = args.run_dir / 'adaptive-cap8' / 'result'
    rows = [json.loads(line) for line in (result / 'all-layer-selected-positions.jsonl').read_text().splitlines()[1:]]
    meta = json.loads((args.run_dir / 'campaign.json').read_text())
    if meta.get('status') != 'pass':
        raise ValueError('paired campaign did not pass')
    summary = {
        'scope': 'same-input layer-39 IQ2_S/IQ4_NL expert oracle at captured adaptive owner changes',
        'model': meta['model_repository'], 'revision': meta['model_revision'],
        'quantization': meta['quantization'], 'binary_sha256': meta['binary_sha256'],
        'parity_binary_sha256': hashlib.sha256(PARITY.read_bytes()).hexdigest(),
        'layer': LAYER, 'width': WIDTH, 'selector': 'iq2_s/iq4_nl@layer=39',
        'positions': {},
    }
    activation_dir = args.run_dir / 'oracle-activations'
    activation_dir.mkdir(exist_ok=True)
    logs = args.run_dir / 'oracle-logs'
    logs.mkdir(exist_ok=True)
    for position in (521, 522):
        selected = [row for row in rows if row['layer'] == LAYER and row['position'] == position]
        if len(selected) != 4:
            raise ValueError(f'position {position}: expected four request rows, found {len(selected)}')
        initial, intermediate = selected[0], selected[1]
        if not initial['activation_valid'] or not intermediate['activation_valid']:
            raise ValueError(f'position {position}: CPU dispatch activation is not materialized')
        activation = struct.pack(f'<{WIDTH}f', *initial['activation'])
        other = struct.pack(f'<{WIDTH}f', *intermediate['activation'])
        if activation != other:
            raise ValueError(f'position {position}: layer-39 input differs across initial/intermediate requests')
        activation_path = activation_dir / f'activation-position-{position}.f32'
        activation_path.write_bytes(activation)
        moved = [expert for expert, before, after in zip(initial['ids'], initial['route_kind'], intermediate['route_kind'])
                 if before < 0 <= after]
        if not moved:
            raise ValueError(f'position {position}: expected CPU-to-GPU owner transitions at layer 39')
        entry = {
            'position': position, 'token_id': initial['token_id'],
            'activation_sha256': hashlib.sha256(activation).hexdigest(),
            'request_activation_bitwise_equal': True, 'moved_cpu_to_gpu_experts': moved,
            'experts': {},
        }
        for expert in moved:
            expert_result = {}
            for mode in ('default', 'q8_1'):
                work = Path(tempfile.mkdtemp(prefix=f'strata-l39-{position}-{expert}-{mode}-'))
                dump_dir = work / 'dump'
                dump_dir.mkdir()
                env = os.environ.copy()
                if mode == 'q8_1':
                    env['STRATA_NATIVE_CPU_Q8_1_DOT'] = 'iq2_s/iq4_nl@layer=39'
                else:
                    env.pop('STRATA_NATIVE_CPU_Q8_1_DOT', None)
                command = [str(PARITY), str(MODEL), '--expert', str(expert),
                           '--activation-f32', str(activation_path), '--dump-f32-dir', str(dump_dir), str(LAYER)]
                proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True)
                (logs / f'position-{position}-expert-{expert}-{mode}.txt').write_text(proc.stdout)
                if proc.returncode != 0 or 'native_expert_parity: 0 failures' not in proc.stdout:
                    shutil.rmtree(work, ignore_errors=True)
                    raise RuntimeError(f'parity failed at position {position}, expert {expert}, mode {mode}')
                cpu = (dump_dir / f'layer-{LAYER}-expert-{expert}-cpu-output.f32').read_bytes()
                gpu = (dump_dir / f'layer-{LAYER}-expert-{expert}-gpu-output.f32').read_bytes()
                expert_result[mode] = {'cpu_vs_gpu': metric(cpu, gpu)}
                shutil.rmtree(work)
            entry['experts'][str(expert)] = expert_result
        summary['positions'][str(position)] = entry
    summary['q8_1_cpu_gpu_bitwise_for_all_rows'] = all(
        row['q8_1']['cpu_vs_gpu']['bitwise_equal']
        for position in summary['positions'].values() for row in position['experts'].values())
    output = args.run_dir / 'layer39-oracle-analysis.json'
    output.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({position: {
        expert: {mode: row[mode]['cpu_vs_gpu'] for mode in ('default', 'q8_1')}
        for expert, row in data['experts'].items()
    } for position, data in summary['positions'].items()}, indent=2))


if __name__ == '__main__':
    main()
