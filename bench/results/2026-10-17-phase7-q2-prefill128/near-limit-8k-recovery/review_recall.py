#!/usr/bin/env python3
"""Independent marker and same-service recovery oracle for selected Q2 profile."""
import argparse, json
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--result',type=Path,required=True)
 p.add_argument('--workload',type=Path,required=True)
 p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 r=json.loads(a.result.read_text())
 w=json.loads(a.workload.read_text())['workloads'][0]
 answer=r.get('answer','')
 codes=w['expected_codes']
 positions=[answer.find(code) for code in codes]
 marker_pass=(all(answer.count(code)==1 for code in codes) and all(x>=0 for x in positions)
              and positions==sorted(positions))
 recovery=r.get('recovery',{}).get('response',{}).get('choices',[{}])[0].get('message',{}).get('content','')
 recovery_pass='RECOVERED' in recovery
 recall=r.get('recall',{}).get('response',{})
 usage=recall.get('usage',{})
 checks={'runner_status_pass':r.get('status')=='pass','configured_context':r.get('configured_context'),
         'prompt_tokens':usage.get('prompt_tokens'),'completion_tokens':usage.get('completion_tokens'),
         'expected_prompt_tokens':w['prompt_tokens'],'markers_once_in_order':marker_pass,
         'marker_positions':positions,'recovery_answer':recovery,'same_service_recovery':recovery_pass}
 passed=(checks['runner_status_pass'] and checks['configured_context']==8192 and
         checks['prompt_tokens']==7498 and checks['completion_tokens']>0 and marker_pass and recovery_pass)
 review={'overall_pass':passed,'checks':checks,'expected_codes':codes}
 a.output.write_text(json.dumps(review,indent=2)+'\n')
 print(json.dumps(review,indent=2))
 return 0 if passed else 1
if __name__=='__main__': raise SystemExit(main())
