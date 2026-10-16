#!/usr/bin/env python3
"""Prepare shorter-arriving Q2_0 requests to exercise batch-slot yielding."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from tools.conversation_cache_parity import load_tokenizer
from serve.frontend import ChatTemplate

OUT = Path(__file__).resolve().parent
BASE = ROOT / 'bench/results/2026-10-15-phase7-q2-concurrency4'
TARGETS = [1024, 768, 512, 256]
MARKERS = ['ALPHA-ORBIT-731', 'COBALT-HARBOR-284', 'VELVET-COPPER-956', 'MAPLE-EMBER-517']


def main():
    cfg = json.loads((BASE / 'config.json').read_text())
    tokenizer_path = Path(cfg['tokenizer'])
    tokenizer = load_tokenizer(tokenizer_path)
    template = ChatTemplate(tokenizer_path / 'chat_template.jinja')
    workloads = []
    for index, (target, marker) in enumerate(zip(TARGETS, MARKERS), 1):
        instruction = f'After the context, reply with the exact code {marker} and no other text.'
        best = None
        for filler_words in range(target * 2 + 100):
            content = ('red ' * filler_words) + '\n' + instruction
            messages = [{'role': 'user', 'content': content}]
            count = len(tokenizer.encode(template.render(messages, enable_thinking=False), parse_special=True))
            if best is None or abs(count - target) < abs(best[0] - target):
                best = (count, messages)
            if count == target:
                break
            if count > target:
                break
        count, messages = best
        workloads.append({
            'cell': f'stagger-{index}-{count}-tokens', 'prompt_tokens': count,
            'generate_tokens': 16, 'expected_code': marker, 'messages': messages,
            'chat_template_kwargs': {'enable_thinking': False},
        })
    config = dict(cfg)
    config['port'] = 18781
    config['parallel'] = 4
    config['model_name'] = 'Q2_0 4-slot staggered-prompt occupancy diagnostic'
    (OUT / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    (OUT / 'workloads.json').write_text(json.dumps({'workloads': workloads}, indent=2) + '\n')
    warmup = json.loads((BASE / 'warmup-512.json').read_text())
    (OUT / 'warmup.json').write_text(json.dumps(warmup, indent=2) + '\n')
    print(json.dumps({'prompt_tokens': [w['prompt_tokens'] for w in workloads],
                      'markers': MARKERS, 'parallel': 4, 'port': 18781}, indent=2))


if __name__ == '__main__':
    main()
