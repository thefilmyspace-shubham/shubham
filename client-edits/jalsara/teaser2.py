"""Jalsara 'Project B' teaser v2: dreamy, text-led.
9:16 canvas, interview inside a rounded 3:4 window (burned-in subtitles fall outside the window),
motion-graphic background (arches, light), elegant per-letter text animation. No beat pulses / shake.
  python3 teaser2.py --base          # base2.mp4 (window-sized shots)
  python3 teaser2.py --scale 2 --out t.mp4 [--start --end] | --stills t1,t2
"""
import argparse, math, os, random, subprocess, sys
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'film'))
import film as F
from film import hexc, P, SP, R, rrect, text_w, capc, Layer, Tx, clamp, prog, lerp, eo3, eo5, eio3, ei3, rad, lin
import teaser as T

FD = os.path.join(os.path.dirname(HERE), 'film', 'fonts')
TF = {k: skia.Typeface.MakeFromFile(os.path.join(FD, v)) for k, v in {
    'serif': 'PlayfairDisplay-Regular.ttf', 'serifb': 'PlayfairDisplay-SemiBold.ttf', 'serifi': 'PlayfairDisplay-Italic.ttf',
    'script': 'Allura-Regular.ttf', 'sans': 'InterTight-Medium.ttf', 'sansb': 'InterTight-SemiBold.ttf', 'sansl': 'InterTight-Light.ttf'}.items()}
_f = {}
def font(k, s):
    key = (k, round(s, 1))
    if key not in _f:
        f = skia.Font(TF[k], s); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True); f.setHinting(skia.FontHinting.kNone)
        _f[key] = f
    return _f[key]

W, H, FPS = 1080, 1920, 60
END, E = T.END, T.E
SEGS = T.SEGS
CREAM, GOLD, TERRA, DEEP = '#F6EBDD', '#E9C48E', '#C8643B', '#1C0E09'
WIN = (60, 430, 960, 1280)                # x, y, w, h  (3:4)
RAD = 44

# ---------------- base: crop each shot to 3:4 above the burned subtitles ----------------
def base_cmd(out, S=2):
    ow, oh = int(WIN[2] * S), int(WIN[3] * S)
    ins, fl = [], []
    ch = 2830; cw = int(round(ch * 3 / 4 / 2) * 2); x0 = (2160 - cw) // 2
    for k, (a, b, src, bw, ct, kind) in enumerate(SEGS):
        d = b - a
        ins += ['-ss', f'{src:.3f}', '-t', f'{(0.05 if kind == "end" else d + 0.05):.3f}', '-i', T.SRC]
        g = 'hue=s=0,eq=contrast=1.08:brightness=-0.01' if bw else 'eq=contrast=1.04:saturation=1.06,colorbalance=rs=0.03:gs=0.01:bs=-0.04'
        f = f'[{k}:v]setpts=PTS-STARTPTS,fps={FPS},crop={cw}:{ch}:{x0}:0,scale={ow}:{oh}:flags=lanczos,{g}'
        if kind == 'end': f += f',tpad=stop_mode=clone:stop_duration={d:.3f}'
        f += f',trim=duration={d:.4f},setpts=PTS-STARTPTS,format=yuv420p[v{k}]'
        fl.append(f)
    fl.append(''.join(f'[v{k}]' for k in range(len(SEGS))) + f'concat=n={len(SEGS)}:v=1:a=0[out]')
    return ['ffmpeg', '-y', '-v', 'error'] + ins + ['-filter_complex', ';'.join(fl), '-map', '[out]', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out]

# ---------------- text engine: per-letter dreamy reveal ----------------
def draw_str(c, s, x, y, f, col, track=0.0):
    for ch in s:
        c.drawString(ch, x, y, f, P(col)); x += f.measureText(ch) + track

def run_w(runs, sp):
    return sum(text_w(s, f, tr) for s, f, col, tr in runs) + sp * (len(runs) - 1)

def letters(c, runs, cx, y, t, t0, per=0.028, dur=0.55, sp=14, out_t=None, rise=16, blur=10, glow=False):
    """runs: [(text, font, colour, tracking)] laid out on one line centred at cx; each letter fades up + unblurs.
    out_t: start of a soft exit (blur + fade + drift up)."""
    total = run_w(runs, sp); x = cx - total / 2; i = 0
    oa = 1.0; oy = 0.0; ob = 0.0
    if out_t is not None:
        uo = eio3(prog(t, out_t, out_t + 0.35)); oa = 1 - uo; oy = -14 * uo; ob = 10 * uo
    if oa <= 0: return
    for (s, f, col, tr) in runs:
        for ch in s:
            u = eo3(prog(t, t0 + i * per, t0 + i * per + dur)); i += 1
            cw = f.measureText(ch)
            if u > 0 and ch != ' ':
                b = blur * (1 - u) + ob
                h = f.getSize()
                with Layer(c, u * oa, (b, b), bounds=R(x - 40, y - h * 1.4 - 40, cw + 80, h * 1.9 + 80)):
                    if glow:
                        g = skia.Paint(AntiAlias=True, Color=hexc(GOLD, 0.45))
                        g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
                        c.drawString(ch, x, y + rise * (1 - u) + oy, f, g)
                    c.drawString(ch, x, y + rise * (1 - u) + oy, f, P(col))
            x += cw + tr
        x += sp

def shadow_band(c, y0, y1, a=0.62):
    c.drawRect(R(WIN[0], y0, WIN[2], y1 - y0), skia.Paint(Shader=lin(0, y0, 0, y1, [hexc('#0B0604', 0), hexc('#0B0604', a)])))

# ---------------- captions (speech) inside the window bottom, over a soft shadow ----------------
WORDS2 = [  # same timings as teaser.CAP_T, softer wording: one script accent per line
    [('abhi', 0), ('toh', 0), ('main', 0)],
    [('reveal', 1), ('nahi', 0), ('karunga', 0)],
    [('1990', 1), ('mein…', 0)],
    [('toh', 0), ('woh', 0), ('sab', 0)],
    [('Project B', 1), ('laane', 0), ('wala', 0), ('hai', 0)],
    [('aur', 0), ('Ratlam', 1), ('walon', 0), ('ko', 0)],
    [('bahut', 0), ('hi', 0), ('maza', 1), ('aayega', 0)],
    [('pura', 0), ('naya', 0), ('experience', 1)],
    [('rahega', 0), ('unke', 0), ('liye', 0)],
    [('ki', 0), ('Jalsara', 1), ('mein', 0), ('naya', 0)],
    [('kya', 1), ('hone', 0), ('wala', 0), ('hai?', 0)],
]
CAPS2 = [(a, b, ws) for (a, b, _), ws in zip(T.CAP_T, WORDS2)]
def cap_runs(ws, size=52):
    out = []
    for w_, acc in ws:
        if acc: out.append((w_, font('script', size * 1.6), hexc(GOLD), 0))
        else: out.append((w_, font('sansb', size), hexc(CREAM), 0.5))
    return out
def draw_captions(c, t):
    y = WIN[1] + WIN[3] - 92
    for (a, b, ws) in CAPS2:
        if not (a - 0.05 <= t < b + 0.3): continue
        runs = cap_runs(ws)
        if run_w(runs, 14) > 860:
            runs = cap_runs(ws, 52 * 860 / run_w(runs, 14))
        nxt = [x for x in CAPS2 if x[0] > a]
        out_t = (nxt[0][0] - 0.12) if nxt and nxt[0][0] < b + 0.4 else b
        lw = run_w(runs, 14); ua = eo3(prog(t, a - 0.05, a + 0.25)) * (1 - eo3(prog(t, out_t, out_t + 0.35)))
        if ua > 0:
            with Layer(c, ua * 0.75, (34, 22)):
                rrect(c, W / 2 - lw / 2 - 40, y - 62, lw + 80, 92, 46, P(hexc('#0A0503')))
        letters(c, runs, W / 2, y, t, a, per=0.018, dur=0.38, sp=14, out_t=out_t, rise=10, blur=8)

# ---------------- headline zone (above the window) ----------------
HEADS = [  # (t_in, t_out, runs-builder)
    (0.10, None, 'projectb'), (None, None, 'since'), (None, None, 'ratlam'), (None, None, 'experience'), (None, None, 'next')]
def seg_t(name):
    for s in SEGS:
        if s[5] == name: return s[0], s[1]
def head_layout():
    m = [s for s in SEGS if s[5].startswith('m')]
    b2, b3, b4, b5 = seg_t('b2'), seg_t('b3'), seg_t('b4'), seg_t('b5')
    return [
        (0.12, m[0][0] - 0.1, [('Project', font('serif', 96), hexc(CREAM), 1), ('B', font('script', 170), hexc(GOLD), 0)]),
        (m[0][0] + 0.05, b2[0] - 0.08, [('since', font('script', 120), hexc(GOLD), 0), ('1990', font('serif', 110), hexc(CREAM), 2)]),
        (b2[0] + 0.05, b3[0] - 0.08, [('ten years', font('serifi', 74), hexc(CREAM), 0), ('in the making', font('script', 118), hexc(GOLD), 0)]),
        (b3[0] + 0.05, b4[0] - 0.08, [('for', font('script', 130), hexc(GOLD), 0), ('Ratlam', font('serif', 104), hexc(CREAM), 1)]),
        (b4[0] + 0.05, b5[0] - 0.08, [('a whole new', font('serifi', 74), hexc(CREAM), 0), ('experience', font('script', 128), hexc(GOLD), 0)]),
        (b5[0] + 0.05, E - 0.15, [('what’s', font('serifi', 82), hexc(CREAM), 0), ('next?', font('script', 150), hexc(GOLD), 0)]),
    ]
HEADS = head_layout()
def draw_heads(c, t):
    for (a, b, runs) in HEADS:
        if a - 0.01 <= t < b + 0.4:
            letters(c, runs, W / 2, 330, t, a, per=0.035, dur=0.7, sp=22, out_t=b, rise=22, blur=14, glow=False)

def kicker(c, t):
    f = font('sans', 22); s = 'J A L S A R A   ·   R A T L A M'
    u = eo3(prog(t, 0.0, 0.8)) * (1 - eo3(prog(t, E - 0.2, E + 0.2)))
    if u > 0:
        with Layer(c, u * 0.75):
            F.text(c, s, W / 2, 175, f, hexc(CREAM), 'c', 1.5)
        L = 70 * u
        c.drawLine(W / 2 - 250, 167, W / 2 - 250 - L, 167, SP(hexc(GOLD, 0.6 * u), 1.5))
        c.drawLine(W / 2 + 250, 167, W / 2 + 250 + L, 167, SP(hexc(GOLD, 0.6 * u), 1.5))

# ---------------- motion-graphic background ----------------
ORBS = [(random.Random(i).uniform(0, W), random.Random(i + 50).uniform(0, H), random.Random(i + 9).uniform(60, 220),
         random.Random(i + 3).uniform(0.15, 0.45), random.Random(i + 77).uniform(0, 6.28)) for i in range(14)]
def arch_path(cx, base_y, w, h):
    p = skia.Path(); r = w / 2
    p.moveTo(cx - r, base_y); p.lineTo(cx - r, base_y - h + r)
    p.arcTo(R(cx - r, base_y - h, w, w), 180, 180, False)
    p.lineTo(cx + r, base_y)
    return p
def background(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 760, 1500, [hexc('#5A2A18'), hexc('#2C150D'), hexc(DEEP)], [0, 0.5, 1])))
    for (x, y, r, a, ph) in ORBS:
        xx = x + 30 * math.sin(t * 0.35 + ph); yy = y - 18 * t
        yy = (yy % (H + 400)) - 200
        c.drawCircle(xx, yy, r, skia.Paint(AntiAlias=True, Shader=rad(xx, yy, r, [hexc('#FFB36B', a * 0.35), hexc('#FFB36B', 0)])))
    # thin line arches (the venue's niche motif) drawing in behind the window
    ua = eo5(prog(t, 0.0, 1.6))
    for i, (cx, w, h, al) in enumerate([(W / 2, 1040, 1580, 0.22), (W / 2, 1100, 1660, 0.12)]):
        pth = arch_path(cx, 1840 + 6 * math.sin(t * 0.4 + i), w, h)
        meas = skia.PathMeasure(pth, False); Lp = meas.getLength(); seg = skia.Path()
        meas.getSegment(Lp * (0.5 - 0.5 * ua), Lp * (0.5 + 0.5 * ua), seg, True)
        c.drawPath(seg, SP(hexc(GOLD, al), 2))

# ---------------- window (video) ----------------
def window(c, img, t, alpha=1.0, extra_blur=0.0, sc_extra=0.0):
    x, y, w, h = WIN
    seg = [s for s in SEGS if s[0] <= t < s[1]] or [SEGS[-1]]
    a, b = seg[0][0], seg[0][1]
    push = 1.0 + 0.035 * eio3(prog(t, a, b)) + sc_extra          # slow, smooth push per shot (no pulses)
    # dreamy light-bloom across cuts (single-frame: blur + lift)
    bl, lift = 0.0, 0.0
    for ct in T.CUTS:
        if ct >= E - 0.1: continue
        d = t - ct
        if -0.12 <= d < 0: q = (d + 0.12) / 0.12; bl, lift = 18 * q * q, 0.35 * q * q
        elif 0 <= d < 0.22: q = 1 - d / 0.22; bl, lift = 18 * q * q, 0.35 * q * q
    rr = skia.RRect.MakeRectXY(R(x, y, w, h), RAD, RAD)
    # soft drop shadow
    with Layer(c, 0.55 * alpha, (40, 40)):
        c.drawRRect(skia.RRect.MakeRectXY(R(x + 8, y + 30, w, h), RAD, RAD), P(hexc('#000000')))
    c.save(); c.clipRRect(rr, True)
    p = skia.Paint(); p.setAlphaf(alpha)
    if bl + extra_blur > 0.5: p.setImageFilter(skia.ImageFilters.Blur(bl + extra_blur, bl + extra_blur))
    c.save(); c.translate(x + w / 2, y + h / 2); c.scale(push, push); c.translate(-w / 2, -h / 2)
    c.drawImageRect(img, R(0, 0, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.restore()
    if lift > 0: c.drawRect(R(x, y, w, h), P(hexc('#FFE4C2', lift * alpha)))
    shadow_band(c, y + h - 340, y + h, 0.78 * alpha)
    c.restore()
    c.drawRRect(rr, SP(hexc(GOLD, 0.35 * alpha), 2))

# ---------------- end card ----------------
def end_card(c, t, img):
    u = eio3(prog(t, E, E + 0.6))
    window(c, img, t, alpha=1 - 0.75 * u, extra_blur=30 * u, sc_extra=-0.03 * u)
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 1000, 900, [hexc('#000000', 0.45 * u), hexc('#000000', 0.15 * u)])))
    cy = 980
    letters(c, [('Project', font('serif', 128), hexc(CREAM), 1)], W / 2, cy - 30, t, E + 0.15, per=0.05, dur=0.8, rise=26, blur=16)
    letters(c, [('B', font('script', 300), hexc(GOLD), 0)], W / 2 + 10, cy + 230, t, E + 0.55, per=0.05, dur=0.9, rise=30, blur=20, glow=True)
    letters(c, [('unveiling this month', font('serifi', 46), hexc(CREAM), 0.5)], W / 2, cy + 360, t, E + 1.05, per=0.02, dur=0.6, rise=12, blur=8)
    us = eo3(prog(t, E + 1.5, E + 2.1))
    if us > 0:
        with Layer(c, us):
            F.text(c, 'stay tuned', W / 2, cy + 470, font('script', 74), hexc(GOLD), 'c', 0)
        c.drawLine(W / 2 - 160 * us, cy + 500, W / 2 + 160 * us, cy + 500, SP(hexc(GOLD, 0.5), 1.5))
    kick = eo3(prog(t, E + 0.9, E + 1.6))
    if kick > 0:
        with Layer(c, kick * 0.8):
            F.text(c, 'J A L S A R A   ·   R A T L A M', W / 2, cy - 300, font('sans', 24), hexc(CREAM), 'c', 1.5)

def render_frame(c, img, t):
    background(c, t)
    if t >= E:
        end_card(c, t, img)
    else:
        u_in = eo5(prog(t, 0.0, 0.7))
        window(c, img, t, alpha=u_in, sc_extra=0.04 * (1 - u_in))
        draw_captions(c, t)
        draw_heads(c, t)
    kicker(c, t)
    F.grain(c, t, 0.045)
    F.vignette(c, 0.4)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', action='store_true'); ap.add_argument('--out', default='teaser2.mp4')
    ap.add_argument('--scale', type=float, default=2); ap.add_argument('--stills', default='')
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=END)
    a = ap.parse_args()
    basef = os.path.join(HERE, 'base2.mp4')
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
        os.makedirs(os.path.join(HERE, 'stills2'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s); g = frames(t, t + 0.05); arr = next(g); g.close()
            skia.Image.fromarray(one(arr, t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'stills2', f'{t:05.2f}.png'))
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
