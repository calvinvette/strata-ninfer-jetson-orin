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
        if "STATE_HASH_QSA_LAYERS " in line:
            # Optional per-QSA diagnostics may be emitted between GDN hashes
            # and the accepted-prefix record they describe.
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


def activation_valid(row):
    # Legacy captures did not carry the flag. A CPU activation is only
    # materialized when at least one expert in that token row is CPU-owned.
    return row.get("activation_valid", any(owner < 0 for owner in row["route_kind"]))


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
        sequence = campaign.get("sequence", "short-long-short")
        expected_names = (["short-512", "long-2048", "short-512-recovery"]
                          if sequence == "short-long-short" else
                          ["short-512", "short-512-intermediate", "short-512-recovery"])
        if [request["name"] for request in api_requests[:3]] != expected_names:
            raise ValueError(f"{arm}: unexpected request sequence")
        prefixes, gdn_hashes = read_prefixes(result / "service.log")
        expected = sum(len(request["ids"]) for request in api_requests)
        if len(prefixes) != expected or len(gdn_hashes) != expected:
            raise ValueError(f"{arm}: accepted-prefix trace count mismatch")
        request_rows = []
        cursor = 0
        for request in api_requests:
            count = len(request["ids"])
            rows = prefixes[cursor:cursor + count]
            if [row["token_id"] for row in rows] != request["ids"]:
                raise ValueError(f"{arm}/{request['name']}: trace/API token mismatch")
            request_rows.append((rows, gdn_hashes[cursor:cursor + count]))
            cursor += count
        initial, initial_gdn = request_rows[0]
        recovery, recovery_gdn = request_rows[2]
        same_prompt_pairs = []
        if sequence == "short-short-short":
            for left, right in ((0, 1), (1, 2)):
                a_rows, a_gdn = request_rows[left]
                b_rows, b_gdn = request_rows[right]
                same_prompt_pairs.append({
                    "requests": [api_requests[left]["name"], api_requests[right]["name"]],
                    "token_id_differences": sum(a["token_id"] != b["token_id"]
                                                for a, b in zip(a_rows, b_rows)),
                    "state_difference_prefixes": [i for i, (a, b) in enumerate(zip(a_rows, b_rows))
                                                   if a["state"] != b["state"]],
                    "gdn_difference_prefixes": [i for i, (a, b) in enumerate(zip(a_gdn, b_gdn))
                                                if a != b],
                })

        trace_path = next((path for path in (
            result / "all-layer-selected-positions.jsonl",
            result / "all-layer-position511.jsonl",
        ) if path.is_file()), None)
        if trace_path is None:
            raise ValueError(f"{arm}: missing all-layer dispatch trace")
        records = [json.loads(line) for line in trace_path.read_text().splitlines()]
        if not records or records[0].get("format") != "strata-moe-dispatch-v3":
            raise ValueError(f"{arm}: missing v3 dispatch trace")
        by_position = defaultdict(list)
        for row in records[1:]:
            by_position[row["position"]].append(row)
        position_results = {}
        for position in positions:
            rows = by_position[position]
            if not rows:
                position_results[str(position)] = {
                    "capture_observed": False,
                    "reason": "no dispatch was recorded at this emitted-token position",
                }
                continue
            if len(rows) % 48 or not 2 <= len(rows) // 48 <= len(api_requests):
                raise ValueError(f"{arm}/position {position}: expected 2..{len(api_requests)} complete 48-layer request blocks, got {len(rows)} rows")
            request_blocks = [rows[offset:offset + 48] for offset in range(0, len(rows), 48)]
            if sequence == "short-long-short" and len(request_blocks) == 2:
                # A position-511 dispatch is present for both 512-token prompts;
                # the long prompt has no verifier dispatch at this prompt-tail position.
                captured_request_indices = [0, 2]
            elif len(request_blocks) <= len(api_requests):
                # Short/short/short captures are appended in request order. A
                # row-cap-limited capture can therefore contain only the first
                # two requests, which must not be mislabeled as recovery.
                captured_request_indices = list(range(len(request_blocks)))
            else:
                raise ValueError(f"{arm}/position {position}: cannot map capture blocks to requests")
            if len(captured_request_indices) != len(request_blocks):
                raise ValueError(f"{arm}/position {position}: capture/request mapping is incomplete")
            before, after = request_blocks[0], request_blocks[-1]
            expected_layers = list(range(48))
            if [row["layer"] for row in before] != expected_layers or \
                    [row["layer"] for row in after] != expected_layers:
                raise ValueError(f"{arm}/position {position}: layer ordering mismatch")
            activation_diffs = []
            activation_unknown = []
            expert_id_diffs = []
            owner_diffs = []
            for a, b in zip(before, after):
                if not activation_valid(a) or not activation_valid(b):
                    activation_unknown.append(a["layer"])
                else:
                    delta = compare_activation(a["activation"], b["activation"])
                    if not delta["equal"]:
                        activation_diffs.append({"layer": a["layer"], **delta})
                if a["ids"] != b["ids"]:
                    expert_id_diffs.append(a["layer"])
                if a["route_kind"] != b["route_kind"]:
                    owner_diffs.append(a["layer"])
            position_results[str(position)] = {
                "capture_observed": True,
                "captured_requests": [api_requests[index]["name"] for index in captured_request_indices],
                "first_activation_difference_layer": activation_diffs[0]["layer"] if activation_diffs else None,
                "activation_differences": activation_diffs,
                "activation_unknown_layers": activation_unknown,
                "expert_id_difference_layers": expert_id_diffs,
                "owner_difference_layers": owner_diffs,
            }
            transitions = []
            for left in range(len(request_blocks) - 1):
                right = left + 1
                a_block, b_block = request_blocks[left], request_blocks[right]
                changed_activations = [a["layer"] for a, b in zip(a_block, b_block)
                                       if activation_valid(a) and activation_valid(b) and
                                       not compare_activation(a["activation"], b["activation"])["equal"]]
                unknown_activations = [a["layer"] for a, b in zip(a_block, b_block)
                                       if not activation_valid(a) or not activation_valid(b)]
                transitions.append({
                    "request_pair": [api_requests[captured_request_indices[left]]["name"],
                                     api_requests[captured_request_indices[right]]["name"]],
                    "activation_difference_layers": changed_activations,
                    "activation_unknown_layers": unknown_activations,
                    "expert_id_difference_layers": [a["layer"] for a, b in zip(a_block, b_block)
                                                     if a["ids"] != b["ids"]],
                    "owner_difference_layers": [a["layer"] for a, b in zip(a_block, b_block)
                                                if a["route_kind"] != b["route_kind"]],
                })
            if transitions:
                position_results[str(position)]["request_sequence_transitions"] = transitions
        arms[arm] = {
            "short_recovery_token_id_differences": sum(
                a["token_id"] != b["token_id"] for a, b in zip(initial, recovery)),
            "short_recovery_state_difference_prefixes": [
                i for i, (a, b) in enumerate(zip(initial, recovery)) if a["state"] != b["state"]],
            "short_recovery_gdn_difference_prefixes": [
                i for i, (a, b) in enumerate(zip(initial_gdn, recovery_gdn)) if a != b],
            "gdn_probe_prefix_index": min(8, len(initial_gdn) - 1),
            "first_gdn_difference_ordinals": [
                i for i, (a, b) in enumerate(zip(
                    initial_gdn[min(8, len(initial_gdn) - 1)],
                    recovery_gdn[min(8, len(recovery_gdn) - 1)])) if a != b]
                if initial_gdn[min(8, len(initial_gdn) - 1)] !=
                recovery_gdn[min(8, len(recovery_gdn) - 1)] else [],
            "selected_position_request_blocks": {
                str(position): len(by_position[position]) // 48 for position in positions
            },
            "adjacent_same_prompt_comparisons": same_prompt_pairs,
            "positions": position_results,
        }
    output = {
        "scope": f"same-service {campaign.get('sequence', 'short-long-short')} accepted-prefix and selected-position trace",
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
        "position_results": data["positions"],
    } for arm, data in arms.items()}, indent=2))


if __name__ == "__main__":
    main()
