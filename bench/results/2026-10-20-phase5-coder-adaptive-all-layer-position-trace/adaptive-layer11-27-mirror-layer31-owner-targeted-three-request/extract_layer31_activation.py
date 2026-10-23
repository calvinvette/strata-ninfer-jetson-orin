#!/usr/bin/env python3
"""Extract and validate the repeated layer-11 position-511 activation."""
import hashlib
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADER = struct.Struct('<8sIIIIQq8i')
LAYER = 31
POSITION = 511
WIDTH = 2560
EXPECTED = 3


def main():
    for arm in ('delayed-control', 'adaptive-cap8'):
        source = ROOT / arm / 'result' / 'verify-moe-input.bin'
        data = source.read_bytes()
        offset = 0
        rows = []
        while offset < len(data):
            if len(data) - offset < HEADER.size:
                raise ValueError(f'{source}: truncated input header')
            magic, version, layer, count, reserved, width, pos0, *tokens = HEADER.unpack_from(data, offset)
            offset += HEADER.size
            if magic != b'STMOINP1' or version != 1 or reserved != 0 or width != WIDTH:
                raise ValueError(f'{source}: invalid MoE input header')
            nbytes = count * width * 4
            if count < 1 or len(data) - offset < nbytes:
                raise ValueError(f'{source}: truncated MoE input payload')
            payload = data[offset:offset + nbytes]
            offset += nbytes
            if layer == LAYER and pos0 <= POSITION < pos0 + count:
                row = POSITION - pos0
                if tokens[row] != 271:
                    raise ValueError(f'{source}: unexpected token {tokens[row]} at position {POSITION}')
                activation = payload[row * WIDTH * 4:(row + 1) * WIDTH * 4]
                values = struct.unpack(f'<{WIDTH}f', activation)
                if not all(math.isfinite(value) for value in values):
                    raise ValueError(f'{source}: non-finite activation')
                rows.append(activation)
        if len(rows) != EXPECTED or any(row != rows[0] for row in rows[1:]):
            raise ValueError(f'{arm}: expected {EXPECTED} bit-identical layer-{LAYER} activations, got {len(rows)}')
        output = ROOT / f'{arm}-layer31-position511-activation.f32'
        output.write_bytes(rows[0])
        print(f'{arm}: {output.name} sha256={hashlib.sha256(rows[0]).hexdigest()} bytes={len(rows[0])}')


if __name__ == '__main__':
    main()
