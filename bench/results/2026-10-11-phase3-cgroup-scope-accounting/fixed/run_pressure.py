import json
import pathlib
import subprocess
import time

root = pathlib.Path(__file__).parent
cmd = ["systemd-run", "--user", "--scope", "-p", "MemoryMax=6G",
       "python3", str(root / "hold_memory.py")]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
rows = []
def process_cgroup(pid):
    for line in pathlib.Path(f"/proc/{pid}/cgroup").read_text().splitlines():
        if line.startswith("0::"):
            return pathlib.Path("/sys/fs/cgroup") / line[3:].lstrip("/")
    return None

while p.poll() is None:
    mem = {}
    for line in pathlib.Path('/proc/meminfo').read_text().splitlines():
        if line.startswith(('MemAvailable:', 'MemTotal:')):
            key, value = line.split(':', 1)
            mem[key] = int(value.strip().split()[0]) * 1024
    scope = process_cgroup(p.pid)
    scope_record = None
    if scope is not None and scope.name.startswith('run-') and scope.name.endswith('.scope'):
        try:
            scope_record = {
                "path": str(scope),
                "current_bytes": int((scope / "memory.current").read_text()),
                "max_bytes": (scope / "memory.max").read_text().strip(),
            }
        except (OSError, ValueError):
            pass
    rows.append({"t": time.time(), **mem, "scope": scope_record})
    time.sleep(0.25)
out, err = p.communicate()
(root / 'stdout.txt').write_text(out)
(root / 'stderr.txt').write_text(err)
result = {"command": cmd, "returncode": p.returncode, "samples": rows}
(root / 'memory.json').write_text(json.dumps(result, indent=2) + '\n')
peak = max((row['scope']['current_bytes'] for row in rows if row['scope']), default=0)
print(f"returncode={p.returncode}; samples={len(rows)}; min_available={min((r['MemAvailable'] for r in rows), default=0)}; peak_scope_bytes={peak}; stdout={out.strip()}; stderr={err.strip()}")
raise SystemExit(p.returncode)
