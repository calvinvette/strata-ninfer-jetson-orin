#!/usr/bin/env python3
"""Compare matched Coder IQ1_M context-sweep medians from both Orin ports.

Run with --strata-matrix pointing at the original port's committed
2026-10-08-jetson-orin/rebased-context-sweep/matrix.json.
"""
import argparse
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY = HERE.parent / "summary.json"
OUT = HERE / "strata-iq1m-comparison.svg"
CONTEXTS = [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]
LABELS = ["1K", "2K", "4K", "8K", "16K", "32K", "64K", "128K", "256K"]
SERIES = [("Strata Orin 0.1.41", "strata", "#7851a9"),
          ("Strata + NInfer candidate", "combined", "#008b8b")]


def old_data(path):
    matrix = json.loads(path.read_text())
    result = {}
    for cell in matrix["cells"]:
        if cell["label"] != "rebased":
            continue
        rows = [r["response"] for r in cell["requests"]
                if r.get("task") == "throughput" and r.get("round", 99) < 99
                and r["response"].get("usage", {}).get("prompt_tokens") == 557]
        if rows:
            result[cell["context_limit"]] = (
                statistics.median(r["timings"]["prompt_per_second"] for r in rows),
                statistics.median(r["timings"]["predicted_per_second"] for r in rows),
            )
    return result, matrix


def new_data():
    metrics = json.loads(SUMMARY.read_text())["metrics"]["coder-iq1m"]
    return {int(context): (row["prompts"]["557"]["prompt_tok_s"]["median"],
                           row["prompts"]["557"]["decode_tok_s"]["median"])
            for context, row in metrics.items() if "557" in row.get("prompts", {})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strata-matrix", type=Path, required=True)
    args = parser.parse_args()
    old, matrix = old_data(args.strata_matrix)
    new = new_data()
    source = next(c["source_commit"] for c in matrix["cells"] if c["label"] == "rebased")
    data = {"strata": old, "combined": new}
    W,H,L,R=1000,690,90,965
    panels=[("Prompt processing",0,70,110,340),("Token generation",1,25,415,630)]
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#202124}.title{font-size:24px;font-weight:700}.sub{font-size:14px;fill:#555}.panel{font-size:16px;font-weight:700}.tick{font-size:12px;fill:#555}.axis{stroke:#444}.grid{stroke:#ddd}.label{font-size:13px}.legend{font-size:14px}</style>',
         '<rect width="100%" height="100%" fill="white"/>',
         f'<text x="{L}" y="34" class="title">Coder IQ1_M: Strata Orin vs combined port</text>',
         f'<text x="{L}" y="58" class="sub">557-token prompt + 64 generated tokens; medians of three requests per context</text>',
         f'<text x="{L}" y="78" class="sub">Historical Strata source {source[:10]}; combined binary source 348e6261</text>']
    x0=L
    for name,key,color in SERIES:
        svg += [f'<line x1="{x0}" y1="101" x2="{x0+24}" y2="101" stroke="{color}" stroke-width="3"/>',
                f'<circle cx="{x0+12}" cy="101" r="4" fill="{color}"/>',
                f'<text x="{x0+31}" y="106" class="legend">{name}</text>']
        x0+=360
    for title,metric,ymax,top,bottom in panels:
        svg.append(f'<text x="{L}" y="{top-18}" class="panel">{title}</text>')
        for i in range(6):
            y=bottom-(bottom-top)*i/5; value=ymax*i/5
            svg += [f'<line x1="{L}" y1="{y:.1f}" x2="{R}" y2="{y:.1f}" class="grid"/>',
                    f'<text x="{L-12}" y="{y+4:.1f}" text-anchor="end" class="tick">{value:.0f}</text>']
        svg += [f'<line x1="{L}" y1="{top}" x2="{L}" y2="{bottom}" class="axis"/>',
                f'<line x1="{L}" y1="{bottom}" x2="{R}" y2="{bottom}" class="axis"/>']
        for i,label in enumerate(LABELS):
            x=L+(R-L)*i/(len(LABELS)-1)
            svg.append(f'<text x="{x:.1f}" y="{bottom+22}" text-anchor="middle" class="tick">{label}</text>')
        for name,key,color in SERIES:
            points=[]
            for i,context in enumerate(CONTEXTS):
                pair=data[key].get(context)
                if pair is not None:
                    x=L+(R-L)*i/(len(CONTEXTS)-1); y=bottom-(bottom-top)*pair[metric]/ymax
                    points.append((x,y))
            coords=" ".join(f"{x:.1f},{y:.1f}" for x,y in points)
            svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
            for x,y in points:
                svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" stroke="white" stroke-width="1.5"/>')
        svg.append(f'<text transform="translate(27 {(top+bottom)/2:.1f}) rotate(-90)" text-anchor="middle" class="label">tokens/s</text>')
    svg += [f'<text x="{(L+R)/2}" y="680" text-anchor="middle" class="label">Configured context capacity (tokens, log₂ spacing)</text>',
            '</svg>']
    OUT.write_text("\n".join(svg)+"\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
