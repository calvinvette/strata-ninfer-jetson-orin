"""Run fixed-prefix multi-token Q2_0 output and retain accepted-prefix trace."""
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from file_tier_transfer_parity import load_tokenizer, ChatTemplate, exact_prompt, StrataEngine

config_path, engine_path, output_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
max_new = int(sys.argv[4])
cfg = json.loads(config_path.read_text())
tokenizer = load_tokenizer(Path(cfg['tokenizer']))
template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
render = lambda text: tokenizer.encode(
    template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
full_prompt = render(exact_prompt(512, render))
prompt = full_prompt[:511]
if len(full_prompt) != 512 or len(prompt) != 511:
    raise RuntimeError('prepared prompt token lengths changed')

args = list(cfg['args'])
for key, value in (('--max-context', str(max(640, 511 + max_new + 16))), ('--prompt-cache', '6')):
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])
env = dict(cfg.get('env', {}))
env.update({
    'STRATA_STAGE_PIN': '0',
    'STRATA_PREFILL_CPU_SHARE': '0',
    'STRATA_INTEGRATION_TRACE': '1',
    'STRATA_STATE_HASH': '1',
    'STRATA_STATE_HASH_GDN': '1',
    'STRATA_ACCEPTED_PREFIX_TRACE': '1',
})
engine = StrataEngine(str(engine_path.resolve()), args, cwd=cfg.get('cwd'),
                      log=str((output_dir / 'engine.log').resolve()), env=env)
try:
    ids = [token for token in engine.generate(prompt, max_new, {'temperature': 0}, threading.Event())
           if token is not None]
    result = {
        'prompt_tokens': len(prompt),
        'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'requested_output_tokens': max_new,
        'generated_ids': ids,
        'generated_ids_sha256': hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest(),
        'usage': dict(engine.last),
        'engine_args': args,
        'completed_requested_output': len(ids) == max_new,
        'early_termination': len(ids) < max_new,
        'passed': len(ids) > 0,
    }
    (output_dir / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('prompt_tokens', 'requested_output_tokens',
                                                    'generated_ids_sha256', 'usage', 'passed')}))
    if not result['passed']:
        raise RuntimeError('generation returned no output tokens')
finally:
    engine.close()
