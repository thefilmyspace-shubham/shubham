"""Jalsara 'Project B' teaser v3: only the opening line is spoken, then a clean visual edit (music added on Instagram).
Reuses the v2 look (rounded 3:4 window, arches background, per-letter text).
  python3 teaser3.py --base | --scale 2 --out t.mp4 [--start --end] | --stills t1,t2
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import teaser as T
import teaser2 as T2
from teaser2 import font, hexc, CREAM, GOLD

HOOK = (50.00, 52.70)
# montage shots (src_in, dur, b&w) — each fully inside one camera shot of the interview, no on-screen titles
MONT = [(2.36, 0.60, True), (0.03, 0.55, True), (0.96, 0.58, True),       # legacy flashes
        (22.20, 1.15, False),                                            # father close-up
        (12.80, 1.15, False),                                            # both, wide
        (40.10, 1.15, False),                                            # son, window light
        (34.70, 1.10, False),                                            # father
        (48.45, 1.15, False),                                            # son smiling
        (44.10, 1.10, False),                                            # both
        (62.70, 1.12, False)]                                            # son, last look
E = T.E                                                                   # 12.45: end card
def build():
    segs = [(0.0, HOOK[1] - HOOK[0], HOOK[0], False, 0.0, 'b1')]
    t = HOOK[1] - HOOK[0]
    total = sum(d for _, d, _ in MONT); k = (E - t) / total             # fit the montage exactly up to the end card
    for i, (src, d, bw) in enumerate(MONT):
        dd = d * k; segs.append((t, t + dd, src, bw, 0.0, f'm{i}')); t += dd
    last = MONT[-1]
    segs.append((E, T.END, last[0] + last[1] * k - 0.02, False, 0.0, 'end'))
    return segs
SEGS = build()
CUTS = [s[0] for s in SEGS[1:]]

# patch the v2 renderer to this edit
T2.SEGS = SEGS; T.SEGS = SEGS; T.CUTS = CUTS
T2.CAPS2 = [c for c in T2.CAPS2 if c[0] < SEGS[0][1]]                   # hook captions only
def seg_start(i): return SEGS[i][0]
m = SEGS[1:-1]
T2.HEADS = [
    (0.12, m[0][0] - 0.10, [('Project', font('serif', 96), hexc(CREAM), 1), ('B', font('script', 170), hexc(GOLD), 0)]),
    (m[0][0] + 0.05, m[4][0] - 0.12, [('since', font('script', 120), hexc(GOLD), 0), ('1990', font('serif', 110), hexc(CREAM), 2)]),
    (m[4][0] + 0.05, m[6][0] - 0.12, [('ten years', font('serifi', 74), hexc(CREAM), 0), ('in the making', font('script', 118), hexc(GOLD), 0)]),
    (m[6][0] + 0.05, m[8][0] - 0.12, [('for', font('script', 130), hexc(GOLD), 0), ('Ratlam', font('serif', 104), hexc(CREAM), 1)]),
    (m[8][0] + 0.05, m[9][0] - 0.10, [('a whole new', font('serifi', 74), hexc(CREAM), 0), ('experience', font('script', 128), hexc(GOLD), 0)]),
    (m[9][0] + 0.05, E - 0.15, [('what’s', font('serifi', 82), hexc(CREAM), 0), ('next?', font('script', 150), hexc(GOLD), 0)]),
]

if __name__ == '__main__':
    import argparse, subprocess
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', action='store_true')
    a, rest = ap.parse_known_args()
    if a.base:
        subprocess.run(T2.base_cmd(os.path.join(HERE, 'base2.mp4')), check=True)
    else:
        sys.argv = [sys.argv[0]] + rest
        T2.main()
