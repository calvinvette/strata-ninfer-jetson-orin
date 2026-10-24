#!/usr/bin/env python3
"""Align retained host memory and NVMe counters with each request in a campaign."""

import argparse
import json
import statistics
from pathlib import Path


def disk_counters(snapshot):
    """Return read/write bytes for nvme0n1 from Linux /proc/diskstats sectors."""
    for line in snapshot["host_diskstats"].splitlines():
        fields = line.split()
        if len(fields) >= 10 and fields[2] == "nvme0n1":
            return {"read_bytes": int(fields[5]) * 512,
                    "write_bytes": int(fields[9]) * 512}
    raise ValueError("nvme0n1 is absent from a retained host diskstats sample")


def nearest(samples, timestamp):
    return min(samples, key=lambda row: abs(row["monotonic_s"] - timestamp))


def summarize(root, supervisor, output):
    samples = [json.loads(line) for line in supervisor.open() if line.strip()]
    if len(samples) < 2:
        raise ValueError("at least two supervisor samples are required")
    rows = []
    for request_path in sorted((root / "campaign/runs").glob("*/requests.json")):
        result = json.loads(request_path.read_text())
        checks = [row for row in result.get("checks", [])
                  if not row.get("warmup") and row.get("status") == "pass"]
        if not checks:
            continue
        check = checks[0]
        stream = check.get("stream_observation", {})
        events = stream.get("events", [])
        if not events or "request_start_monotonic_s" not in check:
            raise ValueError(f"{request_path}: missing request timing observations")
        start = check["request_start_monotonic_s"]
        end = start + events[-1]["elapsed_s"]
        start_sample, end_sample = nearest(samples, start), nearest(samples, end)
        in_request = [row for row in samples
                      if start <= row["monotonic_s"] <= end]
        if not in_request:
            in_request = [start_sample, end_sample]
        start_disk = disk_counters(start_sample)
        end_disk = disk_counters(end_sample)
        rows.append({
            "run": request_path.parent.name,
            "status": check["status"],
            "prompt_tokens": check["response"]["usage"]["prompt_tokens"],
            "completion_tokens": check["response"]["usage"]["completion_tokens"],
            "ttft_ms": stream.get("first_visible_delta_s", 0) * 1000,
            "request_ms": events[-1]["elapsed_s"] * 1000,
            "decode_ms": check["response"].get("timings", {}).get("predicted_ms"),
            "minimum_sampled_memavailable_bytes": min(
                row["available_bytes"] for row in in_request),
            "nvme0n1_read_bytes": end_disk["read_bytes"] - start_disk["read_bytes"],
            "nvme0n1_write_bytes": end_disk["write_bytes"] - start_disk["write_bytes"],
            "start_sample_gap_s": start_sample["monotonic_s"] - start,
            "end_sample_gap_s": end_sample["monotonic_s"] - end,
            "start_monotonic_s": start,
            "end_monotonic_s": end,
        })

    groups = {}
    for workers in (4, 8):
        for transfer in ("mapped", "pread"):
            selected = [row for row in rows
                        if f"workers-{workers}-{transfer}" in row["run"]]
            if not selected:
                continue
            groups[f"{workers}-{transfer}"] = {
                "n": len(selected),
                "ttft_ms_median": statistics.median(row["ttft_ms"] for row in selected),
                "request_ms_median": statistics.median(row["request_ms"] for row in selected),
                "request_ms_max": max(row["request_ms"] for row in selected),
                "decode_ms_median": statistics.median(row["decode_ms"] for row in selected),
                "minimum_memavailable_gib": min(
                    row["minimum_sampled_memavailable_bytes"] for row in selected) / 2**30,
                "median_nvme0n1_read_gb": statistics.median(
                    row["nvme0n1_read_bytes"] for row in selected) / 1e9,
                "median_nvme0n1_write_gb": statistics.median(
                    row["nvme0n1_write_bytes"] for row in selected) / 1e9,
                "maximum_endpoint_gap_s": max(
                    abs(row[key]) for row in selected
                    for key in ("start_sample_gap_s", "end_sample_gap_s")),
            }

    return {
        "schema": 1,
        "scope": "request-aligned host-wide telemetry; not process-attributed",
        "method": {
            "memory": "minimum sampled /proc/meminfo MemAvailable within request interval",
            "request_interval": "supervisor monotonic start to final streamed event",
            "disk": "/proc/diskstats nvme0n1 read/write sectors multiplied by 512 bytes",
            "disk_endpoints": "nearest retained one-second sample to request start and end",
            "limitations": ["concurrent host I/O is included", "kernel read-ahead is included",
                            "one-second samples limit endpoint precision"],
        },
        "requests": rows,
        "groups": groups,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--supervisor", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    supervisor = args.supervisor or args.root / "supervisor/memory.jsonl"
    result = summarize(args.root, supervisor, args.output)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
