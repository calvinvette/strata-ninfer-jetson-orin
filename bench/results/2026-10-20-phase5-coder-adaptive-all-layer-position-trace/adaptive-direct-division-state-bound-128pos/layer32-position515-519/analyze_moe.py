#!/usr/bin/env python3
"""Compare selected layer-32 verifier routes, parts and combined MoE outputs."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

H = struct.Struct('<8sIIIIQq8i')


def read_blob(path, magic, layer):
    raw = path.read_bytes(); off = 0; rows = []
    while off < len(raw):
        got, version, got_layer, count, k, width, pos, *tokens = H.unpack_from(raw, off)
        off += H.size
        if got != magic or version != 1 or got_layer != layer or count != 1:
            raise ValueError(f'invalid capture record in {path}')
        n = (k * width if magic == b'STMPART1' else 2 * width) * 4
        payload = raw[off:off + n]; off += n
        if len(payload) != n:
            raise ValueError(f'truncated capture in {path}')
        rows.append({'position': pos, 'token': tokens[0], 'k': k, 'width': width,
                     'payload': payload})
    return raw, rows


def compare(a, b):
    av = struct.unpack(f'<{len(a) // 4}f', a)
    bv = struct.unpack(f'<{len(b) // 4}f', b)
    if not all(math.isfinite(x) for x in av + bv):
        raise ValueError('non-finite expert output')
    delta = [float(y) - float(x) for x, y in zip(av, bv)]
    denom = math.fsum(float(x) * float(x) for x in av)
    return {'bitwise_equal': a == b, 'different_values': sum(x != y for x, y in zip(av, bv)),
            'relative_l2': math.sqrt(math.fsum(x * x for x in delta) / denom) if denom else None,
            'max_abs_diff': max(map(abs, delta), default=0.0)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run-dir', type=Path, required=True)
    ap.add_argument('--layer', type=int, default=32)
    ap.add_argument('--positions', type=int, nargs='*',
                    help='optional selected accepted positions to compare')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    routes = [json.loads(line) for line in (args.run_dir / 'verify-moe-routes.jsonl').read_text().splitlines()][1:]
    parts_raw, parts = read_blob(args.run_dir / 'verify-moe-parts.bin', b'STMPART1', args.layer)
    out_raw, outputs = read_blob(args.run_dir / 'verify-moe-output.bin', b'STMOEOUT', args.layer)
    if len(routes) != len(parts) or len(parts) != len(outputs) or not routes:
        raise ValueError('route, expert-part and combined-output record counts differ')
    rows = {}
    for route, part, output in zip(routes, parts, outputs):
        if (route['position'], route['token_id']) != (part['position'], part['token']) or \
           (part['position'], part['token']) != (output['position'], output['token']):
            raise ValueError('route and output record identities differ')
        rows.setdefault(route['position'], []).append((route, part, output))
    result = {'layer': args.layer, 'raw_sha256': {
        'verify-moe-parts.bin': hashlib.sha256(parts_raw).hexdigest(),
        'verify-moe-output.bin': hashlib.sha256(out_raw).hexdigest()}, 'positions': {}}
    for pos, pair in sorted(rows.items()):
        if args.positions is not None and pos not in args.positions:
            continue
        if len(pair) != 2:
            raise ValueError(f'position {pos}: expected initial/recovery pair')
        (ra, pa, oa), (rb, pb, ob) = pair
        if ra['token_id'] != rb['token_id']:
            raise ValueError(f'accepted token changed at position {pos}')
        w, k = pa['width'], pa['k']
        per_expert = [compare(pa['payload'][i*w*4:(i+1)*w*4],
                              pb['payload'][i*w*4:(i+1)*w*4]) for i in range(k)]
        result['positions'][str(pos)] = {
            'token_id': ra['token_id'], 'route_ids_equal': ra['ids'] == rb['ids'],
            'route_weights_equal': ra['weights'] == rb['weights'],
            'expert_parts_bitwise_equal': all(x['bitwise_equal'] for x in per_expert),
            'per_expert': per_expert,
            'shared_and_combined_output': compare(oa['payload'], ob['payload'])}
    if not result['positions']:
        raise ValueError('no requested position records found')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({p: {'ids': r['route_ids_equal'], 'weights': r['route_weights_equal'],
                          'parts': r['expert_parts_bitwise_equal'],
                          'combined': r['shared_and_combined_output']['bitwise_equal']}
                      for p, r in result['positions'].items()}, indent=2))


if __name__ == '__main__':
    main()
