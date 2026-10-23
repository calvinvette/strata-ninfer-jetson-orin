#!/usr/bin/env python3
"""Join captured layer owner outputs to the same-input CPU/GPU/float oracle."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sIIIIQqii')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', type=Path, required=True,
                    help='target-only capture directory containing serial/batch owner and part files')
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--model', type=Path, default=Path.home() / 'models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
parser.add_argument('--parity', type=Path, default=ROOT / 'build/integration/candidate/native_expert_parity')
parser.add_argument('--position', type=int, default=119)
parser.add_argument('--token', type=int, default=16)
parser.add_argument('--layer', type=int, default=11)
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)

def select_owner(path):
    lines = Path(path).read_text().splitlines()
    if not lines or json.loads(lines[0]).get('format') != 'strata-moe-dispatch-v3':
        raise ValueError(f'{path}: invalid MoE dispatch capture')
    rows = [json.loads(line) for line in lines[1:]
            if json.loads(line).get('layer') == args.layer
            and json.loads(line).get('position') == args.position
            and json.loads(line).get('token_id') == args.token]
    if len(rows) != 1:
        raise ValueError(f'{path}: expected one selected owner row, got {len(rows)}')
    row = rows[0]
    if not row.get('activation_valid') or len(row['activation']) != 2560:
        raise ValueError(f'{path}: selected row has no 2560-value activation')
    return row

def select_parts(path, slot):
    data = Path(path).read_bytes()
    at = 0
    records = []
    while at < len(data):
        if len(data) - at < HEADER.size:
            raise ValueError(f'{path}: truncated header at {at}')
        magic, version, layer, count, reserved, width, position, row_slot, token = HEADER.unpack_from(data, at)
        at += HEADER.size
        if magic != b'STMPART2' or version != 2 or reserved or layer != args.layer or count < 1:
            raise ValueError(f'{path}: invalid record at {at - HEADER.size}')
        n = count * width
        size = n * 4
        if len(data) - at < size:
            raise ValueError(f'{path}: truncated payload at {at}')
        values = struct.unpack_from(f'<{n}f', data, at)
        at += size
        if position == args.position and row_slot == slot and token == args.token:
            records.append({'width': width * count, 'values': values})
    if len(records) != 1:
        raise ValueError(f'{path}: expected one slot={slot} row, got {len(records)}')
    return records[0]

def pack(values):
    return struct.pack(f'<{len(values)}f', *values)

def metrics(actual, reference):
    if len(actual) != len(reference):
        raise ValueError('output vectors have different lengths')
    delta = [a - b for a, b in zip(actual, reference)]
    ref_l1 = math.fsum(abs(x) for x in reference)
    ref_l2 = math.sqrt(math.fsum(x*x for x in reference))
    return {
        'bitwise_equal': pack(actual) == pack(reference),
        'different_values': sum(a != b for a, b in zip(actual, reference)),
        'values': len(actual),
        'max_abs': max(map(abs, delta), default=0.0),
        'relative_l1': math.fsum(map(abs, delta)) / ref_l1 if ref_l1 else 0.0,
        'relative_l2': math.sqrt(math.fsum(x*x for x in delta)) / ref_l2 if ref_l2 else 0.0,
    }

serial_owner = select_owner(args.run / 'serial.moe-owners.jsonl')
batch_owner = select_owner(args.run / 'batch.moe-owners.jsonl')
if pack(serial_owner['activation']) != pack(batch_owner['activation']):
    raise ValueError('serial and batch owner captures do not have the exact same f32 activation')
serial_parts = select_parts(args.run / 'moe-parts.stmparts', -1)
batch_parts = select_parts(args.run / 'moe-parts.stmparts', 0)
if serial_parts['width'] != batch_parts['width'] or serial_parts['width'] != 2560 * len(serial_owner['ids']):
    raise ValueError('unexpected expert-part width')
owner_changes = [(rank, expert) for rank, (expert, so, bo) in enumerate(zip(
    serial_owner['ids'], serial_owner['route_kind'], batch_owner['route_kind']))
    if so != bo]
if not owner_changes or any(serial_owner['ids'][rank] != batch_owner['ids'][rank]
                             or so != 0 or bo != -1
                             for rank, _ in owner_changes
                             for so, bo in [(serial_owner['route_kind'][rank], batch_owner['route_kind'][rank])]):
    raise ValueError(f'expected same-ID primary-VRAM-to-CPU owner changes, got {owner_changes}')
activation_path = out / 'activation-position119-token16.f32'
activation_bytes = pack(batch_owner['activation'])
activation_path.write_bytes(activation_bytes)

result = {
    'schema': 1,
    'model_repository': 'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
    'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
    'model_quantization': 'IQ1_M; per-expert codecs recorded by native oracle output',
    'layer': args.layer,
    'position': args.position,
    'token': args.token,
    'expert_ids': [expert for _, expert in owner_changes],
    'activation_bytes': len(activation_bytes),
    'activation_sha256': hashlib.sha256(activation_bytes).hexdigest(),
    'serial_and_batch_activation_bitwise_equal': True,
    'expected_serial_owners': 'primary VRAM',
    'expected_batch_owners': 'CPU',
    'experts': {},
    'parity_binary_sha256': hashlib.sha256(args.parity.read_bytes()).hexdigest(),
    'model_shard': args.model.name,
    'model_shard_bytes': args.model.stat().st_size,
}
for rank, expert in owner_changes:
    record = {'rank': rank, 'expert': expert,
              'serial_owner_code': serial_owner['route_kind'][rank],
              'batch_owner_code': batch_owner['route_kind'][rank]}
    if serial_owner['ids'][rank] != expert or batch_owner['ids'][rank] != expert:
        raise ValueError(f'expert {expert}: route ID does not match rank {rank}')
    if record['serial_owner_code'] != 0 or record['batch_owner_code'] != -1:
        raise ValueError(f'expert {expert}: expected VRAM->CPU owner change, got {record}')
    serial_service = serial_parts['values'][rank * 2560:(rank + 1) * 2560]
    batch_service = batch_parts['values'][rank * 2560:(rank + 1) * 2560]
    with tempfile.TemporaryDirectory(prefix=f'strata-layer{args.layer}-e{expert}-') as temp:
        dump = Path(temp)
        command = [str(args.parity), str(args.model), '--expert', str(expert),
                   '--activation-f32', str(activation_path), '--dump-f32-dir', str(dump), str(args.layer)]
        proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, check=False)
        log = out / f'expert-{expert}-parity.txt'
        log.write_text(proc.stdout)
        if proc.returncode != 0 or 'native_expert_parity: 0 failures' not in proc.stdout:
            raise RuntimeError(f'expert {expert} native parity failed; see {log}')
        stem = f'layer-{args.layer}-expert-{expert}'
        cpu = struct.unpack('<2560f', (dump / f'{stem}-cpu-output.f32').read_bytes())
        gpu = struct.unpack('<2560f', (dump / f'{stem}-gpu-output.f32').read_bytes())
        reference = struct.unpack('<2560f', (dump / f'{stem}-float-output.f32').read_bytes())
        record.update({
            'serial_service_vs_cpu_oracle': metrics(serial_service, cpu),
            'serial_service_vs_gpu_oracle': metrics(serial_service, gpu),
            'batch_service_vs_cpu_oracle': metrics(batch_service, cpu),
            'batch_service_vs_gpu_oracle': metrics(batch_service, gpu),
            'cpu_oracle_vs_float_reference': metrics(cpu, reference),
            'gpu_oracle_vs_float_reference': metrics(gpu, reference),
        })
        for suffix in ('cpu-output', 'gpu-output', 'float-output'):
            shutil.copy2(dump / f'{stem}-{suffix}.f32', out / f'expert-{expert}-{suffix}.f32')
    result['experts'][str(expert)] = record

(out / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
