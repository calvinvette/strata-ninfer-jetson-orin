import json, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
root=next(p for p in Path(__file__).resolve().parents if (p/'serve/server.py').exists())
sys.path.insert(0,str(root/'tools/integration'))
from run_control import write_result
out=Path(__file__).resolve().parent; cfg=json.loads((out/'server-config.json').read_text()); base=f"http://127.0.0.1:{cfg['port']}"
result={'scope':'Q2_0 native verifier spec4 graph-shape and NVMap startup probe','model':cfg['model_name'],'spec':4,'checks':[]}
server=subprocess.Popen([sys.executable,'-m','serve.server','--engine','strata','--config',str(out/'server-config.json'),'--host','127.0.0.1','--port',str(cfg['port'])],cwd=cfg['cwd'])
sampler=None
try:
  deadline=time.monotonic()+300; health=None
  while time.monotonic()<deadline:
    if server.poll() is not None: raise RuntimeError(f'server exited: {server.returncode}')
    try:
      with urllib.request.urlopen(base+'/health',timeout=5) as r: health=json.load(r)
      if health.get('model'): break
    except (urllib.error.URLError,OSError,ValueError): time.sleep(.5)
  else: raise TimeoutError('service readiness deadline')
  result['health']=health
  sampler=subprocess.Popen(['sudo','-n',sys.executable,str(root/'tools/integration/nvmap_owner_trace.py'),'--output',str(out/'nvmap-clients.jsonl'),'--duration','45','--interval','0.1'])
  time.sleep(2)
  body={'model':health['model'],'messages':[{'role':'user','content':'Count from 1 to 1000 separated by commas. Continue with numbers only.'}],'temperature':0,'max_tokens':24,'stream':False,'chat_template_kwargs':{'enable_thinking':False}}
  req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  start=time.monotonic()
  with urllib.request.urlopen(req,timeout=300) as r: response=json.load(r)
  result['checks'].append({'check':'first_decode_request','status':'pass','elapsed_s':time.monotonic()-start,'usage':response.get('usage'),'text':response.get('choices',[{}])[0].get('message',{}).get('content','')})
  write_result(out/'result.json',result)
  if sampler.wait(timeout=60)!=0: raise RuntimeError(f'NVMap sampler exited {sampler.returncode}')
  result['server_alive_after_request']=server.poll() is None
  write_result(out/'result.json',result)
except BaseException as exc:
  if isinstance(exc,SystemExit): raise
  result['error']=f'{type(exc).__name__}: {exc}';write_result(out/'result.json',result);raise
finally:
  if sampler and sampler.poll() is None: sampler.terminate();sampler.wait(timeout=5)
  server.terminate()
  try: server.wait(timeout=10)
  except subprocess.TimeoutExpired: server.kill();server.wait(timeout=5)
