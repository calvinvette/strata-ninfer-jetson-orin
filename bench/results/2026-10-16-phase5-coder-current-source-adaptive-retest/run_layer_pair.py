#!/usr/bin/env python3
"""Run a randomized current-binary all-layer Coder adaptive pair."""
import argparse, hashlib, json, random, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'bench/results/2026-10-16-phase5-coder-fixed-residency-confirm7'
HERE=Path(__file__).resolve().parent
EXPECTED={
'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf':'e11083ba855e7666b48ea3f2db6a9c3a20c18751a012cc24f948de91b7087fad',
'Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00002-of-00002.gguf':'316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113'}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--seed',type=int,default=20261031); ap.add_argument('--run',action='store_true'); a=ap.parse_args()
 if a.output.exists(): ap.error('output directory already exists')
 cfg=json.loads((BASE/'config.json').read_text()); binary=Path(cfg['exe'])
 for flag in ('--native','--ple-gguf'):
  model=Path(cfg['args'][cfg['args'].index(flag)+1])
  if digest(model)!=EXPECTED.get(model.name): raise RuntimeError(f'model checksum mismatch: {model}')
 rows=[{'name':'delayed-control','adapt_every':100000,'adapt_swaps':96},{'name':'adaptive-cap8','adapt_every':4,'adapt_swaps':8}]
 random.Random(a.seed).shuffle(rows)
 campaign={'schema':1,'status':'planned','seed':a.seed,'order':[x['name'] for x in rows],
 'scope':'one randomized, same-service short/long/short/continuation trace pair; all-layer dispatch capture; correctness only',
 'repository_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'binary_sha256':digest(binary),'model_repository':'ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF',
 'model_revision':'5348543e0147355ac9cbcb031184a3546350988e','quantization':'IQ1_M','runs':[]}
 print(json.dumps({'order':campaign['order'],'binary_sha256':campaign['binary_sha256']},indent=2),flush=True)
 if not a.run:return 0
 a.output.mkdir(parents=True); campaign['status']='running'
 def save():
  q=a.output/'campaign.json.tmp'; q.write_text(json.dumps(campaign,indent=2)+'\n'); q.replace(a.output/'campaign.json')
 save(); py='/home/calvin/.local/python/bin/python3'
 for arm in rows:
  d=a.output/arm['name']; d.mkdir(); sup=d/'supervisor'; result=d/'result'
  cmd=[py,str(ROOT/'tools/integration/run_control.py'),'--output',str(sup),'--timeout','1800','--interval','1','--sample-clocks','--',py,str(HERE/'run_one_all_layers.py'),'--adapt-every',str(arm['adapt_every']),'--adapt-swaps',str(arm['adapt_swaps']),'--output',str(result)]
  launch='systemd-run --user --scope --collect -p MemoryMax=28G -p IOAccounting=yes '+' '.join(cmd)+'\n'
  (d/'launch.txt').write_text(launch); start=time.time()
  done=subprocess.run(['systemd-run','--user','--scope','--collect','-p','MemoryMax=28G','-p','IOAccounting=yes',*cmd],cwd=ROOT,capture_output=True,text=True)
  with (d/'launch.txt').open('a') as f:f.write(done.stdout+done.stderr)
  sr=json.loads((sup/'result.json').read_text()) if (sup/'result.json').exists() else {}
  result_json=json.loads((result/'analysis.json').read_text()) if (result/'analysis.json').exists() else {}
  ok=done.returncode==0 and sr.get('status')=='pass' and result_json.get('binary_sha256')==campaign['binary_sha256']
  campaign['runs'].append({**arm,'status':'pass' if ok else 'fail','launcher_returncode':done.returncode,
   'supervisor_status':sr.get('status'),'minimum_available_bytes':sr.get('minimum_available_bytes'),
   'minimum_admission_available_bytes':sr.get('minimum_admission_available_bytes'),'elapsed_s':sr.get('elapsed_s'),
   'analysis':result_json,'wall_start_s':start})
  save()
  if not ok: campaign['status']='fail'; save(); return 1
 campaign['status']='pass'; campaign['finished_wall_time_s']=time.time(); save(); return 0
if __name__=='__main__': raise SystemExit(main())
