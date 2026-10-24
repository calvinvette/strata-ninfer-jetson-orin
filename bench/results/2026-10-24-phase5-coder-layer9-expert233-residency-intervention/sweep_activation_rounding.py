#!/usr/bin/env python3
"""Replay distinct captured layer-9/expert-233 activations through CPU/GPU oracle."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INPUT_ROOTS = [
    ROOT / 'bench/results/2026-10-23-phase5-coder-two-live-target-q8all',
    ROOT / 'bench/results/2026-10-24-phase5-coder-layer9-expert233-residency-intervention',
    ROOT / 'bench/results/2026-10-24-phase5-coder-layer39-expert50-residency-intervention',
]
MODEL = Path.home() / 'models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf'
BINARY = ROOT / 'build/integration/candidate/native_expert_parity'
QUANTIZER = HERE / 'analyze_silu_quantizer.py'


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def find_activations():
    unique = {}
    for base in INPUT_ROOTS:
        for path in sorted(base.rglob('*.owners.jsonl')):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                if '"layer":9' not in line or '233' not in line:
                    continue
                row = json.loads(line)
                if (row.get('layer') != 9 or row.get('position') is None or
                        233 not in row.get('ids', []) or not row.get('activation_valid')):
                    continue
                raw = struct.pack(f'<{len(row["activation"])}f', *row['activation'])
                digest = sha256(raw)
                unique.setdefault(digest, {'activation': raw, 'references': []})
                unique[digest]['references'].append({
                    'path': str(path.relative_to(ROOT)), 'line': line_number,
                    'position': row['position'], 'token_id': row['token_id'],
                    'owner_code': row['route_kind'][row['ids'].index(233)],
                })
    return unique


def main():
    if not MODEL.is_file() or not BINARY.is_file():
        raise SystemExit(f'missing model or native oracle: {MODEL} / {BINARY}')
    activations = find_activations()
    if len(activations) < 3:
        raise SystemExit(f'expected at least three distinct captured activations; found {len(activations)}')
    env = os.environ.copy()
    env.update({
        'STRATA_GROUPED_V1': '1',
        'STRATA_NATIVE_CPU_Q8_1_DOT': 'iq2_s/iq4_nl@layer=9',
        'STRATA_PARITY_DUMP_HIDDEN_Q8_1': '1',
        'STRATA_PARITY_COMPARE_HIDDEN_Q8_1': '1',
        'STRATA_PARITY_TRY_EXP2F_SILU': '1',
        'STRATA_EXP_MODE': '0',
    })
    rows = []
    with tempfile.TemporaryDirectory(prefix='phase5-e233-activation-sweep-') as td:
        temp = Path(td)
        for digest, item in sorted(activations.items()):
            activation = temp / f'{digest}.activation.f32'
            dump = temp / digest
            dump.mkdir()
            activation.write_bytes(item['activation'])
            cmd = [str(BINARY), str(MODEL), '--expert', '233',
                   '--activation-f32', str(activation), '--dump-f32-dir', str(dump), '9']
            process = subprocess.run(cmd, cwd=ROOT, env=env, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = process.stdout
            reconstruction = re.search(r'independent IQ2_S/Q8_1 gate/up reconstruction vs native hidden: (\d+)/(\d+) words differ', output)
            hidden = re.search(r'CPU vs CUDA hidden Q8_1 after SwiGLU: (\d+)/(\d+) blocks differ', output)
            candidate = re.search(
                r'host exp2f SiLU-Q8_1 candidate: (\d+)/(\d+) hidden blocks differ; '
                r'CPU down vs CUDA (\d+)/(\d+) words differ \(max ([^,]+), relL2 ([^)]+)\)', output)
            if reconstruction is None or hidden is None or candidate is None:
                raise RuntimeError(f'oracle output was incomplete for {digest}: {output[-2000:]}')
            names = {
                'cpu_gate': f'layer-9-expert-233--cpu-gate.f32',
                'gpu_gate': f'layer-9-expert-233--gpu-gate.f32',
                'cpu_up': f'layer-9-expert-233--cpu-up.f32',
                'gpu_up': f'layer-9-expert-233--gpu-up.f32',
                'cpu_hidden': f'layer-9-expert-233--cpu-hidden.f32',
                'gpu_hidden': f'layer-9-expert-233--gpu-hidden.f32',
                'cpu_hidden_q8': f'layer-9-expert-233--cpu-hidden.q8_1',
                'gpu_hidden_q8': f'layer-9-expert-233--gpu-hidden.q8_1',
                'cpu_output': f'layer-9-expert-233-cpu-output.f32',
                'gpu_output': f'layer-9-expert-233-gpu-output.f32',
            }
            stage = {key: (dump / name).read_bytes() for key, name in names.items()}
            analyzer_path = temp / f'{digest}.quantizer.json'
            subprocess.run([
                'python3', str(QUANTIZER), '--gate', str(dump / names['gpu_gate']),
                '--up', str(dump / names['gpu_up']), '--cuda-hidden-q8', str(dump / names['gpu_hidden_q8']),
                '--cuda-hidden-f32', str(dump / names['gpu_hidden']), '--output', str(analyzer_path),
            ], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
            quantizer = json.loads(analyzer_path.read_text())
            hidden_cpu = struct.unpack(f'<{len(stage["cpu_hidden"]) // 4}f', stage['cpu_hidden'])
            hidden_gpu = struct.unpack(f'<{len(stage["gpu_hidden"]) // 4}f', stage['gpu_hidden'])
            delta = [a - b for a, b in zip(hidden_cpu, hidden_gpu)]
            row = {
                'activation_sha256': digest,
                'references': item['references'],
                'native_expert_parity_returncode': process.returncode,
                'independent_hidden_f32_reconstruction_mismatches': int(reconstruction.group(1)),
                'hidden_q8_1_blocks_different_cpu_vs_gpu': int(hidden.group(1)),
                'host_exp2f_hidden_q8_1_blocks_different_vs_cuda': int(candidate.group(1)),
                'host_exp2f_cpu_down_words_different_vs_cuda': int(candidate.group(3)),
                'host_exp2f_cpu_down_max_abs_vs_cuda': float(candidate.group(5)),
                'host_exp2f_cpu_down_relative_l2_vs_cuda': float(candidate.group(6)),
                'cpu_gpu_gate_bitwise_equal': stage['cpu_gate'] == stage['gpu_gate'],
                'cpu_gpu_up_bitwise_equal': stage['cpu_up'] == stage['gpu_up'],
                'cpu_gpu_hidden_q8_1_bitwise_equal': stage['cpu_hidden_q8'] == stage['gpu_hidden_q8'],
                'cpu_gpu_final_output_bitwise_equal': stage['cpu_output'] == stage['gpu_output'],
                'cpu_gpu_hidden_f32_differing_values': sum(x != 0 for x in delta),
                'cpu_gpu_hidden_f32_max_abs': max(map(abs, delta)),
                'host_quantizer_candidates': {
                    name: {
                        'different_cuda_hidden_f32_values': details['different_cuda_hidden_f32_values'],
                        'different_q8_1_blocks': len(details['different_q8_1_blocks']),
                        'q8_1_field_block_mismatches': details['q8_1_field_block_mismatches'],
                    }
                    for name, details in quantizer['variants'].items()
                },
            }
            rows.append(row)
            if process.returncode != 0:
                raise RuntimeError(f'native oracle failed for {digest}: {output[-2000:]}')

    result = {
        'schema': 1,
        'scope': 'Distinct exact captured Coder IQ1_M activation rows at layer 9 where expert 233 is routed; replayed through native CPU and CUDA operator oracle.',
        'model_revision': '5348543e0147355ac9cbcb031184a3546350988e',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_sha256': {
            path: sha256((ROOT / path).read_bytes())
            for path in (
                'include/strata/kernels/cpu/native_expert.hpp',
                'src/kernels/cpu/native_expert.cpp',
                'src/kernels/cpu/pool.cpp',
                'src/kernels/native_expert_parity.cpp',
            )
        },
        'native_expert_parity_binary_sha256': sha256(BINARY.read_bytes()),
        'activation_count': len(rows),
        'notes': [
            'Rows from separate capture files were deduplicated by exact float32 activation bytes.',
            'Owner codes in source captures are metadata; the CPU/GPU replay is independent and does not assert the captured service used either route.',
            'This operator-only diagnostic does not establish end-to-end persistent-state parity or a runtime change.',
        ],
        'activations': rows,
    }
    out = HERE / 'activation-rounding-sweep.json'
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({
        'activation_count': len(rows),
        'all_gate_up_equal': all(r['cpu_gpu_gate_bitwise_equal'] and r['cpu_gpu_up_bitwise_equal'] for r in rows),
        'cpu_gpu_hidden_q8_1_equal_count': sum(r['cpu_gpu_hidden_q8_1_bitwise_equal'] for r in rows),
        'cpu_gpu_final_output_equal_count': sum(r['cpu_gpu_final_output_bitwise_equal'] for r in rows),
        'host_expf_q8_matches_count': sum(r['host_quantizer_candidates']['libm_expf']['different_q8_1_blocks'] == 0 for r in rows),
        'host_exp2f_q8_matches_count': sum(r['host_quantizer_candidates']['host_exp2f_log2e']['different_q8_1_blocks'] == 0 for r in rows),
        'host_exp2f_cpu_down_matches_count': sum(r['host_exp2f_cpu_down_words_different_vs_cuda'] == 0 for r in rows),
        'output': str(out),
    }, indent=2))


if __name__ == '__main__':
    main()
