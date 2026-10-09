"""Exercise pressure admission, cancellation and bounded descendant cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from run_control import GIB, memory_snapshot, run


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def execute(self, source, **kwargs):
        return run([sys.executable, '-c', source], self.root / 'run',
                   lock_path=self.root / 'lock', interval_s=0.02, grace_s=0.1,
                   sample=kwargs.pop('sample', lambda: {'available_bytes': 10 * GIB,
                                                       'admission_available_bytes': 10 * GIB}), **kwargs)

    def test_prelaunch_refusal_does_not_start_child(self):
        result = self.execute('raise AssertionError("must not run")',
                              sample=lambda: {'available_bytes': 5 * GIB,
                                              'admission_available_bytes': 5 * GIB})
        self.assertEqual(result['status'], 'pressure_abort')
        self.assertFalse((self.root / 'run/stdout.txt').exists())
        self.assertEqual(json.loads((self.root / 'run/result.json').read_text())['status'], 'pressure_abort')

    def test_success_and_durable_samples(self):
        self.assertEqual(self.execute('print("control")')['status'], 'pass')
        self.assertIn('control', (self.root / 'run/stdout.txt').read_text())
        self.assertTrue((self.root / 'run/memory.jsonl').read_text())

    def test_nonzero_exit(self):
        result = self.execute('raise SystemExit(7)')
        self.assertEqual((result['status'], result['returncode']), ('fail', 7))

    def test_pressure_after_launch(self):
        calls = iter([10 * GIB, 5 * GIB])
        def sample():
            available = next(calls)
            return {'available_bytes': available, 'admission_available_bytes': available}
        result = self.execute('import time; time.sleep(60)', sample=sample)
        self.assertEqual(result['status'], 'pressure_abort')

    def test_timeout_kills_term_ignoring_descendant(self):
        marker = self.root / 'child.pid'
        source = ('import os, signal, time\n'
                  'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                  'pid = os.fork()\n'
                  'if pid == 0:\n'
                  f' open({str(marker)!r}, "w").write(str(os.getpid()))\n'
                  ' time.sleep(60)\n'
                  'else:\n'
                  ' time.sleep(60)\n')
        start = time.monotonic()
        result = self.execute(source, timeout_s=0.3)
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(result['reason'], 'timeout')
        pid = int(marker.read_text())
        status = Path(f'/proc/{pid}/stat')
        self.assertTrue(not status.exists() or status.read_text().split()[2] == 'Z')

    def test_lock_blocks_second_campaign(self):
        import fcntl
        with (self.root / 'lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(self.execute('raise AssertionError()')['status'], 'not_run')

    def test_cgroup_ancestor_is_limiting(self):
        proc = self.root / 'proc'
        (proc / 'self').mkdir(parents=True)
        (proc / 'meminfo').write_text('MemAvailable: 10485760 kB\nMemTotal: 20971520 kB\nSwapTotal: 1024 kB\nSwapFree: 512 kB\n')
        (proc / 'self/cgroup').write_text('0::/parent/leaf\n')
        cgroup = self.root / 'cgroup'
        (cgroup / 'parent/leaf').mkdir(parents=True)
        for node, limit in [(cgroup, 'max'), (cgroup / 'parent', str(7 * GIB)),
                            (cgroup / 'parent/leaf', 'max')]:
            (node / 'memory.max').write_text(limit)
            (node / 'memory.current').write_text(str(2 * GIB))
        result = memory_snapshot(proc, cgroup)
        self.assertEqual(result['admission_available_bytes'], 5 * GIB)
        self.assertEqual(result['available_bytes'], 10 * GIB)

    def test_floor_cannot_be_lowered(self):
        with self.assertRaises(ValueError):
            self.execute('pass', floor_bytes=GIB)

    def test_signal_preserves_partial_result_and_cleans_up(self):
        import signal
        output = self.root / 'signalled'
        source = ('import sys; sys.path.insert(0, sys.argv[1]); from run_control import run, GIB; '
                  'run([sys.executable, "-c", "import time; time.sleep(60)"], sys.argv[2], '
                  'interval_s=0.02, grace_s=0.1, lock_path=sys.argv[3], '
                  'sample=lambda: {"available_bytes": 10*GIB, "admission_available_bytes": 10*GIB})')
        supervisor = subprocess.Popen([sys.executable, '-c', source, str(Path(__file__).parent),
                                       str(output), str(self.root / 'signal-lock')])
        self.addCleanup(lambda: supervisor.poll() is None and supervisor.kill())
        deadline = time.monotonic() + 5
        while not (output / 'result.json').exists():
            if time.monotonic() > deadline:
                self.fail('supervisor did not launch')
            time.sleep(0.01)
        supervisor.send_signal(signal.SIGTERM)
        supervisor.wait(timeout=3)
        result = json.loads((output / 'result.json').read_text())
        self.assertEqual(result['status'], 'fail')
        self.assertIn('signal', result['reason'])


if __name__ == '__main__':
    unittest.main()
