#!/usr/bin/env python3
"""Replay a captured GDN recurrence against an independent FP64 equation oracle.

Inputs are opt-in runtime captures: an STGCMT1 state record at the prompt
boundary, STGDIAG4 rows for consecutive generated tokens, and STGDOO1 raw-o
rows. The oracle implements the gated delta update directly in Python doubles;
it does not call the CUDA or NInfer kernel implementation.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import sys

COMMIT_HEADER = struct.Struct("<8sIiqQQii")
DIAG_HEADER = struct.Struct("<8sIiiqQQQQQ8i")
O_HEADER = struct.Struct("<8sIiiqQ8i")


def read_state(path: Path, layer: int, position: int) -> tuple[list[float], int]:
    with path.open("rb") as stream:
        while header := stream.read(COMMIT_HEADER.size):
            if len(header) != COMMIT_HEADER.size:
                raise ValueError(f"{path}: truncated state header")
            magic, version, row_layer, row_pos, recurrent, count, _token, slot = COMMIT_HEADER.unpack(header)
            if magic[:7] != b"STGCMT1" or version != 1 or not count or recurrent > count:
                raise ValueError(f"{path}: invalid STGCMT1 record")
            payload = stream.read(count * 4)
            if len(payload) != count * 4:
                raise ValueError(f"{path}: truncated STGCMT1 payload")
            if row_layer == layer and row_pos == position and slot == 0:
                return list(struct.unpack(f"<{count}f", payload)), recurrent
    raise ValueError(f"{path}: no layer {layer}, position {position}, slot 0 state")


def read_inputs(path: Path, layer: int) -> dict[int, tuple[int, int, int, int, list[float], list[float], list[float]]]:
    rows = {}
    with path.open("rb") as stream:
        while header := stream.read(DIAG_HEADER.size):
            if len(header) != DIAG_HEADER.size:
                raise ValueError(f"{path}: truncated STGDIAG4 header")
            magic, version, row_layer, count, pos0, n_embd, channels, heads, value_dim, _state_floats, *tokens = DIAG_HEADER.unpack(header)
            if magic != b"STGDIAG4" or version != 4 or not 1 <= count <= len(tokens):
                raise ValueError(f"{path}: expected STGDIAG4 records")
            dims = [count * n_embd, count * channels, count * channels, count * heads,
                    count * heads, count * value_dim, count * value_dim,
                    count * n_embd, count * n_embd, count * n_embd]
            fields = []
            for size in dims:
                payload = stream.read(size * 4)
                if len(payload) != size * 4:
                    raise ValueError(f"{path}: truncated STGDIAG4 payload")
                fields.append(struct.unpack(f"<{size}f", payload))
            if row_layer != layer:
                continue
            for i in range(count):
                pos = pos0 + i
                if pos in rows:
                    raise ValueError(f"{path}: duplicate position {pos}")
                h = fields[2][i * channels:(i + 1) * channels]
                gate = fields[3][i * heads:(i + 1) * heads]
                beta = fields[4][i * heads:(i + 1) * heads]
                rows[pos] = (tokens[i], channels, heads, value_dim, list(h), list(gate), list(beta))
    if not rows:
        raise ValueError(f"{path}: no GDN rows for layer {layer}")
    return rows


def read_outputs(path: Path, layer: int) -> dict[int, tuple[int, int, list[float]]]:
    rows = {}
    with path.open("rb") as stream:
        while header := stream.read(O_HEADER.size):
            if len(header) != O_HEADER.size:
                raise ValueError(f"{path}: truncated STGDOO1 header")
            magic, version, row_layer, count, pos0, value_dim, *tokens = O_HEADER.unpack(header)
            if magic != b"STGDOO1\0" or version != 1 or not 1 <= count <= len(tokens):
                raise ValueError(f"{path}: invalid STGDOO1 record")
            payload = stream.read(count * value_dim * 4)
            if len(payload) != count * value_dim * 4:
                raise ValueError(f"{path}: truncated STGDOO1 payload")
            values = struct.unpack(f"<{count * value_dim}f", payload)
            if row_layer != layer:
                continue
            for i in range(count):
                pos = pos0 + i
                if pos in rows:
                    raise ValueError(f"{path}: duplicate raw-o position {pos}")
                rows[pos] = (tokens[i], value_dim, list(values[i * value_dim:(i + 1) * value_dim]))
    if not rows:
        raise ValueError(f"{path}: no raw-o rows for layer {layer}")
    return rows


def replay_step(state: list[float], row: tuple, head_size: int, key_heads: int) -> list[float]:
    _token, channels, value_heads, value_dim, h, gate, beta = row
    s_size = head_size
    if value_dim != head_size * value_heads:
        raise ValueError("unexpected GDN value dimension")
    expected_channels = 2 * head_size * key_heads + value_dim
    recurrent_count = head_size * value_heads * head_size
    if channels != expected_channels or len(state) < recurrent_count:
        raise ValueError("unexpected Qwen GDN geometry or truncated recurrent state")
    if len(h) != channels or len(gate) != value_heads or len(beta) != value_heads:
        raise ValueError("incomplete GDN input row")

    qk_size = head_size * key_heads
    row_stride = value_heads * head_size
    output = [0.0] * value_dim
    for head in range(value_heads):
        query_head = head % key_heads
        q0 = query_head * head_size
        k0 = qk_size + query_head * head_size
        v0 = 2 * qk_size + head * head_size
        decay = math.exp(gate[head])
        b = beta[head]
        for col in range(head_size):
            base = head * head_size + col
            kv = 0.0
            for r in range(head_size):
                kv += state[r * row_stride + base] * h[k0 + r]
            delta = (h[v0 + col] - decay * kv) * b
            o = 0.0
            for r in range(head_size):
                index = r * row_stride + base
                state[index] = decay * state[index] + h[k0 + r] * delta
                o += state[index] * h[q0 + r]
            output[base] = o
    return output


def compare(expected: list[float], actual: list[float]) -> dict:
    if len(expected) != len(actual):
        raise ValueError("oracle and captured output sizes differ")
    error_sq = reference_sq = 0.0
    max_abs = 0.0
    for ref, got in zip(expected, actual):
        if not math.isfinite(ref) or not math.isfinite(got):
            raise ValueError("non-finite GDN value")
        error = got - ref
        error_sq += error * error
        reference_sq += ref * ref
        max_abs = max(max_abs, abs(error))
    return {"values": len(expected), "max_abs": max_abs,
            "relative_l2": math.sqrt(error_sq / reference_sq) if reference_sq else math.sqrt(error_sq)}


def validate_positions(positions: list[int], state_position: int) -> None:
    if not positions or positions[0] != state_position + 1:
        raise ValueError("captured GDN rows must start immediately after the state position")
    if positions != list(range(positions[0], positions[-1] + 1)):
        raise ValueError("captured GDN rows must be consecutive")


def run(state_path: Path, diag_path: Path, output_path: Path, layer: int,
        state_position: int, head_size: int, key_heads: int) -> dict:
    state, recurrent = read_state(state_path, layer, state_position)
    inputs = read_inputs(diag_path, layer)
    outputs = read_outputs(output_path, layer)
    positions = sorted(inputs)
    validate_positions(positions, state_position)
    if set(positions) != set(outputs):
        raise ValueError("GDN input and raw-o position sets differ")
    value_heads = inputs[positions[0]][2]
    if recurrent != head_size * value_heads * head_size:
        raise ValueError(f"state recurrent size {recurrent} does not match geometry")
    records = []
    for position in positions:
        input_row = inputs[position]
        token, value_dim, actual = outputs[position]
        if input_row[0] != token or input_row[3] != value_dim:
            raise ValueError(f"token or output dimension differs at position {position}")
        predicted = replay_step(state, input_row, head_size, key_heads)
        records.append({"position": position, "token": token, **compare(predicted, actual)})
    worst = max(records, key=lambda row: row["relative_l2"])
    return {"schema": 1, "layer": layer, "state_position": state_position,
            "position_range": [positions[0], positions[-1]], "positions_replayed": len(records),
            "method": "independent FP64 gated-delta recurrence over captured h/gate/beta and initial state",
            "worst_position": worst["position"], "worst_relative_l2": worst["relative_l2"],
            "records": records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True, help="STGCMT1 accepted-prefix state capture")
    parser.add_argument("--diag", type=Path, required=True, help="STGDIAG4 GDN input capture")
    parser.add_argument("--raw-o", type=Path, required=True, help="STGDOO1 recurrence output capture")
    parser.add_argument("--layer", type=int, required=True)
    parser.add_argument("--state-position", type=int, required=True,
                        help="accepted-prefix state immediately before the first captured token")
    parser.add_argument("--head-size", type=int, default=128)
    parser.add_argument("--key-heads", type=int, default=16)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = run(args.state, args.diag, args.raw_o, args.layer,
                     args.state_position, args.head_size, args.key_heads)
    except (OSError, ValueError, struct.error) as exc:
        print(f"gdn_trace_oracle: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
