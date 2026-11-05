#!/usr/bin/env python3
"""Trace per-layer accepted-prefix state for the held-out is_prime prompt."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from serve.frontend import ChatTemplate
from serve.server import StrataEngine
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
TASK = ('Write a Python function named is_prime(n) that returns True exactly when n is a prime integer. '
        'Handle integers less than 2 correctly. Output only the function definition, with no explanation.')


def parse_layer_hashes(log: Path, count: int) -> list[dict]:
    gdn_rows, qsa_rows = [], []
    for line in log.read_text(errors='replace').splitlines():
        if 'STATE_HASH_GDN ' in line:
            values = line.split('STATE_HASH_GDN ', 1)[1].split()
            gdn_rows.append(values)
        elif 'STATE_HASH_QSA_LAYERS ' in line:
            match = re.search(r'STATE_HASH_QSA_LAYERS L=\d+ (.*)$', line)
            qsa = {}
            if match:
                for item in match.group(1).split():
                    m = re.fullmatch(r'qsa=(\d+) layer=(\d+) hash=([0-9a-f]+) idx=([0-9a-f]+) kv=([0-9a-f]+)', item)
                    if m:
                        qsa[int(m.group(2))] = {'state': m.group(3), 'index': m.group(4), 'kv': m.group(5)}
            qsa_rows.append(qsa)
    if len(gdn_rows) < count or len(qsa_rows) < count:
        raise RuntimeError(f'{log}: only {len(gdn_rows)} GDN / {len(qsa_rows)} QSA rows for {count} commits')
    return [{'gdn_layers': row, 'qsa_layers': qsa_rows[i]} for i, row in enumerate(gdn_rows[:count])]


def cumulative(arm: dict) -> dict[int, dict]:
    total, out, flat = 0, {}, []
    for record, hashes in zip(arm['accepted_prefix'], arm['layer_hashes']):
        total += record['committed']
        flat.extend(record['token_ids'])
        out[total] = {'state': record['state'], **hashes}
    if flat != arm['token_ids']:
        raise RuntimeError(f"{arm['backend']}: accepted token trace mismatch")
    return out


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    token_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 42
    output.mkdir(parents=True, exist_ok=False)
    command = json.loads(BASE.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    del args[args.index('--tokens'):args.index('--tokens') + 2]
    args[args.index('--max-new') + 1] = str(token_limit)
    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    prompt = tokenizer.encode(template.render([{'role': 'user', 'content': TASK}],
                                             enable_thinking=False), parse_special=True)
    env = os.environ.copy()
    env.update({'STRATA_PREFILL_CPU_SHARE': '0', 'STRATA_STATE_HASH': '1',
                'STRATA_ACCEPTED_PREFIX_TRACE': '1', 'STRATA_STATE_HASH_GDN': '1',
                'STRATA_STATE_HASH_QSA_LAYERS': '1', 'STRATA_MTP_BATCH': '1'})
    result = {'task': 'held-out is_prime(n); truncated state trace',
              'prompt_tokens': len(prompt), 'token_limit': token_limit, 'arms': []}
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        log = output / f'{backend}.log'
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            ids = [int(value) for value in engine.generate(prompt, token_limit,
                                                           {'temperature': 0}, threading.Event())
                   if value is not None]
            prefixes = read_accepted_prefix_trace(log)
            hashes = parse_layer_hashes(log, len(prefixes))
            result['arms'].append({'backend': backend, 'token_ids': ids,
                                   'token_sha256': hashlib.sha256(b''.join(
                                       int(v).to_bytes(4, 'little') for v in ids)).hexdigest(),
                                   'accepted_prefix': prefixes, 'layer_hashes': hashes,
                                   'finish': engine.last, 'log': log.name})
        finally:
            engine.close()
    left, right = result['arms']
    lmap, rmap = cumulative(left), cumulative(right)
    shared = sorted(set(lmap) & set(rmap))
    first = next((position for position in shared if lmap[position]['state'] != rmap[position]['state']), None)
    first_live = next((position for position in shared if any(
        lmap[position]['state'][key] != rmap[position]['state'][key]
        for key in lmap[position]['state'] if key != 'stale')), None)
    gdn_diff = []
    full_equal_count = gdn_equal_count = qsa_equal_count = 0
    for position in shared:
        full_equal_count += lmap[position]['state'] == rmap[position]['state']
        gdn_equal_count += lmap[position]['gdn_layers'] == rmap[position]['gdn_layers']
        qsa_equal_count += lmap[position]['qsa_layers'] == rmap[position]['qsa_layers']
    if first_live is not None:
        a, b = lmap[first_live]['gdn_layers'], rmap[first_live]['gdn_layers']
        gdn_diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    qsa_diff = []
    if first_live is not None:
        a, b = lmap[first_live]['qsa_layers'], rmap[first_live]['qsa_layers']
        qsa_diff = [layer for layer in sorted(set(a) | set(b)) if a.get(layer) != b.get(layer)]
    result['comparison'] = {
        'tokens_equal': left['token_ids'] == right['token_ids'],
        'token_counts': [len(left['token_ids']), len(right['token_ids'])],
        'shared_state_endpoints': len(shared),
        'full_state_equal_shared_endpoints': full_equal_count,
        'all_gdn_layer_hashes_equal_shared_endpoints': gdn_equal_count,
        'all_qsa_layer_hashes_equal_shared_endpoints': qsa_equal_count,
        'first_full_state_difference_token': first,
        'first_non_stale_difference_token': first_live,
        'first_live_difference_gdn_layer_indices': gdn_diff,
        'first_live_difference_qsa_model_layers': qsa_diff,
    }
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['comparison'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
