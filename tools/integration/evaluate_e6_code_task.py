#!/usr/bin/env python3
"""Apply an independent executable oracle to E6 merge_ranges API captures."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import sys


ALLOWED_NODES = {
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign,
    ast.Expr, ast.If, ast.For, ast.Name, ast.Load, ast.Store, ast.Constant,
    ast.List, ast.Tuple, ast.Subscript, ast.Call, ast.Attribute, ast.BinOp,
    ast.Add, ast.Sub, ast.Compare, ast.Lt, ast.LtE, ast.Eq, ast.Gt, ast.GtE,
    ast.UnaryOp, ast.USub, ast.UAdd, ast.BoolOp, ast.And, ast.Or, ast.IfExp,
    ast.ListComp, ast.comprehension, ast.AugAssign, ast.Not, ast.Lambda, ast.keyword,
}
SAFE_BUILTINS = {"len": len, "sorted": sorted, "list": list, "min": min, "max": max}
CASES = [
    ([], []),
    ([[1, 3], [5, 7]], [[1, 3], [5, 7]]),
    ([[1, 3], [4, 5]], [[1, 5]]),
    ([[8, 10], [1, 2], [2, 4], [-5, -2]], [[-5, -2], [1, 4], [8, 10]]),
    ([[2, 2], [2, 2], [-1, -1]], [[-1, -1], [2, 2]]),
]


def extract_code(text: str) -> str:
    text = text.strip()
    match = re.fullmatch(r"```(?:python)?\s*\n?(.*?)\n?```", text, flags=re.S | re.I)
    if match:
        text = match.group(1).strip()
    return text


def compile_solution(text: str):
    code = extract_code(text)
    tree = ast.parse(code, mode="exec")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("output must define only merge_ranges")
    fn = tree.body[0]
    if fn.name != "merge_ranges" or len(fn.args.args) != 1 or fn.args.args[0].arg != "ranges":
        raise ValueError("expected def merge_ranges(ranges)")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(f"unsupported syntax: {type(node).__name__}")
        if isinstance(node, ast.Attribute) and node.attr != "append":
            raise ValueError(f"unsupported attribute: {node.attr}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id not in SAFE_BUILTINS:
                raise ValueError(f"unsupported function call: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr != "append":
                raise ValueError(f"unsupported method call: {node.func.attr}")
    scope = {"__builtins__": SAFE_BUILTINS}
    exec(compile(tree, "<model-code>", "exec"), scope, scope)
    return code, scope["merge_ranges"]


def evaluate(text: str) -> dict:
    code, function = compile_solution(text)
    for inputs, expected in CASES:
        original = [row[:] for row in inputs]
        actual = function(inputs)
        if actual != expected:
            raise AssertionError(f"{inputs!r}: expected {expected!r}, got {actual!r}")
        if inputs != original:
            raise AssertionError(f"function mutated input {original!r} into {inputs!r}")
    return {
        "passed": True,
        "unit_cases": len(CASES),
        "input_immutability": True,
        "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("response_json", type=Path,
                        help="benchmark_control.py result JSON containing checks")
    args = parser.parse_args()
    result = json.loads(args.response_json.read_text())
    outcomes = []
    for row in result.get("checks", []):
        if row.get("status") != "pass" or not row.get("response"):
            outcomes.append({"cell": row.get("cell"), "warmup": row.get("warmup"),
                             "passed": False, "error": "request did not pass API workload checks"})
            continue
        text = row["response"].get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            outcomes.append({"cell": row.get("cell"), "warmup": row.get("warmup"),
                             **evaluate(text)})
        except Exception as exc:  # retain every failed generation as a quality failure
            outcomes.append({"cell": row.get("cell"), "warmup": row.get("warmup"),
                             "passed": False, "error": f"{type(exc).__name__}: {exc}",
                             "answer_sha256": hashlib.sha256(text.encode()).hexdigest()})
    payload = {"source": str(args.response_json), "outcomes": outcomes,
               "all_passed": bool(outcomes) and all(row.get("passed") for row in outcomes)}
    print(json.dumps(payload, indent=2))
    return 0 if payload["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
