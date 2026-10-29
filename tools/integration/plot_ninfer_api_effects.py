#!/usr/bin/env python3
"""Render a stdlib-only SVG forest plot from sanitized paired API effects."""
import argparse
import csv
import json
from pathlib import Path


METRICS = (
    ('prompt_tps', 'Prompt TPS', '#315f9b'),
    ('decode_tps', 'Decode TPS', '#6d4a9b'),
    ('first_visible_ttft_s', 'First-visible TTFT', '#c05a24'),
    ('client_total_s', 'Client total', '#39804b'),
)


def render(data):
    cells = data['cells']
    rows = [(cell, key, label, color)
            for cell in cells for key, label, color in METRICS]
    width, top, bottom = 1300, 115, 72
    row_height = 43
    height = top + row_height * len(rows) + bottom
    left, right = 350, 220
    plot_width = width - left - right
    xmin, xmax = -22.0, 50.0

    def x(value):
        return left + (value - xmin) * plot_width / (xmax - xmin)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<style>text{font-family:Arial,sans-serif;fill:#202124}.title{font-size:22px;font-weight:bold}.sub{font-size:13px;fill:#555}.label{font-size:14px}.small{font-size:12px;fill:#555}.axis{stroke:#777;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.zero{stroke:#222;stroke-width:1.5;stroke-dasharray:5 4}.ci{stroke-width:2}.pair{opacity:.55}</style>',
           f'<text x="{left}" y="32" class="title">No-staging Q2_0 API screen: paired NInfer effect</text>',
           f'<text x="{left}" y="57" class="sub">Three randomized process pairs per workload; candidate / Strata change in percent; positive TPS is faster and positive latency is slower</text>',
           f'<text x="{left}" y="78" class="sub">Bootstrap intervals use whole paired blocks (screening only); output matched within each pair; no independent task-quality oracle</text>',
           f'<text x="{left}" y="99" class="small">Small circles: individual paired blocks; diamond: paired median; horizontal line: paired bootstrap 95% interval</text>']

    for tick in range(-20, 51, 10):
        xpos = x(tick)
        out.append(f'<line x1="{xpos:.1f}" y1="{top-8}" x2="{xpos:.1f}" y2="{height-bottom+2}" class="{"zero" if tick == 0 else "grid"}"/>')
        out.append(f'<text x="{xpos:.1f}" y="{height-bottom+24}" text-anchor="middle" class="small">{tick:+d}%</text>')

    prev_cell = None
    for index, (cell, key, label, color) in enumerate(rows):
        ypos = top + index * row_height + row_height / 2
        if cell['name'] != prev_cell:
            out.append(f'<text x="24" y="{ypos+4:.1f}" class="label" font-weight="bold">{cell["name"]}</text>')
            prev_cell = cell['name']
        out.append(f'<text x="205" y="{ypos+4:.1f}" text-anchor="end" class="label">{label}</text>')
        metric = cell['metrics'][key]
        lo, hi = metric['bootstrap_95_interval_pct']
        med = metric['median_paired_change_pct']
        out.append(f'<line x1="{x(lo):.1f}" y1="{ypos:.1f}" x2="{x(hi):.1f}" y2="{ypos:.1f}" class="ci" stroke="{color}"/>')
        out.append(f'<line x1="{x(lo):.1f}" y1="{ypos-5:.1f}" x2="{x(lo):.1f}" y2="{ypos+5:.1f}" class="ci" stroke="{color}"/>')
        out.append(f'<line x1="{x(hi):.1f}" y1="{ypos-5:.1f}" x2="{x(hi):.1f}" y2="{ypos+5:.1f}" class="ci" stroke="{color}"/>')
        for pair in metric['paired_changes_pct']:
            py = ypos + (pair['block'] - 1) * 4
            out.append(f'<circle cx="{x(pair["value"]):.1f}" cy="{py:.1f}" r="3" fill="{color}" class="pair"/>')
        out.append(f'<path d="M {x(med):.1f} {ypos-7:.1f} L {x(med)+6:.1f} {ypos:.1f} L {x(med):.1f} {ypos+7:.1f} L {x(med)-6:.1f} {ypos:.1f} Z" fill="{color}"/>')
        out.append(f'<text x="{left+plot_width+10}" y="{ypos+4:.1f}" class="small">{med:+.2f}% [{lo:+.2f}, {hi:+.2f}]</text>')
        if index in (3,):
            out.append(f'<line x1="24" y1="{ypos+row_height/2:.1f}" x2="{width-24}" y2="{ypos+row_height/2:.1f}" class="grid"/>')
    out.append(f'<text x="{left+plot_width/2}" y="{height-20}" text-anchor="middle" class="label">NInfer relative to Strata</text>')
    out.append('</svg>')
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.summary.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'paired-effects.svg').write_text(render(data))
    with (args.output / 'paired-effects.csv').open('w', newline='') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['workload', 'context_tokens', 'metric', 'block', 'order', 'paired_change_pct', 'median_change_pct', 'bootstrap_95_low_pct', 'bootstrap_95_high_pct'])
        for cell in data['cells']:
            for key, label, _ in METRICS:
                metric = cell['metrics'][key]
                for pair in metric['paired_changes_pct']:
                    writer.writerow([cell['name'], cell['context_tokens'], label,
                                     pair['block'], pair['order'], pair['value'],
                                     metric['median_paired_change_pct'],
                                     metric['bootstrap_95_interval_pct'][0],
                                     metric['bootstrap_95_interval_pct'][1]])
    print(json.dumps({'svg': str(args.output / 'paired-effects.svg'),
                      'csv': str(args.output / 'paired-effects.csv'),
                      'cells': [cell['name'] for cell in data['cells']]}, indent=2))


if __name__ == '__main__':
    main()
