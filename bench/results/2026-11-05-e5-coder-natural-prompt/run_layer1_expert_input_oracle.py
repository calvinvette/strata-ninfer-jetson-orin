"""Run the mixed-expert oracle on the exact captured layer-1 route input."""
from __future__ import annotations

import array
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path('/home/calvin/workspace/strata-ninfer-expert-e0')
sys.path.insert(0, str(ROOT))
from tools.integration.compare_moe_bundle import read_bundle

CAPTURE = ROOT / 'bench/results/2026-11-05-e5-coder-natural-prompt/moe-boundaries-pos41'
MODEL = Path('/home/calvin/models/strata-orin-validation/Coder-GGUF/IQ1_M/Qwen3.8-Flash-Next-GSQ-RCO-IQ1_M-00001-of-00002.gguf')
ORACLE = ROOT / 'build/integration/e0-cuda-build/ninfer_iq_expert_parity'
LAYER, POSITION, EXPERT = 1, 41, 198


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for backend in ('strata', 'ninfer'):
        _, records = read_bundle(CAPTURE / f'{backend}.moe-bundle')[(LAYER, POSITION)]
        activation = array.array('f', records['input'])
        path = output / f'{backend}-layer1-pos41-input.f32'
        with path.open('wb') as stream:
            activation.tofile(stream)
        log = output / f'{backend}-oracle.log'
        command = [str(ORACLE), str(MODEL), str(LAYER), str(EXPERT), str(path)]
        proc = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=False)
        log.write_text(proc.stdout)
        results.append({'backend_input': backend, 'activation_file': path.name,
                        'activation_values': len(activation), 'oracle_returncode': proc.returncode,
                        'oracle_output': proc.stdout.strip(), 'log_file': log.name})
        if proc.returncode:
            raise SystemExit(proc.returncode)
    summary = {'layer': LAYER, 'position': POSITION, 'expert': EXPERT,
               'weights': str(MODEL), 'arms': results}
    (output / 'results.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
