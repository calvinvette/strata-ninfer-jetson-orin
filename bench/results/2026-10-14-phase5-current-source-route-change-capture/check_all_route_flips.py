#!/usr/bin/env python3
"""Run the independent CPU/GPU expert oracle on every exact-input route flip."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAPTURE = ROOT / 'bench/results/2026-10-14-phase5-current-source-route-change-capture/run/start-0.jsonl'
MODEL = Path('/home/calvin/models/strata-orin-validation/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf')
BINARY = ROOT / 'build/integration/candidate/native_expert_parity'

a = [json.loads(line) for line in CAPTURE.read_text().splitlines()][1:]
initial, recovery = a[:22], a[44:66]
assert len(initial) == len(recovery) == 22
checks = []
args = argparse.ArgumentParser(description=__doc__)
args.add_argument('--output', type=Path, required=True)
opt = args.parse_args()
opt.output.mkdir(parents=True, exist_ok=False)
raw = opt.output / 'inputs'
raw.mkdir()
for row, (before, after) in enumerate(zip(initial[:7], recovery[:7])):
    assert before['activation'] == after['activation'] and before['ids'] == after['ids']
    activation_path = raw / f'layer0-row{row}.f32'
    activation_path.write_bytes(struct.pack('<2560f', *before['activation']))
    for expert, owner_before, owner_after in zip(before['ids'], before['route_kind'], after['route_kind']):
        if owner_before == owner_after:
            continue
        assert owner_before == -1 and owner_after == 0, (row, expert, owner_before, owner_after)
        proc = subprocess.run([str(BINARY), str(MODEL), '--expert', str(expert),
                               '--activation-f32', str(activation_path), '0'],
                              cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (opt.output / 'all-parity-output.txt').open('a').write(proc.stdout)
        match = re.search(r'layer 0 expert (\d+) .*?cpu rel ([0-9.eE+-]+)  gpu rel ([0-9.eE+-]+)  cpu-gpu ([0-9.eE+-]+) \((\d+)/(\d+) words differ\)', proc.stdout)
        if proc.returncode != 0 or match is None:
            raise RuntimeError(f'parity failed for row {row}, expert {expert}: {proc.stdout}')
        checks.append({'row': row, 'expert': expert, 'owner_before': owner_before,
                       'owner_after': owner_after, 'activation_sha256': hashlib.sha256(activation_path.read_bytes()).hexdigest(),
                       'cpu_relative_l1_to_float': float(match.group(2)),
                       'gpu_relative_l1_to_float': float(match.group(3)),
                       'cpu_gpu_relative_l1': float(match.group(4)),
                       'bitwise_different_words': int(match.group(5)), 'output_words': int(match.group(6))})
assert len(checks) == 18, len(checks)
vals = [c['cpu_gpu_relative_l1'] for c in checks]
result = {'status': 'pass', 'model': 'Qwen3.8-Flash-Next Coder IQ1_M', 'layer': 0,
          'comparisons': len(checks), 'unique_experts': sorted({c['expert'] for c in checks}),
          'same_activation_owner_flips': checks,
          'cpu_gpu_relative_l1_min': min(vals), 'cpu_gpu_relative_l1_median': sorted(vals)[len(vals)//2],
          'cpu_gpu_relative_l1_max': max(vals),
          'all_outputs_bitwise_different': all(c['bitwise_different_words'] == c['output_words'] for c in checks),
          'source_capture_sha256': hashlib.sha256(CAPTURE.read_bytes()).hexdigest()}
(opt.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'comparisons': len(checks),
                  'unique_experts': result['unique_experts'],
                  'cpu_gpu_relative_l1_min': result['cpu_gpu_relative_l1_min'],
                  'cpu_gpu_relative_l1_median': result['cpu_gpu_relative_l1_median'],
                  'cpu_gpu_relative_l1_max': result['cpu_gpu_relative_l1_max'],
                  'all_outputs_bitwise_different': result['all_outputs_bitwise_different']}, indent=2))
