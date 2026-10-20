#!/usr/bin/env python3
"""Compare same-service per-layer dispatch inputs and owners at selected positions."""
import argparse
import json
from pathlib import Path


def load_rows(path, positions):
    records = [json.loads(line) for line in path.read_text().splitlines()]
    if not records or records[0].get("format") != "strata-moe-dispatch-v3":
        raise ValueError(f"{path}: invalid v3 MoE dispatch capture")
    rows = [row for row in records[1:] if row.get("position") in positions]
    if any(len(row.get("ids", [])) != row.get("k") or
           len(row.get("route_kind", [])) != row.get("k") for row in rows):
        raise ValueError(f"{path}: route IDs/owners have an invalid shape")
    grouped = {}
    for row in rows:
        key = (row["position"], row["layer"])
        grouped.setdefault(key, []).append(row)
    expected = {(position, layer) for position in positions for layer in range(48)}
    if set(grouped) != expected:
        raise ValueError(f"{path}: expected selected positions × 48 layers; missing/extra keys")
    if any(len(grouped[key]) != 2 for key in expected):
        counts = {str(key): len(grouped[key]) for key in expected if len(grouped[key]) != 2}
        raise ValueError(f"{path}: expected initial/recovery rows for every layer: {counts}")
    return grouped, records[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--positions", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.positions != sorted(set(args.positions)) or any(value < 0 for value in args.positions):
        parser.error("--positions must be strictly increasing non-negative integers")
    campaign = json.loads((args.run / "campaign.json").read_text())
    if campaign.get("status") != "pass" or campaign.get("capture_moe_positions") != args.positions:
        raise ValueError("campaign did not pass with exactly the requested per-layer positions")
    arms = {}
    for arm in ("delayed-control", "adaptive-cap8"):
        grouped, header = load_rows(args.run / arm / "result/all-layer-selected-positions.jsonl",
                                    set(args.positions))
        positions = {}
        for position in args.positions:
            by_layer = []
            for layer in range(48):
                initial, recovery = grouped[(position, layer)]
                by_layer.append({
                    "layer": layer,
                    "activation_identical": initial["activation"] == recovery["activation"],
                    "expert_ids_identical": initial["ids"] == recovery["ids"],
                    "route_owners_identical": initial["route_kind"] == recovery["route_kind"],
                    "owner_flips": [
                        {"expert": expert, "initial_owner": before, "recovery_owner": after}
                        for expert, before, after in zip(initial["ids"], initial["route_kind"], recovery["route_kind"])
                        if before != after
                    ],
                })
            activation_diffs = [row["layer"] for row in by_layer if not row["activation_identical"]]
            owner_diffs = [row["layer"] for row in by_layer if row["owner_flips"]]
            positions[str(position)] = {
                "first_activation_difference_layer": activation_diffs[0] if activation_diffs else None,
                "activation_difference_layers": activation_diffs,
                "owner_flip_layers": owner_diffs,
                "layer_rows": by_layer,
            }
        arms[arm] = {"header": header, "positions": positions}
    result = {
        "scope": "same-service IQ1_M Coder initial/recovery MoE dispatch capture",
        "model_repository": campaign["model_repository"],
        "model_revision": campaign["model_revision"],
        "quantization": campaign["quantization"],
        "binary_sha256": campaign["binary_sha256"],
        "repository_head": campaign["repository_head"],
        "positions": args.positions,
        "arms": arms,
        "limits": ["dispatch inputs, expert IDs and owners only; no expert-output or persistent-state causality claim"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({arm: {position: {
        "first_activation_difference_layer": data["first_activation_difference_layer"],
        "owner_flip_layers": data["owner_flip_layers"],
    } for position, data in rows["positions"].items()} for arm, rows in arms.items()}, indent=2))


if __name__ == "__main__":
    main()
