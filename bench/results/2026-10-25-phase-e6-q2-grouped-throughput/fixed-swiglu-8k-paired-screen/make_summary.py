#!/usr/bin/env python3
"""Summarize paired 8K Q2_0 service screening and export CSV/JSON/SVG."""
from __future__ import annotations

import csv
import json
import random
import statistics
from pathlib import Path

OUT = Path(__file__).resolve().parent
CELLS = (
    "pp512+tg64", "pp2048+tg128", "pp172+tg64", "pp557+tg64", "pp1069+tg64",
)
METRICS = {
    "ttft": ("TTFT latency change", "latency"),
    "client_total": ("Full client latency change", "latency"),
    "prompt_tps": ("Prompt throughput change", "throughput"),
    "decode_tps": ("Decode throughput change", "throughput"),
}
BOOTSTRAP_DRAWS = 100_000
BOOTSTRAP_SEED = 20261025


def percentile_interval(values: list[float], *, seed: int) -> list[float]:
    rng = random.Random(seed)
    draws = sorted(
        statistics.median(values[rng.randrange(len(values))] for _ in values)
        for _ in range(BOOTSTRAP_DRAWS)
    )
    return [draws[int((BOOTSTRAP_DRAWS - 1) * .025)],
            draws[int((BOOTSTRAP_DRAWS - 1) * .975)]]


def read_pair(pair: int, arm: str) -> tuple[dict[str, dict], dict]:
    folder = OUT / f"pair-{pair}" / "8192"
    matrix = json.loads((OUT / f"pair-{pair}" / "matrix.json").read_text())
    requests = json.loads((folder / arm / "requests.json").read_text())
    measured = {row["cell"]: row for row in requests["checks"] if not row["warmup"]}
    if len(measured) != len(CELLS) or any(row["status"] != "pass" for row in measured.values()):
        raise RuntimeError(f"pair {pair} {arm}: expected five passing measured requests")
    return measured, next(row for row in matrix["cells"] if row["arm"] == arm)


def paired_data() -> dict:
    pairs = []
    for pair in (1, 2, 3):
        strata, s_matrix = read_pair(pair, "strata")
        ninfer, n_matrix = read_pair(pair, "ninfer")
        if s_matrix["status"] != "pass" or n_matrix["status"] != "pass":
            raise RuntimeError(f"pair {pair}: service supervision did not pass")
        if s_matrix["residency_sha256"] != n_matrix["residency_sha256"]:
            raise RuntimeError(f"pair {pair}: resident-map hash mismatch")
        pair_row = {"pair": pair, "resident_map_sha256": s_matrix["residency_sha256"],
                    "minimum_available_bytes": min(s_matrix["minimum_available_bytes"],
                                                    n_matrix["minimum_available_bytes"]),
                    "workloads": {}}
        for cell in CELLS:
            s, n = strata[cell], ninfer[cell]
            if s["output_sha256"] != n["output_sha256"]:
                raise RuntimeError(f"pair {pair} {cell}: response hash mismatch")
            st, nt = s["response"]["timings"], n["response"]["timings"]
            raw = {
                "ttft": (s["stream_observation"]["first_visible_delta_s"],
                         n["stream_observation"]["first_visible_delta_s"]),
                "client_total": (s["client_elapsed_s"], n["client_elapsed_s"]),
                "prompt_tps": (st["prompt_per_second"], nt["prompt_per_second"]),
                "decode_tps": (st["predicted_per_second"], nt["predicted_per_second"]),
            }
            metrics = {}
            for name, (control, candidate) in raw.items():
                metrics[name] = {
                    "strata": control, "ninfer": candidate,
                    "change_pct": (candidate / control - 1) * 100,
                }
            pair_row["workloads"][cell] = {
                "metrics": metrics,
                "output_sha256": s["output_sha256"],
            }
        pairs.append(pair_row)

    summaries = []
    for cell_index, cell in enumerate(CELLS):
        for metric_index, metric in enumerate(METRICS):
            changes = [row["workloads"][cell]["metrics"][metric]["change_pct"] for row in pairs]
            summaries.append({
                "workload": cell, "metric": metric,
                "metric_label": METRICS[metric][0], "effect_kind": METRICS[metric][1],
                "pairs": len(changes), "pair_changes_pct": changes,
                "median_change_pct": statistics.median(changes),
                "bootstrap_95pct_interval_pct": percentile_interval(
                    changes, seed=BOOTSTRAP_SEED + cell_index * 10 + metric_index),
                "bootstrap_draws": BOOTSTRAP_DRAWS,
            })
    return {
        "date": "2026-10-25", "model": "Qwen3.8-Flash-Next Coder Q2_0",
        "context": 8192, "binary_sha256": "c7301655b1a8d2569ab8744d92259b6d05b2baccb8bd04ad86da724a42bd4d75",
        "supported_model_scope": "Q2_0 is the only model codec currently supported by this NInfer expert path; other model variants are unsupported.",
        "screening_only": True, "pair_count": len(pairs),
        "all_response_hashes_matched": True,
        "resident_map_sha256": pairs[0]["resident_map_sha256"],
        "minimum_available_bytes": min(row["minimum_available_bytes"] for row in pairs),
        "metrics_definition": "Negative latency changes and positive throughput changes favor NInfer.",
        "pairs": pairs, "summaries": summaries,
    }


def svg_chart(data: dict, path: Path) -> None:
    width, height = 1360, 650
    left, right, top, bottom = 90, 36, 100, 150
    panel_gap = 95
    panel_width = (width - left - right - panel_gap) / 2
    plot_top, plot_bottom = top + 42, height - bottom
    y_min, y_max = -10.0, 10.0
    colors = ["#3b82f6", "#f97316", "#16a34a"]
    cell_labels = ["512 + 64", "2,048 + 128", "172 + 64", "557 + 64", "1,069 + 64"]

    def esc(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def y_pos(value: float) -> float:
        return plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top)

    fragments = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.small{font-size:12px}.tick{font-size:12px;fill:#465266}.title{font-size:23px;font-weight:700}.subtitle{font-size:14px;fill:#465266}</style>',
        '<text x="50%" y="35" text-anchor="middle" class="title">Corrected Q2_0 NInfer 8K paired screen</text>',
        '<text x="50%" y="61" text-anchor="middle" class="subtitle">Three randomized process pairs per workload; points are paired changes, whiskers are 95% paired-bootstrap intervals</text>',
    ]
    panel_specs = [("ttft", "Client TTFT change (%)"),
                   ("client_total", "Full client completion change (%)")]
    for panel_index, (metric, title) in enumerate(panel_specs):
        x0 = left + panel_index * (panel_width + panel_gap)
        x1 = x0 + panel_width
        fragments.append(f'<text x="{(x0+x1)/2}" y="90" text-anchor="middle" font-size="17" font-weight="700">{esc(title)}</text>')
        for tick in (-10, -5, 0, 5, 10):
            y = y_pos(tick)
            stroke = "#64748b" if tick == 0 else "#dbe2ea"
            sw = "2" if tick == 0 else "1"
            fragments.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.2f}" y2="{y:.2f}" stroke="{stroke}" stroke-width="{sw}"/>')
            fragments.append(f'<text x="{x0-12}" y="{y+4:.2f}" text-anchor="end" class="tick">{tick}</text>')
        step = panel_width / len(CELLS)
        for i, (cell, label) in enumerate(zip(CELLS, cell_labels)):
            cx = x0 + step * (i + .5)
            summary = next(row for row in data["summaries"] if row["workload"] == cell and row["metric"] == metric)
            lo, hi = summary["bootstrap_95pct_interval_pct"]
            med = summary["median_change_pct"]
            fragments.append(f'<line x1="{cx:.2f}" x2="{cx:.2f}" y1="{y_pos(lo):.2f}" y2="{y_pos(hi):.2f}" stroke="#111827" stroke-width="2"/>')
            fragments.append(f'<line x1="{cx-8:.2f}" x2="{cx+8:.2f}" y1="{y_pos(lo):.2f}" y2="{y_pos(lo):.2f}" stroke="#111827" stroke-width="2"/>')
            fragments.append(f'<line x1="{cx-8:.2f}" x2="{cx+8:.2f}" y1="{y_pos(hi):.2f}" y2="{y_pos(hi):.2f}" stroke="#111827" stroke-width="2"/>')
            for pair_index, pair in enumerate(data["pairs"]):
                effect = pair["workloads"][cell]["metrics"][metric]["change_pct"]
                px = cx + (pair_index - 1) * 12
                fragments.append(f'<circle cx="{px:.2f}" cy="{y_pos(effect):.2f}" r="5" fill="{colors[pair_index]}" stroke="white" stroke-width="1"/>')
            diamond = f'{cx:.2f},{y_pos(med)-7:.2f} {cx+7:.2f},{y_pos(med):.2f} {cx:.2f},{y_pos(med)+7:.2f} {cx-7:.2f},{y_pos(med):.2f}'
            fragments.append(f'<polygon points="{diamond}" fill="#111827"/>')
            fragments.append(f'<text x="{cx:.2f}" y="{plot_bottom+26}" text-anchor="middle" class="tick">{esc(label)}</text>')
        fragments.append(f'<text x="{(x0+x1)/2:.2f}" y="{height-86}" text-anchor="middle" class="small">NInfer relative to Strata; negative latency favors NInfer</text>')
    legend_y = height - 43
    for index, color in enumerate(colors, start=1):
        x = width / 2 - 120 + (index - 1) * 75
        fragments.append(f'<circle cx="{x}" cy="{legend_y}" r="5" fill="{color}"/><text x="{x+10}" y="{legend_y+4}" class="small">pair {index}</text>')
    fragments.append(f'<text x="{width/2+135}" y="{legend_y+4}" class="small">black diamond: median; whisker: bootstrap interval</text>')
    fragments.append(f'<text x="{width/2}" y="{height-10}" text-anchor="middle" class="small">Q2_0 is the only supported model; combined supported-model scope is therefore Q2_0 only. Screening results, not confirmation.</text>')
    fragments.append('</svg>')
    path.write_text('\n'.join(fragments) + '\n')


def main() -> None:
    data = paired_data()
    (OUT / "summary.json").write_text(json.dumps(data, indent=2) + "\n")
    with (OUT / "paired-effects.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            "workload", "metric", "effect_kind", "pairs", "pair_1_pct", "pair_2_pct",
            "pair_3_pct", "median_change_pct", "bootstrap_95_lo_pct", "bootstrap_95_hi_pct"))
        writer.writeheader()
        for row in data["summaries"]:
            writer.writerow({
                "workload": row["workload"], "metric": row["metric"],
                "effect_kind": row["effect_kind"], "pairs": row["pairs"],
                "pair_1_pct": row["pair_changes_pct"][0], "pair_2_pct": row["pair_changes_pct"][1],
                "pair_3_pct": row["pair_changes_pct"][2], "median_change_pct": row["median_change_pct"],
                "bootstrap_95_lo_pct": row["bootstrap_95pct_interval_pct"][0],
                "bootstrap_95_hi_pct": row["bootstrap_95pct_interval_pct"][1],
            })
    svg_chart(data, OUT / "q2_0-8k-effects.svg")


if __name__ == "__main__":
    main()
