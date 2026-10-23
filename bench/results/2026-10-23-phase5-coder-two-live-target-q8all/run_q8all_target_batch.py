#!/usr/bin/env python3
"""Compare two-live target-only batch output with fresh serial controls under Q8_1 parity."""
import hashlib
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, remove_arg, replace_arg

HERE = Path(__file__).resolve().parent
CONFIG = ROOT / "bench/results/2026-10-22-phase5-coder-batch-mtp-graph-lifecycle/config.json"
MODEL_SHA = ROOT / "bench/results/2026-10-21-phase6-coder-current-source-cache-context-screen3/model-sha256.txt"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=HERE / "run",
                    help="new directory for raw run logs and summary")
parser.add_argument("--expert-cache-slots", "--expert-cache-mib", type=int, default=1500,
                    help="requested Strata expert-cache slot count (legacy MiB alias accepted)")
parser.add_argument("--generated-tokens", type=int, default=96,
                    help="tokens generated for each serial and batch request")
parser.add_argument("--accepted-prefix-trace", action="store_true",
                    help="hash committed persistent state at each accepted verifier prefix")
cli = parser.parse_args()
if cli.generated_tokens < 1:
    parser.error("--generated-tokens must be positive")
OUT = cli.output.resolve()
EXPERT_CACHE_SLOTS = cli.expert_cache_slots
GENERATED_TOKENS = cli.generated_tokens
OUT.mkdir(parents=True, exist_ok=False)
cfg = json.loads(CONFIG.read_text())
args = list(cfg["args"])
for key in ("--mtp", "--mtp-max-t", "--adapt-every", "--adapt-accepted-only"):
    remove_arg(args, key)
replace_arg(args, "--spec", "2")
replace_arg(args, "--max-context", "1024")
replace_arg(args, "--expert-cache", str(EXPERT_CACHE_SLOTS))
replace_arg(args, "--prompt-cache", "6")
prompts = prepared_prompts(cfg, 2)
env = child_env(cfg)
env.update({
    "STRATA_NATIVE_CPU_Q8_1_DOT": "all",
    "STRATA_IQ_MT_MIN": "1",
    "STRATA_INTEGRATION_TRACE": "1",
    "STRATA_STATE_HASH": "1",
    "STRATA_PREFILL_CPU_SHARE": "0",
})
if cli.accepted_prefix_trace:
    env["STRATA_ACCEPTED_PREFIX_TRACE"] = "1"


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def generate(engine, prompt):
    tokens = [token for token in engine.generate(prompt, GENERATED_TOKENS, {"temperature": 0}, threading.Event())
              if token is not None]
    return {"tokens": tokens, "finish": engine.last.get("finish"), "usage": dict(engine.last)}


serial = {}
for name, prompt in prompts.items():
    log = OUT / f"serial-{name}.log"
    engine = StrataEngine(cfg["exe"], args, cwd=cfg.get("cwd"), log=str(log), env=env)
    try:
        serial[name] = generate(engine, prompt)
    finally:
        engine.close()

batch_log = OUT / "batch-target-only.log"
batch = StrataEngine(cfg["exe"], args + ["--batch", "2"], cwd=cfg.get("cwd"),
                     log=str(batch_log), env=env)
try:
    if batch.batch != 2:
        raise RuntimeError(f"batch admitted {batch.batch} slots, expected 2")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {name: pool.submit(generate, batch, prompt) for name, prompt in prompts.items()}
        batched = {name: futures[name].result() for name in prompts}
finally:
    batch.close()

matches = {name: serial[name]["tokens"] == batched[name]["tokens"] for name in prompts}
first_mismatch = {
    name: next((i for i, (a, b) in enumerate(zip(serial[name]["tokens"], batched[name]["tokens"])) if a != b), None)
    for name in prompts
}
log_text = batch_log.read_text(errors="replace")
model_shards_sha256 = {
    line.split(maxsplit=1)[1]: line.split(maxsplit=1)[0]
    for line in MODEL_SHA.read_text().splitlines() if line.strip()
}
result = {
    "scope": "one supervised two-live target-only batch correctness diagnostic; no performance claim",
    "repository_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "binary_sha256": file_sha256(cfg["exe"]),
    "model_identity": "ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF IQ1_M",
    "model_revision": "5348543e0147355ac9cbcb031184a3546350988e",
    "model_shards": [cfg["args"][cfg["args"].index("--native") + 1],
                     cfg["args"][cfg["args"].index("--ple-gguf") + 1]],
    "model_shards_sha256": model_shards_sha256,
    "profile": {"live_requests": 2, "batch_slots": 2, "mtp": False, "context": 1024,
                "expert_cache_slots": EXPERT_CACHE_SLOTS, "prompt_cache": 6, "generated_tokens": GENERATED_TOKENS,
                "STRATA_NATIVE_CPU_Q8_1_DOT": "all", "STRATA_IQ_MT_MIN": "1"},
    "prompt_token_counts": {name: len(prompt) for name, prompt in prompts.items()},
    "outputs": {name: {"serial": serial[name], "batch": batched[name]} for name in prompts},
    "per_prompt_match": matches,
    "first_mismatch_index": first_mismatch,
    "q8_selector_environment": "STRATA_NATIVE_CPU_Q8_1_DOT=all passed to fresh serial and batch engines",
    "batch_state_hash_records": sum("STATE_HASH " in line for line in log_text.splitlines()),
    "accepted_prefix_trace_enabled": cli.accepted_prefix_trace,
    "accepted_prefix_records": {
        "serial": {name: sum("ACCEPTED_PREFIX " in line for line in
                              (OUT / f"serial-{name}.log").read_text(errors="replace").splitlines())
                   for name in prompts},
        "batch": sum("ACCEPTED_PREFIX " in line for line in log_text.splitlines()),
    },
    "limits": ["same-input operator parity is not inferred from output equality",
               "terminal batch state hashes are retained in the raw log but not paired by prompt here",
               "single correctness cell; no speed, energy, or general quality claim"],
}
(OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"profile": result["profile"], "per_prompt_match": matches,
                  "first_mismatch_index": first_mismatch,
                  "batch_state_hash_records": result["batch_state_hash_records"]}))
