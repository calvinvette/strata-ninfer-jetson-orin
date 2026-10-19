#!/usr/bin/env python3
"""Summarize exact and numeric differences between two raw GDN state dumps."""
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


def load(path):
    data = path.read_bytes()
    if len(data) < 32:
        raise ValueError(f"{path}: truncated GDN dump")
    magic, cells, layers, floats_per_layer = struct.unpack("<8sQQQ", data[:32])
    if magic != b"STGDN01\0":
        raise ValueError(f"{path}: unexpected GDN dump magic {magic!r}")
    values = array("f")
    values.frombytes(data[32:])
    if sys.byteorder != "little":
        values.byteswap()
    if len(values) != layers * floats_per_layer:
        raise ValueError(f"{path}: expected {layers * floats_per_layer} values, found {len(values)}")
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "cells": cells,
            "layers": layers, "floats_per_layer": floats_per_layer, "values": values,
            "raw_state": memoryview(data)[32:]}


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f"{value:016x}"


def position511_gdn_hashes(path, occurrence):
    lines = path.read_text().splitlines()
    hashes = []
    for index, line in enumerate(lines):
        if "ACCEPTED_PREFIX position=511 " not in line:
            continue
        if index == 0 or "STATE_HASH_GDN " not in lines[index - 1]:
            raise ValueError(f"{path}: position-511 accepted prefix lacks preceding GDN hashes")
        row = [value.lower() for value in lines[index - 1].split("STATE_HASH_GDN ", 1)[1].split()]
        hashes.append(row)
    if occurrence < 1 or occurrence > len(hashes):
        raise ValueError(f"{path}: requested position-511 occurrence {occurrence}, found {len(hashes)}")
    return hashes[occurrence - 1]


def verify_log_alignment(reference, candidate, reference_log, candidate_log,
                         reference_occurrence, candidate_occurrence):
    if reference_log is None and candidate_log is None:
        return None
    if reference_log is None or candidate_log is None:
        raise ValueError("both --reference-log and --candidate-log are required together")
    ref_hashes = position511_gdn_hashes(reference_log, reference_occurrence)
    cand_hashes = position511_gdn_hashes(candidate_log, candidate_occurrence)
    initial_hashes = position511_gdn_hashes(reference_log, 1)
    candidate_initial_hashes = position511_gdn_hashes(candidate_log, 1)
    if len(ref_hashes) != reference["layers"] or len(cand_hashes) != candidate["layers"]:
        raise ValueError("per-layer log hash count does not match dump layer count")
    layer_bytes = reference["floats_per_layer"] * 4
    ref_dump_hashes = [fnv1a(reference["raw_state"][i * layer_bytes:(i + 1) * layer_bytes])
                       for i in range(reference["layers"])]
    cand_dump_hashes = [fnv1a(candidate["raw_state"][i * layer_bytes:(i + 1) * layer_bytes])
                        for i in range(candidate["layers"])]
    if ref_dump_hashes != ref_hashes:
        raise ValueError("reference dump does not match its logged accepted-prefix GDN hashes")
    if cand_dump_hashes != cand_hashes:
        raise ValueError("candidate dump does not match its logged accepted-prefix GDN hashes")
    return {
        "reference_dump_matches_logged_prefix": True,
        "candidate_dump_matches_logged_prefix": True,
        "reference_occurrence": reference_occurrence,
        "candidate_occurrence": candidate_occurrence,
        "initial_hashes_match_across_runs": initial_hashes == candidate_initial_hashes,
    }


def summarize(reference, candidate):
    if (reference["cells"], reference["layers"], reference["floats_per_layer"]) != (
            candidate["cells"], candidate["layers"], candidate["floats_per_layer"]):
        raise ValueError("GDN dump shapes differ")
    per_layer = []
    totals = {"different_values": 0, "max_abs_diff": 0.0, "sum_sq_diff": 0.0, "sum_sq_reference": 0.0}
    for layer in range(reference["layers"]):
        start = layer * reference["floats_per_layer"]
        stop = start + reference["floats_per_layer"]
        ref_values = reference["values"][start:stop]
        new_values = candidate["values"][start:stop]
        if any(not math.isfinite(value) for value in ref_values) or any(not math.isfinite(value) for value in new_values):
            raise ValueError(f"GDN state contains a non-finite value at ordinal {layer}")
        diffs = [abs(a - b) for a, b in zip(ref_values, new_values)]
        changed = sum(a != b for a, b in zip(ref_values, new_values))
        sum_sq_diff = math.fsum(d * d for d in diffs)
        sum_sq_ref = math.fsum(v * v for v in ref_values)
        per_layer.append({"gdn_ordinal": layer, "different_values": changed,
                          "value_count": len(diffs), "max_abs_diff": max(diffs, default=0.0),
                          "relative_l2": math.sqrt(sum_sq_diff / sum_sq_ref) if sum_sq_ref else None})
        totals["different_values"] += changed
        totals["max_abs_diff"] = max(totals["max_abs_diff"], max(diffs, default=0.0))
        totals["sum_sq_diff"] += sum_sq_diff
        totals["sum_sq_reference"] += sum_sq_ref
    return {
        "scope": "float32 GDN state at identical accepted length; numerical comparison is descriptive, not an accuracy oracle",
        "cells": reference["cells"], "layers": reference["layers"],
        "floats_per_layer": reference["floats_per_layer"],
        "reference_sha256": reference["sha256"], "candidate_sha256": candidate["sha256"],
        "different_values": totals["different_values"],
        "value_count": reference["layers"] * reference["floats_per_layer"],
        "max_abs_diff": totals["max_abs_diff"],
        "relative_l2": math.sqrt(totals["sum_sq_diff"] / totals["sum_sq_reference"])
            if totals["sum_sq_reference"] else None,
        "per_layer": per_layer,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True, help="initial short-request dump")
    parser.add_argument("--candidate", type=Path, required=True, help="recovery short-request dump")
    parser.add_argument("--reference-log", type=Path,
                        help="service log associated with the reference dump")
    parser.add_argument("--candidate-log", type=Path,
                        help="service log associated with the candidate dump")
    parser.add_argument("--reference-occurrence", type=int, default=1,
                        help="1-based position-511 accepted-prefix occurrence for reference (default: 1)")
    parser.add_argument("--candidate-occurrence", type=int, default=2,
                        help="1-based position-511 accepted-prefix occurrence for candidate (default: 2)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference = load(args.reference)
    candidate = load(args.candidate)
    result = summarize(reference, candidate)
    validation = verify_log_alignment(reference, candidate, args.reference_log, args.candidate_log,
                                      args.reference_occurrence, args.candidate_occurrence)
    if validation is not None:
        result["log_alignment"] = validation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("cells", "layers", "floats_per_layer", "different_values",
                                               "value_count", "max_abs_diff", "relative_l2")}, indent=2))


if __name__ == "__main__":
    main()
