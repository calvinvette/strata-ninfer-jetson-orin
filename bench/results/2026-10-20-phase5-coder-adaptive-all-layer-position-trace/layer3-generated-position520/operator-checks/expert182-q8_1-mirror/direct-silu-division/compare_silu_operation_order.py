#!/usr/bin/env python3
"""Compare the temporary direct-SiLU replay with reciprocal baseline and CUDA output."""
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'stage-detail-parts'


def float_words(path):
    data = path.read_bytes()
    if len(data) % 4:
        raise ValueError(f'{path} is not an F32 array')
    return struct.unpack(f'<{len(data) // 4}f', data)


def f32_comparison(left, right):
    if len(left) != len(right):
        raise ValueError('F32 arrays have different element counts')
    diff = [a - b for a, b in zip(left, right)]
    return {
        'values': len(left),
        'different_float32_words': sum(a != b for a, b in zip(left, right)),
        'max_abs_difference': max((abs(value) for value in diff), default=0.0),
        'relative_l2_difference': math.sqrt(sum(value * value for value in diff)) /
            max(math.sqrt(sum(value * value for value in right)), 1e-300),
    }


def byte_comparison(left, right):
    a, b = left.read_bytes(), right.read_bytes()
    if len(a) != len(b):
        raise ValueError(f'{left} and {right} have different sizes')
    return {'bytes': len(a), 'different_bytes': sum(x != y for x, y in zip(a, b))}


def main():
    direct_float = float_words(HERE / 'layer-3-expert-182--cpu-hidden.f32')
    reciprocal_reconstruction = float_words(
        HERE / 'layer-3-expert-182--cpu-hidden-on-gpu-activation.f32')
    direct_hidden = HERE / 'cpu-hidden.q8_1'
    gpu_hidden = HERE / 'gpu-hidden.q8_1'
    direct_output = HERE / 'cpu-output.f32'
    gpu_output = HERE / 'gpu-output.f32'
    baseline_hidden_cpu = BASE / 'layer-3-expert-182--cpu-hidden.q8_1'
    baseline_hidden_gpu = BASE / 'layer-3-expert-182--gpu-hidden.q8_1'
    baseline_output_cpu = BASE / 'layer-3-expert-182-cpu-output.f32'
    baseline_output_gpu = BASE / 'layer-3-expert-182-gpu-output.f32'
    result = {
        'scope': 'one captured layer-3 IQ2_S/IQ4_NL expert-182 activation; diagnostic only',
        'direct_float_vs_reciprocal_reconstruction': f32_comparison(
            direct_float, reciprocal_reconstruction),
        'direct_cpu_vs_cuda_hidden_q8_1': byte_comparison(direct_hidden, gpu_hidden),
        'direct_cpu_vs_cuda_output': f32_comparison(
            float_words(direct_output), float_words(gpu_output)),
        'reciprocal_cpu_vs_cuda_hidden_q8_1': byte_comparison(
            baseline_hidden_cpu, baseline_hidden_gpu),
        'reciprocal_cpu_vs_cuda_output': f32_comparison(
            float_words(baseline_output_cpu), float_words(baseline_output_gpu)),
        'reciprocal_vs_direct_cpu_hidden_q8_1': byte_comparison(
            baseline_hidden_cpu, direct_hidden),
        'reciprocal_vs_direct_cpu_output': f32_comparison(
            float_words(baseline_output_cpu), float_words(direct_output)),
        'native_expert_parity_exit_status': 1,
        'parity_failure_reason': (
            'the independent float reconstruction retains reciprocal operation order; '
            'packed Q8_1 and final CPU/CUDA comparisons are exact'),
    }
    (HERE / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
