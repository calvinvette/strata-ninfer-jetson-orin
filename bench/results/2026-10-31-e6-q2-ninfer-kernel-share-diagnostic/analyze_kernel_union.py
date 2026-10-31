#!/usr/bin/env python3
"""Summarize CUDA kernel interval unions in Nsight Systems SQLite exports."""

import argparse
import json
import sqlite3


def union_duration(intervals):
    merged = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged)


def summarize(path):
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = db.execute(
        """SELECT k.start, k.end, s.value
           FROM CUPTI_ACTIVITY_KIND_KERNEL AS k
           JOIN StringIds AS s ON s.id = k.demangledName
           WHERE k.end > k.start"""
    ).fetchall()
    db.close()
    intervals = [(start, end) for start, end, _ in rows]
    total = sum(end - start for start, end in intervals)
    active = union_duration(intervals)
    ninfer = [
        (start, end)
        for start, end, name in rows
        if "d3_q2_0_grouped" in name
        or "d4_q2_0_grouped" in name
        or "ninfer_swiglu_quantize_q8_1_many" in name
    ]
    ninfer_sum = sum(end - start for start, end in ninfer)
    ninfer_union = union_duration(ninfer)
    return {
        "kernel_events": len(rows),
        "summed_kernel_duration_ms": total / 1e6,
        "kernel_interval_union_ms": active / 1e6,
        "overlap_ms": (total - active) / 1e6,
        "ninfer_identified_kernel_duration_ms": ninfer_sum / 1e6,
        "ninfer_identified_kernel_union_ms": ninfer_union / 1e6,
        "ninfer_share_of_kernel_union_percent": 100 * ninfer_union / active,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("strata_sqlite")
    parser.add_argument("ninfer_sqlite")
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "strata": summarize(args.strata_sqlite),
                "ninfer": summarize(args.ninfer_sqlite),
                "scope": "GPU kernel activity across one warmup and one measured request per arm; not request wall time",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
