"""Cut a feathered face patch out of each 'mouth open' AI still so it can be faded over its base still (lip flap).
   python3 build_patches.py  -> ai/patch_*.png + ai/patches.json"""
import json, os
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); A = f'{HERE}/ai'
HINT = {'gesture_open': (0.12, 0.39), 'wide_wtalk': (0.085, 0.415)}                                    # face centre when the diff is noisy
PAIRS = [('wide2', 'wide_wtalk'), ('wide_gesture', 'gesture_open'), ('waiter', 'waiter_open'), ('close', 'close_open'), ('close', 'close_laugh'), ('delight', 'delight_open')]
out = {}
for base, var in PAIRS:
    a = Image.open(f'{A}/{base}.png').convert('RGB'); b = Image.open(f'{A}/{var}.png').convert('RGB').resize(a.size)
    W, H = a.size
    d = np.abs(np.asarray(a, float) - np.asarray(b, float)).mean(2)
    d = np.asarray(Image.fromarray(np.clip(d, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(W * 0.006)), float)
    ys, xs = np.where(d > 28)
    cx, cy = np.median(xs), np.median(ys); r = 0.16
    if var in HINT: cx, cy, r = HINT[var][0] * W, HINT[var][1] * H, 0.07
    near = (np.abs(xs - cx) < W * r) & (np.abs(ys - cy) < W * r)
    xs, ys = xs[near], ys[near]
    x0, x1, y0, y1 = np.percentile(xs, 1), np.percentile(xs, 99), np.percentile(ys, 1), np.percentile(ys, 99)
    pad = W * 0.035; x0 -= pad; x1 += pad; y0 -= pad; y1 += pad
    # align the variant to the base on the upper face (eyes/hair), which should not change between the two
    ga = np.asarray(a.convert('L'), float); gb = np.asarray(b.convert('L'), float)
    X0, X1, Y0, Y1 = int(max(60, x0)), int(min(W - 60, x1)), int(max(60, y0 - (y1 - y0) * 0.3)), int(min(H - 60, y0 + (y1 - y0) * 0.5))
    best = (1e18, 0, 0)
    for dy in range(-48, 49, 2):
        for dx in range(-48, 49, 2):
            e = np.abs(ga[Y0:Y1:2, X0:X1:2] - gb[Y0 - dy:Y1 - dy:2, X0 - dx:X1 - dx:2]).mean()
            if e < best[0]: best = (e, dx, dy)
    e0 = np.abs(ga[Y0:Y1:2, X0:X1:2] - gb[Y0:Y1:2, X0:X1:2]).mean()
    _, dx, dy = best; print('  align', var, 'shift', dx, dy, 'err', round(e0, 1), '->', round(best[0], 1))
    b = Image.fromarray(np.roll(np.asarray(b), (dy, dx), axis=(0, 1)))
    yy, xx = np.mgrid[0:H, 0:W]
    ex = ((xx - (x0 + x1) / 2) / ((x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / ((y1 - y0) / 2)) ** 2
    alpha = np.clip((1.0 - ex) / 0.45, 0, 1)                                  # soft elliptical edge
    bx0, bx1, by0, by1 = int(max(0, x0)), int(min(W, x1)), int(max(0, y0)), int(min(H, y1))
    patch = np.dstack([np.asarray(b), (alpha * 255).astype(np.uint8)])[by0:by1, bx0:bx1]
    Image.fromarray(patch, 'RGBA').save(f'{A}/patch_{var}.png')
    out[var] = {'base': base, 'x': bx0 / W, 'y': by0 / H, 'w': (bx1 - bx0) / W, 'h': (by1 - by0) / H}
    print(var, out[var])
json.dump(out, open(f'{A}/patches.json', 'w'), indent=1)
