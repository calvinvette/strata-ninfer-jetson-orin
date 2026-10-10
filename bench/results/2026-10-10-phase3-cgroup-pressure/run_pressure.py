import json, pathlib, subprocess, time
root = pathlib.Path(__file__).parent
cmd = ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G",
       "python3", str(root / "hold_memory.py")]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
rows=[]
while p.poll() is None:
    mem = {}
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        if line.startswith(('MemAvailable:', 'MemTotal:')):
            k,v = line.split(':',1); mem[k] = int(v.strip().split()[0]) * 1024
    scopes=[]
    for cg in pathlib.Path('/sys/fs/cgroup/user.slice/user-1000.slice').glob('run-*.scope'):
        try: scopes.append({"path":str(cg),"current_bytes":int((cg/'memory.current').read_text()),"max_bytes":(cg/'memory.max').read_text().strip()})
        except (OSError,ValueError): pass
    rows.append({"t": time.time(), **mem, "scopes":scopes})
    time.sleep(0.25)
out,err = p.communicate()
(root/'stdout.txt').write_text(out)
(root/'stderr.txt').write_text(err)
(root/'memory.json').write_text(json.dumps({"command":cmd,"returncode":p.returncode,"samples":rows},indent=2)+'\n')
peak_cgroup=max((s['current_bytes'] for r in rows for s in r['scopes']),default=0)
print(f"returncode={p.returncode}; samples={len(rows)}; min_available={min((r['MemAvailable'] for r in rows),default=0)}; peak_scope_bytes={peak_cgroup}; stdout={out.strip()}; stderr={err.strip()}")
raise SystemExit(p.returncode)
