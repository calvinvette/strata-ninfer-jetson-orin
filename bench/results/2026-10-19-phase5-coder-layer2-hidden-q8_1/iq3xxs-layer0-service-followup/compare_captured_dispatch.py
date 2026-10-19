#!/usr/bin/env python3
"""Bitwise-check captured CPU expert outputs against the standalone parity runner."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--dispatch-jsonl', type=Path, required=True)
    ap.add_argument('--cpu-output-jsonl', type=Path, required=True)
    ap.add_argument('--parity', type=Path, default=Path('build/integration/candidate/native_expert_parity'))
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    records = [json.loads(line) for line in args.dispatch_jsonl.read_text().splitlines()]
    header, rows = records[0], records[1:]
    dispatch = next(row for row in rows if row['dispatch'] == 0)
    out_lines = [json.loads(line) for line in args.cpu_output_jsonl.read_text().splitlines()]
    out_header = out_lines[0]
    if header.get('format') != 'strata-moe-dispatch-v3' or out_header.get('format') != 'strata-moe-cpu-output-v2':
        raise SystemExit('unexpected capture schema')
    expected = {row['expert']: row for row in out_lines[1:] if row['dispatch'] == dispatch['dispatch']}
    cpu_experts = [expert for expert, owner in zip(dispatch['ids'], dispatch['route_kind']) if owner == -1]
    if sorted(expected) != sorted(cpu_experts):
        raise SystemExit(f'CPU route/output mismatch: {cpu_experts} vs {sorted(expected)}')

    args.output.mkdir(parents=True, exist_ok=False)
    activation = args.output / 'dispatch0-activation.f32'
    activation.write_bytes(struct.pack('<%sf' % len(dispatch['activation']), *dispatch['activation']))
    results = []
    with tempfile.TemporaryDirectory(prefix='strata-q8-parity-') as tmp:
        tmp = Path(tmp)
        q8_dump, baseline_dump = tmp / 'q8', tmp / 'baseline'
        q8_dump.mkdir()
        baseline_dump.mkdir()
        for expert in cpu_experts:
            cmd = [str(args.parity), str(args.model), '--expert', str(expert), '--activation-f32', str(activation),
                   '--activation-rows', '1', '--token-width', '1', '--dump-f32-dir', str(q8_dump), '0']
            env = os.environ.copy()
            env['STRATA_NATIVE_CPU_Q8_1_DOT'] = 'iq3_xxs/iq4_nl@layer=0'
            proc = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if proc.returncode:
                raise SystemExit(proc.stdout)
            stem = f'layer-0-expert-{expert}-nt=1-cpu-output.f32'
            replay = struct.unpack('<%sf' % len(expected[expert]['output']), (q8_dump / stem).read_bytes())
            baseline_cmd = cmd.copy()
            baseline_cmd[baseline_cmd.index('--dump-f32-dir') + 1] = str(baseline_dump)
            baseline_env = env.copy()
            baseline_env.pop('STRATA_NATIVE_CPU_Q8_1_DOT', None)
            baseline_proc = subprocess.run(baseline_cmd, env=baseline_env, text=True,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if baseline_proc.returncode:
                raise SystemExit(baseline_proc.stdout)
            baseline = struct.unpack('<%sf' % len(expected[expert]['output']),
                                     (baseline_dump / stem).read_bytes())
            # The capture stores F32 values as nine-significant-digit JSON; round
            # those decimals back to F32 before comparing their bit patterns.
            service = struct.unpack('<%sf' % len(expected[expert]['output']),
                                    struct.pack('<%sf' % len(expected[expert]['output']),
                                                *expected[expert]['output']))
            different = sum(a != b for a, b in zip(replay, service))
            result = {'expert': expert, 'values': len(service), 'different_words': different,
                      'max_abs': max(abs(a-b) for a, b in zip(replay, service)),
                      'baseline_vs_q8_1': {
                          'different_words': sum(a != b for a, b in zip(baseline, replay)),
                          'max_abs': max(abs(a-b) for a, b in zip(baseline, replay)),
                          'relative_l1': sum(abs(a-b) for a, b in zip(baseline, replay)) /
                                         sum(abs(a) for a in baseline),
                      },
                      'parity_stdout': proc.stdout.strip().splitlines()[-2:]}
            results.append(result)
            if different:
                raise SystemExit(f'expert {expert}: {different} service/replay words differ')
    report = {'dispatch': dispatch['dispatch'], 'position': dispatch['position'], 'token_id': dispatch['token_id'],
              'cpu_experts': cpu_experts, 'results': results}
    args.output.joinpath('operator-replay.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
