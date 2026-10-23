#!/usr/bin/env python3
"""Parse adaptive round/choice records from STRATA_TRACE_ADAPT service logs."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEDULE = re.compile(r'ADAPT schedule position=(\d+) round=(\d+) window=(\d+) accepted_rows=(\d+) accepted_total=(\d+)')
CHOICES = re.compile(r'ADAPT choices count=(\d+)(.*)')
SWAP = re.compile(r'(\d+):(\d+)>(\d+)')
result = {'scope': 'adaptive choices selected with STRATA_TRACE_ADAPT=1', 'arms': {}}
for arm in ('adaptive-cap8', 'delayed-control'):
    path = ROOT / arm / 'result/service.log'
    lines = path.read_text(errors='replace').splitlines()
    pending = None
    rows = []
    for line in lines:
        if 'ADAPT schedule ' in line:
            m = SCHEDULE.search(line)
            if not m: raise ValueError(f'unparsed schedule line: {line}')
            pending = dict(zip(('position','round','window','accepted_rows','accepted_total'), map(int,m.groups())))
        elif 'ADAPT choices ' in line:
            m = CHOICES.search(line)
            if not m: raise ValueError(f'unparsed choices line: {line}')
            choices = [{'layer':int(a),'incoming_expert':int(b),'outgoing_expert':int(c)} for a,b,c in SWAP.findall(m.group(2))]
            rows.append({'schedule':pending,'count':int(m.group(1)),'choices':choices})
            pending = None
    if pending is not None: raise ValueError(f'{arm}: schedule lacks choices record')
    result['arms'][arm] = {'trace_records':len(rows), 'rounds':rows,
                           'layer21_expert132_in': [r for r in rows if any(x['layer']==21 and x['incoming_expert']==132 for x in r['choices'])],
                           'layer21_expert132_out': [r for r in rows if any(x['layer']==21 and x['outgoing_expert']==132 for x in r['choices'])]}
out = ROOT / 'adapt-choice-trace.json'
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({a:{'trace_records':v['trace_records'],'layer21_expert132_in':v['layer21_expert132_in'],
                     'layer21_expert132_out':v['layer21_expert132_out']} for a,v in result['arms'].items()},indent=2))
