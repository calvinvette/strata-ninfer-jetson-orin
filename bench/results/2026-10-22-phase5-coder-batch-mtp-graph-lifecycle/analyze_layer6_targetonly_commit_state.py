#!/usr/bin/env python3
"""Compare committed layer-6 GDN state arrays in the targeted batch capture."""
from array import array
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run-layer6-targetonly-commit-state'
HEADER = struct.Struct('<8sIiqQQii')


def records(path):
    result = []
    with path.open('rb') as f:
        while True:
            raw = f.read(HEADER.size)
            if not raw:
                break
            if len(raw) != HEADER.size:
                raise ValueError(f'{path}: truncated state header')
            magic, version, layer, position, recurrent, count, token, slot = HEADER.unpack(raw)
            if magic != b'STGCMT1\0' or version != 1 or layer != 6:
                raise ValueError(f'{path}: unsupported commit record')
            payload = f.read(count * 4)
            if len(payload) != count * 4:
                raise ValueError(f'{path}: truncated state payload')
            values = array('f')
            values.frombytes(payload)
            result.append({'position': position, 'layer': layer, 'token': token, 'slot': slot,
                           'recurrent_floats': recurrent, 'values': values})
    return result


def metrics(reference, candidate, start, end):
    a, b = reference['values'][start:end], candidate['values'][start:end]
    changed = 0
    max_abs = 0.0
    sum_abs = 0.0
    sum_sq = 0.0
    norm_sq = 0.0
    for x, y in zip(a, b):
        d = abs(x - y)
        changed += d != 0.0
        max_abs = max(max_abs, d)
        sum_abs += d
        sum_sq += d * d
        norm_sq += x * x
    return {'changed_values': changed, 'total_values': len(a), 'max_abs': max_abs,
            'mean_abs': sum_abs / len(a) if a else 0.0,
            'relative_l2': (sum_sq / norm_sq) ** 0.5 if norm_sq else 0.0}


serial = {key: records(RUN / f'serial-{key}.stgcmt') for key in ('slot-0', 'slot-1')}
batch = records(RUN / 'batch.stgcmt')
by_slot = {}
for slot in sorted({item['slot'] for item in batch}):
    slot_records = [item for item in batch if item['slot'] == slot]
    segments = []
    current = []
    previous_position = -1
    for item in slot_records:
        if current and item['position'] < previous_position:
            segments.append(current)
            current = []
        current.append(item)
        previous_position = item['position']
    if current:
        segments.append(current)
    comparisons = []
    segment_summaries = []
    for segment_index, segment in enumerate(segments):
        boundary = next((item for item in segment if item['position'] == 67), segment[0])
        scored = []
        for prompt, controls in serial.items():
            ref = next((x for x in controls if x['position'] == boundary['position'] and
                        x['token'] == boundary['token']), None)
            if ref:
                scored.append((metrics(ref, boundary, 0, len(boundary['values']))['relative_l2'], prompt))
        mapping = min(scored)[1] if scored else None
        segment_comparisons = []
        if mapping:
            for b in segment:
                candidates = {prompt: next((x for x in controls
                                            if x['position'] == b['position'] and x['token'] == b['token']), None)
                              for prompt, controls in serial.items()}
                ref = candidates[mapping]
                if ref is None:
                    continue
                n = len(b['values'])
                r = b['recurrent_floats']
                nearest = {prompt: metrics(control, b, 0, n)['relative_l2']
                           for prompt, control in candidates.items() if control is not None}
                item = {
                    'position': b['position'], 'token': b['token'], 'slot': slot,
                    'relative_l2_by_serial_prompt': nearest,
                    'recurrent': metrics(ref, b, 0, r),
                    'convolution': metrics(ref, b, r, n),
                    'whole_state': metrics(ref, b, 0, n),
                }
                segment_comparisons.append(item)
                comparisons.append(item)
        segment_summaries.append({'segment': segment_index, 'record_count': len(segment),
                                  'prompt_mapping': mapping,
                                  'positions': [x['position'] for x in segment],
                                  'comparisons': segment_comparisons})
    by_slot[str(slot)] = {'segments': segment_summaries, 'comparisons': comparisons}

summary = {
    'model': 'Qwen3.8-Flash-Next-Coder-GGUF-IQ1_M',
    'hardware': 'Jetson AGX Orin, ARM64, CUDA 12.6',
    'layer': 6,
    'layer_role': 'GDN-state ordinal 5 (the first changed ordinal in the mapped prompt-0 sweep row)',
    'serial_record_counts': {key: len(value) for key, value in serial.items()},
    'batch_record_count': len(batch),
    'batch_rows': by_slot,
    'limits': ['Target-only diagnostic; no speed claim.',
               'The dump captures committed state after the named token position.',
               'Raw commit-state arrays remain local-only.'],
}
(ROOT / 'layer6-targetonly-commit-state-analysis.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'batch_record_count': len(batch), 'rows': {
    slot: [{'prompt': seg['prompt_mapping'], 'positions': seg['positions'],
           'comparisons': [{'position': x['position'], 'token': x['token'],
                            'recurrent_rel_l2': x['recurrent']['relative_l2'],
                            'conv_rel_l2': x['convolution']['relative_l2'],
                            'changed': x['whole_state']['changed_values']}
                           for x in seg['comparisons']]}
          for seg in value['segments']]
    for slot, value in by_slot.items()}}, indent=2))
