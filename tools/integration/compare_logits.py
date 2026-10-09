"""Compare last headered CPU reference row to one raw Strata F32 row."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--strata', type=Path, required=True)
    parser.add_argument('--tokens', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    from control_manifest import digest
    header = np.frombuffer(args.reference.read_bytes()[:8], dtype='<i4')
    if len(header) != 2 or min(header) <= 0:
        raise ValueError('invalid reference header')
    vocabulary, rows = map(int, header)
    ids = [int(token) for token in args.tokens.split(',')]
    if rows != len(ids):
        raise ValueError('reference row count does not match explicit input ids')
    ref = np.frombuffer(args.reference.read_bytes()[8:], dtype='<f4')
    actual = np.frombuffer(args.strata.read_bytes(), dtype='<f4')
    if ref.size != vocabulary * rows or actual.size != vocabulary:
        raise ValueError('truncated, extra or wrong-vocabulary logit rows')
    ref = ref.reshape(rows, vocabulary)[-1].astype(np.float64)
    actual = actual.astype(np.float64)
    if not np.isfinite(ref).all() or not np.isfinite(actual).all():
        raise ValueError('nonfinite logits')
    def logprob(values):
        maximum = values.max()
        return values - maximum - np.log(np.exp(values - maximum).sum())
    a, b = logprob(ref), logprob(actual)
    top = int(ref.argmax())
    result = {'tokens': ids, 'reference_rows': rows, 'vocabulary': vocabulary,
              'reference_argmax': top, 'strata_argmax': int(actual.argmax()), 'finite_logits': True,
              'max_abs_logit_difference': float(np.abs(ref - actual).max()),
              'rms_logit_difference': float(np.sqrt(np.mean((ref - actual)**2))),
              'reference_top_logprob': float(a[top]), 'strata_reference_top_logprob': float(b[top]),
              'kl_reference_to_strata': float((np.exp(a) * (a - b)).sum()),
              'reference_sha256': digest(args.reference), 'strata_sha256': digest(args.strata),
              'qualification': 'diagnostic only; argmax agreement is not numerical parity; no whole-model tolerance adopted',
              'scope': 'raw four-token prefix, CPU oracle vs native Strata, n_ctx=256, final reference position'}
    if args.output.exists():
        parser.error('preserve earlier comparison; use a new output path')
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
