#!/usr/bin/env python3
"""Pool paired E6 ledger screens only when their measured conditions match."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from summarize_controls import interval  # noqa: E402

METRICS = ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")
CONTROL_KEYS = (
    "fixed_map_sha256", "gpu_expert_slots", "ram_expert_budget_gib",
    "max_context", "prefill_chunk", "speculation_configured",
    "accepted_drafts", "workers", "prompt_cache", "adaptation",
    "pcie_staging_fraction",
)


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def combine(screens: list[tuple[Path, Path]], seed: int = 870126) -> dict:
    if len(screens) < 2:
        raise ValueError("at least two independent screens are required")
    loaded = []
    seeds = set()
    for summary_path, evidence_path in screens:
        summary, evidence = _json(summary_path), _json(evidence_path)
        if summary.get("paired_blocks") != 3 or len(summary.get("pairs", [])) != 3:
            raise ValueError(f"expected a three-pair screen: {summary_path}")
        if summary.get("api_content_matching_blocks") != 3:
            raise ValueError(f"screen contains mismatched API outputs: {summary_path}")
        seed = evidence.get("controls", {}).get("randomized_seed")
        if seed in seeds:
            raise ValueError("screens must use distinct randomized seeds")
        seeds.add(seed)
        loaded.append((summary_path, summary, evidence))

    first_evidence = loaded[0][2]
    baseline_controls = first_evidence["controls"]
    baseline_task = first_evidence["task"]
    for summary_path, summary, evidence in loaded:
        if evidence.get("date") != first_evidence.get("date"):
            raise ValueError("screens must be from the same day")
        for key in ("hardware", "system", "runtime_binary_sha256", "model", "model_files"):
            if evidence.get(key) != first_evidence.get(key):
                raise ValueError(f"screen identity differs: {key}")
        controls = evidence["controls"]
        for key in CONTROL_KEYS:
            if controls.get(key) != baseline_controls.get(key):
                raise ValueError(f"screen control differs: {key}")
        task = evidence["task"]
        for key in ("name", "family", "prompt_tokens", "generation_limit",
                    "allow_natural_stop", "fixture_sha256", "quality_oracle"):
            if task.get(key) != baseline_task.get(key):
                raise ValueError(f"screen workload differs: {key}")
        if summary.get("fixture_sha256") != first_evidence["task"].get("fixture_sha256"):
            raise ValueError(f"screen fixture differs: {summary_path}")
        if summary.get("cell") != loaded[0][1].get("cell"):
            raise ValueError("screen cells differ")

    all_pairs = []
    answer_hashes = set()
    output_lengths = set()
    for summary_path, summary, _evidence in loaded:
        for pair in summary["pairs"]:
            if not pair.get("api_responses_identical"):
                raise ValueError("paired API responses are not identical")
            arms = pair["arms"]
            baseline, candidate = arms["baseline"], arms["candidate"]
            if baseline.get("answer_sha256") != candidate.get("answer_sha256"):
                raise ValueError("paired response hashes differ")
            if baseline.get("completion_tokens") != candidate.get("completion_tokens"):
                raise ValueError("paired output lengths differ")
            answer_hashes.add(baseline["answer_sha256"])
            output_lengths.add(baseline["completion_tokens"])
            all_pairs.append((summary_path, pair))
    if len(answer_hashes) != 1 or len(output_lengths) != 1:
        raise ValueError("screen answers or output lengths differ across pairs")

    combined_metrics = {}
    for metric in METRICS:
        rows = []
        for summary_path, pair in all_pairs:
            baseline = pair["arms"]["baseline"]["metrics"][metric]
            candidate = pair["arms"]["candidate"]["metrics"][metric]
            rows.append({
                "source_summary": str(summary_path),
                "source_block": pair["block"],
                "baseline": baseline,
                "candidate": candidate,
                "candidate_over_baseline": candidate / baseline,
            })
        ratios = [row["candidate_over_baseline"] for row in rows]
        combined_metrics[metric] = {
            "paired_median_effect_percent": (statistics.median(ratios) - 1) * 100,
            "paired_bootstrap_95_interval_effect_percent": [
                (value - 1) * 100 for value in interval(ratios, seed=seed)
            ],
            "baseline_median": statistics.median(row["baseline"] for row in rows),
            "candidate_median": statistics.median(row["candidate"] for row in rows),
            "pairs": rows,
        }

    return {
        "scope": "descriptive pooling of same-day independent screens with identical model, task, map, runtime and context cap",
        "source_summaries": [str(summary_path) for summary_path, _, _ in loaded],
        "paired_blocks": len(all_pairs),
        "method": (
            "Compute candidate/baseline ratios within each pair; report their median. "
            "Paired bootstrap resamples ratios with replacement 5,000 times, takes "
            "each sample median, uses the supplied deterministic seed, and returns "
            "sorted elements at floor(0.025*n) and floor(0.975*n). Intervals are "
            "reported as percent change from ratio 1."
        ),
        "qualification": "Exploratory pooling, not a preregistered confirmation; retain every pair, including outliers.",
        "answer_sha256": next(iter(answer_hashes)),
        "completion_tokens": next(iter(output_lengths)),
        "bootstrap_seed": seed,
        "bootstrap_resamples": 5000,
        "metrics": combined_metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", action="append", nargs=2, required=True,
                        metavar=("SUMMARY_JSON", "EVIDENCE_JSON"),
                        help="repeat for each independent three-pair screen")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=870126)
    args = parser.parse_args()
    result = combine([(Path(summary), Path(evidence)) for summary, evidence in args.screen], args.seed)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
