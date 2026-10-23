#!/usr/bin/env python3
"""Compare all 64 accepted-prefix records by request for a short/long/short pair."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCEPTED = re.compile(r"ACCEPTED_PREFIX position=(\d+).*?tokens=(\d+) state=\{STATE_HASH (.*?)\}")
GDN = re.compile(r"STATE_HASH_GDN ((?:[0-9a-f]{16}\s*)+)")
REQUESTS = ("short-512", "long-2048", "short-512-recovery")


def read_arm(arm):
    result = arm / "result"
    expected = json.loads((result / "requests.json").read_text())["requests"]
    if [row["name"] for row in expected] != list(REQUESTS):
        raise ValueError(f"{arm}: unexpected request order")
    records = []
    pending_gdn = None
    for line in (result / "service.log").read_text(errors="replace").splitlines():
        match = GDN.search(line)
        if match:
            pending_gdn = match.group(1).split()
        match = ACCEPTED.search(line)
        if match:
            if pending_gdn is None:
                raise ValueError(f"{arm}: accepted prefix has no per-GDN state hashes")
            fields = dict(item.split("=", 1) for item in match.group(3).split() if "=" in item)
            records.append({"position": int(match.group(1)), "token_id": int(match.group(2)),
                            "state": fields, "gdn": pending_gdn})
            pending_gdn = None
    if len(records) != 3 * 64:
        raise ValueError(f"{arm}: expected 192 accepted-prefix records, got {len(records)}")
    grouped = {}
    for index, name in enumerate(REQUESTS):
        rows = records[index * 64:(index + 1) * 64]
        token_ids = [int(token) for token in expected[index]["ids"]]
        if [row["token_id"] for row in rows] != token_ids:
            raise ValueError(f"{arm}/{name}: service token IDs do not match requests.json")
        if any(len(row["gdn"]) != 36 for row in rows):
            raise ValueError(f"{arm}/{name}: expected 36 per-layer GDN hashes per prefix")
        grouped[name] = rows
    for index in range(64):
        if grouped[REQUESTS[0]][index]["position"] != grouped[REQUESTS[2]][index]["position"]:
            raise ValueError(f"{arm}: initial and recovery absolute positions differ at prefix {index}")
    return grouped


def compare(left, right):
    changed_state = [i for i, (a, b) in enumerate(zip(left, right)) if a["state"] != b["state"]]
    changed_token = [i for i, (a, b) in enumerate(zip(left, right)) if a["token_id"] != b["token_id"]]
    gdn_differences = [
        {"prefix": i, "ordinals": [j for j, (a, b) in enumerate(zip(x["gdn"], y["gdn"])) if a != b]}
        for i, (x, y) in enumerate(zip(left, right))
    ]
    gdn_differences = [row for row in gdn_differences if row["ordinals"]]
    state_fields = sorted({key for row in left + right for key in row["state"]})
    field_counts = {key: sum(a["state"].get(key) != b["state"].get(key) for a, b in zip(left, right))
                    for key in state_fields}
    return {
        "prefix_count": len(left),
        "different_token_prefixes": changed_token,
        "different_state_prefixes": changed_state,
        "first_state_difference": changed_state[0] if changed_state else None,
        "state_field_difference_counts": field_counts,
        "different_gdn_prefixes": [row["prefix"] for row in gdn_differences],
        "first_gdn_difference": gdn_differences[0] if gdn_differences else None,
        "gdn_difference_counts_by_ordinal": {
            str(ordinal): sum(ordinal in row["ordinals"] for row in gdn_differences)
            for ordinal in range(36)
        },
    }


def main():
    campaign = json.loads((ROOT / "campaign.json").read_text())
    result = {
        "scope": "same-position direct accepted-prefix state fingerprints and per-GDN hashes, three 64-token requests",
        "binary_sha256": campaign["binary_sha256"],
        "model_identity": f"{campaign['model_repository']} {campaign['quantization']}",
        "requests": list(REQUESTS),
        "arms": {},
    }
    for name in ("delayed-control", "adaptive-cap8"):
        rows = read_arm(ROOT / name)
        result["arms"][name] = {
            "initial_to_recovery": compare(rows[REQUESTS[0]], rows[REQUESTS[2]]),
            "initial_to_long_request": compare(rows[REQUESTS[0]], rows[REQUESTS[1]]),
        }
    (ROOT / "accepted-prefix-analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({arm: {
        key: {"different_token_prefixes": len(value["different_token_prefixes"]),
              "different_state_prefixes": len(value["different_state_prefixes"]),
              "first_state_difference": value["first_state_difference"],
              "first_gdn_difference": value["first_gdn_difference"]}
        for key, value in rows.items()} for arm, rows in result["arms"].items()}, indent=2))


if __name__ == "__main__":
    main()
