"""Diagnostic request windows in an explicit Nsight Systems SQLite export."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
from statistics import median


def summarize(db, start, end):
    rows = list(db.execute('''select k.start,k.end,s.value from CUPTI_ACTIVITY_KIND_KERNEL k
        join StringIds s on s.id=k.demangledName where k.end>? and k.start<?''', (start,end)))
    grouped = defaultdict(lambda: [0,0])
    intervals = []
    for a,b,name in rows:
        a,b = max(a,start),min(b,end)
        grouped[name][0] += b-a; grouped[name][1] += 1; intervals.append((a,b))
    summed = sum(v[0] for v in grouped.values())
    occupied = 0; last = start
    for a,b in sorted(intervals):
        occupied += max(0,b-max(a,last));last=max(last,b)
    return {'kernel_events':len(rows), 'sum_kernel_duration_ms':summed/1e6,
            'union_kernel_intervals_ms':occupied/1e6,
            'top_kernels':[{'name':n,'events':v[1],'duration_sum_ms':v[0]/1e6,
                            'fraction_of_kernel_duration_sum':v[0]/summed}
                           for n,v in sorted(grouped.items(),key=lambda x:x[1][0],reverse=True)[:10]]}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sqlite',type=Path,required=True)
    p.add_argument('--requests',type=Path,required=True)
    p.add_argument('--memory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    db=sqlite3.connect(a.sqlite.resolve().as_uri()+'?mode=ro',uri=True)
    origins=list(db.execute('select utcEpochNs from TARGET_INFO_SESSION_START_TIME'))
    if len(origins)!=1: raise ValueError('ambiguous session origin')
    offsets=[r['wall_time_s']-r['monotonic_s'] for r in
             map(json.loads,a.memory.read_text().splitlines())]
    offset=median(offsets); windows=[]
    for r in json.loads(a.requests.read_text())['checks']:
        if r['status']!='pass':raise ValueError('request did not pass workload checks')
        lo=round((r['request_start_monotonic_s']+offset)*1e9)-origins[0][0]
        hi=round((r['request_end_monotonic_s']+offset)*1e9)-origins[0][0]
        if hi<=lo:raise ValueError('invalid request window')
        nominal=summarize(db,lo,hi)
        if not nominal['kernel_events']:raise ValueError('no GPU kernels in request window')
        windows.append({'cell':r['cell'],'warmup':r['warmup'],
                        'client_duration_ms':(hi-lo)/1e6,'profile_start_ns':lo,'profile_end_ns':hi,
                        'nominal':nominal,'boundary_sensitivity_50ms':{
                            'contracted':summarize(db,lo+50_000_000,hi-50_000_000),
                            'expanded':summarize(db,lo-50_000_000,hi+50_000_000)}})
    result={'scope':'one profiled process; kernel-duration sums include concurrent streams and spin waits, not critical-path fractions or speedups',
            'alignment':'Nsight session UTC epoch plus median sampled wall/monotonic offset; no request NVTX marker; absolute alignment error not independently bounded',
            'sensitivity':'plus/minus 50ms boundaries are a sensitivity check, not a confidence bound',
            'sampled_wall_monotonic_offset_spread_ms':(max(offsets)-min(offsets))*1000,
            'windows':windows}
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')


if __name__=='__main__':main()
