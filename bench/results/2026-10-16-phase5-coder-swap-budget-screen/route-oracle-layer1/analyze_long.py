#!/usr/bin/env python3
"""Analyze CPU/GPU and quantizer-oracle deltas for long-row owner changes."""
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ORACLE_PATH = ROOT / 'bench/results/2026-10-15-phase5-activation-error-decomposition/analyze_oracles.py'
spec = importlib.util.spec_from_file_location('analyze_oracles', ORACLE_PATH)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def main():
    meta = json.loads((OUT / 'long-parity.json').read_text())
    activation_values = struct.unpack('<2560f', (OUT / 'layer1-long-row0.f32').read_bytes())
    records = []
    for item in meta['runs']:
        expert = item['expert']
        directory = OUT / f'long-expert-{expert}'
        stem = f'layer-1-expert-{expert}'
        gate = reference.load_f32(directory / f'{stem}-gate.f32', reference.FF * reference.H)
        up = reference.load_f32(directory / f'{stem}-up.f32', reference.FF * reference.H)
        down = reference.load_f32(directory / f'{stem}-down.f32', reference.H * reference.FF)
        cpu = reference.load_f32(directory / f'{stem}-cpu-output.f32', reference.H)
        gpu = reference.load_f32(directory / f'{stem}-gpu-output.f32', reference.H)
        full = reference.load_f32(directory / f'{stem}-float-output.f32', reference.H)
        cpu_oracle = reference.oracle(gate, up, down, activation_values, 'Q8_K/Q8_0')
        gpu_oracle = reference.oracle(gate, up, down, activation_values, 'Q8_1/Q8_1')
        records.append({
            'expert': expert,
            'activation_sha256': hashlib.sha256(struct.pack('<2560f', *activation_values)).hexdigest(),
            'actual_cpu_vs_gpu_relative_l1': reference.metric(cpu, gpu),
            'shared_weight_q8k_vs_q81_oracle_relative_l1': reference.metric(cpu_oracle, gpu_oracle),
            'actual_cpu_vs_q8k_oracle_relative_l1': reference.metric(cpu, cpu_oracle),
            'actual_gpu_vs_q81_oracle_relative_l1': reference.metric(gpu, gpu_oracle),
            'actual_vs_oracle_delta_residual_relative_l1': reference.delta_residual(cpu, gpu, cpu_oracle, gpu_oracle),
            'cpu_vs_float_weight_relative_l1': reference.metric(cpu, full),
            'gpu_vs_float_weight_relative_l1': reference.metric(gpu, full),
        })
    result = {
        'status': 'pass',
        'method': 'native packed CPU/GPU expert kernels plus independently reconstructed Q8_K/Q8_0 and Q8_1/Q8_1 activation oracles over GGUF-dequantized weights and CBLAS FP32 dots',
        'limitations': ['one captured activation per routed expert, one block',
                        'operator sensitivity does not by itself prove complete service-level causality'],
        'route_evidence': meta['route_evidence'], 'records': records,
    }
    (OUT / 'long-analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    for row in records:
        print('expert', row['expert'], 'CPU/GPU', f"{row['actual_cpu_vs_gpu_relative_l1']:.5%}",
              'oracle', f"{row['shared_weight_q8k_vs_q81_oracle_relative_l1']:.5%}",
              'residual', f"{row['actual_vs_oracle_delta_residual_relative_l1']:.5%}")


if __name__ == '__main__':
    main()
