#!/usr/bin/env python3
"""Create a pixel-grounded four-quadrant circle-count fixture without dependencies."""
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
W = H = 224
COLORS = {'red': (220, 35, 35), 'blue': (35, 80, 220),
          'green': (30, 175, 65), 'yellow': (245, 210, 35)}
counts = {'TL': 1, 'TR': 2, 'BL': 3, 'BR': 4}
quadrants = [((0, 0), 'red', [(56, 56)]),
             ((1, 0), 'blue', [(140, 42), (182, 82)]),
             ((0, 1), 'green', [(40, 145), (56, 184), (82, 145)]),
             ((1, 1), 'yellow', [(145, 145), (185, 145), (145, 185), (185, 185)])]
pixels = [[(255, 255, 255) for _ in range(W)] for _ in range(H)]
for (cx, cy), color, centers in quadrants:
    x0, y0 = cx * 112, cy * 112
    for y in range(y0 + 2, y0 + 110):
        for x in range(x0 + 2, x0 + 110):
            pixels[y][x] = COLORS[color]
    for x, y in centers:
        for yy in range(y - 13, y + 14):
            for xx in range(x - 13, x + 14):
                if (xx - x) ** 2 + (yy - y) ** 2 <= 13 ** 2:
                    pixels[yy][xx] = (0, 0, 0)
# White cross and border make quadrant boundaries explicit.
for y in range(H):
    for x in range(W):
        if x < 2 or y < 2 or x >= W - 2 or y >= H - 2 or 110 <= x < 114 or 110 <= y < 114:
            pixels[y][x] = (255, 255, 255)
raw = b''.join(b'\x00' + b''.join(bytes(px) for px in row) for row in pixels)
def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
(ROOT / 'fixture.png').write_bytes(png)
# Independent image oracle: count connected black components in the raster itself.
seen = set()
observed = {'TL': 0, 'TR': 0, 'BL': 0, 'BR': 0}
for sy in range(H):
    for sx in range(W):
        if pixels[sy][sx] != (0, 0, 0) or (sx, sy) in seen:
            continue
        stack = [(sx, sy)]; seen.add((sx, sy)); component = []
        while stack:
            x, y = stack.pop(); component.append((x, y))
            for nx, ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= nx < W and 0 <= ny < H and pixels[ny][nx] == (0,0,0) and (nx,ny) not in seen:
                    seen.add((nx,ny)); stack.append((nx,ny))
        xmid = sum(x for x,_ in component) / len(component)
        ymid = sum(y for _,y in component) / len(component)
        key = ('T' if ymid < H/2 else 'B') + ('L' if xmid < W/2 else 'R')
        observed[key] += 1
assert observed == counts, (observed, counts)
answer = f"TL={observed['TL']} TR={observed['TR']} BL={observed['BL']} BR={observed['BR']} SUM={sum(observed.values())}"
(ROOT / 'oracle.json').write_text(json.dumps({'width': W, 'height': H, 'quadrant_backgrounds': {'TL':'red','TR':'blue','BL':'green','BR':'yellow'}, 'black_circle_counts': observed, 'sum': sum(observed.values()), 'expected_exact_response': answer, 'oracle_basis': 'Four-connected component count of black pixels in the generated raster, classified by quadrant centroid; the counts are independently checked against the drawing specification.'}, indent=2) + '\n')
print(json.dumps({'fixture': str(ROOT/'fixture.png'), 'dimensions': [W,H], 'expected': answer}))
