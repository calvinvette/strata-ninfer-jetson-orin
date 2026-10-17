#!/usr/bin/env python3
"""Independently check the retained three-cycle Q2_0 teardown evidence."""
import argparse
import json
from pathlib import Path

EXPECTED = "EARLY=MAPLE-ORBIT-731, MIDDLE=COBALT-HARBOR-284, LATE=VELVET-COPPER-956"
MARKERS = ("MAPLE-ORBIT-731", "COBALT-HARBOR-284", "VELVET-COPPER-956")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True, help="teardown-3cycle directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    campaign = json.loads((root / "run/campaign.json").read_text())
    config = json.loads((root / "config.json").read_text())
    checks = []
    cycles = campaign.get("cycles", [])
    assert campaign.get("status") == "pass" and campaign.get("planned_cycles") == 3
    assert len(cycles) == 3
    for index, cycle in enumerate(cycles, 1):
        assert cycle.get("cycle") == index and cycle.get("status") == "pass"
        assert cycle.get("listener_closed") is True and cycle.get("processes_closed") is True
        assert not cycle.get("remaining_strata_engine_pids")
        assert cycle.get("prompt_tokens") == [7498]
        assert cycle.get("completion_tokens") == [41]
        data = json.loads((root / f"run/cycle-{index:02d}/requests.json").read_text())
        rows = [row for row in data["checks"] if row.get("cell") == "multineedle-8192"]
        assert len(rows) == 1
        row = rows[0]
        response = row["response"]
        content = response["choices"][0]["message"]["content"]
        usage = response["usage"]
        assert row.get("status") == "pass"
        assert content == EXPECTED
        assert all(content.count(marker) == 1 for marker in MARKERS)
        assert [content.index(marker) for marker in MARKERS] == sorted(content.index(marker) for marker in MARKERS)
        assert usage.get("prompt_tokens") == 7498 and usage.get("completion_tokens") == 41
        assert row.get("metrics_after", {}).get("engine", {}).get("max_context") == 8192
        checks.append({"cycle": index, "status": "pass", "prompt_tokens": 7498,
                       "completion_tokens": 41, "answer": content,
                       "listener_closed": True, "processes_closed": True})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"status": "pass", "independent_review": True,
                                       "configured_context": config["args"][config["args"].index("--max-context") + 1],
                                       "cycles": checks}, indent=2) + "\n")


if __name__ == "__main__":
    main()
