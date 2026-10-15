#!/usr/bin/env python3
"""Validate and summarize the seven-pair long-prompt int8/MTP3 confirmation."""
import hashlib
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "integration")]
from summarize_controls import interval

HERE = Path(__file__).resolve().parent
MIB = 1024 * 1024
GIB = 1024 ** 3


def require(ok, reason):
    if not ok:
        raise AssertionError(reason)


def canonical_args(args):
    out, i = [], 0
    while i < len(args):
        if args[i] in ("--mtp", "--mtp-max-t"):
            i += 2
        elif args[i] == "--spec":
            out.extend(("--spec", "{mtp}"))
            i += 2
        else:
            out.append(args[i])
            i += 1
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-name", default="campaign-retry1")
    parser.add_argument("--output", type=Path, default=Path("analysis.json"))
    args = parser.parse_args()
    run_root = HERE / args.campaign_name
    campaign = json.loads((run_root / "campaign.json").read_text())
    workload_doc = json.loads((HERE / "workload/workload-8192.json").read_text())
    workload = workload_doc["workloads"][0]
    expected_codes = workload["expected_codes"]
    expected_prompt = workload["prompt_tokens"]
    require(campaign["status"] == "pass" and len(campaign["runs"]) == 14,
            "campaign did not complete all 14 arms")
    require(len({run["block"] for run in campaign["runs"]}) == 7,
            "campaign does not contain seven blocks")
    configs = {
        "baseline": json.loads((HERE / "config-mtp-off.json").read_text()),
        "candidate": json.loads((HERE / "config-mtp3.json").read_text()),
    }
    for arm, config in configs.items():
        engine_args = config["args"]
        require(engine_args[engine_args.index("--kv") + 1] == "int8"
                and engine_args[engine_args.index("--max-context") + 1] == "8192",
                f"expected KV/context settings are absent in {arm} config")
        require(not any(arg.startswith("--adapt") for arg in engine_args),
                f"adaptive residency flag unexpectedly enabled in {arm} config")
    pairs = {i: {} for i in range(7)}
    report = {"scope": "Q2_0 held-out near-limit int8-KV MTP-off versus MTP3 confirmation",
              "date": "2026-10-14", "seed": campaign["seed"], "blocks": 7,
              "configured_context": 8192, "prompt_tokens": expected_prompt,
              "generation_cap": workload["generate_tokens"],
              "expected_codes": expected_codes, "block_order": [],
              "paired_blocks": [], "comparisons": {},
              "resource_minima": {"host_gib": float("inf"), "admission_gib": float("inf")},
              "resource_maxima": {"scope_use_gib": 0.0, "swap_use_gib": 0.0},
              "host_swap_gib_range": [float("inf"), 0.0],
              "cgroup_event_maxima": {key: 0 for key in ("low", "high", "max", "oom", "oom_kill")},
              "observed_gpu_clock_mhz": [], "tegrastats_tj_c": [],
              "limitations": ["one held-out prompt and one KV/MTP combination",
                              "dynamic clocks; no request-attributed energy",
                              "no serving default or profile is promoted"]}
    all_quality = True
    all_content_equal = True
    metric_pairs = {key: [] for key in ("prompt_tps", "decode_tps", "client_ttft_s", "client_total_s")}
    for run in campaign["runs"]:
        block, arm = run["block"], run["variant"]
        require(run["status"] == "pass", f"failed run: block {block} {arm}")
        directory = run_root / f"block-{block:02d}-{arm}"
        config = json.loads((directory / "server-config.json").read_text())
        require(canonical_args(config["args"]) == canonical_args(configs[arm]["args"]),
                f"run config differs from declared {arm} config: block {block}")
        for key in ("exe", "cwd", "tokenizer", "draft_vocab", "env", "cuda", "lib_dirs"):
            require(config.get(key) == configs[arm].get(key),
                    f"run {arm} config differs for {key}: block {block}")
        data = json.loads((directory / "requests.json").read_text())
        checks = data["checks"]
        measured = [row for row in checks if not row.get("warmup")]
        require(len(measured) == 1 and measured[0]["status"] == "pass",
                f"missing passing request: block {block} {arm}")
        row = measured[0]
        response = row["response"]
        usage, timing = response["usage"], response["timings"]
        message = response["choices"][0]["message"].get("content", "")
        positions = [message.find(code) for code in expected_codes]
        quality = (usage["prompt_tokens"] == expected_prompt
                   and usage["completion_tokens"] > 0
                   and all(message.count(code) == 1 for code in expected_codes)
                   and all(pos >= 0 for pos in positions)
                   and positions == sorted(positions)
                   and timing.get("cache_n", 0) == 0)
        all_quality &= quality
        engine = row["metrics_after"]["engine"]
        request_metrics = row["metrics_after"]["requests"][0]
        expected_mtp = 0 if arm == "baseline" else 3
        require(engine["kv"] == "int8" and engine["context"] == 8192
                and engine["expert_slots"] == 3000 and engine["mtp_max"] == expected_mtp,
                f"actual engine settings differ: block {block} {arm}")
        require(request_metrics["prompt_tokens"] == usage["prompt_tokens"]
                and request_metrics["output_tokens"] == usage["completion_tokens"]
                and request_metrics.get("reused", 0) == 0,
                f"per-request counters disagree: block {block} {arm}")
        supervisor = json.loads((directory / "result.json").read_text())
        require(supervisor["status"] == "pass" and supervisor["returncode"] == 0,
                f"supervisor did not pass: block {block} {arm}")
        report["resource_minima"]["host_gib"] = min(report["resource_minima"]["host_gib"],
                                                       supervisor["minimum_available_bytes"] / GIB)
        report["resource_minima"]["admission_gib"] = min(report["resource_minima"]["admission_gib"],
                                                            supervisor["minimum_admission_available_bytes"] / GIB)
        samples = [json.loads(line) for line in (directory / "memory.jsonl").read_text().splitlines()]
        for sample in samples:
            for cg in sample.get("cgroups", []):
                if cg.get("max_bytes"):
                    report["resource_maxima"]["scope_use_gib"] = max(
                        report["resource_maxima"]["scope_use_gib"], cg["current_bytes"] / GIB)
                events = cg.get("memory_events", {})
                for key in report["cgroup_event_maxima"]:
                    report["cgroup_event_maxima"][key] = max(report["cgroup_event_maxima"][key], events.get(key, 0))
            report["resource_maxima"]["swap_use_gib"] = max(
                report["resource_maxima"]["swap_use_gib"], sample["swap_used_bytes"] / GIB)
            report["host_swap_gib_range"][0] = min(
                report["host_swap_gib_range"][0], sample["swap_used_bytes"] / GIB)
        temps = [float(value) for value in re.findall(r"\btj@([0-9.]+)C",
                    (directory / "tegrastats.txt").read_text())]
        report["tegrastats_tj_c"].extend(temps)
        request_samples = [sample for sample in samples
            if row["request_start_monotonic_s"] <= sample["monotonic_s"] <= row["request_end_monotonic_s"]]
        gpu_clocks = [(sample.get("clock_observations") or {}).get("gpu", {}).get("hz")
                      for sample in request_samples]
        gpu_clocks = [value / 1e6 for value in gpu_clocks if isinstance(value, int)]
        report["observed_gpu_clock_mhz"].extend(gpu_clocks)
        prompt_ms, decode_ms = request_metrics.get("prompt_ms"), request_metrics.get("decode_ms")
        require(prompt_ms and decode_ms and request_metrics.get("prompt_read") == usage["prompt_tokens"],
                f"missing or inconsistent high-resolution engine counters: block {block} {arm}")
        observation = {
            "status": "pass", "quality_pass": quality, "content": message,
            "prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"],
            "prompt_tps": request_metrics["prompt_tokens"] * 1000 / prompt_ms,
            "decode_tps": request_metrics["engine_generated"] * 1000 / decode_ms,
            "client_total_s": row["client_elapsed_s"],
            "client_ttft_s": row["stream_observation"]["first_visible_delta_s"],
            "drafted": request_metrics.get("drafts_offered", timing.get("draft_n", 0)),
            "accepted": request_metrics.get("drafts_accepted", timing.get("draft_n_accepted", 0)),
            "kv": engine["kv"], "mtp_max": engine["mtp_max"],
            "expert_slots": engine["expert_slots"],
            "min_request_host_gib": min((sample["available_bytes"] for sample in request_samples),
                                        default=supervisor["minimum_available_bytes"]) / GIB,
            "request_gpu_clock_mhz_range": ([min(gpu_clocks), max(gpu_clocks)] if gpu_clocks else None),
            "tj_range_c": ([min(temps), max(temps)] if temps else None),
        }
        pairs[block][arm] = observation
        report["block_order"].append({"block": block, "arm": arm})

    require(all_quality, "one or more responses failed exact marker retrieval")
    base_config = configs["baseline"]
    cand_config = configs["candidate"]
    require(canonical_args(base_config["args"]) == canonical_args(cand_config["args"]),
            "paired configs differ outside MTP setting")
    for key in ("exe", "cwd", "tokenizer", "draft_vocab", "env", "cuda", "lib_dirs"):
        require(base_config.get(key) == cand_config.get(key), f"paired config differs: {key}")
    for block, arms in sorted(pairs.items()):
        require(set(arms) == {"baseline", "candidate"}, f"block {block} is not paired")
        baseline, candidate = arms["baseline"], arms["candidate"]
        same_text = baseline["content"] == candidate["content"]
        all_content_equal &= same_text
        entry = {"block": block, "baseline": baseline, "candidate": candidate,
                 "exact_content_match": same_text}
        for key in metric_pairs:
            ratio = candidate[key] / baseline[key]
            entry[key + "_ratio"] = ratio
            metric_pairs[key].append(ratio)
        report["paired_blocks"].append(entry)
    for key, ratios in metric_pairs.items():
        report["comparisons"][key] = {
            "baseline_median": statistics.median(pair["baseline"][key] for pair in report["paired_blocks"]),
            "candidate_median": statistics.median(pair["candidate"][key] for pair in report["paired_blocks"]),
            "median_paired_percent_change": (statistics.median(ratios) - 1) * 100,
            "paired_bootstrap_95_interval_percent": [(value - 1) * 100 for value in interval(ratios, 20261017)],
            "block_percent_changes": [(value - 1) * 100 for value in ratios],
        }
    report["all_14_quality_checks_passed"] = all_quality
    report["all_7_exact_text_pairs_match"] = all_content_equal
    report["minimum_supervisor_host_gib"] = report["resource_minima"].pop("host_gib")
    report["minimum_supervisor_admission_gib"] = report["resource_minima"].pop("admission_gib")
    report["host_swap_gib_range"][1] = report["resource_maxima"]["swap_use_gib"]
    report["tegrastats_tj_c_range"] = [min(report["tegrastats_tj_c"]), max(report["tegrastats_tj_c"])]
    report["tegrastats_tj_c_last_arm_median_range"] = [
        statistics.median(pair[arm]["tj_range_c"][0] for pair in report["paired_blocks"]
                          for arm in ("baseline", "candidate")),
        statistics.median(pair[arm]["tj_range_c"][1] for pair in report["paired_blocks"]
                          for arm in ("baseline", "candidate")),
    ]
    report["observed_gpu_clock_mhz_range"] = ([min(report["observed_gpu_clock_mhz"]),
                                               max(report["observed_gpu_clock_mhz"])]
                                              if report["observed_gpu_clock_mhz"] else None)
    report["prompt_content_sha256"] = hashlib.sha256(workload["messages"][0]["content"].encode()).hexdigest()
    report["workload_sha256"] = hashlib.sha256((HERE / "workload/workload-8192.json").read_bytes()).hexdigest()
    report["binary_sha256"] = hashlib.sha256(Path(base_config["exe"]).read_bytes()).hexdigest()
    report["configuration_sha256"] = {
        "baseline": hashlib.sha256((HERE / "config-mtp-off.json").read_bytes()).hexdigest(),
        "candidate": hashlib.sha256((HERE / "config-mtp3.json").read_bytes()).hexdigest(),
    }
    report["model_checksums"] = (HERE / "model-checksums.txt").read_text().splitlines()
    report["actual_kv"] = "int8"
    report["actual_context"] = 8192
    report["actual_expert_slots"] = 3000
    report["completion_scope"] = "all 14 fresh-service requests completed without cgroup events"
    out = args.output if args.output.is_absolute() else HERE / args.output
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"quality": all_quality, "exact_text_pairs": all_content_equal,
                      "comparisons": report["comparisons"],
                      "minimum_supervisor_host_gib": report["minimum_supervisor_host_gib"],
                      "minimum_supervisor_admission_gib": report["minimum_supervisor_admission_gib"],
                      "resource_maxima": report["resource_maxima"],
                      "host_swap_gib_range": report["host_swap_gib_range"],
                      "cgroup_event_maxima": report["cgroup_event_maxima"],
                      "tj_range_c": report["tegrastats_tj_c_range"],
                      "gpu_clock_mhz_range": report["observed_gpu_clock_mhz_range"]}, indent=2))


if __name__ == "__main__":
    main()
