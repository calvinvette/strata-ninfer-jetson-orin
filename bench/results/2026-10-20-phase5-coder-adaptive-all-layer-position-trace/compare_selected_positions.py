#!/usr/bin/env python3
"""Compare same-position route inputs and accepted-prefix state in a paired run."""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

STATE_KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "ple_prev")
PREFIX_RE = re.compile(
    r"ACCEPTED_PREFIX position=(\d+).*?tokens=([0-9,]+) state=\{STATE_HASH ([^}]+)\}"
)


def read_prefixes(path):
    prefixes = []
    gdn_hashes = []
    pending_gdn = None
    for line in path.read_text().splitlines():
        if "STATE_HASH_GDN " in line:
            pending_gdn = [value.lower() for value in line.split("STATE_HASH_GDN ", 1)[1].split()]
            continue
        match = PREFIX_RE.search(line)
        if match is None:
            if pending_gdn is not None:
                pending_gdn = None
            continue
        if pending_gdn is None:
            raise ValueError(f"accepted prefix has no GDN hash record: {line[:160]}")
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", match.group(3)))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError("accepted-prefix state fields are incomplete")
        tokens = [int(value) for value in match.group(2).split(",")]
        if len(tokens) != 1:
            raise ValueError("expected one accepted token per verifier round")
        prefixes.append({"position": int(match.group(1)), "token_id": tokens[0],
                         "state": {key: fields[key] for key in STATE_KEYS}})
        gdn_hashes.append(pending_gdn)
        pending_gdn = None
    return prefixes, gdn_hashes


def compare_activation(before, after):
    if before == after:
        return {"equal": True, "relative_l2": 0.0, "max_abs": 0.0}
    if len(before) != len(after):
        raise ValueError("activation widths differ")
    delta = [a - b for a, b in zip(before, after)]
    norm = math.sqrt(sum(value * value for value in delta))
    ref = math.sqrt(sum(value * value for value in after))
    return {"equal": False, "relative_l2": norm / ref if ref else None,
            "max_abs": max(abs(value) for value in delta)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    campaign = json.loads((args.run / "campaign.json").read_text())
    if campaign.get("status") != "pass":
        raise ValueError("paired campaign did not pass")
    positions = campaign["capture_moe_positions"]
    arms = {}
    for arm in ("delayed-control", "adaptive-cap8"):
        result = args.run / arm / "result"
        api_requests = json.loads((result / "requests.json").read_text())["requests"]
        if [request["name"] for request in api_requests[:3]] != [
                "short-512", "long-2048", "short-512-recovery"]:
            raise ValueError(f"{arm}: unexpected request sequence")
        prefixes, gdn_hashes = read_prefixes(result / "service.log")
        expected = sum(len(request["ids"]) for request in api_requests)
        if len(prefixes) != expected or len(gdn_hashes) != expected:
            raise ValueError(f"{arm}: accepted-prefix trace count mismatch")
        for request, rows in zip(api_requests, (prefixes[:64], prefixes[64:128], prefixes[128:192])):
            if [row["token_id"] for row in rows] != request["ids"]:
                raise ValueError(f"{arm}/{request['name']}: trace/API token mismatch")
        initial = prefixes[:64]
        recovery = prefixes[128:192]
        initial_gdn = gdn_hashes[:64]
        recovery_gdn = gdn_hashes[128:192]

        trace_path = result / "all-layer-selected-positions.jsonl"
        records = [json.loads(line) for line in trace_path.read_text().splitlines()]
        if not records or records[0].get("format") != "strata-moe-dispatch-v3":
            raise ValueError(f"{arm}: missing v3 dispatch trace")
        by_position = defaultdict(list)
        for row in records[1:]:
            by_position[row["position"]].append(row)
        position_results = {}
        for position in positions:
            rows = by_position[position]
            if len(rows) != 96:
                raise ValueError(f"{arm}/position {position}: expected 96 rows, got {len(rows)}")
            before, after = rows[:48], rows[48:]
            expected_layers = list(range(48))
            if [row["layer"] for row in before] != expected_layers or \
                    [row["layer"] for row in after] != expected_layers:
                raise ValueError(f"{arm}/position {position}: layer ordering mismatch")
            activation_diffs = []
            expert_id_diffs = []
            owner_diffs = []
            for a, b in zip(before, after):
                delta = compare_activation(a["activation"], b["activation"])
                if not delta["equal"]:
                    activation_diffs.append({"layer": a["layer"], **delta})
                if a["ids"] != b["ids"]:
                    expert_id_diffs.append(a["layer"])
                if a["route_kind"] != b["route_kind"]:
                    owner_diffs.append(a["layer"])
            position_results[str(position)] = {
                "first_activation_difference_layer": activation_diffs[0]["layer"] if activation_diffs else None,
                "activation_differences": activation_diffs,
                "expert_id_difference_layers": expert_id_diffs,
                "owner_difference_layers": owner_diffs,
            }
        arms[arm] = {
            "short_recovery_token_id_differences": sum(
                a["token_id"] != b["token_id"] for a, b in zip(initial, recovery)),
            "short_recovery_state_difference_prefixes": [
                i for i, (a, b) in enumerate(zip(initial, recovery)) if a["state"] != b["state"]],
            "short_recovery_gdn_difference_prefixes": [
                i for i, (a, b) in enumerate(zip(initial_gdn, recovery_gdn)) if a != b],
            "first_gdn_difference_ordinals": [
                i for i, (a, b) in enumerate(zip(initial_gdn[8], recovery_gdn[8])) if a != b]
                if initial_gdn[8] != recovery_gdn[8] else [],
            "positions": position_results,
        }
    output = {
        "scope": "same-service short/long/short accepted-prefix and selected-position trace",
        "model_repository": campaign["model_repository"],
        "model_revision": campaign["model_revision"],
        "quantization": campaign["quantization"],
        "binary_sha256": campaign["binary_sha256"],
        "capture_positions": positions,
        "arms": arms,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({arm: {
        "state_difference_prefixes": data["short_recovery_state_difference_prefixes"],
        "gdn_difference_prefixes": data["short_recovery_gdn_difference_prefixes"],
        "position_519": data["positions"].get("519"),
    } for arm, data in arms.items()}, indent=2))


if __name__ == "__main__":
    main()
