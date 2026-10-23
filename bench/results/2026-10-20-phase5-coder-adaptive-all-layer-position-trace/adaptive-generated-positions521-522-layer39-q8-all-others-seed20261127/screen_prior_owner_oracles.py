#!/usr/bin/env python3
"""Screen same-input adaptive owner switches before layer 40 with native CPU/CUDA oracles."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TRACE = HERE.parent / 'adaptive-generated-positions512-521-522-layer14-state' / 'adaptive-cap8' / 'result' / 'all-layer-selected-positions.jsonl'
MODEL = Path.home() / 'models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf'
PARITY = ROOT / 'build/integration/candidate/native_expert_parity'
WIDTH = 2560


def metric(a, b):
    x = struct.unpack(f'<{WIDTH}f', a)
    y = struct.unpack(f'<{WIDTH}f', b)
    d = [float(i) - float(j) for i, j in zip(x, y)]
    den = math.fsum(float(v) ** 2 for v in y)
    return {'bitwise_equal': a == b, 'different_values': sum(i != j for i, j in zip(x, y)),
            'max_abs': max(map(abs, d), default=0.0),
            'relative_l2': math.sqrt(math.fsum(v * v for v in d) / den) if den else None}


def main():
    selectors = {}
    for pair, layers in re.findall(r'([a-z0-9_]+/[a-z0-9_]+)@layer=([0-9,]+)',
                                    (HERE.parent / 'selector-all-except-layer39.txt').read_text()):
        for layer in layers.rstrip(',').split(','):
            selectors[int(layer)] = pair
    records = [json.loads(line) for line in TRACE.read_text().splitlines()[1:]]
    rows = {}
    for pos in (521, 522):
        selected = [r for r in records if r['position'] == pos]
        if len(selected) != 192:
            raise ValueError(f'position {pos}: expected four complete layer blocks, got {len(selected)}')
        for req in range(4):
            for row in selected[req * 48:(req + 1) * 48]:
                rows[(pos, req, row['layer'])] = row
    candidates = {}
    for pos in (521, 522):
        for layer in range(39):
            before, after = rows[(pos, 0, layer)], rows[(pos, 1, layer)]
            if before['ids'] != after['ids']:
                raise ValueError(f'route ID changed before layer 40 at position {pos}, layer {layer}')
            if before['activation'] != after['activation']:
                raise ValueError(f'input activation changed before layer 40 at position {pos}, layer {layer}')
            if not before.get('activation_valid') or not after.get('activation_valid'):
                continue
            for slot, (left, right) in enumerate(zip(before['route_kind'], after['route_kind'])):
                if left != right:
                    expert = before['ids'][slot]
                    key = (layer, expert)
                    candidates.setdefault(key, {'layer': layer, 'expert': expert, 'selector_pair': selectors.get(layer),
                                                'positions': []})['positions'].append(pos)
    output = {'scope': 'same-input owner switches in adaptive initial-to-intermediate requests, layers 0-38',
              'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
              'model_revision': '5348543e0147355ac9cbcb031184a3546350988e', 'quantization': 'IQ1_M',
              'trace_source': str(TRACE.relative_to(ROOT)),
              'parity_binary_sha256': hashlib.sha256(PARITY.read_bytes()).hexdigest(),
              'candidate_rows': []}
    activations = HERE / 'prior-owner-oracle-activations'
    activations.mkdir(exist_ok=True)
    for (layer, expert), entry in sorted(candidates.items()):
        per_position = {}
        for pos in sorted(set(entry['positions'])):
            row = rows[(pos, 0, layer)]
            activation = struct.pack(f'<{WIDTH}f', *row['activation'])
            activation_path = activations / f'layer-{layer}-expert-{expert}-position-{pos}.f32'
            activation_path.write_bytes(activation)
            modes = {}
            for mode in ('default', 'q8_1'):
                with tempfile.TemporaryDirectory(prefix=f'prior-owner-{layer}-{expert}-{mode}-') as td:
                    env = os.environ.copy()
                    if mode == 'q8_1':
                        if entry['selector_pair'] is None:
                            modes[mode] = {'unsupported': 'no selector for this layer'}
                            continue
                        env['STRATA_NATIVE_CPU_Q8_1_DOT'] = f"{entry['selector_pair']}@layer={layer}"
                    else:
                        env.pop('STRATA_NATIVE_CPU_Q8_1_DOT', None)
                    cmd = [str(PARITY), str(MODEL), '--expert', str(expert), '--activation-f32',
                           str(activation_path), '--dump-f32-dir', td, str(layer)]
                    proc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True)
                    if proc.returncode or 'native_expert_parity: 0 failures' not in proc.stdout:
                        raise RuntimeError(f'oracle failed layer={layer} expert={expert} mode={mode}: {proc.stdout[-2000:]}')
                    cpu = (Path(td) / f'layer-{layer}-expert-{expert}-cpu-output.f32').read_bytes()
                    gpu = (Path(td) / f'layer-{layer}-expert-{expert}-gpu-output.f32').read_bytes()
                    modes[mode] = {'cpu_vs_gpu': metric(cpu, gpu), 'activation_sha256': hashlib.sha256(activation).hexdigest()}
            per_position[str(pos)] = modes
        output['candidate_rows'].append({**entry, 'positions': per_position})
    output['rows_screened'] = len(output['candidate_rows'])
    output['q8_1_exact_at_every_sampled_position'] = all(
        row['positions'][str(pos)].get('q8_1', {}).get('cpu_vs_gpu', {}).get('bitwise_equal', False)
        for row in output['candidate_rows'] for pos in row['positions'])
    result = HERE / 'prior-owner-oracle-screen.json'
    result.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({'rows_screened': output['rows_screened'], 'q8_1_exact_at_every_sampled_position': output['q8_1_exact_at_every_sampled_position'],
                      'rows': [{k: r[k] for k in ('layer', 'expert', 'selector_pair', 'positions')} for r in output['candidate_rows']]}, indent=2))


if __name__ == '__main__':
    main()
