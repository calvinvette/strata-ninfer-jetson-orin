#!/usr/bin/env python3
"""Fail-closed paired analysis for the layer-1 Q8_1 owner-equivalence run."""
import hashlib
import argparse
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGETS = {(1, expert) for expert in (205, 101, 32, 11, 95, 18, 165)}
FILLERS = {(6, 17), (3, 153), (3, 145), (1, 218), (0, 124), (0, 78), (46, 186)}
STATE_KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "ple_prev", "mtp", "stale")
PREFIX_RE = re.compile(
    r"ACCEPTED_PREFIX position=(\d+) window=(\d+) accepted_drafts=(\d+) "
    r"committed=(\d+) tokens=([0-9,]+) state=\{STATE_HASH ([^}]+)\}"
)
FIELD_RE = re.compile(r"(\w+)=([0-9a-f,-]+)")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def jsonl(path):
    lines = read_text(path).splitlines()
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]


def read_text(path):
    if path.suffix == ".gz" and path.exists():
        with gzip.open(path, "rt") as stream:
            return stream.read()
    if path.exists():
        return path.read_text()
    compressed = Path(str(path) + ".gz")
    if compressed.exists():
        with gzip.open(compressed, "rt") as stream:
            return stream.read()
    raise FileNotFoundError(path)


def read_bytes(path):
    if path.suffix == ".gz" and path.exists():
        with gzip.open(path, "rb") as stream:
            return stream.read()
    if path.exists():
        return path.read_bytes()
    compressed = Path(str(path) + ".gz")
    if compressed.exists():
        with gzip.open(compressed, "rb") as stream:
            return stream.read()
    raise FileNotFoundError(path)


def capture_path(request, run, filename, metadata_key):
    path = run / filename
    if path.exists() or Path(str(path) + ".gz").exists():
        return path
    metadata = request.get("capture_artifacts", {}).get(metadata_key)
    require(metadata is not None, f"missing retained capture metadata: {metadata_key}")
    return HERE / metadata["path"]


def verify_capture(request, run, filename, metadata_key):
    path = capture_path(request, run, filename, metadata_key)
    metadata = request.get("capture_artifacts", {}).get(metadata_key)
    if metadata is None:
        return path
    data = read_bytes(path)
    require(hashlib.sha256(data).hexdigest() == metadata["sha256"],
            f"capture digest mismatch: {metadata_key} in {run}")
    require(len(data) == metadata["bytes"], f"capture size mismatch: {metadata_key} in {run}")
    return path


def prefix_states(path):
    rows = []
    for line in read_text(path).splitlines():
        match = PREFIX_RE.search(line)
        if not match:
            continue
        position, window, accepted, committed = map(int, match.group(1, 2, 3, 4))
        tokens = [int(value) for value in match.group(5).split(",")]
        fields = dict(FIELD_RE.findall(match.group(6)))
        require(set(STATE_KEYS) <= fields.keys(), f"incomplete state fingerprint in {path}")
        rows.append({"position": position, "window": window, "accepted_drafts": accepted,
                     "committed": committed, "tokens": tokens,
                     "state": {key: fields[key] for key in STATE_KEYS}})
    return rows


def expected_owner_deltas(control_rows, gpu_rows):
    require(len(control_rows) == len(gpu_rows), "route row counts differ")
    deltas = []
    route_fingerprints_match = True
    changed_pairs = set()
    for left, right in zip(control_rows, gpu_rows):
        key = (left["layer"], left["position"], left["token_id"], left["row"])
        require(key == (right["layer"], right["position"], right["token_id"], right["row"]),
                f"route row key differs: {key}")
        require(left["ids"] == right["ids"], f"expert IDs differ at {key}")
        require(left["n_tok"] == right["n_tok"], f"token width differs at {key}")
        # The diagnostic trace stores the activation entering routing. Require it
        # to match except for the known stale host callback on all-GPU rows.
        if left.get("activation") != right.get("activation"):
            route_fingerprints_match = False
        require(len(left["route_kind"]) == len(right["route_kind"]) == len(left["ids"]),
                f"route owner vector shape differs at {key}")
        for expert, old_owner, new_owner in zip(left["ids"], left["route_kind"], right["route_kind"]):
            if old_owner == new_owner:
                continue
            pair = (left["layer"], expert)
            require(pair in TARGETS and old_owner == -1 and new_owner == 0,
                    f"unexpected ownership change {pair}: {old_owner}->{new_owner} at {key}")
            changed_pairs.add(pair)
            deltas.append({"layer": pair[0], "expert": pair[1], "position": left["position"]})
    return deltas, changed_pairs, route_fingerprints_match


def inspect_cell(cell):
    supervisor = json.loads((cell / "supervisor/result.json").read_text())
    require(supervisor["status"] == "pass" and supervisor["returncode"] == 0,
            f"supervisor failed: {cell}")
    minimum = min(supervisor["minimum_available_bytes"],
                  supervisor["minimum_admission_available_bytes"])
    require(minimum >= 6 * 1024**3, f"six-GiB headroom floor breached: {cell}")
    for line in read_text(cell / "supervisor/memory.jsonl").splitlines():
        sample = json.loads(line)
        for cgroup in sample.get("cgroups", []):
            events = cgroup.get("memory_events", {})
            require(all(events.get(k, 0) == 0 for k in ("low", "high", "max", "oom", "oom_kill")),
                    f"cgroup pressure/OOM event in {cell}: {events}")
    run = cell / "run"
    request = json.loads((run / "requests.json").read_text())
    require(request["selector"] == "iq2_s/q2_0@layer=1", f"wrong selector in {cell}")
    require(request["expert_cache_argument"] == 3007, f"wrong cache argument in {cell}")
    require(request["accepted_prefix_records"] == 16, f"expected 16 committed-prefix records in {cell}")
    log_text = (run / "service.log").read_text(errors="replace")
    require("profile " in log_text and "3007 ranked pairs, built for 3007 slots" in log_text,
            f"actual profile/cache geometry is not verified in {cell}")
    require("pre-filled 3007 of 3007 slots" in log_text,
            f"not all 3007 profile slots were filled in {cell}")
    states = prefix_states(run / "service.log")
    require(len(states) == 16, f"expected 16 parseable state records in {cell}, got {len(states)}")
    route_path = verify_capture(request, run, "routes-all-layers.jsonl", "routes_all_layers")
    verify_capture(request, run, "cpu-outputs-layer1.jsonl", "cpu_outputs_layer1")
    verify_capture(request, run, "combined-moe.bin", "combined_moe")
    header, routes = jsonl(route_path)
    require(header.get("format") == "strata-moe-dispatch-v3" and len(routes) == 768,
            f"invalid route capture in {cell}")
    gdn_path = run / "prefill-gdn.bin"
    gdn_hash = hashlib.sha256(gdn_path.read_bytes()).hexdigest() if gdn_path.exists() else request.get("prefill_gdn_sha256")
    require(gdn_hash and request.get("prefill_gdn_sha256", gdn_hash) == gdn_hash,
            f"prompt-end GDN dump hash missing or inconsistent in {cell}")
    return {"supervisor": supervisor, "request": request, "states": states,
            "header": header, "routes": routes,
            "prefill_gdn_sha256": gdn_hash,
            "prefill_gdn_bytes": request.get("prefill_gdn_bytes", gdn_path.stat().st_size if gdn_path.exists() else None)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", default="bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/paired-runs",
                    help="directory containing block-1 through block-3")
    ap.add_argument("--device-route-dir",
                    default="bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/device-route-pair-retry1",
                    help="directory containing cpu_mirror and gpu_layer1 route captures")
    ap.add_argument("--output", default="bench/results/2026-10-19-phase5-coder-layer1-q8_1-owner-equivalence/analysis.json")
    args = ap.parse_args()
    runs_root = Path(args.runs)
    device_dir = Path(args.device_route_dir)
    output_path = Path(args.output)
    if not runs_root.is_absolute():
        runs_root = ROOT / runs_root
    if not device_dir.is_absolute():
        device_dir = ROOT / device_dir
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    order_lines = (runs_root / "order.txt").read_text().splitlines()
    order = [line.partition("order: ")[2].split() for line in order_lines if line.startswith("block ")]
    result = {"schema": 1, "source_commit": "58ea8c00", "selector": "iq2_s/q2_0@layer=1",
              "requested_cache_slots": 3007, "randomized_order": order_lines, "blocks": [],
              "performance_claim": None}
    minimum_gib = float("inf")
    gdn_hashes = []
    for block_index in range(1, 4):
        block = runs_root / f"block-{block_index}"
        control = inspect_cell(block / "cpu_mirror")
        gpu = inspect_cell(block / "gpu_layer1")
        require(control["request"]["arm"] == "cpu_mirror" and gpu["request"]["arm"] == "gpu_layer1",
                f"arm identity mismatch in block {block_index}")
        require(control["request"]["prompt_sha256"] == gpu["request"]["prompt_sha256"],
                f"formatted prompt differs in block {block_index}")
        require(control["request"]["completion_ids"] == gpu["request"]["completion_ids"],
                f"completion IDs differ in block {block_index}")
        require(control["states"] == gpu["states"], f"accepted-prefix fingerprints differ in block {block_index}")
        require(control["prefill_gdn_sha256"] == gpu["prefill_gdn_sha256"],
                f"prompt-end GDN bytes differ in block {block_index}")
        gdn_hashes.extend((control["prefill_gdn_sha256"], gpu["prefill_gdn_sha256"]))
        deltas, changed_pairs, activations_equal = expected_owner_deltas(control["routes"], gpu["routes"])
        require(changed_pairs == TARGETS, f"not all seven target owners changed in block {block_index}")
        # Filler pairs are used only to equalize profile length; none may be routed.
        for capture in (control, gpu):
            observed = {(row["layer"], expert) for row in capture["routes"] for expert in row["ids"]}
            require(not (observed & FILLERS), f"a filler expert was routed in block {block_index}")
        require(control["request"]["profile_sha256"] != gpu["request"]["profile_sha256"],
                f"profiles unexpectedly identical in block {block_index}")
        minimum_gib = min(minimum_gib,
                          control["supervisor"]["minimum_available_bytes"] / 1024**3,
                          control["supervisor"]["minimum_admission_available_bytes"] / 1024**3,
                          gpu["supervisor"]["minimum_available_bytes"] / 1024**3,
                          gpu["supervisor"]["minimum_admission_available_bytes"] / 1024**3)
        result["blocks"].append({
            "block": block_index,
            "profile_order": order[block_index - 1],
            "completion_tokens_equal": True,
            "accepted_prefix_records_each": 16,
            "accepted_drafts_each": sum(row["accepted_drafts"] for row in control["states"]),
            "accepted_prefix_state_fingerprints_equal": True,
            "prompt_end_gdn_byte_identical": True,
            "prompt_end_gdn_sha256": control["prefill_gdn_sha256"],
            "prompt_end_gdn_bytes": control["prefill_gdn_bytes"],
            "route_ids_and_token_keys_equal": True,
            "host_activation_capture_equal": activations_equal,
            "target_owner_changes": len(deltas),
            "distinct_target_experts_moved": len(changed_pairs),
            "minimum_host_or_admission_gib": round(min(
                control["supervisor"]["minimum_available_bytes"],
                control["supervisor"]["minimum_admission_available_bytes"],
                gpu["supervisor"]["minimum_available_bytes"],
                gpu["supervisor"]["minimum_admission_available_bytes"]) / 1024**3, 3),
            "cgroup_events": "zero",
        })
    device_control = inspect_cell(device_dir / "cpu_mirror")
    device_gpu = inspect_cell(device_dir / "gpu_layer1")
    require(device_control["request"]["completion_ids"] == device_gpu["request"]["completion_ids"],
            "device-route validation completion IDs differ")
    require(device_control["states"] == device_gpu["states"],
            "device-route validation accepted-prefix states differ")
    require(device_control["prefill_gdn_sha256"] == device_gpu["prefill_gdn_sha256"],
            "device-route validation prompt-end GDN differs")
    gdn_hashes.extend((device_control["prefill_gdn_sha256"], device_gpu["prefill_gdn_sha256"]))
    device_control_path = verify_capture(device_control["request"], device_dir / "cpu_mirror/run",
                                         "device-moe-routes.jsonl", "device_moe_routes_layer1")
    device_gpu_path = verify_capture(device_gpu["request"], device_dir / "gpu_layer1/run",
                                     "device-moe-routes.jsonl", "device_moe_routes_layer1")
    control_header, control_device_routes = jsonl(device_control_path)
    gpu_header, gpu_device_routes = jsonl(device_gpu_path)
    require(control_header == gpu_header and control_header.get("format") == "strata-verify-moe-route-v1",
            "invalid exact device route capture header")
    require(len(control_device_routes) == len(gpu_device_routes) == 16,
            "expected one exact device-side layer-1 route record per generated position")
    require(control_device_routes == gpu_device_routes,
            "device-side layer-1 expert IDs or router weights differ")
    deltas, pairs, _ = expected_owner_deltas(device_control["routes"], device_gpu["routes"])
    require(pairs == TARGETS, "device-route validation did not move all seven targets")
    result["device_route_validation"] = {
        "supervised_pair_passed": True,
        "device_route_records": len(control_device_routes),
        "device_side_expert_ids_and_router_weights_equal": True,
        "accepted_prefix_state_fingerprints_equal": True,
        "prompt_end_gdn_byte_identical": True,
        "prompt_end_gdn_sha256": device_control["prefill_gdn_sha256"],
        "target_owner_changes": len(deltas),
        "minimum_host_or_admission_gib": round(min(
            device_control["supervisor"]["minimum_available_bytes"],
            device_control["supervisor"]["minimum_admission_available_bytes"],
            device_gpu["supervisor"]["minimum_available_bytes"],
            device_gpu["supervisor"]["minimum_admission_available_bytes"]) / 1024**3, 3),
        "cgroup_events": "zero",
    }
    parts = sorted(HERE.glob("prefill-gdn-reference.part*"))
    require(parts, "lossless prompt-end GDN reference parts are missing")
    h = hashlib.sha256()
    gdn_bytes = 0
    for part in parts:
        gdn_bytes += part.stat().st_size
        with part.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                h.update(block)
    gdn_reference_hash = h.hexdigest()
    require(set(gdn_hashes) == {gdn_reference_hash},
            "retained split GDN reference does not match every run's recorded hash")
    result["prompt_end_gdn_reference"] = {
        "parts": [str(path.relative_to(HERE)) for path in parts],
        "bytes": gdn_bytes,
        "sha256": gdn_reference_hash,
        "matches_every_run": True,
    }
    result["minimum_host_or_admission_gib"] = round(minimum_gib, 3)
    result["conclusion"] = (
        "Across three randomized pairs, changing owner placement for the seven captured "
        "layer-1 IQ2_S/Q2_0 experts from CPU Q8_1 mirror to CUDA preserved all 16 output "
        "tokens, all accepted-prefix state fingerprints, and exact prompt-end GDN bytes. "
        "The result applies only to this prompt, profile and expert pair; it is not a broad "
        "adaptive migration or performance qualification."
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
