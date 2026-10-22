#!/usr/bin/env python3
"""Fit blocked full-factorial log-response models using only Python stdlib."""
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE / "campaign/campaign.json"
ENERGY = HERE / "rail-energy.json"


def solve_and_inverse(matrix):
    """Gauss-Jordan solve A^-1, with partial pivoting and rank failure."""
    n = len(matrix)
    work = [list(row) + [float(i == j) for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(work[row][col]))
        if abs(work[pivot][col]) < 1e-10:
            raise ValueError(f"singular design normal matrix at column {col}")
        work[col], work[pivot] = work[pivot], work[col]
        scale = work[col][col]
        work[col] = [value / scale for value in work[col]]
        for row in range(n):
            if row == col:
                continue
            scale = work[row][col]
            if scale:
                work[row] = [a - scale * b for a, b in zip(work[row], work[col])]
    return [row[n:] for row in work]


def rank(matrix):
    work = [list(map(float, row)) for row in matrix]
    rows, cols = len(work), len(work[0])
    r = 0
    for col in range(cols):
        pivot = max(range(r, rows), key=lambda row: abs(work[row][col]), default=r)
        if r >= rows or abs(work[pivot][col]) < 1e-10:
            continue
        work[r], work[pivot] = work[pivot], work[r]
        scale = work[r][col]
        work[r] = [x / scale for x in work[r]]
        for row in range(rows):
            if row != r:
                scale = work[row][col]
                work[row] = [a - scale * b for a, b in zip(work[row], work[r])]
        r += 1
        if r == rows:
            break
    return r


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    campaign = json.loads(CAMPAIGN.read_text())
    energy = json.loads(ENERGY.read_text())
    energy_by_run = {
        row["run"]: row["joules_per_output_token_by_named_rail"]["VIN_SYS_5V0"]
        for row in energy["request_estimates"]
        if row["request_status"] == "estimated"
        and "VIN_SYS_5V0" in row["joules_per_output_token_by_named_rail"]
    }
    runs = [row for row in campaign["runs"] if row["status"] == "pass"]
    blocks = sorted({row["block"] for row in runs})
    terms = ["intercept"] + [f"block_{block}" for block in blocks[1:]] + [
        "workload_long", "kv_int8", "mtp4", "workload_long:kv_int8",
        "workload_long:mtp4", "kv_int8:mtp4", "workload_long:kv_int8:mtp4"]
    design, labels = [], []
    data = {name: [] for name in (
        "client_ttft_s", "client_total_s", "prompt_tps", "decode_tps",
        "VIN_SYS_5V0_j_per_output_token")}
    cell_counts = {}
    for run in runs:
        short_long = 1 if run["workload"].endswith("7501") else -1
        kv = 1 if run["kv"] == "int8" else -1
        mtp = 1 if run["window"] == 4 else -1
        row = [1.0] + [float(run["block"] == block) for block in blocks[1:]]
        factors = [short_long, kv, mtp]
        row += factors + [factors[0] * factors[1], factors[0] * factors[2],
                          factors[1] * factors[2], factors[0] * factors[1] * factors[2]]
        design.append(row)
        labels.append(run["name"])
        cell = (run["workload"], run["kv"], run["window"])
        cell_counts[cell] = cell_counts.get(cell, 0) + 1
        for metric in ("client_ttft_s", "client_total_s", "prompt_tps", "decode_tps"):
            data[metric].append(float(run["metrics"][metric]))
        data["VIN_SYS_5V0_j_per_output_token"].append(energy_by_run[run["name"]])

    n, p = len(design), len(terms)
    design_rank = rank(design)
    if design_rank != p:
        raise ValueError(f"factorial design is rank deficient: {design_rank} < {p}")
    expected = campaign["blocks"]
    if len(cell_counts) != 8 or any(value != expected for value in cell_counts.values()):
        raise ValueError(f"expected seven observations in all eight cells, found {cell_counts}")
    xtx = [[sum(row[i] * row[j] for row in design) for j in range(p)] for i in range(p)]
    xtx_inverse = solve_and_inverse(xtx)
    results = {}
    tcrit = 2.018  # two-sided 95% Student-t critical value, 42 residual degrees of freedom
    contrasts = {
        "workload_long": ("workload long versus short", 2),
        "kv_int8": ("INT8 versus FP16 KV", 2),
        "mtp4": ("MTP4 versus off", 2),
        "workload_long:kv_int8": ("workload × KV ratio interaction", 4),
        "workload_long:mtp4": ("workload × MTP ratio interaction", 4),
        "kv_int8:mtp4": ("KV × MTP ratio interaction", 4),
        "workload_long:kv_int8:mtp4": ("three-way ratio interaction", 8),
    }
    for metric, raw in data.items():
        y = [math.log(value) for value in raw]
        xty = [sum(row[i] * value for row, value in zip(design, y)) for i in range(p)]
        beta = [sum(xtx_inverse[i][j] * xty[j] for j in range(p)) for i in range(p)]
        fitted = [dot(row, beta) for row in design]
        residuals = [actual - pred for actual, pred in zip(y, fitted)]
        df = n - p
        sse = sum(value * value for value in residuals)
        mse = sse / df
        mean = sum(y) / n
        sst = sum((value - mean) ** 2 for value in y)
        r_squared = 1 - sse / sst if sst else 1.0
        leverage = [dot(row, [dot(xtx_inverse[i], row) for i in range(p)]) for row in design]
        standardized = [residual / math.sqrt(mse * max(1e-12, 1 - h))
                        for residual, h in zip(residuals, leverage)]
        predictions = []
        for term, (meaning, multiplier) in contrasts.items():
            index = terms.index(term)
            estimate = multiplier * beta[index]
            se = multiplier * math.sqrt(mse * xtx_inverse[index][index])
            predictions.append({
                "term": term, "meaning": meaning,
                "effect_percent": (math.exp(estimate) - 1) * 100,
                "ci95_percent": [(math.exp(estimate - tcrit * se) - 1) * 100,
                                 (math.exp(estimate + tcrit * se) - 1) * 100],
                "log_contrast": estimate, "log_contrast_se": se})
        flagged = [{"arm": labels[i], "studentized_residual": standardized[i],
                    "observed": raw[i], "fitted_geometric": math.exp(fitted[i])}
                   for i in range(n) if abs(standardized[i]) >= 3]
        results[metric] = {
            "transformation": "natural log of positive response",
            "rank": design_rank, "columns": p, "n": n, "residual_df": df,
            "r_squared": r_squared, "residual_rmse_log": math.sqrt(mse),
            "max_abs_studentized_residual": max(abs(x) for x in standardized),
            "arms_abs_studentized_residual_ge_3": flagged,
            "contrasts": predictions}

    output = {
        "schema": 1,
        "campaign": "campaign/campaign.json",
        "model": "balanced OLS on log response, fixed block effects plus all workload × KV × MTP terms",
        "coding": {"workload": "short=-1, long=+1", "kv": "fp16=-1, int8=+1",
                   "mtp": "off=-1, window4=+1"},
        "interpretation": "Main effects are high/low geometric-mean ratios; two-way and three-way terms are ratios of ratios. The paired bootstrap audit remains primary. Model intervals are diagnostic and rely on the log-OLS residual assumptions.",
        "n": n, "columns": p, "rank": design_rank, "residual_df": n - p,
        "cell_counts": [{"workload": workload, "kv": kv, "mtp_window": window, "n": count}
                        for (workload, kv, window), count in sorted(cell_counts.items())],
        "metrics": results}
    target = HERE / "factorial-model.json"
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"rank": design_rank, "columns": p, "n": n, "residual_df": n-p,
                      "models": {name: {"r_squared": row["r_squared"],
                                         "max_abs_studentized_residual": row["max_abs_studentized_residual"],
                                         "flagged_arms": row["arms_abs_studentized_residual_ge_3"],
                                         "contrasts": row["contrasts"]}
                                 for name, row in results.items()}}, indent=2))


if __name__ == "__main__":
    main()
