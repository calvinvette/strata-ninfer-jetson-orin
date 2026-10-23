#!/usr/bin/env python3
"""Compare captured CPU/GPU Q8_1 hidden blocks and locate FP16 scale ties."""

import argparse
import json
import struct
from pathlib import Path


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def ordered_f32(value: float) -> int:
    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    return (~bits & 0xFFFFFFFF) if bits & 0x80000000 else (bits | 0x80000000)


def analyze(cpu_path: Path, root: Path) -> dict | None:
    gpu_path = cpu_path.with_name(cpu_path.name.replace("--cpu-hidden.q8_1", "--gpu-hidden.q8_1"))
    float_path = cpu_path.with_name(cpu_path.name.replace("--cpu-hidden.q8_1", "--cpu-hidden.f32"))
    if not gpu_path.is_file() or not float_path.is_file():
        return None
    cpu = cpu_path.read_bytes()
    gpu = gpu_path.read_bytes()
    floats_raw = float_path.read_bytes()
    if len(cpu) != len(gpu) or len(cpu) % 36 or len(floats_raw) != (len(cpu) // 36) * 32 * 4:
        return None
    hidden = struct.unpack(f"<{len(floats_raw) // 4}f", floats_raw)
    mismatched = []
    for block in range(len(cpu) // 36):
        off = block * 36
        c, g = cpu[off : off + 36], gpu[off : off + 36]
        if c == g:
            continue
        cd, gd = struct.unpack("<e", c[:2])[0], struct.unpack("<e", g[:2])[0]
        cs = f32(max(abs(x) for x in hidden[block * 32 : (block + 1) * 32]) / 127.0)
        midpoint = f32((cd + gd) * 0.5)
        mismatched.append(
            {
                "block": block,
                "cpu_d_hex": c[:2].hex(),
                "gpu_d_hex": g[:2].hex(),
                "cpu_scale_f32_hex": struct.pack("<f", cs).hex(),
                "cpu_scale_minus_midpoint_ulps": ordered_f32(cs) - ordered_f32(midpoint),
                "sum_equal": c[2:4] == g[2:4],
                "code_bytes_differ": sum(x != y for x, y in zip(c[4:], g[4:])),
            }
        )
    return {
        "cpu_q8_1": str(cpu_path.relative_to(root)),
        "gpu_q8_1": str(gpu_path.relative_to(root)),
        "cpu_float_hidden": str(float_path.relative_to(root)),
        "blocks": len(cpu) // 36,
        "differing_blocks": len(mismatched),
        "d_only_blocks": sum(x["sum_equal"] and x["code_bytes_differ"] == 0 for x in mismatched),
        "details": mismatched,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="directory tree containing paired captures")
    parser.add_argument(
        "--cpu-q8",
        action="append",
        required=True,
        help="explicit CPU hidden Q8_1 capture relative to --root; repeat for each matched-input pair",
    )
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()
    root = args.root.resolve()
    reports = []
    for name in args.cpu_q8:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            parser.error(f"capture escapes --root: {name}")
        report = analyze(path, root)
        if report is None:
            parser.error(f"capture has no matching GPU Q8_1 and CPU float hidden files: {name}")
        reports.append(report)
    payload = json.dumps(reports, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")
    print(f"analyzed {len(reports)} CPU/GPU hidden-Q8_1 capture pairs", file=__import__("sys").stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
