#!/usr/bin/env python3
"""Render paired-effect bootstrap intervals to a dependency-free SVG."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / 'analysis.json').read_text())['paired_factor_effects']
CONTRASTS = [
    ('capture_mtp0', 'Capture / off'),
    ('capture_mtp2', 'Capture / MTP2'),
    ('mtp2_captured', 'MTP2 / captured'),
    ('mtp2_eager', 'MTP2 / eager'),
    ('capture_x_mtp', 'Capture × MTP2'),
]
METRICS = [
    ('client_elapsed_s', 'Client request time (%)'),
    ('client_ttft_s', 'Client TTFT (%)'),
    ('prompt_tps', 'Prompt throughput (%)'),
    ('decode_tps', 'Decode throughput (%)'),
]
WIDTH, HEIGHT = 1280, 620
LEFT, PANEL, GAP = 230, 250, 35
XMIN, XMAX = -12.0, 12.0
TOP, ROW = 90, 62

def xcoord(value, x):
    return x + (value - XMIN) * PANEL / (XMAX - XMIN)

parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
         '<rect width="100%" height="100%" fill="white"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#202124}.title{font-size:22px;font-weight:bold}.panel{font-size:15px;font-weight:bold}.label{font-size:13px}.tick{font-size:11px;fill:#5f6368}.grid{stroke:#dadce0;stroke-width:1}.zero{stroke:#555;stroke-width:1.5}.ci{stroke:#2864a5;stroke-width:2}.point{fill:#174a7e}</style>',
         '<text x="32" y="32" class="title">Q2_0 graph × MTP2: paired effects and 95% bootstrap intervals</text>',
         '<text x="32" y="56" class="label">Seven randomized process pairs per contrast; positive values are candidate/baseline change. Latency: positive is slower; throughput: positive is faster.</text>']
for mi, (metric, title) in enumerate(METRICS):
    x0 = LEFT + mi * (PANEL + GAP)
    parts.append(f'<text x="{x0 + PANEL/2}" y="80" text-anchor="middle" class="panel">{html.escape(title)}</text>')
    for tick in (-10, -5, 0, 5, 10):
        x = xcoord(tick, x0)
        parts.append(f'<line x1="{x:.1f}" y1="{TOP-10}" x2="{x:.1f}" y2="{TOP+ROW*5-18}" class="{"zero" if tick == 0 else "grid"}"/>')
        parts.append(f'<text x="{x:.1f}" y="{TOP+ROW*5-2}" text-anchor="middle" class="tick">{tick:+d}%</text>')
    for ri, (prefix, label) in enumerate(CONTRASTS):
        y = TOP + ri * ROW + 18
        key = prefix + '_' + metric
        item = DATA[key]
        lo, hi = item['paired_bootstrap_95_interval_percent']
        mid = item['median_change_percent']
        if mi == 0:
            parts.append(f'<text x="24" y="{y+4}" class="label">{html.escape(label)}</text>')
        xa, xb, xm = xcoord(lo, x0), xcoord(hi, x0), xcoord(mid, x0)
        parts.append(f'<line x1="{xa:.1f}" y1="{y}" x2="{xb:.1f}" y2="{y}" class="ci"/>')
        parts.append(f'<line x1="{xa:.1f}" y1="{y-5}" x2="{xa:.1f}" y2="{y+5}" class="ci"/>')
        parts.append(f'<line x1="{xb:.1f}" y1="{y-5}" x2="{xb:.1f}" y2="{y+5}" class="ci"/>')
        parts.append(f'<circle cx="{xm:.1f}" cy="{y}" r="4.5" class="point"><title>{html.escape(label)} {title}: median {mid:.2f}%, 95% interval [{lo:.2f}%, {hi:.2f}%]</title></circle>')
parts.append('</svg>')
(HERE / 'paired-effects.svg').write_text('\n'.join(parts) + '\n')
