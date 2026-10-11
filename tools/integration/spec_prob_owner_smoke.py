"""Exercise probabilistic MTP verification and require its scratch owner to balance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "integration"))
from owner_observations import summarize  # noqa: E402
from serve.server import StrataEngine, child_env  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--mtp", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new", type=int, default=12)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    engine_args = list(cfg["args"])
    for key, value in (("--prompt-cache", "6"), ("--spec", "4")):
        if key in engine_args:
            engine_args[engine_args.index(key) + 1] = value
        else:
            engine_args.extend([key, value])
    engine_args.extend(["--mtp", str(args.mtp)])
    log_path = args.output / "engine.log"
    env = child_env(cfg)
    env.update({"STRATA_INTEGRATION_TRACE": "1", "STRATA_STATE_HASH": "1",
                "STRATA_PREFILL_CPU_SHARE": "0", "STRATA_SPEC_PROB": "1"})
    engine = StrataEngine(cfg["exe"], engine_args, cwd=cfg.get("cwd"), log=str(log_path), env=env)
    try:
        if engine.batch:
            raise RuntimeError(f"unexpected batch mode: {engine.batch}")
        tokens = [token for token in engine.generate([32], args.max_new,
                  {"temperature": 1.0, "seed": 20261011}, threading.Event()) if token is not None]
        usage = dict(engine.last)
    finally:
        engine.close()

    log = log_path.read_text(encoding="utf-8", errors="replace")
    owners = summarize(log.splitlines())
    aux = [row for row in owners["owners"] if row["owner"] == "verifier-aux-device"]
    checks = {
        "probabilistic_mode_reported": "probabilistic draft acceptance on (STRATA_SPEC_PROB)" in log,
        "drafts_offered": usage.get("drafts_offered", 0),
        "generated_tokens": len(tokens),
        "auxiliary_owner_seen": bool(aux),
        "auxiliary_owner_balanced": bool(aux) and all(row["live_observed_requested_bytes"] == 0 for row in aux),
        "all_traced_allocations_balanced": owners["allocation_events"] == owners["free_events"] and
                                            all(value == 0 for value in owners["observed_allocation_bytes_by_device"]["live_at_log_end"].values()),
    }
    result = {"checks": checks, "tokens": tokens, "usage": usage, "owner_summary": owners}
    result["passed"] = (checks["probabilistic_mode_reported"] and checks["drafts_offered"] > 0 and
                        checks["generated_tokens"] > 0 and checks["auxiliary_owner_seen"] and
                        checks["auxiliary_owner_balanced"] and checks["all_traced_allocations_balanced"])
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["passed"]:
        raise AssertionError(json.dumps(checks, sort_keys=True))
    print("PASS: probabilistic MTP drafts ran; verifier auxiliary allocations and all traced owners balanced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
