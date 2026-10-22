#!/usr/bin/env python3
"""Exercise batch-MTP graph eviction/recapture with a small opt-in pool cap."""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from serve.server import StrataEngine, child_env
from tools.integration.batch_mtp_graph_lifecycle import prepared_prompts, replace_arg, remove_arg

OUT = Path(__file__).resolve().parent / 'run-graph-lifecycle-recapture'
OUT.mkdir(parents=True, exist_ok=False)
CFG = json.loads((Path(__file__).resolve().parent / 'config.json').read_text())
args = list(CFG['args'])
replace_arg(args, '--spec', '2')
replace_arg(args, '--max-context', '1024')
replace_arg(args, '--expert-cache', '1500')
replace_arg(args, '--prompt-cache', '6')
remove_arg(args, '--adapt-every')
remove_arg(args, '--adapt-accepted-only')
prompts = prepared_prompts(CFG, 2)
env = child_env(CFG)
env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
            'STRATA_BATCH_MTP_GRAPH_LIMIT': '1'})
engine = StrataEngine(CFG['exe'], args + ['--batch', '2', '--batch-mtp'],
                      cwd=CFG.get('cwd'), log=str(OUT / 'batch-mtp.log'), env=env)
try:
    if engine.batch != 2:
        raise RuntimeError(f'only admitted {engine.batch} batch slots')
    def generate(prompt):
        tokens = [token for token in engine.generate(prompt, 6, {'temperature': 0}, threading.Event())
                  if token is not None]
        return {'tokens': tokens, 'finish': engine.last.get('finish')}
    prompt_keys = list(prompts)
    jobs = {f'request-{index}': prompt_keys[index % len(prompt_keys)] for index in range(8)}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(generate, prompts[key]) for name, key in jobs.items()}
        outputs = {name: future.result() for name, future in futures.items()}
finally:
    engine.close()
result = {'profile': {'live_slots': 2, 'batch_slots': 2, 'mtp_depth': 2,
                      'max_new': 6, 'requests_submitted_concurrently': 8, 'graph_pool_limit': 1},
          'prompt_sha256': {key: hashlib.sha256(json.dumps(value).encode()).hexdigest()
                     for key, value in prompts.items()},
          'request_prompt_template': jobs, 'batch_mtp': outputs}
(OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'profile': result['profile'], 'token_counts':
                  {name: len(value['tokens']) for name, value in outputs.items()}}))
