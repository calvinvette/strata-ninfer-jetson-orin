#!/usr/bin/env python3
"""Render paired request-time and named-rail energy changes as a compact SVG."""
import argparse
import html
import json
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
root = ap.parse_args().root.resolve()
data = json.loads((root / "analysis.json").read_text())
metrics = [
    ("request_ms", "Request time", "Lower is faster"),
    ("vin_sys_j_per_token", "VIN_SYS_5V0 rail / output token", "Board rail estimate; includes idle/background"),
]
width, height = 900, 500
left, right, top, bottom = 100, 840, 85, 390
ymin, ymax = -55.0, 5.0


def y(value):
    return top + (ymax - value) * (bottom - top) / (ymax - ymin)


parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#202124}.small{font-size:13px}.axis{stroke:#444;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.bar{fill:#2b6cb0}.ci{stroke:#182c43;stroke-width:2}</style>',
         '<text x="450" y="30" text-anchor="middle" font-size="20" font-weight="bold">Current-source Q2_0: prefill chunk 128 vs 32</text>',
         '<text x="450" y="54" text-anchor="middle" class="small">Seven paired blocks; negative change favors chunk 128</text>']
for tick in (-50, -40, -30, -20, -10, 0):
    yy = y(tick)
    parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" class="grid"/>')
    parts.append(f'<text x="{left-12}" y="{yy+4:.1f}" text-anchor="end" class="small">{tick}%</text>')
parts.append(f'<line x1="{left}" y1="{y(0):.1f}" x2="{right}" y2="{y(0):.1f}" class="axis"/>')
for idx, (key, title, note) in enumerate(metrics):
    x = 300 + idx * 360
    item = data["paired_contrasts"][key]
    value = item["chunk128_vs_chunk32_median_percent_change"]
    lo, hi = item["paired_block_bootstrap_95pct_percent"]
    yy, ylo, yhi = y(value), y(lo), y(hi)
    parts.append(f'<rect x="{x-30}" y="{y(0):.1f}" width="60" height="{yy-y(0):.1f}" class="bar"/>')
    parts.append(f'<line x1="{x}" y1="{ylo:.1f}" x2="{x}" y2="{yhi:.1f}" class="ci"/>')
    parts.append(f'<line x1="{x-9}" y1="{ylo:.1f}" x2="{x+9}" y2="{ylo:.1f}" class="ci"/>')
    parts.append(f'<line x1="{x-9}" y1="{yhi:.1f}" x2="{x+9}" y2="{yhi:.1f}" class="ci"/>')
    parts.append(f'<text x="{x}" y="{yy+23:.1f}" text-anchor="middle" font-size="15" font-weight="bold">{value:.2f}%</text>')
    parts.append(f'<text x="{x}" y="{bottom+28}" text-anchor="middle" font-size="15">{html.escape(title)}</text>')
    parts.append(f'<text x="{x}" y="{bottom+48}" text-anchor="middle" class="small">95% paired-block bootstrap: {lo:.2f}% to {hi:.2f}%</text>')
    parts.append(f'<text x="{x}" y="{bottom+67}" text-anchor="middle" class="small">{html.escape(note)}</text>')
parts.extend([f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
              '<text x="450" y="480" text-anchor="middle" class="small">Percent change in chunk 128 relative to chunk 32</text>',
              '</svg>'])
(root / "paired-effects.svg").write_text("\n".join(parts) + "\n")
