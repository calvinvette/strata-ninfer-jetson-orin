#!/usr/bin/env python3
"""Swap Coder layer-1 expert 11 to the first residency rank for a local diagnostic."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.make_profile import read_profile, write_profile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=Path('data/expert-profile-coder.bin'))
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
profile = read_profile(args.base, n_expert=256)
try:
    rank = profile.index((1, 11))
except ValueError as exc:
    raise SystemExit('base profile does not contain model layer 1 / expert 11') from exc
profile[0], profile[rank] = profile[rank], profile[0]
write_profile(args.output, profile, n_expert=256)
digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
expected = '8a590044b65ae494e3462067cd76878f3b71ca23519c182ac4660d88c6d9f114'
if digest != expected:
    raise SystemExit(f'generated profile hash mismatch: {digest}')
print(f'{args.output}: {digest}')
