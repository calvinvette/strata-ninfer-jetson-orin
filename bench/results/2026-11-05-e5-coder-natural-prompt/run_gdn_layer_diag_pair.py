"""Capture one GDN layer's full prompt rows under both expert backends."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from serve.server import StrataEngine
from serve.frontend import ChatTemplate
from tools.conversation_cache_parity import load_tokenizer

BASE = ROOT / 'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    layer = int(sys.argv[2])
    bundle_layers = sys.argv[3] if len(sys.argv) > 3 else '1'
    bundle_position = int(sys.argv[4]) if len(sys.argv) > 4 else 41
    output.mkdir(parents=True, exist_ok=False)
    command = json.loads(BASE.read_text())['command']
    index = next(i for i, value in enumerate(command)
                 if value.endswith('/strata') or value == 'build/integration/e0-cuda-build/strata')
    executable = str((ROOT / command[index]).resolve())
    args = command[index + 1:].copy()
    args[args.index('--max-new') + 1] = '1'
    del args[args.index('--tokens'):args.index('--tokens') + 2]

    tokenizer_path = Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    prompt_text = ('Write a Python function named is_even(n) that returns True '
                   'exactly when the integer n is evenly divisible by 2. Output '
                   'only Python code defining is_even.')
    prompt = tokenizer.encode(template.render([{'role': 'user', 'content': prompt_text}],
                                               enable_thinking=False), parse_special=True)
    base_env = os.environ.copy()
    base_env.update({
        'STRATA_PREFILL_CPU_SHARE': '0',
        'STRATA_VERIFY_DUMP_GDN_LAYER': str(layer),
        'STRATA_VERIFY_DUMP_GDN_PATH': str((output / 'PLACEHOLDER').resolve()),
        'STRATA_VERIFY_DUMP_GDN_O': '1',
        'STRATA_VERIFY_DUMP_MOE_BUNDLE_LAYERS': bundle_layers,
        'STRATA_VERIFY_DUMP_MOE_BUNDLE_POSITION': str(bundle_position),
        'STRATA_VERIFY_DUMP_MOE_BUNDLE_PATH': str((output / 'PLACEHOLDER.moe-bundle').resolve()),
    })
    arms = []
    for backend in ('strata', 'ninfer'):
        arm_args = args.copy()
        arm_args[arm_args.index('--expert-backend') + 1] = backend
        if backend == 'ninfer':
            arm_args.append('--expert-backend-strict')
        prefix = output / backend
        env = base_env.copy()
        env['STRATA_VERIFY_DUMP_GDN_PATH'] = str(prefix.with_suffix('.gdn-diag').resolve())
        env['STRATA_VERIFY_DUMP_MOE_BUNDLE_PATH'] = str(prefix.with_suffix('.moe-bundle').resolve())
        env['STRATA_CAPTURE_MOE_PATH'] = str(prefix.with_suffix('.moe-owner.jsonl').resolve())
        env['STRATA_CAPTURE_MOE_LAYER'] = '1'
        env['STRATA_CAPTURE_MOE_POSITION'] = '41'
        env['STRATA_CAPTURE_MOE_ROWS'] = '1'
        env['STRATA_CAPTURE_MOE_OUTPUT_PATH'] = str(prefix.with_suffix('.moe-cpu-output.jsonl').resolve())
        env['STRATA_CAPTURE_MOE_OUTPUT_LAYER'] = '1'
        log = prefix.with_suffix('.log')
        engine = StrataEngine(executable, arm_args, cwd=str(ROOT), log=str(log), env=env)
        try:
            ids = [int(value) for value in engine.generate(prompt, 1, {'temperature': 0},
                                                            threading.Event()) if value is not None]
            diag = prefix.with_suffix('.gdn-diag')
            raw_o = Path(str(diag) + '.o')
            bundle = prefix.with_suffix('.moe-bundle')
            owner = prefix.with_suffix('.moe-owner.jsonl')
            cpu_output = prefix.with_suffix('.moe-cpu-output.jsonl')
            arms.append({
                'backend': backend, 'token_ids': ids, 'finish': engine.last,
                'diag_file': diag.name, 'diag_sha256': hashlib.sha256(diag.read_bytes()).hexdigest(),
                'raw_o_file': raw_o.name, 'raw_o_sha256': hashlib.sha256(raw_o.read_bytes()).hexdigest(),
                'moe_bundle_file': bundle.name,
                'moe_bundle_sha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
                'moe_owner_file': owner.name, 'moe_owner_sha256': hashlib.sha256(owner.read_bytes()).hexdigest(),
                'moe_cpu_output_file': cpu_output.name,
                'moe_cpu_output_sha256': hashlib.sha256(cpu_output.read_bytes()).hexdigest(),
                'log_file': log.name,
            })
        finally:
            engine.close()
    result = {
        'task': 'held-out is_even(n) Coder IQ1_M service prompt',
        'prompt_tokens': len(prompt), 'captured_layer': layer, 'captured_prompt_positions': 'all verifier rows',
        'moe_bundle_layers': bundle_layers, 'moe_bundle_position': bundle_position,
        'temperature': 0, 'arms': arms,
        'token_ids_equal': arms[0]['token_ids'] == arms[1]['token_ids'],
    }
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'arms'}, indent=2))
    for arm in arms:
        print(arm['backend'], arm['token_ids'], arm['diag_sha256'], arm['raw_o_sha256'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
