#!/usr/bin/env python3
"""Prepare an exact-length held-out incident-analysis workload and warmup."""
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'tools'))
from strata_tokenizer import Tokenizer
from serve.frontend import ChatTemplate
TOKENIZER=Path('/home/calvin/models/strata-orin-validation/pack/tokenizer')
OUT=Path(__file__).resolve().parent
vocab=json.loads((TOKENIZER/'vocab.json').read_text()); tokens=[None]*len(vocab)
for text,index in vocab.items(): tokens[index]=text
tok=Tokenizer(tokens,(TOKENIZER/'merges.txt').read_text().split('\n'),json.loads((TOKENIZER/'token_type.json').read_text()))
template=ChatTemplate(TOKENIZER/'chat_template.jinja')
def encode(text): return tok.encode(template.render([{'role':'user','content':text}],enable_thinking=False),parse_special=True)
def exact(target,prefix,filler,suffix):
 low,high=0,target
 while low<=high:
  n=(low+high)//2; text=prefix+filler*n+suffix; ids=encode(text)
  if len(ids)==target:return text,ids
  if len(ids)<target:low=n+1
  else:high=n-1
 raise RuntimeError(f'cannot construct exact {target}-token text')
events=("09:00 gateway north p95=42ms errors=0 retries=1 deploy=none. "
"09:05 search north p95=88ms errors=1 retries=2 deploy=build71. "
"09:10 cache north p95=310ms errors=8 retries=19 deploy=none. "
"09:15 gateway south p95=49ms errors=0 retries=1 deploy=none. "
"09:20 search south p95=91ms errors=0 retries=2 deploy=build71. "
"09:25 cache south p95=295ms errors=7 retries=17 deploy=none. "
"09:30 gateway north p95=45ms errors=0 retries=1 deploy=none. "
"09:35 search north p95=95ms errors=1 retries=2 deploy=build71. "
"09:40 cache north p95=322ms errors=9 retries=21 deploy=none. "
"09:45 gateway south p95=47ms errors=0 retries=1 deploy=none. "
"09:50 search south p95=87ms errors=0 retries=2 deploy=build71. "
"09:55 cache south p95=301ms errors=8 retries=18 deploy=none. ")
measured,mid=exact(2048,'Field incident log: '+events+' Routine observation: ',' x',
 ' Analyze only patterns supported by the log. Separate observations from causes, identify one plausible confounder, and propose a measurement that could distinguish it. Write at least 250 words.')
warmup,wid=exact(512,'Warm-up maintenance note: ',' violet ',
 ' Explain why timestamps and calibration records help interpret later readings. Reply with exactly WARMED.')
def row(cell,prompt,ids,generated):
 return {'cell':cell,'prompt_tokens':len(ids),'generate_tokens':generated,
 'messages':[{'role':'user','content':prompt}],
 'chat_template_kwargs':{'enable_thinking':False}}
files=['vocab.json','merges.txt','token_type.json','chat_template.jinja']
ident=[{'path':str(TOKENIZER/f),'sha256':hashlib.sha256((TOKENIZER/f).read_bytes()).hexdigest()} for f in files]
(OUT/'workloads.json').write_text(json.dumps({'workloads':[row('heldout-incident-2048-tg128',measured,mid,128)],'tokenizer':ident,'policy':'exact 2,048-token semantically held-out incident-analysis prompt; API counts and cache freshness rechecked in every process'},indent=2)+'\n')
(OUT/'warmup-workloads.json').write_text(json.dumps({'workloads':[row('distinct-warmup-512',warmup,wid,1)],'tokenizer':ident,'policy':'distinct exact-512-token warmup prompt, one token; not measured'},indent=2)+'\n')
print(json.dumps({'measured_tokens':len(mid),'warmup_tokens':len(wid),'measured_sha256':hashlib.sha256(('\n'.join(map(str,mid))).encode()).hexdigest(),'warmup_sha256':hashlib.sha256(('\n'.join(map(str,wid))).encode()).hexdigest()},indent=2))
