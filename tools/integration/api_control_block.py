"""Own one loopback server for a measured block, inside run_control's group."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error

from benchmark_control import request


def check_port(port):
    import socket
    with socket.socket() as sock:
        # Match HTTPServer's reuse policy: TIME_WAIT is not an active listener.
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', port))


def require_streaming(metrics):
    resident = metrics.get('engine', {}).get('kv_resident')
    if not isinstance(resident, int) or isinstance(resident, bool) or resident <= 0:
        raise RuntimeError(f'unsupported streaming KV cell: actual kv_resident={resident!r}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--workloads', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variant', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--validate-api-only', action='store_true')
    parser.add_argument('--require-kv-streaming', action='store_true')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    base = 'http://127.0.0.1:' + str(cfg['port'])
    # Never adopt an existing listener as this block's owned engine.
    check_port(cfg['port'])
    cfg['log'] = str((args.output.parent / 'engine.log').resolve())
    cfg['env'] = {**cfg.get('env', {}), 'STRATA_TRACE': '1'}
    owned_config = args.output.parent / 'server-config.json'
    owned_config.write_text(json.dumps(cfg, indent=2) + '\n')
    server = subprocess.Popen([sys.executable, '-m', 'serve.server', '--engine', 'strata',
                               '--config', str(owned_config.resolve()), '--host', '127.0.0.1',
                               '--port', str(cfg['port'])], cwd=cfg['cwd'])
    try:
        deadline = time.monotonic() + 240
        while True:
            if server.poll() is not None:
                raise RuntimeError(f'server exited before readiness: {server.returncode}')
            try:
                # Bound each read too: a TCP listener can accept without answering.
                health = request(base, '/health', timeout=5)
                if health.get('model'):
                    break
            except (urllib.error.URLError, OSError):
                pass
            if time.monotonic() > deadline:
                raise TimeoutError('server readiness deadline')
            time.sleep(0.5)
        metrics = request(base, '/metrics', timeout=5)
        (args.output.parent / 'capabilities.json').write_text(
            json.dumps(metrics, indent=2) + '\n')
        if args.require_kv_streaming:
            require_streaming(metrics)
        if args.validate_api_only:
            command = [sys.executable, str(Path(__file__).with_name('validate_protocol.py')),
                       '--base-url', base, '--out', str(args.output.resolve())]
        else:
            command = [sys.executable, str(Path(__file__).with_name('benchmark_control.py')),
                       '--base-url', base, '--workloads', str(args.workloads.resolve()),
                       '--output', str(args.output.resolve()), '--variant', args.variant,
                       '--rounds', str(args.rounds), '--single-block', '--stream']
        return subprocess.call(command)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        # run_control owns cleanup of the entire group, including engine children.


if __name__ == '__main__':
    raise SystemExit(main())
