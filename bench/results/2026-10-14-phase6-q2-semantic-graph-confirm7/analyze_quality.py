#!/usr/bin/env python3
"""Apply the deterministic task rubric to all four held-out quality runs."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'run' / 'quality-full'
CONDITIONS = ('captured-mtp0', 'eager-mtp0', 'captured-mtp2', 'eager-mtp2')


def main():
    report = {'scope': 'one full-task Q2_0 quality check per graph × MTP condition; same exact 512-token semantic prompt; 512-token generation allowance', 'conditions': {}}
    hashes = set()
    for condition in CONDITIONS:
        directory = ROOT / condition
        data = json.loads((directory / 'results.json').read_text())
        supervisor = json.loads((directory / 'supervisor' / 'result.json').read_text())
        checks = data.get('checks', [])
        if len(checks) != 1:
            raise ValueError(f'{condition}: expected one quality response')
        row = checks[0]
        response = row['response']
        content = response['choices'][0]['message']['content']
        finish = response['choices'][0].get('finish_reason')
        lowered = content.lower()
        words = re.findall(r"\b[\w'-]+\b", content)
        rubric = {
            'natural_stop': finish == 'stop',
            'starts_with_memory_controller': content.startswith('Memory controller:'),
            'at_least_200_words': len(words) >= 200,
            'scan_code': 'scan code' in lowered,
            'input_path': 'input' in lowered and ('keyboard' in lowered or 'usb' in lowered),
            'fetch_decode_execute': all(x in lowered for x in ('fetch', 'decod', 'execut')),
            'binary': 'binary' in lowered,
            'RAM': 'ram' in lowered,
            'output_path': any(x in lowered for x in ('display', 'screen', 'monitor')),
            'storage': any(x in lowered for x in ('storage', 'ssd', 'drive')),
            'exact_arithmetic': re.search(r'17\s*[x×*]\s*19\s*=\s*323', content) is not None,
        }
        digest = hashlib.sha256(content.encode()).hexdigest()
        hashes.add(digest)
        if supervisor.get('status') != 'pass' or supervisor.get('minimum_available_bytes', 0) < 6 * 1024**3 or supervisor.get('minimum_admission_available_bytes', 0) < 3 * 1024**3:
            raise ValueError(f'{condition}: supervisor or memory floor failed')
        report['conditions'][condition] = {
            'finish_reason': finish, 'completion_tokens': response.get('usage', {}).get('completion_tokens'),
            'word_count': len(words), 'answer_sha256': digest, 'rubric': rubric,
            'rubric_pass': all(rubric.values()), 'supervisor': supervisor['status'],
            'minimum_host_gib': supervisor['minimum_available_bytes'] / 1024**3,
            'minimum_admission_gib': supervisor['minimum_admission_available_bytes'] / 1024**3,
            'elapsed_s': row['elapsed_s'],
        }
    report['unique_answer_hashes'] = len(hashes)
    report['all_rubrics_pass'] = all(x['rubric_pass'] for x in report['conditions'].values())
    report['all_supervisors_pass'] = all(x['supervisor'] == 'pass' for x in report['conditions'].values())
    report['minimum_host_gib'] = min(x['minimum_host_gib'] for x in report['conditions'].values())
    report['minimum_admission_gib'] = min(x['minimum_admission_gib'] for x in report['conditions'].values())
    (HERE / 'quality-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
