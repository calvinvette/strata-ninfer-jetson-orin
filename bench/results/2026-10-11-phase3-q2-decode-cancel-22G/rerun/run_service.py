import json, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
root=next(p for p in Path(__file__).resolve().parents if (p/'serve/server.py').exists())
sys.path.insert(0,str(root/'tools'))
from run_control import write_result
out=Path(__file__).resolve().parent
cfg=json.loads((out/'server-config.json').read_text())
base=f"http://127.0.0.1:{cfg['port']}"
server=subprocess.Popen([sys.executable,'-m','serve.server','--engine','strata','--config',str(out/'server-config.json'),'--host','127.0.0.1','--port',str(cfg['port'])],cwd=cfg['cwd'])
result={'scope':'Q2_0 decode stream cancellation and same-process recovery under 22 GiB cgroup MemoryMax','model':cfg['model_name'],'checks':[]}
try:
    until=time.monotonic()+300
    while time.monotonic()<until:
        if server.poll() is not None: raise RuntimeError(f'server exited early: {server.returncode}')
        try:
            with urllib.request.urlopen(base+'/health',timeout=5) as r: health=json.load(r)
            if health.get('model'): break
        except (urllib.error.URLError,OSError,ValueError): time.sleep(.5)
    else: raise TimeoutError('server readiness deadline')
    result['health']=health
    body={'model':health['model'],'messages':[{'role':'user','content':'Count from 1 to 10000 separated by commas.'}], 'temperature':0,'max_tokens':1024,'stream':True,'chat_template_kwargs':{'enable_thinking':False}}
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    row={'check':'decode_disconnect','status':'started'}; result['checks'].append(row); write_result(out/'result.json',result)
    started=time.monotonic(); response=urllib.request.urlopen(req,timeout=300); first_text=''; event_count=0
    try:
        for raw in response:
            line=raw.decode('utf-8','replace').strip()
            if not line.startswith('data: ') or line=='data: [DONE]': continue
            event=json.loads(line[6:]); event_count+=1
            if event.get('choices'):
                first_text=event['choices'][0].get('delta',{}).get('content') or ''
                if first_text: break
    finally: response.close()
    row.update(status='pass' if first_text else 'fail', first_visible_text=first_text,event_count=event_count,close_after_s=time.monotonic()-started)
    if not first_text: raise RuntimeError('stream produced no visible decode text before close')
    write_result(out/'result.json',result)
    rec={'check':'same_process_recovery','status':'started'}; result['checks'].append(rec); write_result(out/'result.json',result)
    recovery={'model':health['model'],'messages':[{'role':'user','content':'Reply with exactly: Hello Orin!'}],'temperature':0,'max_tokens':24,'chat_template_kwargs':{'enable_thinking':False}}
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(recovery).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as r: answer=json.load(r)
    content=answer['choices'][0]['message'].get('content','').strip()
    rec.update(status='pass' if content=='Hello Orin!' else 'fail',response_text=content,server_alive=server.poll() is None)
    if not rec['server_alive']: rec.update(status='fail',reason=f'server exited: {server.returncode}')
    result['server_alive_after_recovery']=rec['server_alive']; result['checks'][-1]=rec
    write_result(out/'result.json',result)
    raise SystemExit(0 if all(x['status']=='pass' for x in result['checks']) else 1)
except BaseException as exc:
    if isinstance(exc,SystemExit): raise
    result['error']=f'{type(exc).__name__}: {exc}'
    if result['checks'] and result['checks'][-1]['status']=='started': result['checks'][-1].update(status='fail',reason=result['error'])
    write_result(out/'result.json',result)
    raise
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill(); server.wait(timeout=5)
