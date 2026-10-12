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
target = int(sys.argv[2])
context = int(sys.argv[5]) if len(sys.argv) > 5 else target + 32
prompt_text = exact_prompt(target, render)
prompt = render(prompt_text)
if len(prompt) != target:
    raise RuntimeError(f'expected {target} prompt tokens, got {len(prompt)}')
args = list(cfg['args'])
for key, value in (('--max-context', str(context)), ('--prompt-cache', '6')):
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])
env = dict(cfg.get('env', {}))
env.update({'STRATA_STAGE_PIN': '0', 'STRATA_PREFILL_CPU_SHARE': '0',
            'STRATA_INTEGRATION_TRACE': '1', 'STRATA_STATE_HASH': '1',
            'STRATA_STATE_HASH_GDN': '1', 'STRATA_ACCEPTED_PREFIX_TRACE': '1'})
out = Path(sys.argv[4])
engine = StrataEngine(str(Path(sys.argv[3]).resolve()), args,
                      cwd=cfg.get('cwd'), log=str(out / 'engine.log'), env=env)
try:
    ids = [token for token in engine.generate(prompt, 32, {'temperature': 0}, threading.Event())
           if token is not None]
    result = {'prompt_tokens': len(prompt),
              'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
              'generated_ids': ids, 'usage': dict(engine.last),
              'engine_args': args, 'passed': len(ids) > 0 and engine.last.get('prompt_tokens') == target}
    (out / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('prompt_tokens', 'generated_ids', 'usage', 'passed')}))
    if not result['passed']:
        raise RuntimeError('prompt did not complete or no token was generated')
finally:
    engine.close()
