#!/usr/bin/env python3
"""Trace no-MTP vs MTP state on the exact measured incident prompt."""
import hashlib, json, threading
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'tools/integration')]
from tools.integration.accepted_prefix_parity import parse_hashes, STATE_KEYS
from tools.integration.pool_worker_screen import read_accepted_prefix_trace
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env
HERE=Path(__file__).resolve().parent
CONFIG=json.loads((HERE/'baseline-mtp4-config.json').read_text())
TOKENIZER=Path(CONFIG['tokenizer'])
TOK=load_tokenizer(TOKENIZER)
TEMPLATE=ChatTemplate(TOKENIZER/'chat_template.jinja')
WORKLOAD=json.loads((HERE/'workloads.json').read_text())['workloads'][0]
PROMPT=TOK.encode(TEMPLATE.render(WORKLOAD['messages'],enable_thinking=False),parse_special=True)
assert len(PROMPT)==2048, f'expected original 2048-token prompt, got {len(PROMPT)}'
if len(sys.argv) != 2:
 raise SystemExit(f'usage: {Path(sys.argv[0]).name} OUTPUT_DIRECTORY')
OUT=Path(sys.argv[1]).resolve()
OUT.mkdir(parents=True,exist_ok=False)
env=child_env(CONFIG)
env.update({'STRATA_STATE_HASH':'1','STRATA_STATE_HASH_GDN':'1','STRATA_ACCEPTED_PREFIX_TRACE':'1',
            'STRATA_INTEGRATION_TRACE':'1',
            'STRATA_PREFILL_CPU_SHARE':'0',
            'STRATA_VERIFY_DUMP_GDN_LAYER':'1',
            'STRATA_VERIFY_DUMP_GDN_PATH':str(OUT/'layer1.bin')})
env.pop('STRATA_MTP_BATCH',None)
results={'prompt_tokens':len(PROMPT),'prompt_token_sha256':hashlib.sha256(json.dumps(PROMPT).encode()).hexdigest(),
         'generated_limit':32,'engine_sha256':hashlib.sha256(Path(CONFIG['exe']).read_bytes()).hexdigest(),'arms':[]}
for label, spec in (('mtp-off',0),('mtp-window4',4)):
 args=list(CONFIG['args'])
 if '--adapt-every' in args: args[args.index('--adapt-every')+1]='100000'
 else: args += ['--adapt-every','100000']
 if '--spec' in args: args[args.index('--spec')+1]=str(max(2,spec))
 else: args += ['--spec',str(max(2,spec))]
 if spec==0:
  for key in ('--mtp','--mtp-max-t'):
   if key in args: del args[args.index(key):args.index(key)+2]
 else:
  if '--mtp-max-t' in args: args[args.index('--mtp-max-t')+1]=str(spec)
  else: args += ['--mtp-max-t',str(spec)]
 log=OUT/f'{label}.log'
 engine=StrataEngine(CONFIG['exe'],args,cwd=CONFIG['cwd'],log=str(log),env=env)
 try:
  ids=[int(t) for t in engine.generate(PROMPT,32,{'temperature':0},threading.Event()) if t is not None]
  last=engine.last
 finally: engine.close()
 states=parse_hashes(log); trace=read_accepted_prefix_trace(log)
 trace_ids=[t for entry in trace for t in entry['token_ids']]
 assert trace_ids==ids, f'{label}: trace token stream did not match publication'
 arm={'name':label,'spec':spec,'ids':ids,'text':TOK.decode(ids),'finish':last.get('finish'),
      'metrics':last,'state':states[-1] if states else None,'trace':trace,
      'trace_tokens_match_output':trace_ids==ids}
 assert len(states)==1 and trace, f'{label}: missing completed-request state evidence'
 results['arms'].append(arm)
 (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
ref,cand=results['arms']
ref_by_prefix={}; count=0
for row in ref['trace']:
 count+=row['committed']; ref_by_prefix[count]=row['state']
shared=[]; count=0
for row in cand['trace']:
 count+=row['committed']; prior=ref_by_prefix.get(count)
 if prior is not None:
  diff=[k for k in STATE_KEYS if prior.get(k)!=row['state'].get(k)]
  shared.append({'generated_prefix_tokens':count,'state_equal':not diff,'differing_fields':diff})
first=next((i for i,(a,b) in enumerate(zip(ref['ids'],cand['ids'])) if a!=b),None)
if first is None and len(ref['ids'])!=len(cand['ids']): first=min(len(ref['ids']),len(cand['ids']))
results['comparison']={'token_ids_equal':ref['ids']==cand['ids'],'first_differing_token_index':first,
 'final_main_state_equal':ref['state']==cand['state'],
 'final_differing_state_fields':[k for k in STATE_KEYS if ref['state'].get(k)!=cand['state'].get(k)],
 'shared_commit_boundaries':shared,'mtp_drafts_offered':cand['metrics'].get('drafts_offered'),
 'mtp_drafts_accepted':cand['metrics'].get('drafts_accepted')}
results['passed']=results['comparison']['token_ids_equal'] and results['comparison']['final_main_state_equal'] and all(x['state_equal'] for x in shared)
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results['comparison'],indent=2))
if not results['passed']: raise SystemExit(1)
