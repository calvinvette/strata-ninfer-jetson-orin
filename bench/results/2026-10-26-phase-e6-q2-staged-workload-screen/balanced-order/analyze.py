#!/usr/bin/env python3
"""Summarize the randomized staged-miss workload screen."""
import csv
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent
ARMS = ("cpu-miss", "ninfer-staged")
CELLS = ("pp512+tg64", "pp2048+tg128", "pp172+tg64", "pp557+tg64", "pp1069+tg64")


def load():
    matrix = json.loads((ROOT / "matrix.json").read_text())
    results = {}
    for block in range(1, len(matrix["pairs"]) + 1):
        for arm in ARMS:
            results[block, arm] = json.loads((ROOT / f"pair-{block}" / arm / "result.json").read_text())
            if results[block, arm]["status"] != "pass":
                raise SystemExit(f"nonpassing run: pair {block} {arm}")
    maps = {row["residency_sha256"] for row in results.values()}
    if len(maps) != 1:
        raise SystemExit(f"resident-map mismatch: {sorted(maps)}")
    return matrix, results, next(iter(maps))


def percent(new, control):
    return 100.0 * (new / control - 1.0)


def row_for(results, block, arm, cell, warmup=False):
    target_round = -1 if warmup else 0
    matches = [r for r in results[block, arm]["checks"]
               if r.get("cell") == cell and r.get("round") == target_round
               and bool(r.get("warmup")) == warmup]
    if len(matches) != 1 or matches[0].get("status") != "pass":
        raise SystemExit(f"missing passing row: pair={block} arm={arm} cell={cell} warmup={warmup}")
    return matches[0]


def summarize():
    matrix, results, map_hash = load()
    table = []
    for cell in CELLS:
        pair_values = {key: [] for key in ("prompt_tps", "decode_tps", "ttft", "client_total")}
        measured_match = []
        warmup_match = []
        token_counts_match = []
        for block in range(1, len(matrix["pairs"]) + 1):
            control = row_for(results, block, "cpu-miss", cell)
            candidate = row_for(results, block, "ninfer-staged", cell)
            ct, nt = control["response"]["timings"], candidate["response"]["timings"]
            pair_values["prompt_tps"].append(percent(nt["prompt_n"] / nt["prompt_ms"],
                                                       ct["prompt_n"] / ct["prompt_ms"]))
            pair_values["decode_tps"].append(percent(nt["predicted_n"] / nt["predicted_ms"],
                                                       ct["predicted_n"] / ct["predicted_ms"]))
            pair_values["ttft"].append(percent(candidate["stream_observation"]["first_visible_delta_s"],
                                                control["stream_observation"]["first_visible_delta_s"]))
            pair_values["client_total"].append(percent(candidate["client_elapsed_s"], control["client_elapsed_s"]))
            measured_match.append(candidate["output_sha256"] == control["output_sha256"])
            warmup_match.append(row_for(results, block, "cpu-miss", cell, True)["output_sha256"] ==
                                row_for(results, block, "ninfer-staged", cell, True)["output_sha256"])
            token_counts_match.append((ct["prompt_n"], ct["predicted_n"]) == (nt["prompt_n"], nt["predicted_n"]))
        summary = {
            "cell": cell,
            "median_prompt_tps_change_pct": statistics.median(pair_values["prompt_tps"]),
            "pair_prompt_tps_change_pct": pair_values["prompt_tps"],
            "median_decode_tps_change_pct": statistics.median(pair_values["decode_tps"]),
            "pair_decode_tps_change_pct": pair_values["decode_tps"],
            "median_ttft_delta_pct": statistics.median(pair_values["ttft"]),
            "pair_ttft_delta_pct": pair_values["ttft"],
            "median_client_total_delta_pct": statistics.median(pair_values["client_total"]),
            "pair_client_total_delta_pct": pair_values["client_total"],
            "measured_output_hash_matches": sum(measured_match),
            "measured_output_hash_pairs": len(measured_match),
            "warmup_output_hash_matches": sum(warmup_match),
            "warmup_output_hash_pairs": len(warmup_match),
            "token_counts_match_in_all_pairs": all(token_counts_match),
        }
        table.append(summary)
    minimum_available = min(row["minimum_available_bytes"] for row in results.values())
    minimum_admission = min(row["minimum_admission_available_bytes"] for row in results.values())
    summary = {
        "paired_effect_scope": "descriptive three-pair screening medians; negative latency change means NInfer is faster",
        "pair_order": [{"block": row["block"], "order": row["order"]} for row in matrix["pairs"]],
        "resident_map_sha256": map_hash,
        "minimum_available_bytes": minimum_available,
        "minimum_admission_available_bytes": minimum_admission,
        "cells": table,
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    columns = ["cell", "median_prompt_tps_change_pct", "pair_prompt_tps_change_pct",
               "median_decode_tps_change_pct", "pair_decode_tps_change_pct",
               "median_ttft_delta_pct", "pair_ttft_delta_pct", "median_client_total_delta_pct",
               "pair_client_total_delta_pct", "measured_output_hash_matches",
               "measured_output_hash_pairs", "warmup_output_hash_matches",
               "warmup_output_hash_pairs", "token_counts_match_in_all_pairs"]
    with (ROOT / "summary.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in table:
            writer.writerow({key: json.dumps(row[key]) if key.startswith("pair_") else row[key]
                             for key in columns})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    summarize()
