import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
for pair in range(3):
    d=OUT/f"pair-{pair:02d}"; d.mkdir(exist_ok=True)
    command=['systemd-run','--user','--scope','-p','MemoryMax=28G',sys.executable,
      'tools/integration/run_control.py','--output',str(d/'supervisor'),'--interval','0.5','--timeout','1800','--',
      sys.executable,'tools/integration/stage_buffer_parity.py','--config',str(OUT/'config.json'),
      '--engine','build/integration/candidate/strata','--output',str(d/'experiment'),
      '--prompt-tokens','512','--generated-tokens','64','--warmup-tokens','172',
      '--warmup-generated-tokens','64','--pairs','1','--seed',str(2026101200+pair),'--run']
    with (d/'launch.log').open('w') as log:
      log.write(json.dumps({'pair':pair,'command':command})+'\n'); log.flush()
      rc=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
      log.write(f'\nreturncode={rc}\n')
    print(f'pair {pair}: returncode={rc}',flush=True)
    if rc: raise SystemExit(rc)
