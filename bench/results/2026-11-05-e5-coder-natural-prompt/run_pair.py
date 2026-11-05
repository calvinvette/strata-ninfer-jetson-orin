import json, os, re, sys, threading
from pathlib import Path
ROOT=Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'tools/integration')]
from serve.server import StrataEngine
from serve.frontend import ChatTemplate
from tools.conversation_cache_parity import load_tokenizer
from tools.integration.pool_worker_screen import read_accepted_prefix_trace
base=ROOT/'bench/results/2026-11-05-e5-mixed-static-one-token-pair/coder-strata-cpu-share-off/result.json'
data=json.loads(base.read_text()); command=data['command']; ix=next(i for i,x in enumerate(command) if x.endswith('/strata') or x=='build/integration/e0-cuda-build/strata'); exe=str((ROOT/command[ix]).resolve()); args=command[ix+1:].copy()
args[args.index('--max-new')+1]='12'; del args[args.index('--tokens'):args.index('--tokens')+2]
tokdir=Path('/home/calvin/models/strata-orin-validation/pack/tokenizer'); tok=load_tokenizer(tokdir); template=ChatTemplate(tokdir/'chat_template.jinja')
messages=[{'role':'user','content':'Solve this arithmetic problem: What is 2 + 2? Respond with only the numeral.'}]
prompt=tok.encode(template.render(messages,enable_thinking=False),parse_special=True)
out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=False)
env=os.environ.copy();env['STRATA_PREFILL_CPU_SHARE']='0';env['STRATA_STATE_HASH']='1';env['STRATA_ACCEPTED_PREFIX_TRACE']='1';env['STRATA_INTEGRATION_TRACE']='1'
results=[]
for backend in ('strata','ninfer'):
 a=args.copy();a[a.index('--expert-backend')+1]=backend
 if backend=='ninfer': a.append('--expert-backend-strict')
 env['STRATA_STATE_DUMP_GDN']=str((out/f'{backend}.gdn.bin').resolve())
 env['STRATA_STATE_DUMP_GDN_AT']='33'
 log=out/f'{backend}.log'; engine=StrataEngine(exe,a,cwd=str(ROOT),log=str(log),env=env)
 try:
  ids=[int(x) for x in engine.generate(prompt,12,{'temperature':0},threading.Event()) if x is not None]
  state=[]
  for line in log.read_text(errors='replace').splitlines():
   if line.startswith('strata serve: STATE_HASH L='):
    state.append(dict(re.findall(r'(\w+)=([0-9a-f,-]+)',line)))
  prefixes=read_accepted_prefix_trace(log)
  raw_text=tok.decode(ids).strip()
  text=raw_text.split('<|im_end|>',1)[0].strip()
  results.append({'backend':backend,'output_ids':ids,'raw_decoded_text':raw_text,'output_text':text,'answer_oracle_passed':text=='4','finish':engine.last,'state':state[-1] if state else None,'accepted_prefix_entries':len(prefixes),'accepted_prefix_token_ids':[t for x in prefixes for t in x['token_ids']]})
 finally: engine.close()
 print(backend,repr(results[-1]['output_text']),results[-1]['finish'])
comparison={'prompt_text':messages[0]['content'],'prompt_ids_sha256':__import__('hashlib').sha256(json.dumps(prompt,separators=(',',':')).encode()).hexdigest(),'prompt_tokens':len(prompt),'max_new':12,'temperature':0,'expected_answer':'4','arms':results,'answer_oracle_passed':all(x['answer_oracle_passed'] for x in results),'output_equal':results[0]['output_ids']==results[1]['output_ids'],'final_state_equal':results[0]['state']==results[1]['state']}
comparison['accepted_prefix_tokens_equal']=[x['accepted_prefix_token_ids'] for x in results][0]==[x['accepted_prefix_token_ids'] for x in results][1]
(out/'results.json').write_text(json.dumps(comparison,indent=2)+'\n')
print(json.dumps({k:v for k,v in comparison.items() if k!='arms'},indent=2))
