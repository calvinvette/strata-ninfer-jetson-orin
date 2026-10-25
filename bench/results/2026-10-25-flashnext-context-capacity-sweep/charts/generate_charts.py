#!/usr/bin/env python3
"""Render context-capacity throughput charts from the checked-in summary."""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE.parent / "summary.json"
OUT = HERE
CONTEXTS = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
PROMPT = "557"
MODELS = [
    ("coder-iq1m", "Coder IQ1_M", "#1769aa", "coder-iq1m.svg"),
    ("coder-q2_0", "Coder Q2_0", "#d97706", "coder-q2_0.svg"),
    ("original-iq3_s", "Original ISTA-DASLab IQ3_S", "#16803c", "original-iq3-s.svg"),
]


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def values(data, key):
    out = []
    for context in CONTEXTS:
        cell = data[key].get(str(context), {})
        p = cell.get("prompts", {}).get(PROMPT)
        out.append((p["prompt_tok_s"]["median"], p["decode_tok_s"]["median"]) if p else None)
    return out


def render(title, series, dest, subtitle):
    # series = [(label, color, [(prompt_rate, decode_rate)|None, ...])]
    W, H = 1000, 700
    left, right = 88, 965
    top1, bottom1 = 110, 345
    top2, bottom2 = 430, 640
    labels = ["1K", "2K", "4K", "8K", "16K", "32K", "64K", "128K", "256K"]
    all_pp = [v[0] for _, _, vals in series for v in vals if v]
    all_tg = [v[1] for _, _, vals in series for v in vals if v]
    max_pp = max(10, math.ceil(max(all_pp) / 10) * 10)
    max_tg = max(5, math.ceil(max(all_tg) / 5) * 5)
    # For the combined plot, keep both panels readable and comparable.
    def panel(title_text, metric_idx, ymax, top, bottom):
        result = [f'<text x="{left}" y="{top-20}" class="panel">{esc(title_text)}</text>']
        ticks = 5
        for i in range(ticks + 1):
            y = bottom - (bottom-top) * i / ticks
            val = ymax * i / ticks
            result.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" class="grid"/>')
            result.append(f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" class="tick">{val:.0f}</text>')
        result.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>')
        result.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>')
        for i, lab in enumerate(labels):
            x = left + (right-left) * i / (len(labels)-1)
            result.append(f'<line x1="{x:.1f}" y1="{bottom}" x2="{x:.1f}" y2="{bottom+5}" class="axis"/>')
            result.append(f'<text x="{x:.1f}" y="{bottom+24}" text-anchor="middle" class="tick">{lab}</text>')
        result.append(f'<text transform="translate(25 {(top+bottom)/2:.1f}) rotate(-90)" text-anchor="middle" class="axislabel">tokens/s</text>')
        for label, color, vals in series:
            points=[]
            for i, pair in enumerate(vals):
                if pair is None: continue
                x=left+(right-left)*i/(len(labels)-1)
                y=bottom-(bottom-top)*pair[metric_idx]/ymax
                points.append((x,y))
            if len(points)>1:
                coords=" ".join(f"{x:.1f},{y:.1f}" for x,y in points)
                result.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
            for x,y in points:
                result.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="white" stroke-width="1.5"/>')
        return "\n".join(result)
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202124}.title{font-size:25px;font-weight:700}.sub{font-size:14px;fill:#555}.panel{font-size:16px;font-weight:700}.tick{font-size:12px;fill:#555}.axis{stroke:#444;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.axislabel{font-size:13px;fill:#333}.legend{font-size:14px}</style>',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{left}" y="34" class="title">{esc(title)}</text>',
         f'<text x="{left}" y="60" class="sub">{esc(subtitle)}</text>']
    # Legend centered on top.
    legend_x=left
    for label,color,_ in series:
        svg.append(f'<line x1="{legend_x}" y1="82" x2="{legend_x+24}" y2="82" stroke="{color}" stroke-width="3"/>')
        svg.append(f'<circle cx="{legend_x+12}" cy="82" r="4" fill="{color}"/>')
        svg.append(f'<text x="{legend_x+31}" y="87" class="legend">{esc(label)}</text>')
        legend_x += max(210, 130+len(label)*7)
    svg.append(panel("Prompt processing",0,max_pp,top1,bottom1))
    svg.append(panel("Token generation",1,max_tg,top2,bottom2))
    svg.append(f'<text x="{(left+right)/2}" y="690" text-anchor="middle" class="axislabel">Configured context capacity (tokens, log₂ spacing)</text>')
    svg.append('</svg>')
    dest.write_text("\n".join(svg)+"\n")


data=json.loads(SUMMARY.read_text())["metrics"]
for key,label,color,name in MODELS:
    render(f"{label}: throughput by context capacity", [(label,color,values(data,key))], OUT/name,
           "557-token prompt + 64 generated tokens; median of three requests per capacity")
series=[(label,color,values(data,key)) for key,label,color,_ in MODELS]
render("Flash-Next variants: throughput by context capacity",series,OUT/"combined.svg",
       "557-token prompt + 64 generated tokens; medians; separate panels share units, not scale")
