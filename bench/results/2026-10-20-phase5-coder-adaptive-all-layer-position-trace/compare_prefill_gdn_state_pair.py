#!/usr/bin/env python3
"""Compare repeated same-service prefill GDN state snapshots and chunk hashes."""
import argparse
from array import array
import hashlib
import json
import math
import re
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')
TRACE = re.compile(r'GDN_STATE_TRACE layer=(\d+) prompt=(\d+) boundary=(\d+) hash=([0-9a-f]{16})')
PREFILL_HASH = re.compile(r'strata prefill: GDN_HASH ((?:[0-9a-f]{4}\s+)+)')


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & 0xffffffffffffffff
    return f'{value:016x}'


def summarize(a, b, recurrent):
    if len(a) != len(b) or not 0 <= recurrent <= len(a):
        raise ValueError('prefill state shapes differ')

    def part(x, y):
        different = 0
        max_abs = 0.0
        delta_sq = ref_sq = 0.0
        for left, right in zip(x, y):
            delta = float(right) - float(left)
            different += left != right
            max_abs = max(max_abs, abs(delta))
            delta_sq += delta * delta
            ref_sq += float(left) * float(left)
        return {'values': len(x), 'different_values': different, 'max_abs_diff': max_abs,
                'relative_l2': math.sqrt(delta_sq / ref_sq) if ref_sq else None}

    return {'recurrent_matrix': part(a[:recurrent], b[:recurrent]),
            'convolution_history': part(a[recurrent:], b[recurrent:])}


def read_prefill(path, layer):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError('truncated prefill GDN state header')
        magic, version, record_layer, boundary, recurrent, count, prompt, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STPFGS1\0' or version != 1 or record_layer != layer or boundary <= 0 or reserved != 0:
            raise ValueError(f'invalid prefill state record: {magic, version, record_layer, boundary, reserved}')
        size = count * 4
        if count < recurrent or len(raw) - offset < size:
            raise ValueError('truncated prefill GDN state payload')
        state = raw[offset:offset + size]
        offset += size
        values = array('f')
        values.frombytes(state)
        records.append({'prompt_tokens': prompt, 'boundary': boundary, 'recurrent': recurrent,
                        'state': values, 'state_bytes': state,
                        'state_sha256': hashlib.sha256(state).hexdigest(),
                        'state_fnv1a': fnv1a(state)})
    return raw, records


def repeated_runs(rows):
    runs = []
    current = []
    previous = None
    for row in rows:
        if previous is not None and row['boundary'] <= previous:
            runs.append(current)
            current = []
        current.append(row)
        previous = row['boundary']
    if current:
        runs.append(current)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-log', type=Path, required=True)
    parser.add_argument('--state-dump', type=Path, required=True)
    parser.add_argument('--layer', type=int, required=True, help='model layer containing the GDN state')
    parser.add_argument('--qsa-interval', type=int, default=4,
                        help='full-attention interval used to map model layers to GDN ordinals (default: 4)')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.layer < 0 or args.layer >= 48 or args.qsa_interval <= 0 or \
            args.layer % args.qsa_interval == args.qsa_interval - 1:
        parser.error('--layer must select a GDN layer in this 48-layer model and --qsa-interval must be positive')

    trace_by_prompt = {}
    lines = args.service_log.read_text(errors='replace').splitlines()
    for line_number, line in enumerate(lines):
        match = TRACE.search(line)
        if match and int(match.group(1)) == args.layer:
            prompt, boundary = map(int, match.group(2, 3))
            trace_by_prompt.setdefault(prompt, []).append(
                {'line': line_number, 'boundary': boundary, 'hash': match.group(4)})

    repeated = []
    for prompt, rows in trace_by_prompt.items():
        runs = repeated_runs(rows)
        if len(runs) in (2, 3):
            repeated.append((prompt, runs))
    if len(repeated) != 1:
        raise ValueError(f'expected one 2- or 3-request repeated prefill length, found {[prompt for prompt, _ in repeated]}')
    prompt_tokens, traces = repeated[0]
    boundaries = [row['boundary'] for row in traces[0]]
    if any([row['boundary'] for row in run] != boundaries for run in traces[1:]):
        raise ValueError('repeated requests have different prefill chunk boundaries')

    _, snapshots = read_prefill(args.state_dump, args.layer)
    snapshots = [row for row in snapshots if row['prompt_tokens'] == prompt_tokens]
    if len(snapshots) != len(traces):
        raise ValueError(f'expected {len(traces)} raw snapshots for repeated {prompt_tokens}-token prompt, found {len(snapshots)}')
    if any(row['boundary'] != run[-1]['boundary'] for row, run in zip(snapshots, traces)):
        raise ValueError('raw end-of-prompt snapshots do not match the final traced boundaries')
    if any(row['recurrent'] != snapshots[0]['recurrent'] or len(row['state']) != len(snapshots[0]['state'])
           for row in snapshots[1:]):
        raise ValueError('repeated-prefill GDN state dimensions differ')

    gdn_ordinal = args.layer - args.layer // args.qsa_interval
    low16_crosschecks = []
    for run in traces:
        end_line = run[-1]['line']
        legacy = next((PREFILL_HASH.search(line) for line in lines[end_line + 1:] if PREFILL_HASH.search(line)), None)
        if legacy is None:
            raise ValueError('missing legacy prefill GDN hashes after a selected prompt trace')
        hashes = legacy.group(1).split()
        if gdn_ordinal >= len(hashes) or run[-1]['hash'][-4:] != hashes[gdn_ordinal]:
            raise ValueError('full-width trace hash does not match the legacy per-GDN prefill hash')
        low16_crosschecks.append(hashes[gdn_ordinal])

    def compare_traces(left, right):
        rows = [{'boundary': a['boundary'], 'initial_hash': a['hash'],
                 'recovery_hash': b['hash'], 'equal': a['hash'] == b['hash']}
                for a, b in zip(left, right)]
        return {'first_differing_boundary': next((row['boundary'] for row in rows if not row['equal']), None),
                'chunk_hashes_equal_at_all_boundaries': all(row['equal'] for row in rows),
                'chunk_hash_comparisons': rows}

    transitions = [compare_traces(traces[index], traces[index + 1])
                   for index in range(len(traces) - 1)]
    comparisons = compare_traces(traces[0], traces[-1])
    state_transitions = [{'requests': [index + 1, index + 2],
                          'comparison': summarize(snapshots[index]['state'], snapshots[index + 1]['state'],
                                                  snapshots[0]['recurrent'])}
                         for index in range(len(snapshots) - 1)]
    result = {
        'layer': args.layer,
        'gdn_ordinal': gdn_ordinal,
        'prompt_tokens': prompt_tokens,
        'request_count': len(traces),
        'chunk_boundaries': boundaries,
        'first_differing_boundary': comparisons['first_differing_boundary'],
        'chunk_hashes_equal_at_all_boundaries': comparisons['chunk_hashes_equal_at_all_boundaries'],
        'chunk_hash_comparisons': comparisons['chunk_hash_comparisons'],
        'adjacent_request_transitions': transitions,
        'legacy_prefill_hash_low16_crosscheck': low16_crosschecks,
        'raw_prefill_state': {
            'initial_sha256': snapshots[0]['state_sha256'],
            'recovery_sha256': snapshots[-1]['state_sha256'],
            'initial_fnv1a': snapshots[0]['state_fnv1a'],
            'recovery_fnv1a': snapshots[-1]['state_fnv1a'],
            'initial_vs_recovery': summarize(snapshots[0]['state'], snapshots[-1]['state'],
                                             snapshots[0]['recurrent'])},
        'adjacent_raw_state_transitions': state_transitions,
        'interpretation_limit': 'chunk and end-of-prompt differences locate state boundaries, not the operation that caused them',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('layer', 'gdn_ordinal', 'prompt_tokens',
                                                   'first_differing_boundary',
                                                   'chunk_hashes_equal_at_all_boundaries',
                                                   'raw_prefill_state')}, indent=2))


if __name__ == '__main__':
    main()
