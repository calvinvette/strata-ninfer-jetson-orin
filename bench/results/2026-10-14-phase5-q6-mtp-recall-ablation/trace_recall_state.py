#!/usr/bin/env python3
"""Trace accepted-prefix state for the held-out long-context recall prompt."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tools"), str(ROOT / "tools" / "integration")]
from conversation_cache_parity import load_tokenizer, require
from pool_worker_screen import read_accepted_prefix_trace
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = ("L", "gdn", "ple", "tail", "dead", "pooled", "pooled_full", "kv", "ple_prev")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def final_state_hashes(path):
    keys = STATE_KEYS
    states = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.startswith("strata serve: STATE_HASH L="):
            continue
        fields = dict(re.findall(r"(\w+)=([0-9a-f,-]+)", line))
        require(set(keys) <= fields.keys(), f"incomplete final state hash in {path}")
        states.append({key: fields[key] for key in keys})
    return states


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mtp0-config", type=Path, required=True)
    ap.add_argument("--mtp4-config", type=Path, required=True)
    ap.add_argument("--workload", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--reuse-mtp0-log", type=Path,
                    help="reuse a completed MTP-off direct-trace log instead of rerunning that arm")
    ap.add_argument("--max-new", type=int, default=48)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    configs = [("mtp-off", args.mtp0_config), ("mtp-window4", args.mtp4_config)]
    workload = json.loads(args.workload.read_text(encoding="utf-8"))["workloads"][0]
    records = {
        "status": "not_run",
        "workload_sha256": digest(args.workload),
        "prompt_tokens_expected": workload["prompt_tokens"],
        "max_new": args.max_new,
        "expected_codes": workload["expected_codes"],
        "arms": [],
    }
    reference_ids = None
    reference_final = None
    reference_prefixes = None
    failures = []
    try:
        for label, config_path in configs:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            tok_path = Path(cfg["tokenizer"])
            tokenizer = load_tokenizer(tok_path)
            template_path = tok_path / "chat_template.jinja"
            template = ChatTemplate(template_path if template_path.exists() else ROOT / "serve/chat_template.jinja")
            rendered = template.render(workload["messages"], enable_thinking=False)
            prompt = tokenizer.encode(rendered, parse_special=True)
            require(len(prompt) == workload["prompt_tokens"],
                    f"{label}: formatted prompt length {len(prompt)} != {workload['prompt_tokens']}")
            arm = {"name": label, "config_sha256": digest(config_path),
                   "engine_sha256": digest(Path(cfg["exe"])),
                   "prompt_sha256": hashlib.sha256(json.dumps(prompt).encode()).hexdigest()}
            reuse_log = label == "mtp-off" and args.reuse_mtp0_log is not None
            if reuse_log:
                log_path = args.reuse_mtp0_log
                arm["trace_source"] = str(log_path.resolve())
            else:
                env = child_env(cfg)
                env["STRATA_STATE_HASH"] = "1"
                env["STRATA_ACCEPTED_PREFIX_TRACE"] = "1"
                env["STRATA_INTEGRATION_TRACE"] = "1"
                env["STRATA_MTP_BATCH"] = "1"
                env["STRATA_PREFILL_CPU_SHARE"] = "0"
                log_path = args.output / f"{label}.log"
                engine = StrataEngine(str(Path(cfg["exe"]).resolve()), list(cfg["args"]),
                                      cwd=cfg.get("cwd"), log=str(log_path), env=env)
                arm["trace_source"] = str(log_path.resolve())
                print(f"starting {label}: {len(prompt)} prompt tokens", flush=True)
                try:
                    ids = [token for token in engine.generate(prompt, args.max_new,
                           {"temperature": 0}, threading.Event()) if token is not None]
                    arm["engine"] = dict(engine.last)
                    arm["token_ids"] = ids
                    arm["text"] = tokenizer.decode(ids)
                finally:
                    engine.close()
            hashes = final_state_hashes(log_path)
            prefixes = read_accepted_prefix_trace(log_path)
            require(len(hashes) == 1, f"{label}: expected one final state fingerprint")
            require(bool(prefixes), f"{label}: accepted-prefix trace missing")
            if reuse_log:
                ids = [token for entry in prefixes for token in entry["token_ids"]]
                arm["token_ids"] = ids
                arm["text"] = tokenizer.decode(ids)
                arm["reused_trace"] = True
            arm["final_state"] = hashes[-1]
            arm["accepted_prefix_trace"] = prefixes
            arm["accepted_prefix_count"] = sum(x["committed"] for x in prefixes)
            require([x for entry in prefixes for x in entry["token_ids"]] == ids,
                    f"{label}: accepted-prefix token trace does not equal published IDs")
            records["arms"].append(arm)
            (args.output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
            if label == "mtp-off":
                reference_ids = ids
                reference_final = arm["final_state"]
                reference_prefixes = {}
                count = 0
                for entry in prefixes:
                    count += entry["committed"]
                    reference_prefixes[count] = entry["state"]
            else:
                if ids != reference_ids:
                    failures.append("generated token IDs differ")
                final_diff = [k for k in STATE_KEYS if arm["final_state"].get(k) != reference_final.get(k)]
                if final_diff:
                    failures.append("final persistent state differs: " + ", ".join(final_diff))
                shared = []
                count = 0
                for entry in prefixes:
                    count += entry["committed"]
                    prior = reference_prefixes.get(count)
                    if prior is None:
                        continue
                    differing = [k for k in STATE_KEYS if prior.get(k) != entry["state"].get(k)]
                    shared.append({"generated_prefix_tokens": count, "equal": not differing,
                                   "differing_state_fields": differing})
                if not shared:
                    failures.append("no common accepted-prefix state boundaries")
                elif any(not x["equal"] for x in shared):
                    failures.append("persistent state differs at a common accepted-prefix boundary")
                records["comparison"] = {"token_ids_equal": ids == reference_ids,
                                          "final_state_equal": not final_diff,
                                          "shared_prefix_checks": shared}
        mtp = records["arms"][1].get("engine", {})
        if mtp.get("drafts_offered", 0) <= 0 or mtp.get("drafts_accepted", 0) <= 0:
            failures.append("MTP arm did not offer and accept drafts")
        records["failures"] = failures
        records["status"] = "pass" if not failures else "fail"
        records["reason"] = ("token IDs and persistent state matched at every shared accepted prefix"
                              if not failures else "; ".join(failures))
        (args.output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
        print(json.dumps({k: records.get(k) for k in ("status", "reason", "comparison", "failures")}, indent=2))
        return 0 if not failures else 1
    except Exception as exc:
        records["status"] = "fail"
        records["reason"] = f"{type(exc).__name__}: {exc}"
        records["failures"] = failures
        (args.output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
