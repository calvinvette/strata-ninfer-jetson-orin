#!/usr/bin/env python3
"""Summarize the Q2_0 8K full-task MTP quality checks."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
CONDITIONS = ('mtp0', 'mtp2', 'mtp3', 'mtp4')


def main():
    report = {'scope': 'one full-task response per Q2_0 MTP setting; exact 8,192-token prompt; 16K context; 512-token allowance', 'conditions': {}}
    hashes = set()
    for condition in CONDITIONS:
        directory = HERE / condition
        result = json.loads((directory / 'results.json').read_text())
        supervisor = json.loads((directory / 'supervisor' / 'result.json').read_text())
        if len(result.get('checks', [])) != 1:
            raise ValueError(f'{condition}: expected one response')
        row = result['checks'][0]
        response = row['response']
        content = response['choices'][0]['message']['content']
        lowered = content.lower()
        words = re.findall(r"\b[\w'-]+\b", content)
        rubric = {
            'natural_stop': response['choices'][0].get('finish_reason') == 'stop',
            'starts_with_processor': content.lstrip().lower().startswith('processor'),
            'at_least_200_words': len(words) >= 200,
            'fetch_decode_execute': all(x in lowered for x in ('fetch', 'decod', 'execut')),
            'RAM': 'ram' in lowered,
            'binary_information': 'binary' in lowered,
            'input_and_output': 'input' in lowered and 'output' in lowered,
            'durable_storage': any(x in lowered for x in ('storage', 'ssd', 'drive')),
        }
        digest = hashlib.sha256(content.encode()).hexdigest()
        hashes.add(digest)
        if supervisor.get('status') != 'pass':
            raise ValueError(f'{condition}: supervisor did not pass')
        report['conditions'][condition] = {
            'prompt_tokens': response.get('usage', {}).get('prompt_tokens'),
            'completion_tokens': response.get('usage', {}).get('completion_tokens'),
            'word_count': len(words), 'finish_reason': response['choices'][0].get('finish_reason'),
            'answer_sha256': digest, 'rubric': rubric,
            'rubric_pass': all(rubric.values()), 'supervisor': supervisor['status'],
            'minimum_host_gib': supervisor['minimum_available_bytes'] / 1024**3,
            'minimum_admission_gib': supervisor['minimum_admission_available_bytes'] / 1024**3,
            'elapsed_s': row['elapsed_s'],
        }
    report['unique_answer_hashes'] = len(hashes)
    report['all_outputs_identical'] = len(hashes) == 1
    report['all_rubrics_pass'] = all(x['rubric_pass'] for x in report['conditions'].values())
    report['minimum_host_gib'] = min(x['minimum_host_gib'] for x in report['conditions'].values())
    report['minimum_admission_gib'] = min(x['minimum_admission_gib'] for x in report['conditions'].values())
    (HERE / 'quality-analysis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
