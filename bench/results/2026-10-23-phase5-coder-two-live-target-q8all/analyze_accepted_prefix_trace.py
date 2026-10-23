#!/usr/bin/env python3
"""Pair available batch accepted-prefix hashes with per-slot serial controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv',
              'mtp', 'stale', 'ple_prev')
PREFIX_RE = re.compile(
    r'ACCEPTED_PREFIX position=(\d+).*?committed=(\d+) tokens=([0-9,]+) '
    r'state=\{STATE_HASH ([^}]+)\}')


def read_trace(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        if 'ACCEPTED_PREFIX ' not in line:
            continue
        match = PREFIX_RE.search(line)
        if match is None:
            raise ValueError(f'malformed accepted-prefix record in {path}: {line}')
        fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match.group(4)))
        if not set(STATE_KEYS) <= fields.keys():
            raise ValueError(f'incomplete accepted-prefix state in {path}: {line}')
        rows.append({
            'position': int(match.group(1)),
            'committed': int(match.group(2)),
            'tokens': [int(value) for value in match.group(3).split(',')],
            'state': {key: fields[key] for key in STATE_KEYS},
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.run / 'result.json').read_text())
    prompt_counts = result['prompt_token_counts']
    output_rows = result['outputs']
    serial = {}
    batch_records: dict[str, list[dict]] = {'slot-0': [], 'slot-1': []}

    for slot in batch_records:
        rows = read_trace(args.run / f'serial-{slot}.log')
        if len(rows) != len(output_rows[slot]['serial']['tokens']):
            raise ValueError(f'{slot}: serial accepted-prefix count does not match output length')
        serial[slot] = rows

    pending = []
    batch_log = (args.run / 'batch-target-only.log').read_text(encoding='utf-8', errors='replace')
    for line in batch_log.splitlines():
        if 'ACCEPTED_PREFIX ' in line:
            row = read_trace_line(line)
            pending.append(row)
        match = re.search(r'strata batch: slot (\d+) takes ', line)
        if match:
            slot = f'slot-{match.group(1)}'
            if slot not in batch_records:
                raise ValueError(f'unexpected batch slot in log: {slot}')
            batch_records[slot].extend(pending)
            pending = []
    if pending:
        raise ValueError(f'{len(pending)} batch trace records have no following slot handoff')

    slots = {}
    for slot, rows in batch_records.items():
        prompt_tokens = prompt_counts[slot]
        batch_tokens = output_rows[slot]['batch']['tokens']
        serial_by_position = {row['position']: row for row in serial[slot]}
        compared = []
        covered_indices = set()
        for row in rows:
            if row['committed'] != 1 or len(row['tokens']) != 1:
                compared.append({'position': row['position'], 'status': 'unsupported-multi-token-commit'})
                continue
            index = row['position'] - prompt_tokens + 1
            if not 0 <= index < len(batch_tokens):
                raise ValueError(f'{slot}: captured position {row["position"]} maps outside output')
            if row['tokens'][0] != batch_tokens[index]:
                raise ValueError(f'{slot}: batch trace token does not match API output at index {index}')
            serial_row = serial_by_position.get(row['position'])
            if serial_row is None or serial_row['tokens'] != row['tokens']:
                equal = False
                differing = list(STATE_KEYS)
            else:
                differing = [key for key in STATE_KEYS
                             if serial_row['state'][key] != row['state'][key]]
                equal = not differing
            covered_indices.add(index)
            compared.append({'generated_token_index': index,
                             'token_id': row['tokens'][0],
                             'state_matches_serial': equal,
                             'differing_state_keys': differing})
        first_diff = next((i for i, (a, b) in enumerate(zip(
            output_rows[slot]['serial']['tokens'], batch_tokens)) if a != b), None)
        slots[slot] = {
            'generated_tokens': len(batch_tokens),
            'first_output_difference_index': first_diff,
            'accepted_prefix_records_paired_to_serial': compared,
            'accepted_prefixes_with_direct_state_match': sum(
                row.get('state_matches_serial') is True for row in compared),
            'untraced_generated_token_count': len(batch_tokens) - len(covered_indices),
        }

    output = {
        'scope': 'batch accepted-prefix records before/at slot handoff, paired to per-slot serial output and state',
        'batch_accepted_prefix_records': sum(map(len, batch_records.values())),
        'terminal_state_coverage': 'not captured after batched decode; do not infer from the handoff records',
        'slots': slots,
    }
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps(output, indent=2))


def read_trace_line(line: str) -> dict:
    match = PREFIX_RE.search(line)
    if match is None:
        raise ValueError(f'malformed accepted-prefix record: {line}')
    fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', match.group(4)))
    if not set(STATE_KEYS) <= fields.keys():
        raise ValueError(f'incomplete accepted-prefix state: {line}')
    return {'position': int(match.group(1)), 'committed': int(match.group(2)),
            'tokens': [int(value) for value in match.group(3).split(',')],
            'state': {key: fields[key] for key in STATE_KEYS}}


if __name__ == '__main__':
    main()
