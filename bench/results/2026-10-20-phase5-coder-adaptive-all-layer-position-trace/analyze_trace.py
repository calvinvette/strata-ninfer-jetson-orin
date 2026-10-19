#!/usr/bin/env python3
"""Compare same-position expert dispatch inputs and owners across migration arms."""
import json
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / "run"
ARM_NAMES = ("delayed-control", "adaptive-cap8")
TYPE_NAMES = {18: "IQ3_XXS", 20: "IQ4_NL", 21: "IQ3_S", 22: "IQ2_S", 23: "IQ4_XS", 42: "Q2_0"}
STATE_KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "ple_prev")


def accepted_prefixes(path, api_requests):
    pattern = re.compile(r"ACCEPTED_PREFIX position=(\d+).*?tokens=(\d+) state=\{STATE_HASH ([^}]+)\}")
    prefixes = []
    for line in path.read_text().splitlines():
        if "ACCEPTED_PREFIX position=" not in line:
            continue
        m = pattern.search(line)
        if m is None:
            raise ValueError(f"malformed accepted-prefix record: {line[:160]}")
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", m.group(3)))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError("accepted-prefix state fields are incomplete")
        prefixes.append({"position": int(m.group(1)), "token_id": int(m.group(2)),
                          "state": {key: fields[key] for key in STATE_KEYS}})
    if len(prefixes) != sum(len(request["ids"]) for request in api_requests):
        raise ValueError(f"accepted-prefix count mismatch: got {len(prefixes)}")
    requests, at = [], 0
    for request in api_requests:
        count = len(request["ids"])
        rows = prefixes[at:at + count]
        at += count
        if [row["token_id"] for row in rows] != request["ids"]:
            raise ValueError(f"{request['name']}: accepted-prefix token IDs differ from API IDs")
        requests.append({"name": request["name"], "token_ids": request["ids"], "prefixes": rows})
    return requests


def accepted_prefix_gdn_hashes(path, api_requests):
    """Read per-GDN-layer hashes emitted immediately before each accepted-prefix row."""
    pending = None
    rows = []
    for line in path.read_text().splitlines():
        if "STATE_HASH_GDN " in line:
            pending = [value.lower() for value in line.split("STATE_HASH_GDN ", 1)[1].split()]
            continue
        if "ACCEPTED_PREFIX position=" not in line:
            if pending is not None:
                pending = None
            continue
        if pending is None:
            raise ValueError("accepted-prefix record has no preceding per-layer GDN state hash")
        match = re.search(r"tokens=([0-9,]+)", line)
        if match is None:
            raise ValueError(f"malformed accepted-prefix token record: {line[:160]}")
        tokens = match.group(1).split(",")
        if len(tokens) != 1:
            raise ValueError("per-layer GDN trace requires one accepted token per verifier round")
        rows.append(pending)
        pending = None
    expected = sum(len(request["ids"]) for request in api_requests)
    if len(rows) != expected:
        raise ValueError(f"per-layer GDN hash count mismatch: got {len(rows)}, expected {expected}")
    counts = {len(row) for row in rows}
    if len(counts) != 1:
        raise ValueError("per-layer GDN hash rows have inconsistent layer counts")
    requests, at = [], 0
    for request in api_requests:
        count = len(request["ids"])
        requests.append({"name": request["name"], "prefixes": rows[at:at + count]})
        at += count
    return requests


def compare_gdn_prefixes(before, after):
    differing = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    first = differing[0] if differing else None
    ordinals = ([i for i, (a, b) in enumerate(zip(before[first], after[first])) if a != b]
                if first is not None else [])
    return {"different_state_prefix_count": len(differing),
            "different_prefix_indices": differing,
            "first_different_prefix": first,
            "first_different_gdn_ordinals": ordinals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=RUN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run = args.run
    campaign = json.loads((run / "campaign.json").read_text())
    if campaign.get("status") != "pass":
        raise ValueError("two-arm campaign did not pass")
    inventory = {}
    with Path.home().joinpath("models/strata-orin-validation/pack/native_experts.txt").open() as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.split()
            layer, gu, down = map(int, fields[:3])
            inventory[layer] = {"gu_type": gu, "gu_name": TYPE_NAMES[gu],
                                "down_type": down, "down_name": TYPE_NAMES[down]}
    if sorted(inventory) != list(range(48)):
        raise ValueError("native expert format inventory is incomplete")

    arms = {}
    prefix_records = {}
    gdn_prefix_records = {}
    for arm in ARM_NAMES:
        path = run / arm / "result/all-layer-position511.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        if not records or records[0].get("format") != "strata-moe-dispatch-v3":
            raise ValueError(f"{arm}: missing current v3 dispatch trace")
        rows = records[1:]
        if len(rows) != 96:
            raise ValueError(f"{arm}: expected 96 initial/recovery rows, found {len(rows)}")
        initial, recovery = rows[:48], rows[48:]
        for label, group in (("initial", initial), ("recovery", recovery)):
            if [row["layer"] for row in group] != list(range(48)) or any(row["position"] != 511 for row in group):
                raise ValueError(f"{arm}/{label}: did not capture position 511 at each layer in order")
        by_layer = []
        for before, after in zip(initial, recovery):
            flips = [{"expert": expert, "initial_owner": owner_a, "recovery_owner": owner_b}
                     for expert, owner_a, owner_b in zip(before["ids"], before["route_kind"], after["route_kind"])
                     if owner_a != owner_b]
            by_layer.append({"layer": before["layer"], **inventory[before["layer"]],
                             "activation_equal": before["activation"] == after["activation"],
                             "expert_ids_equal": before["ids"] == after["ids"],
                             "owner_flips": flips})
        differing_activations = [row["layer"] for row in by_layer if not row["activation_equal"]]
        arm_analysis = json.loads((run / arm / "result/analysis.json").read_text())
        api_requests = json.loads((run / arm / "result/requests.json").read_text())["requests"]
        prefix_records[arm] = accepted_prefixes(run / arm / "result/service.log", api_requests)
        gdn_prefix_records[arm] = accepted_prefix_gdn_hashes(run / arm / "result/service.log", api_requests)
        first, recovery = prefix_records[arm][0], prefix_records[arm][2]
        gdn_initial, gdn_recovery = gdn_prefix_records[arm][0], gdn_prefix_records[arm][2]
        recovery_gdn_comparison = compare_gdn_prefixes(gdn_initial["prefixes"], gdn_recovery["prefixes"])
        arms[arm] = {"recovery_token_differences": arm_analysis["recovery_token_differences"],
                     "changed_final_state_fields": arm_analysis["changed_state_keys"],
                     "adaptive_byte_checks": arm_analysis["adaptive_byte_verification_passes"],
                     "adaptive_residency_checks": arm_analysis["adaptive_residency_verification_passes"],
                     "within_service_short_recovery_state": {
                         "shared_prefixes": len(first["prefixes"]),
                         "different_state_prefixes": sum(a["state"] != b["state"] for a, b in zip(first["prefixes"], recovery["prefixes"])),
                         "different_final_state_fields": [key for key in STATE_KEYS if first["prefixes"][-1]["state"][key] != recovery["prefixes"][-1]["state"][key]],
                     },
                     "within_service_short_recovery_gdn_state": recovery_gdn_comparison,
                     "within_service": {
                         "first_activation_difference_layer": min(differing_activations) if differing_activations else None,
                         "activation_difference_layers": differing_activations,
                         "owner_flip_layers": [row["layer"] for row in by_layer if row["owner_flips"]],
                         "layer_rows": by_layer,
                     }}

    adaptive_rows = arms["adaptive-cap8"]["within_service"]["layer_rows"]
    first_activation = arms["adaptive-cap8"]["within_service"]["first_activation_difference_layer"]
    prior_layer = first_activation - 1 if first_activation is not None else None
    prior = adaptive_rows[prior_layer] if prior_layer is not None else None
    result = {
        "scope": "one randomized IQ1_M Coder current-source delayed/adaptive correctness pair",
        "model_repository": campaign["model_repository"], "model_revision": campaign["model_revision"],
        "quantization": campaign["quantization"], "binary_sha256": campaign["binary_sha256"],
        "repository_head": campaign["repository_head"], "captured_position": 511,
        "capture_rows_per_arm": 96, "capture_layers": 48,
        "selector": "STRATA_NATIVE_CPU_Q8_1_DOT=all",
        "arms": arms,
        "cross_arm_accepted_prefix_state": {
            request_a["name"]: {
                "token_ids_differ": sum(a != b for a, b in zip(request_a["token_ids"], request_b["token_ids"])),
                "different_state_prefixes": sum(a["state"] != b["state"] for a, b in zip(request_a["prefixes"], request_b["prefixes"])),
                "different_final_state_fields": [key for key in STATE_KEYS if request_a["prefixes"][-1]["state"][key] != request_b["prefixes"][-1]["state"][key]],
            }
            for request_a, request_b in zip(prefix_records["adaptive-cap8"], prefix_records["delayed-control"])
        },
        "cross_arm_accepted_prefix_gdn_state": {
            request_a["name"]: compare_gdn_prefixes(request_a["prefixes"], request_b["prefixes"])
            for request_a, request_b in zip(gdn_prefix_records["adaptive-cap8"], gdn_prefix_records["delayed-control"])
        },
        "adaptive_first_downstream_activation_difference": {
            "layer": first_activation, "preceding_layer": prior_layer,
            "preceding_layer_formats": prior,
            "interpretation": "This identifies the earliest changed captured expert-dispatch input. Route rows alone do not identify which upstream operation or persistent-state update caused it.",
        },
        "limits": ["one sequence and one model quantization", "route trace records dispatcher inputs, IDs and owners, not expert outputs or router weights", "one pair, no quality or performance claim"],
    }
    out = args.output or ROOT / "all-layer-analysis.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"adaptive_first_activation_difference_layer": first_activation,
                      "preceding_layer": prior, "adaptive_owner_flip_layers": arms["adaptive-cap8"]["within_service"]["owner_flip_layers"],
                      "delayed_activation_difference_layers": arms["delayed-control"]["within_service"]["activation_difference_layers"]}, indent=2))


if __name__ == "__main__":
    main()
