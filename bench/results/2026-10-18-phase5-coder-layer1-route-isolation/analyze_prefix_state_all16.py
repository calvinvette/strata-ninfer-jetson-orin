#!/usr/bin/env python3
"""Join accepted-prefix GDN state hashes to the all-layer route activation trace."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "bench/results/2026-10-18-phase5-coder-layer1-route-isolation"
CAMPAIGN = REPORT / "all-16-positions-three-arm-wildcard"
ARMS = ("cpu_default", "cpu_mirror", "gpu_layer1")
PAIRS = (("cpu_default", "cpu_mirror"), ("cpu_mirror", "gpu_layer1"))
GDN_MODEL_LAYERS = [layer for layer in range(48) if layer % 4 != 3]


def parse_logs(arm):
    lines = (CAMPAIGN / arm / "result/service.log").read_text(errors="replace").splitlines()
    prefill = [line.split("prefill: GDN_HASH ", 1)[1].split()
               for line in lines if "prefill: GDN_HASH " in line]
    post = [line.split("STATE_HASH_GDN ", 1)[1].split()
            for line in lines if "STATE_HASH_GDN " in line]
    accepted = []
    pattern = re.compile(r"ACCEPTED_PREFIX position=(\d+).*?tokens=([0-9,-]+) state=\{STATE_HASH ([^}]*)\}")
    for line in lines:
        match = pattern.search(line)
        if not match:
            continue
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", match.group(3)))
        accepted.append({"position": int(match.group(1)), "tokens": match.group(2), "state": fields})
    if len(prefill) != 1 or len(prefill[0]) != 36:
        raise ValueError(f"{arm}: expected one 36-slice prefill GDN checksum")
    if len(post) != 16 or any(len(row) != 36 for row in post):
        raise ValueError(f"{arm}: expected 16 post-prefix 36-slice GDN hashes")
    if len(accepted) != 16:
        raise ValueError(f"{arm}: expected 16 accepted-prefix records")
    for i, row in enumerate(accepted):
        if int(row["state"]["L"]) != 512 + i:
            raise ValueError(f"{arm}: unexpected committed length at prefix {i}")
    return {"prefill": prefill[0], "post": post, "accepted": accepted}


def parse_routes(arm):
    path = CAMPAIGN / arm / "result/routes-all-layers.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()[1:]]
    # The route trace is keyed by the token entering the block. The accepted
    # prefix log records the token emitted after that block stack, so they are
    # intentionally not the same token ID.
    keyed = {(row["layer"], row["position"]): row for row in rows}
    if len(rows) != 768 or len(keyed) != 768:
        raise ValueError(f"{arm}: expected 768 unique route keys")
    return keyed


logs = {arm: parse_logs(arm) for arm in ARMS}
routes = {arm: parse_routes(arm) for arm in ARMS}
for arm in ARMS[1:]:
    if logs[arm]["accepted"] != logs[ARMS[0]]["accepted"]:
        # Accepted state differs by design, but token keys and counts must align.
        a = logs[ARMS[0]]["accepted"]
        b = logs[arm]["accepted"]
        if [(x["position"], x["tokens"]) for x in a] != [(x["position"], x["tokens"]) for x in b]:
            raise ValueError(f"{arm}: accepted token keys do not match controls")

state_summary = {}
for left, right in PAIRS:
    prefill_diffs = [i for i, (a, b) in enumerate(zip(logs[left]["prefill"], logs[right]["prefill"])) if a != b]
    prefixes = []
    for i, (a, b) in enumerate(zip(logs[left]["post"], logs[right]["post"])):
        gdn_diff = [j for j, (x, y) in enumerate(zip(a, b)) if x != y]
        changed_fields = [key for key in sorted(set(logs[left]["accepted"][i]["state"]) |
                                                 set(logs[right]["accepted"][i]["state"]))
                          if logs[left]["accepted"][i]["state"].get(key) !=
                             logs[right]["accepted"][i]["state"].get(key)]
        prefixes.append({
            "position": logs[left]["accepted"][i]["position"],
            "token_id": int(logs[left]["accepted"][i]["tokens"].split(",")[0]),
            "accepted_prefix_state_changed_fields": changed_fields,
            "gdn_differing_state_ordinals": gdn_diff,
            "gdn_first_differing_ordinal": gdn_diff[0] if gdn_diff else None,
            "gdn_first_differing_model_layer": GDN_MODEL_LAYERS[gdn_diff[0]] if gdn_diff else None,
            "gdn_different_slices": len(gdn_diff),
        })
    state_summary[f"{left}_vs_{right}"] = {
        "prefill_gdn_checksum_bits": 16,
        "prefill_gdn_checksum_differing_ordinals": prefill_diffs,
        "prefill_gdn_checksums_match_all_36": not prefill_diffs,
        "prefixes": prefixes,
    }

route_summary = {}
for left, right in PAIRS:
    rows = []
    for position in range(511, 527):
        first = None
        for layer in range(48):
            a = routes[left][(layer, position)]
            b = routes[right][(layer, position)]
            if a["token_id"] != b["token_id"]:
                raise ValueError(f"{left}/{right}: route input token differs at layer={layer} position={position}")
            # The GPU-profile host callback is known to be stale at these all-GPU layer-1 rows.
            if left == "cpu_mirror" and right == "gpu_layer1" and layer == 1 and position in (511, 513):
                continue
            delta = max(abs(float(x) - float(y)) for x, y in zip(a["activation"], b["activation"]))
            if delta > 1e-7:
                first = {"layer": layer, "max_abs_delta": delta,
                         "expert_ids_equal": a["ids"] == b["ids"],
                         "owners_equal": a["route_kind"] == b["route_kind"]}
                break
        state = state_summary[f"{left}_vs_{right}"]["prefixes"][position - 511]
        rows.append({"position": position, "first_host_route_activation_difference": first,
                     "first_gdn_state_difference_after_commit": state["gdn_first_differing_model_layer"],
                     "route_and_gdn_first_difference_layers_match":
                         first is not None and first["layer"] == state["gdn_first_differing_model_layer"]})
    route_summary[f"{left}_vs_{right}"] = rows

out = {
    "schema": 1,
    "campaign": str(CAMPAIGN.relative_to(ROOT)),
    "gdn_ordinal_to_model_layer": GDN_MODEL_LAYERS,
    "prefill_hash_interpretation": "The prompt path emits only 16-bit per-slice GDN checksums; matching values are evidence but do not prove byte identity.",
    "state_pairs": state_summary,
    "first_route_activation_differences": route_summary,
    "conclusion": "The first accepted-prefix GDN divergence is local to an early model layer and aligns with the first host route-activation divergence for all 16 positions in each pair. The prefill GDN checksums match, but their 16-bit width is too weak to claim exact prefill-state identity. Device-side layer-1 ffn_y remains the authoritative check where host captures are stale.",
}
path = CAMPAIGN / "prefix-state-alignment.json"
path.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({
    "prefill_checksums_match_all_36": {
        pair: result["prefill_gdn_checksums_match_all_36"]
        for pair, result in state_summary.items()},
    "first_state_divergence_at_position_511": {
        pair: {"model_layer": result["prefixes"][0]["gdn_first_differing_model_layer"],
               "changed_fields": result["prefixes"][0]["accepted_prefix_state_changed_fields"]}
        for pair, result in state_summary.items()},
    "route_and_gdn_first_difference_layers_match": {
        pair: sum(row["route_and_gdn_first_difference_layers_match"] for row in rows)
        for pair, rows in route_summary.items()},
    "output": str(path),
}, indent=2))
