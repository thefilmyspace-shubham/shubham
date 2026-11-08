"""Jalsara Diwali reel (9:16, 4K60). A-roll of the presenter speaking the Diwali script + B-roll cutaways.
Look = the approved Jalsara teaser v2/v3 system: footage in a rounded 3:4 window, warm terracotta background with line
arches, dreamy per-letter headlines above the window (never on faces), no beat pulses / shake / jitter.
Diwali layer: strings of twinkling fairy lights at the top, slow golden sparks, a warm 'Happy Diwali' end card.

  python3 diwali.py --base                         # base.mp4: every shot cropped to the 3:4 window, graded, concatenated
  python3 diwali.py --stills 1,10,30               # check frames -> stills/
  python3 diwali.py --scale 2 --start 0 --end 13 --out c0.mp4   # render a chunk (4 chunks in parallel, then concat)
Sources: $JALSARA_DIWALI_SRC (default ../../../jalsara_diwali) with src/ (first Drive folder) and src2/ (second folder).
"""
import argparse, math, os, random, subprocess, sys
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'tfs-promo', 'film'))
import film as F
from film import hexc, P, SP, R, rrect, text_w, Layer, clamp, prog, lerp, eo3, eo5, eio3, rad, lin

SRC = os.environ.get('JALSARA_DIWALI_SRC', os.path.join(os.path.dirname(REPO), 'jalsara_diwali'))
FD = os.path.join(REPO, 'tfs-promo', 'film', 'fonts')
TF = {k: skia.Typeface.MakeFromFile(os.path.join(FD, v)) for k, v in {
    'serif': 'PlayfairDisplay-Regular.ttf', 'serifb': 'PlayfairDisplay-SemiBold.ttf', 'serifi': 'PlayfairDisplay-Italic.ttf',
    'script': 'Allura-Regular.ttf', 'sans': 'InterTight-Medium.ttf', 'sansb': 'InterTight-SemiBold.ttf'}.items()}
_f = {}
def font(k, s):
    key = (k, round(s, 1))
    if key not in _f:
        f = skia.Font(TF[k], s); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True); f.setHinting(skia.FontHinting.kNone)
        _f[key] = f
    return _f[key]

W, H, FPS = 1080, 1920, 60
CREAM, GOLD, DEEP = '#F6EBDD', '#E9C48E', '#1C0E09'
WIN = (60, 430, 960, 1280)                 # x, y, w, h (3:4)
RAD = 44

# ---------------- edit decision list ----------------
# A-roll lines in script order: (key, file, src_in, src_out, crop=(centre_y_frac, height_frac))
AROLL = [
    ('L1', 'src2/IMG_1124.MOV', 0.40, 5.50, (0.50, 0.75)),   # Hello dosto ... shubhkaamnaayein (only a 320p copy exists)
    ('L2', 'src2/IMG_1130.MOV', 0.00, 9.42, (0.52, 0.72)),   # Iss Diwali agar aap soch rahe hain ... extra special
    ('L3', 'src2/IMG_1151.MOV', 3.42, 11.70, (0.45, 0.62)),  # Ek zaroori baat ... Padwa ho ya Bhai Dooj
    ('L4', 'src2/IMG_1136.MOV', 3.50, 12.55, (0.40, 0.75)),  # Project B final touches ... brand new interiors (exterior, VO)
    ('L5', 'src/COPY_4FE2.mov', 0.60, 7.42, (0.42, 0.75)),   # Ek aur exciting surprise ... naye menu ka pre-launch
    ('L6', 'src/IMG_1177.MOV', 0.62, 5.56, (0.42, 0.75)),    # first few logon mein ... introductory price
    ('L7', 'src2/IMG_1143.MOV', 0.42, 5.86, (0.47, 0.62)),   # Toh der kis baat ki ... Happy Diwali
]
# B-roll cutaways over the voice, in A-roll source time: (key, t0, t1, file, src_in, crop)
CUTAWAY = [
    ('L1', 2.30, 5.50, 'src/IMG_1043.MOV', 0.50, (0.45, 0.75)),   # arch + lamp
    ('L2', 4.55, 6.90, 'src/IMG_1052.MOV', 0.00, (0.55, 0.75)),   # set tables
    ('L3', 8.15, 10.45, 'src/IMG_1111.MOV', 0.40, (0.50, 0.75)),  # tables + food
    ('L4', 6.50, 8.20, 'src/IMG_1042.MOV', 0.50, (0.45, 0.75)),   # brand new interiors ...
    ('L4', 8.20, 9.90, 'src/IMG_1044.MOV', 0.40, (0.45, 0.75)),
    ('L4', 9.90, 11.40, 'src/IMG_1041.MOV', 0.50, (0.45, 0.75)),
    ('L4', 11.40, 12.55, 'src/IMG_1040.MOV', 0.60, (0.45, 0.75)),
    ('L5', 2.30, 4.10, 'src/IMG_1106.MOV', 1.00, (0.50, 1.00)),   # new menu: platter
    ('L5', 4.10, 5.60, 'src/IMG_1083.MOV', 1.00, (0.50, 0.75)),   # chaat
    ('L6', 1.95, 3.85, 'src/IMG_1064.MOV', 0.40, (0.55, 0.75)),   # palak
]
END_HOLD = 3.4

def build():
    lines, shots, t = {}, [], 0.0
    for key, f, a, b, crop in AROLL:
        lines[key] = (t, a, b)
        cuts = sorted([c for c in CUTAWAY if c[0] == key], key=lambda c: c[1])
        pos = a
        for (_, c0, c1, cf, cin, ccrop) in cuts:
            if c0 > pos: shots.append((t + pos - a, t + c0 - a, f, pos, crop))
            shots.append((t + c0 - a, t + c1 - a, cf, cin, ccrop)); pos = c1
        if pos < b: shots.append((t + pos - a, t + b - a, f, pos, crop))
        t += b - a
    return lines, shots, t
LINES, SHOTS, E = build()                  # E: end card starts
END = E + END_HOLD
CUTS = [s[0] for s in SHOTS[1:]]
def G(key, local):                          # global time of a moment in a line's source clock
    t0, a, _ = LINES[key]; return t0 + local - a

# ---------------- base: crop every shot to the window, grade, concatenate ----------------
def dims(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:stream_side_data=rotation',
                          '-of', 'default=nw=1', path], capture_output=True, text=True).stdout
    kv = dict(l.split('=') for l in out.split() if '=' in l)
    w, h = int(kv['width']), int(kv['height'])
    if abs(int(float(kv.get('rotation', 0)))) % 180 == 90: w, h = h, w
    return w, h
def crop_expr(path, cy, hf):
    fw, fh = dims(path)
    if fw > fh: ch = fh; cw = ch * 3 / 4
    else:
        ch = hf * fh; cw = ch * 3 / 4
        if cw > fw: cw = fw; ch = cw * 4 / 3
    cw, ch = int(cw) // 2 * 2, int(ch) // 2 * 2
    x0 = (fw - cw) // 2; y0 = int(clamp(cy * fh - ch / 2, 0, fh - ch))
    return f'crop={cw}:{ch}:{x0}:{y0}', fw

def base_cmd(out, S=2):
    ow, oh = int(WIN[2] * S), int(WIN[3] * S)
    ins, fl = [], []
    shots = SHOTS + [(E, END, SHOTS[-1][2], SHOTS[-1][3] + (SHOTS[-1][1] - SHOTS[-1][0]), SHOTS[-1][4])]
    for k, (a, b, f, sin, (cy, hf)) in enumerate(shots):
        d = b - a; path = os.path.join(SRC, f)
        ins += ['-ss', f'{sin:.3f}', '-t', f'{d + 0.1:.3f}', '-i', path]
        cr, fw = crop_expr(path, cy, hf)
        g = 'eq=contrast=1.04:saturation=1.08,colorbalance=rs=0.03:gs=0.01:bs=-0.035'
        if fw < 600: g = 'hqdn3d=2:2:3:3,' + g + ',unsharp=5:5:0.6'          # the 320p copy of the opener
        fl.append(f'[{k}:v]setpts=PTS-STARTPTS,fps={FPS},{cr},scale={ow}:{oh}:flags=lanczos,{g},'
                  f'tpad=stop_mode=clone:stop_duration={d:.3f},trim=duration={d:.4f},setpts=PTS-STARTPTS,format=yuv420p[v{k}]')
    fl.append(''.join(f'[v{k}]' for k in range(len(shots))) + f'concat=n={len(shots)}:v=1:a=0[out]')
    return ['ffmpeg', '-y', '-v', 'error'] + ins + ['-filter_complex', ';'.join(fl), '-map', '[out]', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out]

# ---------------- text engine: per-letter dreamy reveal (same as teaser v2) ----------------
def run_w(runs, sp): return sum(text_w(s, f, tr) for s, f, col, tr in runs) + sp * (len(runs) - 1)
def letters(c, runs, cx, y, t, t0, per=0.028, dur=0.55, sp=14, out_t=None, rise=16, blur=10, glow=False):
    total = run_w(runs, sp); x = cx - total / 2; i = 0
    oa, oy, ob = 1.0, 0.0, 0.0
    if out_t is not None:
        uo = eio3(prog(t, out_t, out_t + 0.35)); oa = 1 - uo; oy = -14 * uo; ob = 10 * uo
    if oa <= 0: return
    for (s, f, col, tr) in runs:
        for ch in s:
            u = eo3(prog(t, t0 + i * per, t0 + i * per + dur)); i += 1
            cw = f.measureText(ch)
            if u > 0 and ch != ' ':
                b = blur * (1 - u) + ob; h = f.getSize()
                with Layer(c, u * oa, (b, b), bounds=R(x - 40, y - h * 1.4 - 40, cw + 80, h * 1.9 + 80)):
                    if glow:
                        g = skia.Paint(AntiAlias=True, Color=hexc(GOLD, 0.45))
                        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
                        c.drawString(ch, x, y + rise * (1 - u) + oy, f, g)
                    c.drawString(ch, x, y + rise * (1 - u) + oy, f, P(col))
            x += cw + tr
        x += sp

# ---------------- headlines above the window, one per spoken beat ----------------
def sv(s, k=74): return (s, font('serifi', k), hexc(CREAM), 0)
def sr(s, k=96): return (s, font('serif', k), hexc(CREAM), 1)
def sc(s, k=140): return (s, font('script', k), hexc(GOLD), 0)
BEATS = [  # (line, local start, runs)
    ('L1', 0.45, [sv('Hello', 80), sc('dosto', 150)]),
    ('L1', 2.30, [sr('Happy'), sc('Deepawali', 150)]),
    ('L2', 0.05, [sv('celebrate with', 70), sc('family', 150)]),
    ('L2', 4.60, [sv('make it', 74), sc('extra special', 130)]),
    ('L3', 3.50, [sr('open', 96), sc('all festive days', 120)]),
    ('L3', 8.20, [sc('Padwa', 130), sv('to', 64), sc('Bhai Dooj', 130)]),
    ('L4', 3.65, [sr('Project'), sc('B', 170), sv('· final touches', 56)]),
    ('L4', 6.55, [sv('brand new', 74), sc('interiors', 140)]),
    ('L4', 10.10, [sv('a brighter', 74), sc('Diwali', 150)]),
    ('L5', 0.65, [sv('an exciting', 74), sc('surprise', 150)]),
    ('L5', 2.30, [sv('new menu', 74), sc('pre-launch', 140)]),
    ('L6', 0.65, [sv('be among', 74), sc('the first few', 124)]),
    ('L6', 1.95, [sv('special', 74), sc('intro price', 136)]),
    ('L7', 0.45, [sv('make', 74), sc('memories', 150)]),
    ('L7', 3.10, [sv('we’re waiting', 70), sc('for you', 140)]),
]
def fit(runs, maxw=960, sp=22):
    w = run_w(runs, sp)
    if w <= maxw: return runs
    k = maxw / w
    return [(s, font(_fk(f), f.getSize() * k), col, tr) for s, f, col, tr in runs]
def _fk(f):
    for k, v in TF.items():
        if f.getTypeface() == v: return k
    return 'serif'
HEADS = []
for i, (k, lt, runs) in enumerate(BEATS):
    a = G(k, lt)
    b = G(*BEATS[i + 1][:2]) - 0.1 if i + 1 < len(BEATS) else E - 0.2
    HEADS.append((a, b, fit(runs)))
def draw_heads(c, t):
    for (a, b, runs) in HEADS:
        if a - 0.01 <= t < b + 0.4:
            letters(c, runs, W / 2, 335, t, a, per=0.032, dur=0.65, sp=22, out_t=b, rise=22, blur=14)

def kicker(c, t):
    f = font('sans', 22); s = 'J A L S A R A   ·   R A T L A M'
    u = eo3(prog(t, 0.2, 1.0)) * (1 - eo3(prog(t, E - 0.2, E + 0.2)))
    if u > 0:
        with Layer(c, u * 0.75):
            F.text(c, s, W / 2, 185, f, hexc(CREAM), 'c', 1.5)
        L = 70 * u
        c.drawLine(W / 2 - 250, 177, W / 2 - 250 - L, 177, SP(hexc(GOLD, 0.6 * u), 1.5))
        c.drawLine(W / 2 + 250, 177, W / 2 + 250 + L, 177, SP(hexc(GOLD, 0.6 * u), 1.5))

# ---------------- background: warm glow, line arches, fairy lights, sparks ----------------
ORBS = [(random.Random(i).uniform(0, W), random.Random(i + 50).uniform(0, H), random.Random(i + 9).uniform(60, 220),
         random.Random(i + 3).uniform(0.15, 0.45), random.Random(i + 77).uniform(0, 6.28)) for i in range(14)]
_r = random.Random(11)
SPARKS = [(_r.uniform(0, W), _r.uniform(0, H + 200), _r.uniform(1.4, 3.2), _r.uniform(18, 46), _r.uniform(0, 6.28), _r.uniform(1.5, 3.5))
          for _ in range(46)]
def arch_path(cx, base_y, w, h):
    p = skia.Path(); r = w / 2
    p.moveTo(cx - r, base_y); p.lineTo(cx - r, base_y - h + r)
    p.arcTo(R(cx - r, base_y - h, w, w), 180, 180, False); p.lineTo(cx + r, base_y)
    return p
def string_pts(y0, sag, n, x0=-30, x1=W + 30, swing=0.0):
    pts = []
    for i in range(n):
        u = i / (n - 1); x = lerp(x0, x1, u)
        pts.append((x, y0 + sag * 4 * u * (1 - u) + swing * math.sin(u * math.pi)))
    return pts
def fairy_lights(c, t):
    ua = eo5(prog(t, 0.0, 1.4))
    for j, (y0, sag, n, ph) in enumerate([(52, 70, 15, 0.0), (30, 120, 19, 1.7)]):
        sw = 3 * math.sin(t * 0.6 + ph)
        pts = string_pts(y0, sag, 60, swing=sw)
        wire = skia.Path(); wire.moveTo(*pts[0])
        for p in pts[1:]: wire.lineTo(*p)
        meas = skia.PathMeasure(wire, False); Lw = meas.getLength(); seg = skia.Path()
        meas.getSegment(0, Lw * ua, seg, True)
        c.drawPath(seg, SP(hexc('#3A1E12', 0.9), 2))
        for i, (x, y) in enumerate(string_pts(y0, sag, n, swing=sw)):
            if i in (0, n - 1) or (i / (n - 1)) > ua: continue
            tw = 0.62 + 0.38 * math.sin(t * 2.1 + i * 1.9 + ph * 3)
            col = '#FFC874' if (i + j) % 3 else '#FFE3B0'
            c.drawCircle(x, y + 7, 36, skia.Paint(AntiAlias=True, Shader=rad(x, y + 7, 36, [hexc(col, 0.5 * tw), hexc(col, 0)])))
            c.drawCircle(x, y + 7, 6.0, P(hexc(col, 0.6 + 0.4 * tw)))
def sparks(c, t):
    for (x, y, r, sp, ph, fl) in SPARKS:
        yy = (y - sp * t) % (H + 200) - 100
        xx = x + 14 * math.sin(t * 0.5 + ph)
        a = (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * fl + ph))) * 0.55
        c.drawCircle(xx, yy, r * 3.2, skia.Paint(AntiAlias=True, Shader=rad(xx, yy, r * 3.2, [hexc('#FFD08A', a * 0.5), hexc('#FFD08A', 0)])))
        c.drawCircle(xx, yy, r * 0.7, P(hexc('#FFE7C2', a)))
def background(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 760, 1500, [hexc('#5A2A18'), hexc('#2C150D'), hexc(DEEP)], [0, 0.5, 1])))
    for (x, y, r, a, ph) in ORBS:
        xx = x + 30 * math.sin(t * 0.35 + ph); yy = (y - 18 * t) % (H + 400) - 200
        c.drawCircle(xx, yy, r, skia.Paint(AntiAlias=True, Shader=rad(xx, yy, r, [hexc('#FFB36B', a * 0.35), hexc('#FFB36B', 0)])))
    ua = eo5(prog(t, 0.0, 1.6))
    for i, (cx, w, h, al) in enumerate([(W / 2, 1040, 1580, 0.22), (W / 2, 1100, 1660, 0.12)]):
        pth = arch_path(cx, 1840 + 6 * math.sin(t * 0.4 + i), w, h)
        meas = skia.PathMeasure(pth, False); Lp = meas.getLength(); seg = skia.Path()
        meas.getSegment(Lp * (0.5 - 0.5 * ua), Lp * (0.5 + 0.5 * ua), seg, True)
        c.drawPath(seg, SP(hexc(GOLD, al), 2))
    sparks(c, t)
    fairy_lights(c, t)

# ---------------- footage window ----------------
def shot_at(t):
    for s in SHOTS:
        if s[0] <= t < s[1]: return s
    return SHOTS[-1]
def window(c, img, t, alpha=1.0, extra_blur=0.0, sc_extra=0.0):
    x, y, w, h = WIN
    a, b = (E, END) if t >= E else shot_at(t)[:2]
    push = 1.0 + 0.035 * eio3(prog(t, a, b if t < E else b)) + sc_extra   # one slow, smooth push per shot
    bl, lift = 0.0, 0.0                                                   # dreamy light-bloom across cuts
    for ct in CUTS:
        d = t - ct
        if -0.12 <= d < 0: q = (d + 0.12) / 0.12; bl, lift = 18 * q * q, 0.32 * q * q
        elif 0 <= d < 0.22: q = 1 - d / 0.22; bl, lift = 18 * q * q, 0.32 * q * q
    rr = skia.RRect.MakeRectXY(R(x, y, w, h), RAD, RAD)
    with Layer(c, 0.55 * alpha, (40, 40)):
        c.drawRRect(skia.RRect.MakeRectXY(R(x + 8, y + 30, w, h), RAD, RAD), P(hexc('#000000')))
    c.save(); c.clipRRect(rr, True)
    p = skia.Paint(); p.setAlphaf(alpha)
    if bl + extra_blur > 0.5: p.setImageFilter(skia.ImageFilters.Blur(bl + extra_blur, bl + extra_blur))
    c.save(); c.translate(x + w / 2, y + h / 2); c.scale(push, push); c.translate(-w / 2, -h / 2)
    c.drawImageRect(img, R(0, 0, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.restore()
    if lift > 0: c.drawRect(R(x, y, w, h), P(hexc('#FFE4C2', lift * alpha)))
    c.drawRect(R(x, y + h - 220, w, 220), skia.Paint(Shader=lin(0, y + h - 220, 0, y + h, [hexc('#0B0604', 0), hexc('#0B0604', 0.45 * alpha)])))
    c.restore()
    c.drawRRect(rr, SP(hexc(GOLD, 0.35 * alpha), 2))

# ---------------- end card ----------------
def end_card(c, t, img):
    u = eio3(prog(t, E, E + 0.6))
    window(c, img, t, alpha=1 - 0.72 * u, extra_blur=30 * u, sc_extra=-0.03 * u)
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 1000, 900, [hexc('#000000', 0.45 * u), hexc('#000000', 0.15 * u)])))
    cy = 1000
    kick = eo3(prog(t, E + 0.2, E + 0.9))
    if kick > 0:
        with Layer(c, kick * 0.85):
            F.text(c, 'J A L S A R A', W / 2, cy - 330, font('sans', 30), hexc(CREAM), 'c', 2)
            F.text(c, 'Hotel  ·  Restaurant  ·  Banquet', W / 2, cy - 278, font('serifi', 34), hexc(GOLD), 'c', 0.5)
    letters(c, [('Happy', font('serif', 128), hexc(CREAM), 1)], W / 2, cy - 40, t, E + 0.15, per=0.05, dur=0.8, rise=26, blur=16)
    letters(c, [('Diwali', font('script', 290), hexc(GOLD), 0)], W / 2 + 10, cy + 220, t, E + 0.5, per=0.05, dur=0.9, rise=30, blur=20, glow=True)
    letters(c, [('from the Jalsara family', font('serifi', 46), hexc(CREAM), 0.5)], W / 2, cy + 345, t, E + 1.0, per=0.02, dur=0.6, rise=12, blur=8)
    us = eo3(prog(t, E + 1.5, E + 2.1))
    if us > 0:
        c.drawLine(W / 2 - 160 * us, cy + 410, W / 2 + 160 * us, cy + 410, SP(hexc(GOLD, 0.5), 1.5))
        with Layer(c, us):
            F.text(c, 'open all festive days', W / 2, cy + 490, font('script', 72), hexc(GOLD), 'c', 0)
            F.text(c, 'R A T L A M', W / 2, cy + 560, font('sans', 24), hexc(CREAM), 'c', 1.5)

def render_frame(c, img, t):
    background(c, t)
    if t >= E:
        end_card(c, t, img)
    else:
        u_in = eo5(prog(t, 0.0, 0.7))
        window(c, img, t, alpha=u_in, sc_extra=0.04 * (1 - u_in))
        draw_heads(c, t)
    kicker(c, t)
    F.grain(c, t, 0.04)
    F.vignette(c, 0.4)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', action='store_true'); ap.add_argument('--out', default='diwali.mp4')
    ap.add_argument('--scale', type=float, default=2); ap.add_argument('--stills', default='')
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=END)
    a = ap.parse_args()
    basef = os.path.join(HERE, 'base.mp4')
    if a.base:
        subprocess.run(base_cmd(basef), check=True); return
    S = a.scale; OW, OH = int(W * S), int(H * S); bw, bh = int(WIN[2] * S), int(WIN[3] * S)
    surf = skia.Surface(OW, OH); c = surf.getCanvas()
    def frames(t0, t1):
        pr = subprocess.Popen(['ffmpeg', '-v', 'quiet', '-ss', f'{t0:.4f}', '-i', basef, '-t', f'{t1 - t0:.4f}', '-vf', f'scale={bw}:{bh}',
                               '-pix_fmt', 'rgba', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
        n = bw * bh * 4
        while True:
            buf = pr.stdout.read(n)
            if len(buf) < n: break
            yield np.frombuffer(buf, np.uint8).reshape(bh, bw, 4)
        pr.kill()
    def one(arr, t):
        img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)
        c.clear(hexc('#000000')); c.save(); c.scale(S, S); render_frame(c, img, t); c.restore()
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s); g = frames(t, t + 0.05); arr = next(g); g.close()
            skia.Image.fromarray(one(arr, t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'stills', f'{t:05.2f}.png'))
        return
    n0, n1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-x264-params', 'threads=2', a.out],
                           stdin=subprocess.PIPE)
    k = n0
    for arr in frames(n0 / FPS, n1 / FPS + 0.5):
        if k >= n1: break
        enc.stdin.write(one(arr, k / FPS).tobytes()); k += 1
    enc.stdin.close(); enc.wait()

if __name__ == '__main__':
    main()
