#!/usr/bin/env python3
"""Compare prefill chunk hashes and raw end-of-prompt/verifier GDN states."""
import argparse
from array import array
import hashlib
import json
import re
import struct
from pathlib import Path

HEADER = struct.Struct('<8sIiqQQii')
TRACE = re.compile(r'GDN_STATE_TRACE layer=(\d+) prompt=(\d+) boundary=(\d+) hash=([0-9a-f]{16})')
PREFILL_HASH = re.compile(r'strata prefill: GDN_HASH ((?:[0-9a-f]{4}\s+)+)')


def floats(raw):
    values = array('f')
    values.frombytes(raw)
    if values.itemsize != 4:
        raise RuntimeError('host float representation is not FP32')
    return values


def summarize(a, b):
    if len(a) != len(b):
        raise ValueError('state shapes differ')
    different = 0
    max_abs = 0.0
    delta_sq = ref_sq = 0.0
    for x, y in zip(a, b):
        d = float(y) - float(x)
        different += x != y
        max_abs = max(max_abs, abs(d))
        delta_sq += d * d
        ref_sq += float(x) * float(x)
    return {'values': len(a), 'different_values': different, 'max_abs_diff': max_abs,
            'relative_l2': (delta_sq / ref_sq) ** 0.5 if ref_sq else None}


def read_verifier(path):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError('truncated verifier GDN state header')
        magic, version, layer, position, recurrent, count, token, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STGSTAT1' or version != 1 or layer != 26 or position != 511 or reserved != 0:
            raise ValueError(f'invalid verifier state record: {magic, version, layer, position, reserved}')
        size = count * 4
        if count < recurrent or len(raw) - offset < 2 * size:
            raise ValueError('truncated verifier GDN state payload')
        pre = raw[offset:offset + size]
        post = raw[offset + size:offset + 2 * size]
        offset += 2 * size
        records.append({'token': token, 'recurrent': recurrent, 'pre': floats(pre), 'post': floats(post),
                        'pre_sha256': hashlib.sha256(pre).hexdigest()})
    if len(records) != 2:
        raise ValueError(f'expected initial/recovery verifier records, found {len(records)}')
    return raw, records


def read_prefill(path):
    raw = path.read_bytes()
    records = []
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < HEADER.size:
            raise ValueError('truncated prefill GDN state header')
        magic, version, layer, boundary, recurrent, count, prompt_tokens, reserved = HEADER.unpack_from(raw, offset)
        offset += HEADER.size
        if magic != b'STPFGS1\0' or version != 1 or layer != 26 or boundary <= 0 or reserved != 0:
            raise ValueError(f'invalid prefill state record: {magic, version, layer, boundary, reserved}')
        size = count * 4
        if count < recurrent or len(raw) - offset < size:
            raise ValueError('truncated prefill GDN state payload')
        state = raw[offset:offset + size]
        offset += size
        records.append({'prompt_tokens': prompt_tokens, 'boundary': boundary, 'recurrent': recurrent,
                        'state': floats(state), 'state_sha256': hashlib.sha256(state).hexdigest()})
    return raw, records


def fnv1a(data):
    value = 1469598103934665603
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f'{value:016x}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--service-log', type=Path, required=True)
    parser.add_argument('--state-dump', type=Path, required=True,
                        help='verifier STGSTAT1 pre/post snapshots')
    parser.add_argument('--prefill-state-dump', type=Path, required=True,
                        help='prefill STPFGS1 final-prompt snapshots')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    lines = args.service_log.read_text(errors='replace').splitlines()
    trace_by_prompt = {}
    for line_number, line in enumerate(lines):
        match = TRACE.search(line)
        if match and int(match.group(1)) == 26:
            prompt, boundary = map(int, match.group(2, 3))
            trace_by_prompt.setdefault(prompt, []).append(
                {'line': line_number, 'boundary': boundary, 'hash': match.group(4)})

    repeated = []
    for prompt, records in trace_by_prompt.items():
        runs = []
        current = []
        previous = None
        for record in records:
            if previous is not None and record['boundary'] <= previous:
                runs.append(current)
                current = []
            current.append(record)
            previous = record['boundary']
        if current:
            runs.append(current)
        if len(runs) == 2:
            repeated.append((prompt, runs))
    if len(repeated) != 1:
        raise ValueError(f'expected one initial/recovery prefill length, got {[p for p, _ in repeated]}')
    prompt_tokens, runs = repeated[0]
    if [r['boundary'] for r in runs[0]] != [r['boundary'] for r in runs[1]]:
        raise ValueError('initial/recovery chunk boundaries differ')

    # The existing full-session diagnostic stores the low 16 bits per GDN ordinal.
    # Layer 26 is ordinal 20 for this model's QSA interval of four.
    prefill_hashes = []
    for run in runs:
        end_line = run[-1]['line']
        legacy = next((PREFILL_HASH.search(line) for line in lines[end_line + 1:]
                       if PREFILL_HASH.search(line)), None)
        if legacy is None:
            raise ValueError('missing legacy prefill GDN hash after a selected prompt trace')
        values = legacy.group(1).split()
        if len(values) <= 20 or run[-1]['hash'][-4:] != values[20]:
            raise ValueError('full-width trace hash does not match the legacy layer-26 prefill hash')
        prefill_hashes.append(legacy.group(1).split())

    verifier_raw, verifier = read_verifier(args.state_dump)
    prefill_raw, prefill_all = read_prefill(args.prefill_state_dump)
    prefill = [r for r in prefill_all if r['prompt_tokens'] == prompt_tokens]
    if len(prefill) != 2:
        raise ValueError(f'expected initial/recovery raw prefill records for prompt length {prompt_tokens}, found {len(prefill)}')
    if [r['boundary'] for r in prefill] != [runs[0][-1]['boundary'], runs[1][-1]['boundary']]:
        raise ValueError('raw prefill snapshots do not match the final traced boundaries')
    if len(verifier) != 2 or any(v['recurrent'] != p['recurrent'] for v, p in zip(verifier, prefill)):
        raise ValueError('verifier/prefill state dimensions differ')

    boundaries = [r['boundary'] for r in runs[0]]
    comparisons = [{'boundary': a['boundary'], 'initial_hash': a['hash'], 'recovery_hash': b['hash'],
                    'equal': a['hash'] == b['hash']} for a, b in zip(runs[0], runs[1])]
    first_difference = next((r['boundary'] for r in comparisons if not r['equal']), None)
    recurrent = verifier[0]['recurrent']
    total = len(verifier[0]['pre'])

    def split(a, b):
        return {'recurrent_matrix': summarize(a[:recurrent], b[:recurrent]),
                'convolution_history': summarize(a[recurrent:], b[recurrent:])}

    result = {
        'layer': 26,
        'prompt_tokens_batched': prompt_tokens,
        'prefill_boundaries': boundaries,
        'first_differing_boundary': first_difference,
        'initial_recovery_prefill_hashes_equal_at_all_boundaries': all(r['equal'] for r in comparisons),
        'comparisons': comparisons,
        'legacy_prefill_hash_low16_crosscheck': [values[20] for values in prefill_hashes],
        'raw_prefill_states': {
            'bytes': len(prefill_raw), 'sha256': hashlib.sha256(prefill_raw).hexdigest(),
            'initial_vs_recovery': split(prefill[0]['state'], prefill[1]['state'])},
        'raw_verifier_states': {
            'bytes': len(verifier_raw), 'sha256': hashlib.sha256(verifier_raw).hexdigest(),
            'initial_vs_recovery_pre': split(verifier[0]['pre'], verifier[1]['pre']),
            'prefill_vs_verifier_pre': {
                'initial_request': split(prefill[0]['state'], verifier[0]['pre']),
                'recovery_request': split(prefill[1]['state'], verifier[1]['pre'])}},
        'raw_state_identity': {
            'prefill_initial_sha256': prefill[0]['state_sha256'],
            'prefill_recovery_sha256': prefill[1]['state_sha256'],
            'verifier_initial_pre_sha256': verifier[0]['pre_sha256'],
            'verifier_recovery_pre_sha256': verifier[1]['pre_sha256']},
        'interpretation_limit': 'chunk hashes locate state differences only at chunk ends; cross-path numerical differences identify a boundary but not the operation responsible',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
