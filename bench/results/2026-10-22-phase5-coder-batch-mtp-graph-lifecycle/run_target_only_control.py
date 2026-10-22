#!/usr/bin/env python3
"""Target-only serial control for the preserved batch-MTP graph experiment."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.integration.batch_mtp_graph_lifecycle import (  # noqa: E402
    child_env, prepared_prompts, run_serial,
)

OUT = Path(__file__).resolve().parent
CFG = json.loads((OUT / 'config.json').read_text())
args = list(CFG['args'])
for key in ('--mtp', '--mtp-max-t'):
    if key in args:
        index = args.index(key)
        del args[index:index + 2]
for key in ('--adapt-every', '--adapt-accepted-only'):
    if key in args:
        index = args.index(key)
        del args[index:index + (1 if key == '--adapt-accepted-only' else 2)]
env = child_env(CFG)
env.update({'STRATA_INTEGRATION_TRACE': '1', 'STRATA_VERIFY_PROFILE': '1',
            'STRATA_STATE_HASH': '1', 'STRATA_PREFILL_CPU_SHARE': '0'})
prompts = prepared_prompts(CFG, 8)
run_dir = OUT / 'run-target-only-final'
run_dir.mkdir(parents=True, exist_ok=False)
control = run_serial(CFG, args, env, run_dir, prompts, 96)
reference = json.loads((OUT / 'run-chat/result.json').read_text())['batch_mtp']
output_match = {name: control[name]['tokens'] == reference[name]['tokens'] for name in prompts}
(run_dir / 'control-and-batch-outputs.json').write_text(json.dumps({
    'prompts': prompts,
    'control': {name: control[name] for name in prompts},
    'batch_mtp': {name: reference[name] for name in prompts},
    'per_prompt_output_match': output_match,
}, indent=2) + '\n')
prompt_names = list(prompts)
state_keys = ('L', 'gdn', 'ple', 'tail', 'pooled', 'kv', 'mtp', 'stale', 'dead', 'pooled_full', 'ple_prev')

def terminal_states(arm):
    result = {}
    for name in prompt_names:
        # The final emitted token is not yet consumed into recurrent/KV state.
        committed = prompts[name] + arm[name]['tokens'][:-1]
        terminal_length = str(len(committed))
        terminal_tail = ','.join(map(str, committed[-2:]))
        matches = [row for row in arm['state_rows'] if row['L'] == terminal_length and
                   row['ple_prev'] == terminal_tail]
        if len(matches) != 1:
            raise ValueError(f'{name}: expected one terminal fingerprint at L={terminal_length} '
                             f'ple_prev={terminal_tail}, found {len(matches)}')
        result[name] = tuple((key, matches[0][key]) for key in state_keys)
    return result

control_states = terminal_states(control)
batch_states = terminal_states(reference)
result = {
    'comparison': 'serial target-only vs batch-MTP; same chat-formatted prompts and greedy output limit',
    'prompts': prompts,
    'per_prompt_output_match': output_match,
    'all_outputs_match': all(output_match.values()),
    'serial_state_row_count': len(control['state_rows']),
    'batch_log_state_row_count_including_partial_request_legs': len(reference['state_rows']),
    'state_rows_have_complete_keys': all(set(state_keys) <= row.keys()
                                         for row in control['state_rows'] + reference['state_rows']),
    'terminal_state_match_by_prompt': {name: control_states[name] == batch_states[name]
                                       for name in prompt_names},
    'all_terminal_states_match': control_states == batch_states,
    'serial': control,
    'batch_mtp': reference,
}
(run_dir / 'target-only-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: result[key] for key in ('per_prompt_output_match', 'all_outputs_match',
                                                'serial_state_row_count',
                                                'batch_log_state_row_count_including_partial_request_legs',
                                                'state_fingerprint_multiset_match')}, indent=2))
