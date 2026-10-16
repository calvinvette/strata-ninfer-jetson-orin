#!/usr/bin/env python3
"""Run parity on all same-input owner changes at long-request layer-1 row 0."""
import gzip
import hashlib
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN = ROOT / 'bench/results/2026-10-16-phase5-coder-swap-budget-screen/all-layer-campaign'
OUT = Path(__file__).resolve().parent
MODEL = Path('/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
BINARY = ROOT / 'build/integration/candidate/native_expert_parity'
EXPECTED = {11: (-1, 0), 95: (-1, 0), 165: (-1, 0), 205: (-1, 0)}


def get_long_row(path):
    seen = 0
    with gzip.open(path, 'rt') as stream:
        next(stream)
        for line in stream:
            row = json.loads(line)
            if row['layer'] == 1:
                if seen == 22:
                    return row
                seen += 1
    raise RuntimeError('layer-1 long-request row 0 was not captured')


def main():
    control = get_long_row(CAMPAIGN / 'block-0-delayed-control/all-layers.jsonl.gz')
    candidate = get_long_row(CAMPAIGN / 'block-0-swap-8/all-layers.jsonl.gz')
    if control['activation'] != candidate['activation'] or control['ids'] != candidate['ids']:
        raise RuntimeError('long row 0 is not a same-input/same-expert route pair')
    owners = {e: (kc, kn) for e, kc, kn in zip(control['ids'], control['route_kind'], candidate['route_kind']) if kc != kn}
    if owners != EXPECTED:
        raise RuntimeError(f'unexpected owner changes: {owners}')
    activation = OUT / 'layer1-long-row0.f32'
    activation.write_bytes(struct.pack(f'<{len(control["activation"])}f', *control['activation']))
    report = {
        'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'model_quantization': 'IQ1_M',
        'model_sha256': 'e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
        'route_evidence': {
            'block': 0, 'request': 'long-2048', 'layer': 1, 'row': 0,
            'activation_equal': True, 'expert_ids_equal': True,
            'owner_changes': [{'expert': e, 'delayed_control_kind': owners[e][0], 'swap8_kind': owners[e][1]}
                              for e in sorted(owners)],
            'kind_contract': {'-1': 'CPU', '0': 'primary VRAM'},
        },
        'activation_sha256': hashlib.sha256(activation.read_bytes()).hexdigest(),
        'parity_binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
        'runs': [],
    }
    for expert in (11, 95, 165, 205):
        dump_dir = OUT / f'long-expert-{expert}'
        dump_dir.mkdir(exist_ok=False)
        command = [str(BINARY), str(MODEL), '--expert', str(expert),
                   '--activation-f32', str(activation), '--dump-f32-dir', str(dump_dir), '1']
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        (dump_dir / 'stdout.txt').write_text(result.stdout)
        if result.returncode:
            (OUT / 'long-parity.json').write_text(json.dumps(report, indent=2) + '\n')
            raise RuntimeError(f'expert {expert} parity returned {result.returncode}')
        report['runs'].append({'request': 'long-2048', 'expert': expert,
                               'command': command, 'returncode': result.returncode})
    (OUT / 'long-parity.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
