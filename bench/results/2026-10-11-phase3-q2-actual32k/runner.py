import json, sys, threading, hashlib
from pathlib import Path
sys.path.insert(0, '/home/calvin/workspace/strata-ninfer-jetson-orin/tools/integration')
from file_tier_transfer_parity import load_tokenizer, ChatTemplate, exact_prompt, StrataEngine, ROOT
cfg=json.load(open(sys.argv[1]))
tokenizer=load_tokenizer(Path(cfg['tokenizer']))
template_path=Path(cfg['tokenizer'])/'chat_template.jinja'
template=ChatTemplate(template_path if template_path.exists() else ROOT/'serve/chat_template.jinja')
render=lambda text: tokenizer.encode(template.render([{'role':'user','content':text}], enable_thinking=False), parse_special=True)
target=int(sys.argv[2]); prompt_text=exact_prompt(target, render); prompt=render(prompt_text)
if len(prompt)!=target: raise RuntimeError(f'expected {target}, got {len(prompt)}')
args=list(cfg['args'])
for key,value in (('--max-context', str(target+32)),('--prompt-cache','6')):
 if key in args: args[args.index(key)+1]=value
 else: args.extend([key,value])
env=dict(cfg.get('env',{})); env.update({'STRATA_STAGE_PIN':'0','STRATA_PREFILL_CPU_SHARE':'0','STRATA_INTEGRATION_TRACE':'1','STRATA_STATE_HASH':'1','STRATA_STATE_HASH_GDN':'1'})
log=sys.argv[4] + '/engine.log'
e=StrataEngine(str(Path(sys.argv[3]).resolve()),args,cwd=cfg.get('cwd'),log=log,env=env)
try:
 ids=[t for t in e.generate(prompt,1,{'temperature':0},threading.Event()) if t is not None]
 result={'prompt_tokens':len(prompt),'prompt_sha256':hashlib.sha256(json.dumps(prompt,separators=(',',':')).encode()).hexdigest(),'generated_ids':ids,'usage':dict(e.last),'engine_args':args,'passed':len(ids)==1}
 Path(sys.argv[4] + '/workload.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k] for k in ('prompt_tokens','generated_ids','usage','passed')}))
 if not result['passed']: raise RuntimeError('generation count mismatch')
finally: e.close()
