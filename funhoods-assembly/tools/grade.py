# Colour grade for the client's ride-on assembly clip (asked: "colour grade + a bit more brightness").
# 1) per-shot white balance: the white cloth is measured in each shot (low-saturation bright pixels on a few frames) and
#    the channel gains make it neutral -- the top-view shot is much warmer than the rest;
# 2) a brightening curve: the cloth goes from ~150 to ~220 (clean white, not clipped), blacks stay deep;
# 3) +6 % saturation so the yellow body pops while the hands stay natural (more looked neon / made skin too red);
# every shot is first brought to the same cloth level, so the bright top-view shot does not blow out.
# usage: python3 tools/grade.py <src> --stills <out dir> <t,t,...>     (before | current v2 | new grade, side by side)
#        python3 tools/grade.py <src> --filter                           (prints the ffmpeg filter graph for the whole clip)
import os, sys, json, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
SHOTS = [0.0, 6.2, 23.3, 31.783, 37.583, 41.9, 43.56]        # cuts (scene detection); the last shot is the logo card
CURVE = '0/0 0.12/0.13 0.45/0.645 0.59/0.85 0.85/0.965 1/1'   # cloth 150 -> ~218, soft top so yellow does not go neon
CLOTH_IN = 150.0                                               # every shot's cloth is first brought to this level
V2 = 'eq=gamma=1.10:brightness=0.025:saturation=1.04'
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'funhoods-target-blaster', 'fonts', 'Inter-ExtraBold.ttf')

def frame(src, t, vf=None):
    a = ['ffmpeg', '-v', 'error', '-ss', '%.3f' % t, '-i', src, '-frames:v', '1'] + (['-vf', vf] if vf else []) + ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    raw = subprocess.run(a, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(3840, 2160, 3)

def wb_gains(src, a, b):
    """channel gains that make the cloth neutral in shot [a, b)"""
    px = []
    for t in np.linspace(a + 0.3, b - 0.3, 4):
        f = frame(src, t)[::8, ::8].reshape(-1, 3).astype(float)
        sat = f.max(1) - f.min(1); m = (sat < 40) & (f.mean(1) > 110)
        px.append(f[m])
    c = np.median(np.concatenate(px), 0); g = c.mean() / c; g = g / g[1]   # neutral cloth: keep green, move red / blue
    k = np.clip(CLOTH_IN / (c * g).mean(), 0.8, 1.15)                    # same exposure in every shot (top view is brighter)
    return g * k

def shot_filter(g):
    return ('colorchannelmixer=rr=%.4f:gg=%.4f:bb=%.4f,curves=master=\'%s\',eq=saturation=1.06'
            % (g[0], g[1], g[2], CURVE))

def gains_all(src):
    cache = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grade_gains.json')
    if os.path.exists(cache): return json.load(open(cache))
    gs = [list(wb_gains(src, a, b)) if i < len(SHOTS) - 2 else [1, 1, 1] for i, (a, b) in enumerate(zip(SHOTS, SHOTS[1:]))]
    json.dump(gs, open(cache, 'w'), indent=1); return gs

def full_graph(src):
    """split the clip at the cuts, grade each shot with its own white balance, join again"""
    gs = gains_all(src); n = len(gs); parts = []
    for i, (a, b) in enumerate(zip(SHOTS, SHOTS[1:])):
        parts.append('[s%d]trim=start=%.3f:end=%.3f,setpts=PTS-STARTPTS,%s[g%d]' % (i, a, b, shot_filter(gs[i]) if i < n - 1 else 'null', i))
    return '[0:v]split=%d%s;' % (n, ''.join('[s%d]' % i for i in range(n))) + ';'.join(parts) + ';' + ''.join('[g%d]' % i for i in range(n)) + 'concat=n=%d:v=1:a=0[graded]' % n

if __name__ == '__main__':
    src = sys.argv[1]
    if sys.argv[2] == '--filter': print(full_graph(src)); sys.exit()
    out, ts = sys.argv[3], [float(x) for x in sys.argv[4].split(',')]
    os.makedirs(out, exist_ok=True); gs = gains_all(src); print('gains per shot', np.round(gs, 3).tolist())
    fo = ImageFont.truetype(FONT, 34); rows = []
    for t in ts:
        i = max(k for k, c in enumerate(SHOTS) if c <= t)
        cols = [('BEFORE', frame(src, t)), ('ABHI (v2)', frame(src, t, V2)), ('NAYA GRADE', frame(src, t, shot_filter(gs[i])))]
        row = Image.new('RGB', (3 * 600 + 40, 1066 + 60), 'white'); d = ImageDraw.Draw(row)
        for k, (lbl, f) in enumerate(cols):
            row.paste(Image.fromarray(f).resize((600, 1066), Image.LANCZOS), (10 + k * 610, 60)); d.text((10 + k * 610 + 300, 30), lbl, font=fo, fill=(200, 20, 30) if k == 2 else (40, 40, 40), anchor='mm')
        row.save(os.path.join(out, 'compare_%05.1f.jpg' % t), quality=92); rows.append(row)
        f = frame(src, t, shot_filter(gs[i])).astype(float); s_ = f.reshape(-1, 3); sat = s_.max(1) - s_.min(1); m = (sat < 40) & (s_.mean(1) > 110)
        print('t=%.1f graded cloth RGB %s  p99 %.0f  clipped %.2f%%' % (t, np.median(s_[m], 0).round(0), np.percentile(f, 99), 100 * (f >= 254).mean()))
