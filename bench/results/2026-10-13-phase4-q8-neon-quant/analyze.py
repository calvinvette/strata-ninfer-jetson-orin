#!/usr/bin/env python3
"""Summarize independent scalar-versus-ggml ARM Q8_0 quantization runs."""
import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
pattern = re.compile(
    r'^sample=(\d+) order=(\S+) scalar_ms=([0-9.]+) ggml_arm_ms=([0-9.]+) delta_pct=(-?[0-9.]+)$')
runs = []
for index in range(1, 4):
    samples = []
    for line in (ROOT / f'rep-{index:02d}.txt').read_text().splitlines():
        match = pattern.match(line)
        if match:
            samples.append({'sample': int(match.group(1)), 'order': match.group(2),
                            'scalar_ms': float(match.group(3)),
                            'ggml_arm_ms': float(match.group(4)),
                            'ggml_vs_scalar_pct': float(match.group(5))})
    assert len(samples) == 9
    result = (ROOT / f'rep-{index:02d}.json').read_text()
    meta = json.loads(result)
    assert meta['returncode'] == 0
    terminal = (ROOT / f'rep-{index:02d}.txt').read_text().splitlines()[-1]
    assert 'mismatches=0' in terminal and 'contract=bit-identical Q8_0' in terminal
    runs.append({
        'rep': index, 'seed': meta['seed'], 'returncode': 0, 'samples': samples,
        'scalar_median_ms_per_16x256_rows': statistics.median(x['scalar_ms'] for x in samples),
        'ggml_arm_median_ms_per_16x256_rows': statistics.median(x['ggml_arm_ms'] for x in samples),
        'median_paired_delta_pct': statistics.median(x['ggml_vs_scalar_pct'] for x in samples),
    })
scalar = [x['scalar_median_ms_per_16x256_rows'] for x in runs]
arm = [x['ggml_arm_median_ms_per_16x256_rows'] for x in runs]
paired = [x['median_paired_delta_pct'] for x in runs]
out = {
    'scope': 'Q8_0 activation quantization operator only; not full expert or request timing',
    'rows': 256, 'width': 2560, 'iterations_per_sample': 16, 'samples_per_process': 9,
    'independent_processes': len(runs), 'bit_mismatches': 0,
    'process_median_scalar_ms': scalar, 'process_median_ggml_arm_ms': arm,
    'process_median_paired_delta_pct': paired,
    'median_of_process_medians_scalar_ms': statistics.median(scalar),
    'median_of_process_medians_ggml_arm_ms': statistics.median(arm),
    'median_of_process_median_deltas_pct': statistics.median(paired),
    'process_median_delta_range_pct': [min(paired), max(paired)],
    'runs': runs,
    'limits': [
        'Strata scalar arm is the explicit Q8_0 oracle path; default Strata Q8_1 remains unchanged',
        'ggml ARM Q8_0 uses the compiled Cortex-A78AE NEON implementation and matches Q8_0 bytes exactly',
        'operator-only quantization timing excludes expert dot products, GPU work and end-to-end serving',
        'no confidence interval is inferred from repeated samples within only three processes',
        'dynamic clock observations are retained; no clocks were changed',
    ],
}
(ROOT / 'analysis.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({k: out[k] for k in (
    'median_of_process_medians_scalar_ms', 'median_of_process_medians_ggml_arm_ms',
    'median_of_process_median_deltas_pct', 'process_median_delta_range_pct',
    'bit_mismatches')}, indent=2))
