#!/usr/bin/env python3
"""Summarize position-515–519 GDN/input captures and validate raw service hashes."""
import argparse
from array import array
import hashlib
import json
import math
import struct
from pathlib import Path

CMT = struct.Struct('<8sIiqQQii')
MOE = struct.Struct('<8sIIIIQq8i')


def read_commits(path, layer):
    data = path.read_bytes()
    records, off = [], 0
    while off < len(data):
        magic, ver, got_layer, pos, recurrent, total, token, slot = CMT.unpack_from(data, off)
        off += CMT.size
        if magic != b'STGCMT1\0' or ver != 1 or got_layer != layer or total < recurrent:
            raise ValueError('invalid committed GDN record')
        size = total * 4
        vals = array('f'); vals.frombytes(data[off:off + size]); off += size
        if len(vals) != total or not all(math.isfinite(v) for v in vals):
            raise ValueError('invalid committed GDN payload')
        records.append({'position': pos, 'recurrent': recurrent, 'token': token,
                        'slot': slot, 'values': vals})
    return records


def read_stats(path, layer):
    data = path.read_bytes(); records, off = [], 0
    while off < len(data):
        magic, ver, got_layer, pos0, recurrent, total, token, reserved = CMT.unpack_from(data, off)
        off += CMT.size
        if magic != b'STGSTAT1' or ver != 1 or got_layer != layer or reserved != 0 or total < recurrent:
            raise ValueError('invalid verifier GDN state record')
        size = total * 4
        pre = data[off:off + size]; post = data[off + size:off + size * 2]; off += size * 2
        if len(post) != size:
            raise ValueError('truncated verifier GDN state')
        records.append({'position': pos0, 'token': token, 'pre': pre, 'post': post,
                        'recurrent': recurrent})
    return records


def summarize(a, b):
    if not isinstance(a, bytes):
        a = a.tobytes()
    if not isinstance(b, bytes):
        b = b.tobytes()
    av, bv = struct.unpack(f'<{len(a) // 4}f', a), struct.unpack(f'<{len(b) // 4}f', b)
    delta = [float(y) - float(x) for x, y in zip(av, bv)]
    denom = math.fsum(float(x) ** 2 for x in av)
    return {'bitwise_equal': a == b, 'different_values': sum(x != y for x, y in zip(av, bv)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in delta) / denom) if denom else None,
            'max_abs_diff': max(map(abs, delta), default=0.0)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    commits = read_commits(args.run_dir / 'gdn-commit-state.bin', 32)
    stats = read_stats(args.run_dir / 'gdn-state.bin', 32)
    out = {'layer': 32, 'commit_records': len(commits), 'verifier_records': len(stats),
           'raw_sha256': {name: hashlib.sha256((args.run_dir / name).read_bytes()).hexdigest()
                          for name in ('gdn-commit-state.bin', 'gdn-state.bin',
                                       'verify-gdn.bin', 'verify-moe-input.bin',
                                       'verify-moe-parts.bin', 'verify-moe-output.bin',
                                       'verify-boundary.bin')}, 'state_crosschecks': []}
    by_commit = {}
    for item in commits:
        by_commit.setdefault(item['position'], []).append(item)
    by_stat = {}
    for item in stats:
        by_stat.setdefault(item['position'], []).append(item)
    for pos in range(515, 520):
        cgroup, sgroup = by_commit.get(pos, []), by_stat.get(pos, [])
        if len(cgroup) != 2 or len(sgroup) != 2:
            raise ValueError(f'expected initial/recovery records at {pos}')
        item = {'position': pos, 'token_ids': [cgroup[0]['token'], cgroup[1]['token']]}
        item['verifier_post_vs_commit'] = [summarize(s['post'], c['values'])
                                          for s, c in zip(sgroup, cgroup)]
        if pos > 515:
            previous = by_commit[pos - 1]
            item['verifier_pre_vs_previous_commit'] = [summarize(s['pre'], c['values'])
                                                       for s, c in zip(sgroup, previous)]
        out['state_crosschecks'].append(item)
    args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'state_crosschecks': [
        {'position': row['position'],
         'post_exact': all(x['bitwise_equal'] for x in row['verifier_post_vs_commit']),
         'pre_exact': all(x['bitwise_equal'] for x in row.get('verifier_pre_vs_previous_commit', []))}
        for row in out['state_crosschecks']]}, indent=2))


if __name__ == '__main__':
    main()
