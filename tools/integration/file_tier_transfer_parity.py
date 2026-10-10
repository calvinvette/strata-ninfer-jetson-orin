"""Compare mapped expert reads with the whole-blob pread path."""
import argparse
import atexit
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
import statistics
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools'), str(ROOT / 'tools/integration')]
from conversation_cache_parity import load_tokenizer
from prepare_controls import exact_prompt
from owner_observations import summarize
from serve.frontend import ChatTemplate
from serve.server import StrataEngine, child_env

STATE_KEYS = ('L', 'gdn', 'ple', 'tail', 'dead', 'pooled', 'pooled_full', 'kv', 'ple_prev')


class TegraSampler:
    """Opt-in board-rail sampler; request energy is system-level, never process-attributed."""
    _POWER = re.compile(r'([A-Z0-9_]+)\s+(\d+)mW(?:/(\d+)mW)?')
    _CPU_FREQ = re.compile(r'\d+%@([0-9]+)')
    _GPU = re.compile(r'GR3D_FREQ\s+(\d+)%?(?:@([0-9]+))?')
    _EMC = re.compile(r'EMC_FREQ\s+(\d+)%?(?:@([0-9]+))?')

    def __init__(self, path, interval_ms):
        self.path = path
        self.interval_ms = interval_ms
        self.samples = []
        self.lock = threading.Lock()
        self.proc = None
        self.thread = None
        self.file = None

    def start(self):
        try:
            self.proc = subprocess.Popen(['tegrastats', '--interval', str(self.interval_ms)],
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, bufsize=1)
        except FileNotFoundError:
            return False
        self.file = self.path.open('w', encoding='utf-8')
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        return True

    def _read(self):
        for raw in self.proc.stdout:
            now = time.monotonic()
            line = raw.rstrip('\n')
            row = {'monotonic_s': now, 'raw': line, 'power_mw': {}}
            for match in self._POWER.finditer(line):
                row['power_mw'][match.group(1)] = int(match.group(2))
            cpu = self._CPU_FREQ.findall(line)
            row['cpu_clock_mhz'] = [int(x) for x in cpu]
            gpu = self._GPU.search(line)
            if gpu:
                row['gr3d_utilization_percent'] = int(gpu.group(1))
                row['gr3d_clock_mhz'] = int(gpu.group(2)) if gpu.group(2) else None
            emc = self._EMC.search(line)
            if emc:
                row['emc_utilization_percent'] = int(emc.group(1))
                row['emc_clock_mhz'] = int(emc.group(2)) if emc.group(2) else None
            with self.lock:
                self.samples.append(row)
                self.file.write(json.dumps(row) + '\n')
                self.file.flush()

    def stop(self):
        if self.proc is None:
            return
        proc = self.proc
        self.proc = None
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        if self.thread:
            self.thread.join(timeout=2)
        if self.file:
            self.file.close()

    def summarize(self, start_s, end_s):
        with self.lock:
            points = list(self.samples)
        before = [x for x in points if x['monotonic_s'] <= start_s]
        inside = [x for x in points if start_s < x['monotonic_s'] < end_s]
        after = [x for x in points if x['monotonic_s'] >= end_s]
        bounded = ([before[-1]] if before else []) + inside + ([after[0]] if after else [])
        names = set.intersection(*(set(x['power_mw']) for x in bounded)) if len(bounded) >= 2 else set()
        energy_j = {}
        for name in names:
            area = 0.0
            for a, b in zip(bounded, bounded[1:]):
                dt = b['monotonic_s'] - a['monotonic_s']
                if dt <= 0:
                    continue
                left, right = max(start_s, a['monotonic_s']), min(end_s, b['monotonic_s'])
                if right <= left:
                    continue
                y0, y1 = a['power_mw'][name], b['power_mw'][name]
                yl = y0 + (y1 - y0) * (left - a['monotonic_s']) / dt
                yr = y0 + (y1 - y0) * (right - a['monotonic_s']) / dt
                area += (yl + yr) * 0.5 * (right - left) / 1000.0
            energy_j[name] = area
        window = [x for x in points if start_s <= x['monotonic_s'] <= end_s]
        cpu_clocks = [n for x in window for n in x.get('cpu_clock_mhz', [])]
        return {
            'scope': 'named tegrastats system rail sampled during request; includes unrelated system activity',
            'duration_s': end_s - start_s,
            'rail_energy_j_estimate': energy_j,
            'energy_method': 'trapezoid integration of each named rail first mW value at tegrastats sample-arrival times; rails are not additive',
            'cpu_clock_mhz_samples': len(cpu_clocks),
            'cpu_clock_mhz_min': min(cpu_clocks) if cpu_clocks else None,
            'cpu_clock_mhz_median': statistics.median(cpu_clocks) if cpu_clocks else None,
            'cpu_clock_mhz_max': max(cpu_clocks) if cpu_clocks else None,
            'gr3d_clock_mhz_samples': sum(x.get('gr3d_clock_mhz') is not None for x in window),
            'emc_clock_mhz_samples': sum(x.get('emc_clock_mhz') is not None for x in window),
            'gr3d_clock_mhz_supported': any(x.get('gr3d_clock_mhz') is not None for x in window),
            'emc_clock_mhz_supported': any(x.get('emc_clock_mhz') is not None for x in window),
        }


def process_counters(pid):
    """Read Linux process counters used for this one engine request."""
    root = Path('/proc') / str(pid)
    stat = (root / 'stat').read_text()
    tail = stat[stat.rfind(')') + 2:].split()  # fields start at stat field 3
    values = {'minor_faults': int(tail[7]), 'major_faults': int(tail[9])}
    try:
        io_text = (root / 'io').read_text()
    except (FileNotFoundError, PermissionError):
        io_text = ''
    for line in io_text.splitlines():
        key, _, value = line.partition(':')
        if key in ('rchar', 'read_bytes', 'syscr'):
            values[key] = int(value.strip())
    return values


def block_device_counters(path):
    """Read physical block reads for the filesystem holding one model artifact."""
    st = path.stat()
    major, minor = os.major(st.st_dev), os.minor(st.st_dev)
    stat_path = (Path('/sys/dev/block') / f'{major}:{minor}' / 'stat').resolve()
    fields = stat_path.read_text().split()
    # Linux block-stat field 3 is sectors read; the kernel reports 512-byte sectors.
    return {'device': stat_path.parent.name, 'major': major, 'minor': minor,
            'read_sectors': int(fields[2]), 'read_bytes': int(fields[2]) * 512}


def state_hashes(path):
    found = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if 'STATE_HASH L=' in line:
            fields = dict(re.findall(r'(\w+)=([0-9a-f,-]+)', line))
            if not set(STATE_KEYS) <= fields.keys():
                raise ValueError('incomplete persistent state fingerprint')
            found.append({key: fields[key] for key in STATE_KEYS})
    if len(found) != 1:
        raise ValueError(f'expected one completed-request state fingerprint, got {len(found)}')
    return found[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prompt-tokens', type=int, default=4096)
    parser.add_argument('--generated-tokens', type=int, default=64)
    parser.add_argument('--pairs', type=int, default=1)
    parser.add_argument('--seed', type=int, default=870126)
    parser.add_argument('--io-threads', type=int, default=8)
    parser.add_argument('--expert-cache', type=str,
                        help='override auto sizing to hold expert residency constant across paired arms')
    parser.add_argument('--tegrastats-energy', action='store_true',
                        help='sample Orin rails and clocks around each request; board-level, not process-attributed')
    parser.add_argument('--tegrastats-interval-ms', type=int, default=100)
    parser.add_argument('--resume', action='store_true', help='continue an incomplete output directory after a harness interruption')
    parser.add_argument('--run', action='store_true', help='otherwise print the planned exact prompt size only')
    args = parser.parse_args()
    if args.prompt_tokens < 512 or args.generated_tokens < 8 or args.pairs < 1:
        parser.error('require prompt >=512, generation >=8 and pairs >=1')
    if args.tegrastats_interval_ms < 100:
        parser.error('tegrastats interval must be at least 100 ms')
    if args.output.exists() != args.resume:
        parser.error('use a new output directory, or pass --resume for an existing one')

    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    tokenizer = load_tokenizer(Path(cfg['tokenizer']))
    template_path = Path(cfg['tokenizer']) / 'chat_template.jinja'
    template = ChatTemplate(template_path if template_path.exists() else ROOT / 'serve/chat_template.jinja')
    render = lambda text: tokenizer.encode(
        template.render([{'role': 'user', 'content': text}], enable_thinking=False), parse_special=True)
    prompt_text = exact_prompt(args.prompt_tokens, render)
    prompt = render(prompt_text)
    if len(prompt) != args.prompt_tokens:
        raise ValueError(f'formatted prompt has {len(prompt)} tokens, expected {args.prompt_tokens}')
    print(f'formatted prompt tokens: {len(prompt)}')
    if not args.run:
        return 0

    with args.engine.open('rb') as binary:
        binary_hash = hashlib.file_digest(binary, 'sha256').hexdigest()
    result_path = args.output / 'results.json'
    prompt_hash = hashlib.sha256(json.dumps(prompt, separators=(',', ':')).encode()).hexdigest()
    if args.resume:
        if not result_path.is_file():
            parser.error('resume directory has no results.json')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if (result.get('prompt_sha256') != prompt_hash or
                result.get('generated_tokens') != args.generated_tokens or
                result.get('planned_pairs') != args.pairs or result.get('seed') != args.seed or
                result.get('expert_cache') != args.expert_cache or result.get('io_threads') != args.io_threads or
                any(row.get('engine_sha256') != binary_hash for row in result.get('arms', []))):
            parser.error('resume inputs differ from the retained incomplete run')
    else:
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        result = {'scope': 'exact real-model prompt, randomized mapped-versus-pread file-tier transfer screen; screening only',
                  'prompt_tokens': len(prompt), 'prompt_sha256': prompt_hash,
                  'generated_tokens': args.generated_tokens, 'planned_pairs': args.pairs,
                  'io_threads': args.io_threads, 'expert_cache': args.expert_cache,
                  'seed': args.seed, 'arms': [], 'pair_comparisons': []}
    sampler = None
    if args.tegrastats_energy:
        sampler = TegraSampler(args.output / 'tegrastats-energy.jsonl', args.tegrastats_interval_ms)
        result['tegrastats_energy'] = {
            'enabled': sampler.start(), 'interval_ms': args.tegrastats_interval_ms,
            'scope': 'system rail and clock sampling; never process-attributed; rail values are separate and not additive'}
        atexit.register(sampler.stop)
    args_for = list(cfg['args'])
    pack_path = Path(args_for[args_for.index('--pack') + 1])
    disk_counter_path = pack_path / 'experts.bin'
    if not disk_counter_path.is_file():
        raise FileNotFoundError(f'expected packed expert file for block telemetry: {disk_counter_path}')
    for key, value in (('--max-context', str(max(args.prompt_tokens + args.generated_tokens, 8192))),
                       ('--prompt-cache', '6')):
        if key in args_for:
            args_for[args_for.index(key) + 1] = value
        else:
            args_for.extend([key, value])
    if args.expert_cache is not None:
        if '--expert-cache' in args_for:
            args_for[args_for.index('--expert-cache') + 1] = args.expert_cache
        else:
            args_for.extend(['--expert-cache', args.expert_cache])
    rng = random.Random(args.seed)
    modes = [('mapped', '0'), ('pread', '1')]
    orders = []
    for _ in range(args.pairs):
        order = list(modes)
        rng.shuffle(order)
        orders.append(order)
    for pair in range(args.pairs):
        order = orders[pair]
        pair_rows = []
        for label, io_prefetch in order:
            existing = next((row for row in result['arms']
                             if row.get('pair') == pair and row.get('name') == label), None)
            if existing is not None:
                pair_rows.append(existing)
                continue
            log = args.output / f'pair-{pair}-{label}.log'
            if log.exists():
                parser.error(f'incomplete arm log exists without a terminal result: {log}')
            env = child_env(cfg)
            env.update({'STRATA_STAGE_PIN': '0', 'STRATA_STATE_HASH': '1',
                        'STRATA_MTP_BATCH': '1', 'STRATA_PREFILL_CPU_SHARE': '0',
                        'STRATA_INTEGRATION_TRACE': '1', 'STRATA_IO_PREFETCH': io_prefetch,
                        'STRATA_IO_PF_THREADS': str(args.io_threads),
                        'STRATA_IO_PF_STAGE': '0', 'STRATA_IO_STATS': '1'})
            arm = {'pair': pair, 'name': label, 'io_prefetch': io_prefetch,
                   'staging': 'disabled', 'args': args_for,
                   'engine_sha256': binary_hash}
            engine = StrataEngine(str(args.engine.resolve()), args_for, cwd=cfg.get('cwd'),
                                  log=str(log), env=env)
            try:
                before = process_counters(engine.proc.pid)
                block_before = block_device_counters(disk_counter_path)
                request_start = time.monotonic()
                ids = [token for token in engine.generate(prompt, args.generated_tokens,
                       {'temperature': 0}, threading.Event()) if token is not None]
                request_end = time.monotonic()
                after = process_counters(engine.proc.pid)
                block_after = block_device_counters(disk_counter_path)
                arm.update(ids=ids, text=tokenizer.decode(ids), usage=dict(engine.last))
            finally:
                engine.close()
            arm['process_io_and_fault_deltas'] = {
                key: after[key] - before[key] for key in before.keys() & after.keys()}
            if sampler and result['tegrastats_energy']['enabled']:
                arm['board_telemetry_during_request'] = sampler.summarize(request_start, request_end)
            arm['host_block_device_reads_during_request'] = {
                'device': block_after['device'], 'major': block_after['major'],
                'minor': block_after['minor'],
                'read_bytes_delta': block_after['read_bytes'] - block_before['read_bytes'],
                'scope': 'whole host block device; includes unrelated reads and kernel readahead'}
            arm['state'] = state_hashes(log)
            owners = summarize(log.read_text(encoding='utf-8').splitlines())
            arm['owner_observations'] = owners
            arm['observed_allocation_bytes_by_device'] = owners['observed_allocation_bytes_by_device']
            arm['file_tier_summary_lines'] = [line for line in log.read_text(errors='replace').splitlines()
                if 'strata serve: file tier I/O this request:' in line]
            result['arms'].append(arm)
            pair_rows.append(arm)
            result_path.write_text(json.dumps(result, indent=2) + '\n')

        by_name = {row['name']: row for row in pair_rows}
        mapped, pread = by_name['mapped'], by_name['pread']
        failures = []
        if mapped['ids'] != pread['ids']:
            failures.append('generated token IDs differ')
        state_differences = [key for key in STATE_KEYS if mapped['state'][key] != pread['state'][key]]
        if state_differences:
            failures.append('persistent main-model state differs')
        result['pair_comparisons'].append({
            'pair': pair, 'order': [label for label, _ in order],
            'token_ids_equal': mapped['ids'] == pread['ids'],
            'persistent_state_equal': not state_differences,
            'differing_state_fields': state_differences, 'failures': failures,
            'mapped_ms': mapped['usage'].get('prompt_ms', 0) + mapped['usage'].get('decode_ms', 0),
            'pread_ms': pread['usage'].get('prompt_ms', 0) + pread['usage'].get('decode_ms', 0)})
        result_path.write_text(json.dumps(result, indent=2) + '\n')

    if sampler:
        sampler.stop()
        result['tegrastats_energy']['sample_count'] = len(sampler.samples)
        result['tegrastats_energy']['raw_samples'] = 'tegrastats-energy.jsonl'
    failures = sorted({failure for pair in result['pair_comparisons'] for failure in pair['failures']})
    result['summary'] = {}
    for label in ('mapped', 'pread'):
        arms = [row for row in result['arms'] if row['name'] == label]
        result['summary'][label] = {}
        for key in ('prompt_ms', 'decode_ms'):
            result['summary'][label]['median_' + key] = statistics.median(
                row['usage'][key] for row in arms)
        io_samples = [row['process_io_and_fault_deltas']['read_bytes'] for row in arms
                      if 'read_bytes' in row['process_io_and_fault_deltas']]
        result['summary'][label]['median_process_read_bytes'] = (
            statistics.median(io_samples) if len(io_samples) == len(arms) else None)
        result['summary'][label]['median_major_faults'] = statistics.median(
            row['process_io_and_fault_deltas'].get('major_faults', 0) for row in arms)
    result['comparison'] = {'all_pairs_passed': not failures, 'failures': failures}
    result['passed'] = not failures
    (args.output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    if failures:
        raise AssertionError('; '.join(failures))
    print('PASS: token IDs and persistent state match; both stage backing modes observed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
