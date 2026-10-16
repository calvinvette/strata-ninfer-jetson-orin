#!/usr/bin/env python3
"""Dump GGUF-dequantized layer-0 experts and operator outputs for captured inputs."""
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAPTURE = ROOT / "bench/results/2026-10-14-phase5-current-source-route-change-capture/run/start-0.jsonl"
MODEL = Path("/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf")
BINARY = ROOT / "build/integration/candidate/native_expert_parity"
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

rows = [json.loads(line) for line in CAPTURE.read_text().splitlines()]
initial, recovery = rows[1:23], rows[45:67]
experts = sorted({e for b, a in zip(initial[:7], recovery[:7])
                  for e, ob, oa in zip(b["ids"], b["route_kind"], a["route_kind"])
                  if ob != oa})
assert experts == [32, 55, 70, 75, 119, 165], experts
dump = OUT / "weights-and-outputs"
dump.mkdir(exist_ok=True)
activation = OUT / "activation-row0.f32"
activation.write_bytes(struct.pack("<2560f", *initial[0]["activation"]))
log = []
for expert in experts:
    cmd = [str(BINARY), str(MODEL), "--expert", str(expert), "--activation-f32", str(activation),
           "--dump-f32-dir", str(dump), "0"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.append(f"$ {' '.join(cmd)}\n{proc.stdout}")
    if proc.returncode:
        (OUT / "parity-output.txt").write_text("\n".join(log))
        raise SystemExit(f"expert {expert} parity returned {proc.returncode}")
(OUT / "parity-output.txt").write_text("\n".join(log))
print(f"dumped {len(experts)} experts using {activation}")
