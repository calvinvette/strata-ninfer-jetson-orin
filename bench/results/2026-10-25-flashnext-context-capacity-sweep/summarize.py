#!/usr/bin/env python3
"""Summarize the guarded Flash-Next context-capacity sweep."""
import argparse
import json
from pathlib import Path
import statistics


METRICS = {
    "prompt_tok_s": "prompt_tok_s",
    "decode_tok_s": "decode_tok_s",
    "client_ttft_s": "client_ttft_s",
    "client_total_s": "client_total_s",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    matrix = json.loads((args.campaign / "matrix.json").read_text())
    summary = {
        "source_matrix": str((args.campaign / "matrix.json").resolve()),
        "statistic": "median and min/max across three in-process repetitions; descriptive only",
        "metrics": {},
    }
    errors = []
    for cell in matrix["cells"]:
        model, context = cell["model"], cell["context"]
        row = {
            "status": cell["status"],
            "minimum_available_gib": (cell.get("minimum_available_bytes") or 0) / 2**30,
            "minimum_admission_available_gib": (cell.get("minimum_admission_available_bytes") or 0) / 2**30,
            "prompts": {},
        }
        run_dir = args.campaign / model / str(context) / "run"
        for repeat, prompt_tokens in ((32, 172), (128, 557), (256, 1069)):
            if prompt_tokens + 64 > context:
                continue
            samples = []
            for round_index in range(3):
                path = run_dir / f"matched-{round_index}-{repeat}.json"
                if not path.exists():
                    errors.append(f"missing {path}")
                    continue
                item = json.loads(path.read_text())
                if item.get("status") != "pass":
                    errors.append(f"invalid sample {path}: {item.get('status')}")
                    continue
                samples.append(item)
            cell_metrics = {"expected_prompt_tokens": prompt_tokens, "n": len(samples)}
            for key, source in METRICS.items():
                values = [sample.get(source) for sample in samples]
                if len(values) == 3 and all(isinstance(value, (int, float)) for value in values):
                    cell_metrics[key] = {
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                    }
                else:
                    errors.append(f"incomplete {model}/{context}/{prompt_tokens}: {key}")
            row["prompts"][str(prompt_tokens)] = cell_metrics
        summary["metrics"].setdefault(model, {})[str(context)] = row
    summary["errors"] = errors
    summary["status"] = "pass" if not errors else "incomplete"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"status": summary["status"], "error_count": len(errors), "output": str(args.out)}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
