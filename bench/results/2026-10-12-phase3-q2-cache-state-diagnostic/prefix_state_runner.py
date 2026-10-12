"""Compare persistent state for a shared prefix of the prepared Q2_0 prompt."""
import hashlib
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from file_tier_transfer_parity import load_tokenizer, ChatTemplate, exact_prompt, StrataEngine

config_path, engine_path, output_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cfg = json.loads(config_path.read_text())
tokenizer = load_tokenizer(Path(cfg['tokenizer']))
template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
render = lambda text: tokenizer.encode(
    template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
full_prompt = render(exact_prompt(512, render))
prompt = full_prompt[:511]
if len(full_prompt) != 512 or len(prompt) != 511:
    raise RuntimeError('prepared prefix token lengths changed')

args = list(cfg['args'])
for key, value in (('--max-context', '543'), ('--prompt-cache', '6')):
    if key in args:
        args[args.index(key) + 1] = value
    else:
        args.extend([key, value])
env = dict(cfg.get('env', {}))
dump_dir = ROOT / 'build/integration/phase3-q2-cache-state-diagnostic' / output_dir.name
dump_dir.mkdir(parents=True, exist_ok=True)
dump_path = dump_dir / 'gdn-prefix-L511.bin'
env.update({
    'STRATA_STAGE_PIN': '0',
    'STRATA_PREFILL_CPU_SHARE': '0',
    'STRATA_INTEGRATION_TRACE': '1',
    'STRATA_STATE_HASH': '1',
    'STRATA_STATE_HASH_GDN': '1',
    'STRATA_STATE_DUMP_GDN': str(dump_path.resolve()),
    'STRATA_STATE_DUMP_GDN_AT': '511',
})
engine = StrataEngine(str(engine_path.resolve()), args, cwd=cfg.get('cwd'),
                      log=str((output_dir / 'engine.log').resolve()), env=env)
try:
    ids = [token for token in engine.generate(prompt, 1, {'temperature': 0}, threading.Event())
           if token is not None]
    result = {
        'prompt_tokens': len(prompt),
        'prompt_sha256': hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest(),
        'generated_ids': ids,
        'usage': dict(engine.last),
        'engine_args': args,
        'gdn_dump_path': str(dump_path.resolve()),
        'passed': len(ids) == 1,
    }
    (output_dir / 'workload.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('prompt_tokens', 'prompt_sha256', 'generated_ids', 'usage', 'passed')}))
    if not result['passed']:
        raise RuntimeError('generation count mismatch')
finally:
    engine.close()
