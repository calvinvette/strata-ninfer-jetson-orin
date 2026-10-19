#!/usr/bin/env python3
"""Replay the seven moved experts on an identical captured device activation."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = HERE / "weighted-replay-retry1"
OUT = INPUT / "operator-retry1"
MODEL = Path.home() / "models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf"
ENGINE = ROOT / "build/integration/candidate/native_expert_parity"
EXPERTS = (174, 62, 69, 130, 143, 151, 28)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite {OUT}")
    if not MODEL.is_file() or not ENGINE.is_file():
        raise SystemExit("required local GGUF or native_expert_parity binary is missing")
    OUT.mkdir(parents=True)
    activation = INPUT / "activation-position-511.f32"
    results = []
    for expert in EXPERTS:
        dest = OUT / str(expert)
        dest.mkdir()
        with tempfile.TemporaryDirectory(prefix=f"layer2-expert-{expert}-") as temp:
            command = [str(ENGINE), str(MODEL), "--expert", str(expert),
                       "--activation-f32", str(activation), "--activation-rows", "1",
                       "--token-width", "1", "--dump-f32-dir", temp, "2"]
            env = os.environ.copy()
            env["STRATA_NATIVE_CPU_Q8_1_DOT"] = "iq2_s/iq4_nl@layer=2"
            completed = subprocess.run(command, cwd=ROOT, env=env, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (dest / "stdout.txt").write_text(completed.stdout)
            (dest / "command.json").write_text(json.dumps(command, indent=2) + "\n")
            if completed.returncode != 0:
                raise RuntimeError(f"expert {expert} parity replay failed with {completed.returncode}:\n{completed.stdout}")
            stem = f"layer-2-expert-{expert}-nt=1"
            for kind in ("cpu-output", "gpu-output"):
                source = Path(temp) / f"{stem}-{kind}.f32"
                if not source.is_file() or source.stat().st_size != 2560 * 4:
                    raise RuntimeError(f"expert {expert}: missing or invalid {kind} output")
                shutil.copyfile(source, dest / f"{kind}.f32")
        results.append({"expert": expert,
                        "cpu_sha256": sha256(dest / "cpu-output.f32"),
                        "gpu_sha256": sha256(dest / "gpu-output.f32"),
                        "stdout": "passed"})
    report = {
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "native_expert_parity_sha256": sha256(ENGINE), "model_path": str(MODEL),
        "model_revision": "5348543e0147355ac9cbcb031184a3546350988e", "quantization": "IQ1_M",
        "selector": "iq2_s/iq4_nl@layer=2", "layer": 2,
        "activation_path": str(activation), "activation_sha256": sha256(activation),
        "activation_rows": 1, "replayed_experts": results,
        "method": "native_expert_parity real GGUF expert decode, same captured float32 input, one row, CPU Q8_1 and CUDA grouped paths",
    }
    (OUT / "replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
