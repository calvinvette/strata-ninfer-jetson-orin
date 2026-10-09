"""Request-window estimates from named tegrastats rails, without summing rails."""
from datetime import datetime
import re


def rails_from_lines(lines):
    observations = []
    for line in lines:
        try:
            timestamp = datetime.strptime(line[:19], '%m-%d-%Y %H:%M:%S').timestamp()
        except ValueError:
            continue
        rails = {name: int(power) / 1000 for name, power in
                 re.findall(r'((?:VDD|VIN)_[A-Z0-9_]+) (\d+)mW/\d+mW', line)}
        if rails:
            observations.append({'wall_time_s': timestamp, 'rails_watts': rails})
    return observations


def window_energy(observations, start, end):
    """Piecewise-linear power integration, requiring samples bracketing both ends."""
    if end <= start:
        raise ValueError('positive request window required')
    if not observations or observations[0]['wall_time_s'] > start or observations[-1]['wall_time_s'] < end:
        return {'status': 'unsupported', 'reason': 'rail samples do not bracket the full request window'}
    energies = {}
    for left, right in zip(observations, observations[1:]):
        t0, t1 = left['wall_time_s'], right['wall_time_s']
        a, b = max(start, t0), min(end, t1)
        if b <= a:
            continue
        if t1 - t0 > 2.5:
            return {'status': 'unsupported', 'reason': 'rail sampling gap exceeds 2.5 seconds'}
        if left['rails_watts'].keys() != right['rails_watts'].keys():
            return {'status': 'unsupported', 'reason': 'rail schema changed inside request window'}
        for rail in left['rails_watts']:
            p0, p1 = left['rails_watts'][rail], right['rails_watts'][rail]
            pa = p0 + (p1 - p0) * (a - t0) / (t1 - t0)
            pb = p0 + (p1 - p0) * (b - t0) / (t1 - t0)
            energies[rail] = energies.get(rail, 0) + (pa + pb) * (b - a) / 2
    return {'status': 'estimated', 'joules_by_named_rail': energies,
            'scope': 'each named rail separately; no whole-board or summed-rail claim; includes prefill and decode',
            'method': 'linear integration of instantaneous mW; timestamps have one-second granularity'}
