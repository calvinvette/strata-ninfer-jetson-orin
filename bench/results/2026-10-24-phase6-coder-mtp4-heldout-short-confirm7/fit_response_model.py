#!/usr/bin/env python3
"""Fit log-response MTP x KV models with fixed randomized-block effects."""
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / 'campaign.json'
INPUT = json.loads(CAMPAIGN.read_text())
RUNS = [r for r in INPUT['runs'] if r.get('status') == 'pass']
BLOCKS = sorted({r['block'] for r in RUNS})
KVS = INPUT['kv_formats']
WINDOW = max(INPUT['mtp_windows'])
METRICS = ('prompt_tps', 'decode_tps', 'client_ttft_s', 'client_total_s')
T_CRIT_95_DF18 = 2.100922


def solve(matrix, vector):
    n = len(vector)
    a = [list(row) + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError('rank-deficient design')
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [v / scale for v in a[col]]
        for row in range(n):
            if row == col:
                continue
            scale = a[row][col]
            a[row] = [x - scale * y for x, y in zip(a[row], a[col])]
    return [a[i][-1] for i in range(n)]


def inverse(matrix):
    n = len(matrix)
    columns = []
    for col in range(n):
        rhs = [1.0 if i == col else 0.0 for i in range(n)]
        columns.append(solve(matrix, rhs))
    return [[columns[j][i] for j in range(n)] for i in range(n)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def design_row(run):
    m = 0.5 if run['window'] == WINDOW else -0.5
    kv = 0.5 if run['kv'] == KVS[1] else -0.5
    # Intercept, six fixed block contrasts, MTP, KV, and MTP:KV.
    return [1.0] + [1.0 if run['block'] == b else 0.0 for b in BLOCKS[1:]] + [m, kv, m * kv]


rows = []
for run in RUNS:
    y = run['metrics']
    if not all(y.get(metric, 0) > 0 for metric in METRICS):
        raise ValueError(f"nonpositive response in {run['name']}")
    rows.append((run, design_row(run)))
if len(RUNS) != 28 or len(BLOCKS) != 7:
    raise ValueError(f'expected complete seven-block factorial, got {len(RUNS)} runs/{len(BLOCKS)} blocks')
if len({(r['block'], r['kv'], r['window']) for r in RUNS}) != 28:
    raise ValueError('duplicate or missing treatment cell')

p = len(rows[0][1])
xtx = [[sum(x[i] * x[j] for _, x in rows) for j in range(p)] for i in range(p)]
xtx_inv = inverse(xtx)
results = {}
for metric in METRICS:
    ys = [math.log(run['metrics'][metric]) for run, _ in rows]
    xty = [sum(x[j] * y for y, (_, x) in zip(ys, rows)) for j in range(p)]
    beta = solve(xtx, xty)
    fitted = [dot(x, beta) for _, x in rows]
    residuals = [y - yh for y, yh in zip(ys, fitted)]
    df = len(ys) - p
    sse = sum(r * r for r in residuals)
    sigma2 = sse / df
    sigma = math.sqrt(sigma2)
    mean_y = statistics.mean(ys)
    sst = sum((y - mean_y) ** 2 for y in ys)
    estimates = {}
    for name, col in [('mtp_effect', -3), ('kv_effect', -2), ('mtp_by_kv_interaction', -1)]:
        b = beta[col]
        se = math.sqrt(sigma2 * xtx_inv[col][col])
        lo, hi = b - T_CRIT_95_DF18 * se, b + T_CRIT_95_DF18 * se
        estimates[name] = {'log_coefficient': b, 'standard_error': se,
                           'percent_effect': (math.exp(b) - 1) * 100,
                           'model_95_interval_percent': [(math.exp(lo) - 1) * 100,
                                                         (math.exp(hi) - 1) * 100]}
    standardized = [r / sigma for r in residuals] if sigma else [0.0 for r in residuals]
    residual_records = [
        {'run': run['name'], 'block': run['block'], 'kv': run['kv'],
         'mtp_window': run['window'], 'standardized_residual': standardized[i]}
        for i, (run, _) in enumerate(rows)]
    largest_residual = max(residual_records, key=lambda r: abs(r['standardized_residual']))
    results[metric] = {
        'factor_effects': estimates,
        'diagnostics': {'observations': len(ys), 'parameters': p, 'rank': p,
                        'residual_degrees_of_freedom': df,
                        'r_squared_log_response': 1 - sse / sst if sst else None,
                        'rmse_log_response': math.sqrt(sse / len(ys)),
                        'residual_sigma_log_response': sigma,
                        'max_abs_standardized_residual': max(map(abs, standardized)),
                        'largest_residual_run': largest_residual,
                        'standardized_residuals_by_block': {
                            str(block): [standardized[i] for i, (run, _) in enumerate(rows) if run['block'] == block]
                            for block in BLOCKS},
                        'fit_formula': 'log(response) ~ block fixed effects + MTP + KV + MTP:KV'}}

result = {'schema': 1,
          'model_scope': 'Single 512-token held-out retrieval/arithmetic workload; MTP off/4 x FP16/INT8 KV; seven randomized blocks.',
          'transformation': 'Natural logarithm of positive client prompt throughput, decode throughput, TTFT seconds, and total request seconds.',
          'coded_factors': {'mtp': {'off': -0.5, 'candidate': 0.5},
                            'kv': {KVS[0]: -0.5, KVS[1]: 0.5}},
          'block_effects': 'Six fixed block indicators; treatment x block variation remains in residuals.',
          'confidence_intervals': 'Model-based 95% t intervals with 18 residual degrees of freedom (t=2.100922), exponentiated to percent change.',
          'design_rank': p, 'parameter_count': p, 'residual_degrees_of_freedom': len(RUNS) - p,
          'metrics': results}
(HERE / 'response-model.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: {'factor_effects': v['factor_effects'], 'diagnostics': v['diagnostics']} for k, v in results.items()}, indent=2))
