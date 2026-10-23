#!/usr/bin/env python3
"""Move one Coder expert to the first static residency rank for a diagnostic."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.make_profile import read_profile, write_profile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=ROOT / 'data/expert-profile-coder.bin')
parser.add_argument('--layer', type=int, default=4, help='zero-based model layer')
parser.add_argument('--expert', type=int, default=218, help='expert ID within the pruned Coder model')
parser.add_argument('--output', type=Path, required=True)
opts = parser.parse_args()
profile = read_profile(opts.base, n_expert=256)
pair = (opts.layer, opts.expert)
try:
    rank = profile.index(pair)
except ValueError as exc:
    raise SystemExit(f'base profile does not contain layer {opts.layer} / expert {opts.expert}') from exc
profile[0], profile[rank] = profile[rank], profile[0]
write_profile(opts.output, profile, n_expert=256)
print(f'{opts.output}: layer={opts.layer} expert={opts.expert} prior_rank={rank} '
      f'sha256={hashlib.sha256(opts.output.read_bytes()).hexdigest()}')
