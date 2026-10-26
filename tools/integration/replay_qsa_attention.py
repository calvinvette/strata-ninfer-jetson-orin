#!/usr/bin/env python3
"""Replay captured QSA attention with a host FP64 mathematical reference."""
import argparse
import json
import math
from pathlib import Path

from compare_qsa_capture import metrics as qsa_metrics, read_capture as read_qsa
from compare_qsa_kv_capture import compare as compare_kv, read_capture as read_kv


def fwht256(values):
    out = list(values)
    width = 1
    while width < 256:
        for base in range(0, 256, width * 2):
            for j in range(width):
                a, b = out[base + j], out[base + j + width]
                out[base + j], out[base + j + width] = a + b, a - b
        width *= 2
    return [x / 16.0 for x in out]


def replay(qsa_path, kv_path):
    meta, fields, selection = read_qsa(Path(qsa_path))
    kv = read_kv(kv_path)
    layer, position, n_kv, head_dim, capacity, token, valid_count = kv["identity"]
    if (layer, position, token, capacity) != (meta["layer"], meta["position"], meta["token"], meta["cap"]):
        raise ValueError("QSA and K/V capture identities differ")
    if n_kv * head_dim != meta["kv_width"] or len(selection) != capacity:
        raise ValueError("QSA and K/V dimensions differ")
    selected = selection[:valid_count]
    if len(set(selected)) != len(selected):
        raise ValueError("selected cell IDs are not unique")
    q_heads = meta["q_width"] // head_dim
    if q_heads % n_kv:
        raise ValueError("query-head to KV-head ratio is not integral")
    heads_per_kv = q_heads // n_kv
    row_width = kv["row_width"]
    values = kv["data"]
    total = capacity * row_width
    keys = values[:valid_count * row_width]
    vals = values[total:total + valid_count * row_width]
    inv_sqrt = 1.0 / math.sqrt(head_dim)
    replayed = [0.0] * meta["q_width"]
    for h in range(q_heads):
        kvh = h // heads_per_kv
        qrow = fields["query"][h * head_dim:(h + 1) * head_dim]
        scores = []
        for cell in range(valid_count):
            base = cell * row_width + kvh * head_dim
            scores.append(math.fsum(q * k for q, k in zip(qrow, keys[base:base + head_dim])) * inv_sqrt)
        maximum = max(scores)
        weights = [math.exp(score - maximum) for score in scores]
        denom = math.fsum(weights)
        out = [math.fsum(weights[cell] * vals[cell * row_width + kvh * head_dim + d]
                         for cell in range(valid_count)) / denom for d in range(head_dim)]
        if meta["reserved"] & 3:
            out = fwht256(out)
        replayed[h * head_dim:(h + 1) * head_dim] = out
    return {
        "layer": layer,
        "position": position,
        "token": token,
        "valid_count": valid_count,
        "kv_transform_flags": meta["reserved"] & 3,
        "reference_vs_engine_attention": qsa_metrics(tuple(replayed), fields["attention"]),
        "attention": replayed,
    }


def compare_replays(reference_qsa, reference_kv, candidate_qsa, candidate_kv):
    reference = replay(reference_qsa, reference_kv)
    candidate = replay(candidate_qsa, candidate_kv)
    for key in ("layer", "position", "token", "valid_count", "kv_transform_flags"):
        if reference[key] != candidate[key]:
            raise ValueError(f"paired QSA replay metadata differs: {key}")
    _, ref_fields, _ = read_qsa(Path(reference_qsa))
    _, cand_fields, _ = read_qsa(Path(candidate_qsa))
    return {
        "layer": reference["layer"],
        "position": reference["position"],
        "token": reference["token"],
        "valid_count": reference["valid_count"],
        "cache_rows": compare_kv(reference_kv, candidate_kv),
        "oracle_output_difference": qsa_metrics(reference["attention"], candidate["attention"]),
        "captured_engine_output_difference": qsa_metrics(ref_fields["attention"], cand_fields["attention"]),
        "reference_oracle_vs_engine": reference["reference_vs_engine_attention"],
        "candidate_oracle_vs_engine": candidate["reference_vs_engine_attention"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("qsa")
    parser.add_argument("kv")
    parser.add_argument("--candidate-qsa")
    parser.add_argument("--candidate-kv")
    parser.add_argument("--output")
    args = parser.parse_args()
    if (args.candidate_qsa is None) != (args.candidate_kv is None):
        parser.error("--candidate-qsa and --candidate-kv must be given together")
    if args.candidate_qsa:
        result = compare_replays(args.qsa, args.kv, args.candidate_qsa, args.candidate_kv)
    else:
        result = replay(args.qsa, args.kv)
        result.pop("attention")
    output = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
