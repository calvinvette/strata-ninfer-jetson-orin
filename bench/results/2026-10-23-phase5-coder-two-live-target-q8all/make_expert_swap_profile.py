#!/usr/bin/env python3
"""Swap two experts' residency ranks for a narrow correctness intervention."""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.make_profile import read_profile, write_profile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base', type=Path, default=ROOT / 'data/expert-profile-coder.bin')
parser.add_argument('--layer', type=int, required=True, help='zero-based model layer')
parser.add_argument('--expert', type=int, required=True, help='expert to move up')
parser.add_argument('--swap-expert', type=int, required=True,
                    help='same-layer expert whose current rank will be exchanged')
parser.add_argument('--output', type=Path, required=True)
opts = parser.parse_args()
profile = read_profile(opts.base, n_expert=256)
moved = (opts.layer, opts.expert)
swapped = (opts.layer, opts.swap_expert)
try:
    moved_rank = profile.index(moved)
    swapped_rank = profile.index(swapped)
except ValueError as exc:
    raise SystemExit(f'base profile does not contain {moved} and {swapped}') from exc
profile[moved_rank], profile[swapped_rank] = profile[swapped_rank], profile[moved_rank]
write_profile(opts.output, profile, n_expert=256)
print(f'{opts.output}: moved={moved} rank={moved_rank}->{swapped_rank}; '
      f'swapped={swapped} rank={swapped_rank}->{moved_rank}; '
      f'sha256={hashlib.sha256(opts.output.read_bytes()).hexdigest()}')
