#!/usr/bin/env python3
"""Compare selected per-layer GDN commit records, including different aligned positions."""

import argparse
import json
import math
from pathlib import Path
import struct
import sys

HEADER = struct.Struct("<8sIiqQQii")


def read_records(path: Path, position: int, slot: int):
    selected = {}
    with path.open("rb") as stream:
        while True:
            raw = stream.read(HEADER.size)
            if not raw:
                break
            if len(raw) != HEADER.size:
                raise ValueError(f"{path}: truncated header")
            magic, version, layer, pos, recurrent, count, token, record_slot = HEADER.unpack(raw)
            if magic[:7] != b"STGCMT1" or version != 1 or count == 0 or recurrent > count:
                raise ValueError(f"{path}: invalid STGCMT1 header")
            byte_count = count * 4
            if pos == position and record_slot == slot:
                payload = stream.read(byte_count)
                if len(payload) != byte_count:
                    raise ValueError(f"{path}: truncated selected payload for layer {layer}")
                if layer in selected:
                    raise ValueError(f"{path}: duplicate layer {layer} at position {position}, slot {slot}")
                selected[layer] = (token, recurrent, count, payload)
            else:
                stream.seek(byte_count, 1)
    if not selected:
        raise ValueError(f"{path}: no records at position {position}, slot {slot}")
    return selected


def metrics(a: bytes, b: bytes):
    if len(a) != len(b) or len(a) % 4:
        raise ValueError("state payload sizes differ or are not float32 aligned")
    changed = 0
    max_abs = 0.0
    err_sq = ref_sq = 0.0
    for (av,), (bv,) in zip(struct.iter_unpack("<f", a), struct.iter_unpack("<f", b)):
        delta = float(bv) - float(av)
        changed += av != bv
        max_abs = max(max_abs, abs(delta))
        err_sq += delta * delta
        ref_sq += float(av) * float(av)
    return {"values": len(a) // 4, "different_values": changed, "max_abs": max_abs,
            "relative_l2": math.sqrt(err_sq / ref_sq) if ref_sq else 0.0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("serial", type=Path)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--position", type=int, default=119,
                        help="common position fallback (default: %(default)s)")
    parser.add_argument("--serial-position", type=int)
    parser.add_argument("--batch-position", type=int)
    parser.add_argument("--slot", type=int, default=0, help="common slot fallback")
    parser.add_argument("--serial-slot", type=int)
    parser.add_argument("--batch-slot", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    serial_pos = args.position if args.serial_position is None else args.serial_position
    batch_pos = args.position if args.batch_position is None else args.batch_position
    serial_slot = args.slot if args.serial_slot is None else args.serial_slot
    batch_slot = args.slot if args.batch_slot is None else args.batch_slot
    serial = read_records(args.serial, serial_pos, serial_slot)
    batch = read_records(args.batch, batch_pos, batch_slot)
    if serial.keys() != batch.keys():
        raise ValueError(f"unpaired GDN layers: serial={sorted(serial)}, batch={sorted(batch)}")

    layers = []
    for layer in sorted(serial):
        stoken, srecurrent, scount, sdata = serial[layer]
        btoken, brecurrent, bcount, bdata = batch[layer]
        if stoken != btoken:
            raise ValueError(f"layer {layer}: token mismatch serial={stoken}, batch={btoken}")
        if srecurrent != brecurrent or scount != bcount:
            raise ValueError(f"layer {layer}: state dimensions differ")
        split = srecurrent * 4
        layers.append({"layer": layer, "token": stoken,
                       "recurrent": metrics(sdata[:split], bdata[:split]),
                       "convolution": metrics(sdata[split:], bdata[split:]),
                       "combined": metrics(sdata, bdata)})

    result = {"schema": 1,
              "coordinates": {"serial_position": serial_pos, "serial_slot": serial_slot,
                              "batch_position": batch_pos, "batch_slot": batch_slot},
              "layers_compared": len(layers),
              "first_changed_layer": next((x["layer"] for x in layers
                                            if x["combined"]["different_values"]), None),
              "all_layers": layers}
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    sys.stdout.write(rendered)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(f"compare_gdn_commit_state: {exc}", file=sys.stderr)
        raise SystemExit(2)
