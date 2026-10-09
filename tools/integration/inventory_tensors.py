"""Inventory explicit GGUF tensor headers without reading or copying weights."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gguf_reader import BLOCK_GEOMETRY, GGUFFile


def inventory(shards):
    records, metadata, seen = [], [], set()
    for path in shards:
        source = GGUFFile(path)
        if source.version != 3:
            raise ValueError('only the explicit GGUF v3 contract is supported')
        metadata.append({'path': str(path.resolve()), 'file_size_bytes': path.stat().st_size,
                         'version': source.version, 'data_start': source.data_start,
                         'model_fields': {k: v for k, v in source.metadata.items()
                                          if not k.startswith('tokenizer.') and isinstance(v, (str, int, float, bool))}})
        for tensor in source.tensors:
            if tensor.name in seen:
                raise ValueError(f'duplicate tensor across source shards: {tensor.name}')
            seen.add(tensor.name)
            geometry = BLOCK_GEOMETRY.get(tensor.type_name)
            size = tensor.expected_bytes()
            if size is None or any(d <= 0 for d in tensor.shape):
                raise ValueError(f'unknown codec geometry or invalid shape: {tensor.name} {tensor.type_name}')
            if source.data_start + tensor.offset + size > path.stat().st_size:
                raise ValueError(f'tensor extent exceeds source file: {tensor.name}')
            records.append({'source': str(path.resolve()), 'symbol': tensor.name,
                            'shape_fastest_dimension_first': tensor.shape,
                            'ggml_type_id': tensor.type_id, 'format': tensor.type_name,
                            'block_elements': geometry[0], 'block_bytes': geometry[1],
                            'represented_bytes': size})
    return {'schema_version': 1, 'scope': 'header/codec geometry only; no element-level numerical qualification',
            'source_metadata': metadata, 'tensors': records,
            'format_counts': dict(Counter(r['format'] for r in records))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shard', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('preserve previous inventory; output must be new')
    result = inventory(args.shard)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(len(result['tensors']), 'tensors', result['format_counts'])


if __name__ == '__main__':
    main()
