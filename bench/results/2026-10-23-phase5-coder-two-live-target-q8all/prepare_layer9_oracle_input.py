#!/usr/bin/env python3
"""Assemble the owner and parts files expected by the independent expert oracle."""
import argparse
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--capture',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();src=a.capture.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
for name in ('serial','batch'):
    (out/f'{name}.moe-owners.jsonl').write_bytes((src/f'{name}.owners.jsonl').read_bytes())
(out/'moe-parts.stmparts').write_bytes((src/'serial.parts.stmparts').read_bytes()+(src/'batch.parts.stmparts').read_bytes())
print(f'prepared oracle input: {out}')
