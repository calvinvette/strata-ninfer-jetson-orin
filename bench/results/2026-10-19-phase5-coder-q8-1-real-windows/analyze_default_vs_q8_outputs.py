#!/usr/bin/env python3
"""Compare default and Q8_1 CPU outputs and validate Q8_1/CUDA parity captures."""
import json
import math
import pathlib
import re
import struct

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / 'default-vs-q8-expert-outputs'
CASES = [(512,760,e) for e in (95,11,205,18,90)] + [(514,1433,e) for e in (30,159,182)]
out = {"cases": []}
for position, token, expert in CASES:
    cell = BASE / f'position-{position}-token-{token}-expert-{expert}'
    q8_supervisor = cell/'q8_1/supervisor'
    if not q8_supervisor.exists():
        q8_supervisor = HERE/'captured-device-ffnx-experts'/f'position-{position}-token-{token}-expert-{expert}'/'supervisor'
    result = json.loads((q8_supervisor/'result.json').read_text())
    if result['status'] != 'pass' or result['returncode'] != 0:
        raise RuntimeError(f'{q8_supervisor}: Q8_1 supervisor did not pass')
    stdout = (q8_supervisor/'stdout.txt').read_text()
    match = re.search(r'cpu-gpu ([^ ]+) \((\d+)/(\d+) words differ\)', stdout)
    if not match or match.group(1) != '0.00e+00' or match.group(2) != '0' or match.group(3) != '2560':
        raise RuntimeError(f'{q8_supervisor}: Q8_1 CPU/GPU output not bitwise equal')
    case = {'position': position, 'token_id': token, 'expert': expert,
            'q8_1_cpu_cuda_bitwise_equal': True,
            'q8_1_minimum_host_available_gib': result['minimum_available_bytes']/2**30,
            'q8_1_minimum_admission_available_gib': result['minimum_admission_available_bytes']/2**30}
    default_supervisor = cell/'default/supervisor'
    if default_supervisor.exists():
        default_result = json.loads((default_supervisor/'result.json').read_text())
        if default_result['status'] != 'pass' or default_result['returncode'] != 0:
            raise RuntimeError(f'{default_supervisor}: default CPU supervisor did not pass')
        q8_dump = next((cell/'q8_1/dumps').glob('*cpu-output.f32'))
        default_dump = next((cell/'default/dumps').glob('*cpu-output.f32'))
        q8_values = struct.unpack('<2560f', q8_dump.read_bytes())
        default_values = struct.unpack('<2560f', default_dump.read_bytes())
        diffs = [abs(x-y) for x,y in zip(default_values,q8_values)]
        case.update({
            'default_q8_1_differing_values': sum(x != y for x,y in zip(default_values,q8_values)),
            'elements': len(q8_values), 'max_abs_default_q8_1': max(diffs),
            'relative_l1_default_q8_1': math.fsum(diffs)/max(math.fsum(abs(x) for x in default_values),1e-30),
            'default_minimum_host_available_gib': default_result['minimum_available_bytes']/2**30,
            'default_minimum_admission_available_gib': default_result['minimum_admission_available_bytes']/2**30,
        })
    out['cases'].append(case)
path=HERE/'default-vs-q8-output-analysis.json'
path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
