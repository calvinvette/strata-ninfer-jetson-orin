#!/usr/bin/env python3
"""Create a dependency-free SVG summary of paired E6 same-map backend screens."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

SERIES = [
    ("2K", "actual_tokens", "backend_same_learned_map_2k", "metrics", "ninfer_pct_change", "bootstrap95_pct"),
    ("4K", "actual_tokens", "actual_4k_backend_screen", "campaign.metrics", "pct_change", "bootstrap95_pct"),
    ("8K", "actual_tokens", "actual_8k_task", "backend_screen.screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
    ("16K", "actual_tokens", "actual_16k_task", "backend_screen.screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
    ("32K", "actual_tokens", "actual_32k_task", "backend_screen.screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
    ("64K", "actual_tokens", "actual_64k_task", "backend_screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
    ("128K", "actual_tokens", "actual_128k_task", "backend_screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
    ("240K", "actual_tokens", "actual_240k_task", "backend_screen.performance", "paired_median_change_percent", "bootstrap_95_percentile_interval_percent"),
]
METRICS = [
    ("decode_tps", "Decode throughput", "% change, positive favors NInfer"),
    ("prompt_tps", "Prompt throughput", "% change, positive favors NInfer"),
    ("ttft", "First visible token", "% change, negative favors NInfer"),
    ("client", "Client request duration", "% change, negative favors NInfer"),
]
ALIASES = {"ttft": ("ttft_s", "first_visible_s"), "client": ("client_s",)}


def path_get(obj, dotted):
    for key in dotted.split("."):
        obj = obj[key]
    return obj


def collect(evidence, codegen_evidence=None, ledger_evidence=None,
            ledger_cap4k_evidence=None, ledger_cap16k_evidence=None,
            ledger_cap32k_evidence=None, ledger_cap64k_evidence=None,
            code8k_evidence=None, ledger_cap8k_replication_evidence=None,
            ledger_cap8k_pooled_summary=None):
    rows = []
    for label, _, root_key, metric_path, point_key, interval_key in SERIES:
        root = path_get(evidence, root_key)
        metrics = path_get(root, metric_path)
        item = {"label": label, "metrics": {}}
        for name, _, _ in METRICS:
            metric = None
            for key in ALIASES.get(name, (name,)):
                if key in metrics:
                    metric = metrics[key]
                    break
            if metric is None:
                raise ValueError(f"missing {name} under {root_key}.{metric_path}")
            item["metrics"][name] = {"effect": metric[point_key], "interval": metric[interval_key]}
        if label == "2K":
            item["label"] = "2K retrieval"
        rows.append(item)
    if codegen_evidence is not None:
        summary = codegen_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "2K code", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(1, item)
    if ledger_evidence is not None:
        summary = ledger_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L8K-A", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(2, item)
    if ledger_cap4k_evidence is not None:
        summary = ledger_cap4k_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L@4K", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(2, item)
    if ledger_cap16k_evidence is not None:
        summary = ledger_cap16k_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L@16K", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(4, item)
    if ledger_cap32k_evidence is not None:
        summary = ledger_cap32k_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L@32K", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(5, item)
    if ledger_cap64k_evidence is not None:
        summary = ledger_cap64k_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L@64K", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(6, item)
    if code8k_evidence is not None:
        summary = code8k_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "8K code", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        rows.insert(7, item)
    if ledger_cap8k_replication_evidence is not None:
        summary = ledger_cap8k_replication_evidence["paired_summary"]
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L8K-B", "metrics": {}}
        for name, key in aliases.items():
            metric = summary[key]
            item["metrics"][name] = {
                "effect": (metric["median_within_block_candidate_over_baseline"] - 1) * 100,
                "interval": [(x - 1) * 100 for x in metric["paired_bootstrap_95_interval"]],
            }
        at = next((i for i, row in enumerate(rows) if row["label"] == "L8K-A"), len(rows) - 1) + 1
        rows.insert(at, item)
    if ledger_cap8k_pooled_summary is not None:
        aliases = {"decode_tps": "decode_tps", "prompt_tps": "prompt_tps",
                   "ttft": "client_ttft_s", "client": "client_total_s"}
        item = {"label": "L8K-6", "metrics": {}}
        for name, key in aliases.items():
            metric = ledger_cap8k_pooled_summary["metrics"][key]
            item["metrics"][name] = {
                "effect": metric["paired_median_effect_percent"],
                "interval": metric["paired_bootstrap_95_interval_effect_percent"],
            }
        at = next((i for i, row in enumerate(rows) if row["label"] == "L8K-B"), len(rows) - 1) + 1
        rows.insert(at, item)
    return rows


def svg_chart(rows):
    width, panel_h, top, bottom = 1180, 205, 85, 35
    height = top + len(METRICS) * panel_h + bottom
    left, right = 95, 1145
    xs = [left + i * (right-left) / (len(rows)-1) for i in range(len(rows))]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#fff"/>',
             '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#17212b}.small{font-size:12px}.label{font-size:14px}.title{font-size:22px;font-weight:bold}.panel{font-size:17px;font-weight:bold}.grid{stroke:#d7dde3;stroke-width:1}.zero{stroke:#536575;stroke-width:1.5;stroke-dasharray:5 4}.err{stroke:#176b87;stroke-width:3}.cap{stroke:#176b87;stroke-width:2}.point{fill:#e06b32;stroke:#873b1b;stroke-width:1.2}</style>',
             '<text x="40" y="35" class="title">Q2_0 same-map backend screens</text>',
             '<text x="40" y="57" class="small">Strict NInfer relative to Strata · retrieval, code and 2K ledger tasks · 95% paired intervals (three-pair screens; six-pair pooled 8K-cap estimate)</text>']
    for p, (metric, title, subtitle) in enumerate(METRICS):
        y0 = top + p * panel_h
        chart_top, chart_bottom = y0 + 34, y0 + panel_h - 42
        vals = [row['metrics'][metric] for row in rows]
        lo = min(x['interval'][0] for x in vals)
        hi = max(x['interval'][1] for x in vals)
        pad = max(1.0, (hi-lo)*0.12)
        lo, hi = min(lo-pad, 0), max(hi+pad, 0)
        def y(v): return chart_bottom - (v-lo)/(hi-lo)*(chart_bottom-chart_top)
        parts.append(f'<text x="40" y="{y0+18}" class="panel">{html.escape(title)}</text>')
        for frac in (0, .25, .5, .75, 1):
            value = lo + frac*(hi-lo); yy = y(value)
            cls = 'zero' if abs(value) < (hi-lo)*1e-8 else 'grid'
            parts.append(f'<line x1="{left}" x2="{right}" y1="{yy:.1f}" y2="{yy:.1f}" class="{cls}"/>')
            parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" class="small">{value:.1f}%</text>')
        for x,row,value in zip(xs,rows,vals):
            low, high = value['interval']; yy=y(value['effect']); ylo=y(low); yhi=y(high)
            parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{yhi:.1f}" y2="{ylo:.1f}" class="err"/>')
            parts.append(f'<line x1="{x-6:.1f}" x2="{x+6:.1f}" y1="{yhi:.1f}" y2="{yhi:.1f}" class="cap"/>')
            parts.append(f'<line x1="{x-6:.1f}" x2="{x+6:.1f}" y1="{ylo:.1f}" y2="{ylo:.1f}" class="cap"/>')
            parts.append(f'<rect x="{x-4:.1f}" y="{yy-4:.1f}" width="8" height="8" fill="#e06b32" stroke="#873b1b" stroke-width="1.2"><title>{row["label"]}: {value["effect"]:+.2f}% [{low:+.2f}%, {high:+.2f}%]</title></rect>')
            parts.append(f'<text x="{x:.1f}" y="{chart_bottom+20}" text-anchor="middle" class="label">{row["label"]}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)+'\n'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path,default=Path('bench/results/2026-10-31-e6-q2-fixed-map-ORBIT-screen/evidence.json'))
    parser.add_argument('--codegen-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-code-generation-screen/evidence.json'))
    parser.add_argument('--ledger-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-aggregation-screen/evidence.json'))
    parser.add_argument('--ledger-cap4k-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-4096/evidence.json'))
    parser.add_argument('--ledger-cap16k-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-16384/evidence.json'))
    parser.add_argument('--ledger-cap32k-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-32768/evidence.json'))
    parser.add_argument('--ledger-cap64k-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-65536/evidence.json'))
    parser.add_argument('--code8k-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-code-generation-8k-screen/evidence.json'))
    parser.add_argument('--ledger-cap8k-replication-evidence',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-8192/evidence.json'))
    parser.add_argument('--ledger-cap8k-pooled-summary',type=Path,default=Path('bench/results/2026-11-04-e6-q2-ledger-capacity-8192/same-day-pooled-summary.json'))
    parser.add_argument('--output',type=Path,default=Path('bench/results/2026-10-31-e6-q2-fixed-map-ORBIT-screen/same-map-backend-screens.svg'))
    args=parser.parse_args()
    codegen = json.loads(args.codegen_evidence.read_text()) if args.codegen_evidence.exists() else None
    ledger = json.loads(args.ledger_evidence.read_text()) if args.ledger_evidence.exists() else None
    ledger_cap4k = json.loads(args.ledger_cap4k_evidence.read_text()) if args.ledger_cap4k_evidence.exists() else None
    ledger_cap16k = json.loads(args.ledger_cap16k_evidence.read_text()) if args.ledger_cap16k_evidence.exists() else None
    ledger_cap32k = json.loads(args.ledger_cap32k_evidence.read_text()) if args.ledger_cap32k_evidence.exists() else None
    ledger_cap64k = json.loads(args.ledger_cap64k_evidence.read_text()) if args.ledger_cap64k_evidence.exists() else None
    code8k = json.loads(args.code8k_evidence.read_text()) if args.code8k_evidence.exists() else None
    ledger_cap8k_replication = json.loads(args.ledger_cap8k_replication_evidence.read_text()) if args.ledger_cap8k_replication_evidence.exists() else None
    ledger_cap8k_pooled = json.loads(args.ledger_cap8k_pooled_summary.read_text()) if args.ledger_cap8k_pooled_summary.exists() else None
    rows=collect(json.loads(args.evidence.read_text()), codegen, ledger, ledger_cap4k, ledger_cap16k, ledger_cap32k, ledger_cap64k, code8k, ledger_cap8k_replication, ledger_cap8k_pooled)
    args.output.write_text(svg_chart(rows))
    print(f'wrote {args.output} with {len(rows)} task/context cells and {len(METRICS)} paired metrics')

if __name__=='__main__':
    main()
