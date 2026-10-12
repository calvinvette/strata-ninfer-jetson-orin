import hashlib
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, '/home/calvin/workspace/strata-ninfer-jetson-orin/tools/integration')
from file_tier_transfer_parity import load_tokenizer, ChatTemplate, exact_prompt, StrataEngine, ROOT

cfg = json.loads(Path(sys.argv[1]).read_text())
tokenizer = load_tokenizer(Path(cfg['tokenizer']))
template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
render = lambda text: tokenizer.encode(
    template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
long_target = 32768
context = 65536
long_text = exact_prompt(long_target, render)
long_prompt = render(long_text)
if len(long_prompt) != long_target:
    raise RuntimeError(f'expected {long_target} prompt tokens, got {len(long_prompt)}')
recovery_prompt = render('Reply with a short greeting for Orin.')
args = list(cfg['args'])
for key, value in (('--max-context', str(context)), ('--prompt-cache', '6')):
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])
env = dict(cfg.get('env', {}))
env.update({'STRATA_STAGE_PIN': '0', 'STRATA_PREFILL_CPU_SHARE': '0',
            'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH': '1',
            'STRATA_STATE_HASH_GDN': '1'})
out = Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
engine = StrataEngine(str(Path(sys.argv[2]).resolve()), args,
                      cwd=cfg.get('cwd'), log=str(out / 'engine.log'), env=env)
try:
    long_ids = [token for token in engine.generate(
        long_prompt, 1, {'temperature': 0}, threading.Event()) if token is not None]
    long_usage = dict(engine.last)
    recovery_ids = [token for token in engine.generate(
        recovery_prompt, 4, {'temperature': 0}, threading.Event()) if token is not None]
    recovery_usage = dict(engine.last)
    result = {
        'long_prompt_tokens': len(long_prompt),
        'long_prompt_sha256': hashlib.sha256(json.dumps(long_prompt, separators=(',', ':')).encode()).hexdigest(),
        'long_generated_ids': long_ids,
        'long_usage': long_usage,
        'recovery_prompt_tokens': len(recovery_prompt),
        'recovery_prompt_sha256': hashlib.sha256(json.dumps(recovery_prompt, separators=(',', ':')).encode()).hexdigest(),
        'recovery_generated_ids': recovery_ids,
        'recovery_usage': recovery_usage,
        'engine_args': args,
        'same_process_recovery_passed': len(long_ids) == 1 and len(recovery_ids) > 0 and
            long_usage.get('prompt_tokens') == long_target and
            recovery_usage.get('prompt_tokens') == len(recovery_prompt),
    }
    (out / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in (
        'long_prompt_tokens', 'long_generated_ids', 'recovery_prompt_tokens',
        'recovery_generated_ids', 'same_process_recovery_passed')}))
    if not result['same_process_recovery_passed']:
        raise RuntimeError('long request or same-process recovery failed')
finally:
    engine.close()
