#!/usr/bin/env python3
"""Test exact short-task quality before and after an adaptive long request."""
import argparse
import hashlib
import json
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

BASE = ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--sessions', type=int, default=2)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
cfg = json.loads((BASE / 'baseline-mtp0-config.json').read_text())
tok_path = Path(cfg['tokenizer'])
tok = load_tokenizer(tok_path)
template = ChatTemplate(tok_path / 'chat_template.jinja')
# Build a held-out exact-answer prompt, padded with neutral prose to exercise
# the same 512-token short-prefill shape while keeping the task near the end.
code = 'ORCHID-GLACIER-482'
task = f'Return exactly this code and nothing else: {code}'
short_ids = None
for filler_tokens in range(1024):
    user = ('x ' * filler_tokens) + task
    short_ids = tok.encode(template.render([{'role':'user','content':user}], enable_thinking=False), parse_special=True)
    if len(short_ids) == 512:
        break
if len(short_ids) != 512:
    raise RuntimeError(f'could not make exact 512-token short prompt: {len(short_ids)}')

# Recreate the exact 2,048-token workload previously used for the route capture.
long_cfg_source = json.loads((ROOT / 'bench/results/2026-10-13-phase6-q6-warp-mtp-confirm7/workloads.json').read_text())['workloads'][0]
long_ids = tok.encode(template.render(long_cfg_source['messages'], enable_thinking=False), parse_special=True)
if len(long_ids) != 2048:
    raise RuntimeError(f'long prompt changed: {len(long_ids)}')
results = {'status':'running', 'profile':'IQ1_M Coder, MTP off, Q6_K warp-dequant opt-in, accepted-only adaptive cadence 4',
           'sequence':['short-exact-code','long-2048','short-exact-code-recovery'],
           'short_prompt_tokens':len(short_ids),'long_prompt_tokens':len(long_ids),
           'expected_code':code, 'short_prompt_sha256':hashlib.sha256(json.dumps(short_ids).encode()).hexdigest(),
           'long_prompt_sha256':hashlib.sha256(json.dumps(long_ids).encode()).hexdigest(), 'sessions':[]}
(a.output/'prompts.json').write_text(json.dumps({'short_ids':short_ids,'long_ids':long_ids},indent=2)+'\n')
for si in range(a.sessions):
    argv = list(cfg['args'])
    if '--adapt-every' in argv: argv[argv.index('--adapt-every')+1]='4'
    else: argv += ['--adapt-every','4']
    if '--adapt-accepted-only' not in argv: argv.append('--adapt-accepted-only')
    env=child_env(cfg)
    env.update({'STRATA_STATE_HASH':'1','STRATA_STATE_HASH_GDN':'1','STRATA_ACCEPTED_PREFIX_TRACE':'1',
                'STRATA_PREFILL_CPU_SHARE':'0','STRATA_VERIFY_ADAPT_SWAPS':'1'})
    log=a.output/f'session-{si}.log'
    engine=StrataEngine(cfg['exe'],argv,cwd=cfg['cwd'],log=str(log),env=env)
    session={'requests':[]}
    try:
        for name,prompt in [('short-exact-code',short_ids),('long-2048',long_ids),('short-exact-code-recovery',short_ids)]:
            ids=[int(x) for x in engine.generate(prompt,16,{'temperature':0},threading.Event()) if x is not None]
            hashes=parse_hashes(log)
            if len(hashes)!=len(session['requests'])+1: raise RuntimeError(f'state hash count {name}: {len(hashes)}')
            response=tok.decode(ids)
            session['requests'].append({'name':name,'prompt_tokens':len(prompt),'ids':ids,'response':response,
                                       'code_present_exactly_once':response.count(code)==1,
                                       'exact_code_reply':response.replace('<|im_end|>','').strip()==code if name != 'long-2048' else None,
                                       'state':hashes[-1]})
            results['sessions']=[x for x in results['sessions'] if x.get('session')!=si]
            results['sessions'].append({'session':si,**session})
            (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    finally: engine.close()
checks=[]
for session in results['sessions']:
    r=session['requests']
    checks.append({'session':session['session'],'initial_exact_code':r[0]['exact_code_reply'],
                   'recovery_exact_code':r[2]['exact_code_reply'],
                   'short_output_equal':r[0]['ids']==r[2]['ids'],
                   'short_state_equal':r[0]['state']==r[2]['state'],
                   'long_request_completed':len(r[1]['ids'])>0})
results['checks']=checks
results['status']='pass' if all(c['initial_exact_code'] and c['recovery_exact_code'] and c['long_request_completed'] for c in checks) else 'quality_fail'
results['same_service_drift_reproduced']=any(not c['short_output_equal'] or not c['short_state_equal'] for c in checks)
(a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({'status':results['status'],'checks':checks,'expected_code':code},indent=2))
