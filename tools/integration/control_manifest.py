"""Capture explicit build/artifact identities; never download or select models."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def capture(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        return {'command': command, 'returncode': result.returncode,
                'stdout': result.stdout, 'stderr': result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'command': command, 'status': 'unsupported', 'reason': str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--revision', required=True, help='revision represented by this source tree')
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--artifact', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; preserve prior identities')
    files = [args.binary, args.build / 'CMakeCache.txt'] + args.artifact
    identities = [{'path': str(p.resolve()), 'size_bytes': p.stat().st_size,
                   'sha256': digest(p)} for p in files]
    manifest = {'schema_version': 1, 'wall_time_s': time.time(), 'revision': args.revision,
                'source': str(args.source.resolve()), 'platform': platform.uname()._asdict(),
                'files': identities, 'clocks': 'dynamic; no clock changes by harness',
                'qualification': 'identity inventory only; no numerical/performance pass',
                'checks': [capture(command) for command in [
                    ['/usr/local/cuda/bin/nvcc', '--version'],
                    ['c++', '--version'], ['nvpmodel', '-q'],
                    ['jetson_clocks', '--show'], ['file', str(args.binary)],
                    ['/usr/local/cuda/bin/cuobjdump', '--list-elf', str(args.binary)]]],
                'counter_gaps': ['unique allocation/reservation bytes by owner',
                                 'graph pool allocation', 'request-scoped energy',
                                 'independent operator tolerance and persistent-state fixtures']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
