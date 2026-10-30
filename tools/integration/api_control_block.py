"""Own one loopback server for a measured block, inside run_control's group."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error

from benchmark_control import request


TRACE_ENV_KEYS = (
    'STRATA_TRACE', 'STRATA_STATE_HASH', 'STRATA_STATE_HASH_GDN',
    'STRATA_INTEGRATION_TRACE', 'STRATA_ACCEPTED_PREFIX_TRACE',
    'STRATA_PROMPT_BOUNDARY_STATE_HASH', 'STRATA_REQUEST_RESET_STATE_HASH',
    'STRATA_PREFILL_STATE_HASH_AT',
)


def configure_trace_environment(config_env, inherited_env, no_trace, accepted_prefix_trace=False,
                                prompt_boundary_state_hash=False, request_reset_state_hash=False,
                                prefill_state_hash_at=None):
    """Build the environment the server and its engine child will inherit."""
    config_env = dict(config_env or {})
    inherited_env = dict(inherited_env)
    if no_trace:
        for key in TRACE_ENV_KEYS:
            if key == 'STRATA_ACCEPTED_PREFIX_TRACE' and accepted_prefix_trace:
                continue
            if key == 'STRATA_PROMPT_BOUNDARY_STATE_HASH' and prompt_boundary_state_hash:
                continue
            if key == 'STRATA_REQUEST_RESET_STATE_HASH' and request_reset_state_hash:
                continue
            if key == 'STRATA_PREFILL_STATE_HASH_AT' and prefill_state_hash_at:
                continue
            config_env.pop(key, None)
            inherited_env.pop(key, None)
    else:
        config_env['STRATA_TRACE'] = '1'
    inherited_env.update({str(key): str(value) for key, value in config_env.items()})
    return config_env, inherited_env


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
    parser.add_argument('--warmup-workloads', type=Path,
                        help='optional distinct workload set used only for the warmup request')
    parser.add_argument('--variant', choices=['baseline', 'candidate'], required=True)
    parser.add_argument('--rounds', type=int, default=1)
    parser.add_argument('--validate-api-only', action='store_true')
    parser.add_argument('--require-kv-streaming', action='store_true')
    parser.add_argument('--no-trace', action='store_true',
                        help='do not force STRATA_TRACE for timing-only API cells')
    parser.add_argument('--accepted-prefix-trace', action='store_true',
                        help='retain accepted-prefix state tracing while --no-trace disables full tracing')
    parser.add_argument('--prompt-boundary-state-hash', action='store_true',
                        help='retain one prompt-boundary fingerprint while --no-trace disables full tracing')
    parser.add_argument('--request-reset-state-hash', action='store_true',
                        help='retain one post-reset fingerprint while --no-trace disables full tracing')
    parser.add_argument('--prefill-state-hash-at',
                        help='comma-separated prompt token counts for compact prefill state captures')
    parser.add_argument('--state-hash', action='store_true',
                        help='enable final persistent-state fingerprints without enabling STRATA_TRACE')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    base = 'http://127.0.0.1:' + str(cfg['port'])
    # Never adopt an existing listener as this block's owned engine.
    check_port(cfg['port'])
    cfg['log'] = str((args.output.parent / 'engine.log').resolve())
    cfg['env'], server_env = configure_trace_environment(cfg.get('env', {}), os.environ,
                                                        args.no_trace, args.accepted_prefix_trace,
                                                        args.prompt_boundary_state_hash,
                                                        args.request_reset_state_hash,
                                                        args.prefill_state_hash_at)
    if args.prefill_state_hash_at:
        cfg['env']['STRATA_PREFILL_STATE_HASH_AT'] = args.prefill_state_hash_at
        server_env['STRATA_PREFILL_STATE_HASH_AT'] = args.prefill_state_hash_at
    if args.state_hash:
        cfg['env']['STRATA_STATE_HASH'] = '1'
        server_env['STRATA_STATE_HASH'] = '1'
    owned_config = args.output.parent / 'server-config.json'
    owned_config.write_text(json.dumps(cfg, indent=2) + '\n')
    server = subprocess.Popen([sys.executable, '-m', 'serve.server', '--engine', 'strata',
                               '--config', str(owned_config.resolve()), '--host', '127.0.0.1',
                               '--port', str(cfg['port'])], cwd=cfg['cwd'], env=server_env)
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
            if args.warmup_workloads is not None:
                command.extend(['--warmup-workloads', str(args.warmup_workloads.resolve())])
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
