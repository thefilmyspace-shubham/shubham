"""TFS vertical intro reel (1080x1920), reference timing (Foretell) + 4s montage.
python3 reel.py --out reel.mp4 [--fps 30] [--stills 2.5,4.0]
"""
import argparse, math, os, subprocess, sys
import numpy as np
import skia
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as Rn
from render import (font, hexc, text, text_w, cap_center_y, P, SP, R, rrect, Tx, Layer, NAVY, RED, SAND, WHITE, NAVY_L,
                    clamp, prog, lerp, eo3, eo5, eio3, eback, eexpo, ei3, trimmed)

Rn.TF['r'] = skia.Typeface.MakeFromFile(os.path.join(HERE, 'fonts', 'Inter-Regular.ttf'))
Rn.TF['bi'] = skia.Typeface.MakeFromFile(os.path.join(HERE, 'fonts', 'Inter-BoldItalic.ttf'))

W, H = 1080, 1920
OFF, PAPER, INK = '#F2EEE6', '#FAF8F4', '#111114'
# reference scene boundaries (kept identical) + 4s montage before the logo
T1, T2, T3, T4, T5, T6, T7, END = 1.833, 3.333, 5.333, 7.667, 10.667, 13.0, 16.333, 19.35
T8 = T7  # montage removed: logo follows the story line (reference timing)
BEAT = 60 / 123.0
CUTS = [T7] + [2.583 + k * BEAT for k in range(29, 36)]  # 16.73 ... 19.66 (music beats)
FEED = os.path.join(os.path.dirname(HERE), 'feed')
MONTAGE = [('r4', 1.0), ('r1', 17.0), ('r4', 9.0), ('r1', 32.2), ('r4', 24.0), ('r7', 35.0), ('r1', 31.4), ('r4', 18.0)]

def mono_dots(c, col, a, step=54, t=None):
    for yi, y in enumerate(range(40, H, step)):
        for xi, x in enumerate(range(30, W, step)):
            aa = a
            if t is not None:
                aa = a * (0.55 + 0.45 * math.sin(t * 2.2 + xi * 1.7 + yi * 2.3))
            c.drawCircle(x, y, 2.2, P(hexc(col, aa)))

def type_text(c, s, n, x, y, f, col, align='c', caret=True, t=0.0, colors=None):
    shown = s[:n]
    full_w = text_w(s, f)
    x0 = x - full_w / 2 if align == 'c' else x
    xx = x0
    for i, ch in enumerate(shown):
        cc = colors[i] if colors else col
        c.drawString(ch, xx, y, f, P(hexc(cc)))
        xx += f.measureText(ch)
    if caret and int(t * 3.2) % 2 == 0:
        c.drawRect(R(xx + 3, y - f.getSize() * 0.78, 3, f.getSize() * 0.95), P(hexc(WHITE)))
    return x0

# ---------------- S1 typing ----------------
def s1(c, t):
    c.drawPaint(P(hexc('#000000')))
    s = 'Hi there.'
    n = int(clamp((t - 0.35) / 0.075, 0, len(s)))
    type_text(c, s, n, W / 2, 975, font('m', 46), WHITE, t=t)

# ---------------- S2 collage ----------------
def s2(c, t):
    u = t - T1
    c.drawPaint(P(hexc(OFF)))
    sc = lerp(0.55, 1.0, eback(prog(t, T1, T1 + 0.3), 1.4))
    with Tx(c, s=sc, rot=u * 14, px=W / 2, py=900):
        for k in range(44):
            a = k * 2 * math.pi / 44
            rr = 430 * (0.75 + 0.25 * ((k * 7) % 5) / 4) * (1 + 0.05 * math.sin(u * 9 + k))
            c.drawLine(W / 2 + math.cos(a) * 70, 900 + math.sin(a) * 70, W / 2 + math.cos(a) * rr, 900 + math.sin(a) * rr, SP(hexc(RED), 7))
    c.drawCircle(W / 2, 900, 120 * sc, P(hexc(OFF)))
    fw = font('m', 54); ww = text_w("We're a", fw)
    ua = eo3(prog(t, T1, T1 + 0.25))
    with Layer(c, ua):
        rrect(c, W / 2 - ww / 2 - 24, 640, ww + 48, 80, 40, P(hexc(OFF)))
        text(c, "We're a", W / 2, 697 + (1 - ua) * 20, fw, hexc(INK), 'c')
    word = 'CONTENT'; fonts = ['head', 'cond', 'head', 'cond', 'head', 'head', 'cond']
    cols = [NAVY, INK, RED, SAND, NAVY, RED, INK]
    fs = [font(fn, 118 if fn == 'head' else 140) for fn in fonts]
    cws = [f.measureText(ch) + 26 for f, ch in zip(fs, word)]
    total = sum(cws) + 6 * (len(word) - 1)
    x = W / 2 - total / 2; y = 900
    step = int(u / 0.16)  # stop-motion jitter
    for i, ch in enumerate(word):
        pu = prog(t, T1 + 0.06 + i * 0.05, T1 + 0.3 + i * 0.05)
        if pu > 0:
            f = fs[i]; cw = cws[i]
            jit = ((step * 7 + i * 13) % 5 - 2) * 1.2
            with Tx(c, rot=[-6, 4, -3, 7, -5, 3, -4][i] + jit, s=eback(pu, 2.0), px=x + cw / 2, py=y):
                c.drawRect(R(x, y - 85, cw, 170), P(hexc(cols[i])))
                text(c, ch, x + cw / 2, cap_center_y(f, y), f, hexc(WHITE if cols[i] != SAND else INK), 'c')
        x += cws[i] + 6
    pu = eback(prog(t, T1 + 0.45, T1 + 0.7), 1.8)
    if pu > 0:
        with Tx(c, s=pu, px=W / 2, py=1140):
            text(c, 'STUDIO.', W / 2, 1180, font('head', 130), hexc(INK), 'c')

# ---------------- S3 growing brands ----------------
def s3(c, t):
    u = t - T2
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, 1500), 1500, [hexc(NAVY), hexc('#0B1622'), hexc('#05080C')], [0, 0.55, 1])
    c.drawPaint(skia.Paint(Shader=sh))
    mono_dots(c, SAND, 0.28, t=t)
    z = 1 + 0.05 * u / 2
    with Tx(c, s=z, px=W / 2, py=960):
        cx, cy, r = W / 2, 760, 210
        c.drawCircle(cx, cy, r + 60, P(hexc(SAND, 0.25), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60)))
        ang = u * 70
        with Tx(c, rot=ang, px=cx, py=cy):
            g = skia.GradientShader.MakeLinear([skia.Point(cx - r, cy - r), skia.Point(cx + r, cy + r)], [hexc('#F7E3B0'), hexc('#8C6B2E')])
            c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Shader=g))
            for k in range(5):
                a = k * 2 * math.pi / 5 - math.pi / 2
                c.drawCircle(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55, r * 0.22, P(hexc('#0B1622')))
            c.drawCircle(cx, cy, r * 0.12, P(hexc('#0B1622')))
        # orbit ring
        with Tx(c, rot=-12, px=cx, py=cy):
            c.drawOval(R(cx - 340, cy - 70, 680, 140), SP(hexc(WHITE, 0.35), 2))
            oa = u * 3.0
            c.drawCircle(cx + 340 * math.cos(oa), cy + 70 * math.sin(oa), 7, P(hexc(SAND)))
        # "growing" letters assemble
        f = font('bi', 168); s = 'growing'
        tw = text_w(s, f); x = W / 2 - tw / 2
        rng = np.random.default_rng(5)
        for i, ch in enumerate(s):
            cw = f.measureText(ch)
            pu = eo5(prog(t, T2 + 0.05 + i * 0.04, T2 + 0.55 + i * 0.04))
            ox, oy, orot = rng.uniform(-260, 260), rng.uniform(-200, 200), rng.uniform(-50, 50)
            with Layer(c, clamp(pu * 1.6)):
                with Tx(c, (1 - pu) * ox, (1 - pu) * oy, rot=(1 - pu) * orot, px=x + cw / 2, py=1140):
                    c.drawString(ch, x, 1190, f, P(hexc(SAND)))
            x += cw
        ub = eo3(prog(t, T2 + 0.6, T2 + 0.9))
        with Layer(c, ub):
            text(c, 'brands', W / 2, 1270 + (1 - ub) * 16, font('m', 46), hexc(WHITE), 'c')

# ---------------- S4 red ring ----------------
def s4(c, t):
    u = t - T3
    c.drawPaint(P(hexc(PAPER)))
    mono_dots(c, '#999999', 0.35)
    rot = -30 + 26 * u
    squash = 0.45 + 0.35 * math.sin(u * 1.4 + 0.6)
    ri = eo5(prog(t, T3, T3 + 0.45))
    with Tx(c, s=lerp(0.6, 1.0, ri), rot=rot, px=W / 2, py=930):
        hh = 900 * squash
        g = skia.GradientShader.MakeLinear([skia.Point(0, 930 - hh / 2), skia.Point(0, 930 + hh / 2)], [hexc('#EE6A60'), hexc('#8E1C18')])
        p = SP(hexc(RED), 118); p.setShader(g)
        c.drawOval(R(W / 2 - 360, 930 - hh / 2, 720, hh), p)
        c.drawOval(R(W / 2 - 330, 930 - hh / 2 + 28, 660, hh - 56), SP(hexc('#FFFFFF', 0.32), 9))
    f = font('r', 70)
    lines = [('through', 160, 760, 'l', 0.05), ('stories that', W / 2, 935, 'c', 0.30), ('stop the scroll.', W - 140, 1110, 'r', 0.55)]
    for s, x, y, al, d in lines:
        lu = eo5(prog(t, T3 + d, T3 + d + 0.45))
        if lu <= 0: continue
        c.save(); c.clipRect(R(0, y - 80, W, 110))
        text(c, s, x, y + (1 - lu) * 90, f, hexc(INK), al)
        c.restore()

# ---------------- S5 conversation ----------------
def s5(c, t):
    c.drawPaint(P(hexc('#000000')))
    f = font('m', 36)
    if t < T4 + 0.33:
        s = 'Ok'; n = int(clamp((t - T4 - 0.05) / 0.06, 0, 2))
        type_text(c, s, n, W / 2, 975, f, WHITE, t=t)
    elif t < T4 + 1.3:
        s = "Ok that's cool."; n = 2 + int(clamp((t - T4 - 0.33) / 0.04, 0, len(s) - 2))
        type_text(c, s, n, W / 2, 975, f, WHITE, t=t)
    else:
        s = 'But what do we actually do?'
        n = int(clamp((t - T4 - 1.35) / 0.035, 0, len(s)))
        cols = [RED if 4 <= i < 8 else WHITE for i in range(len(s))]
        x0 = type_text(c, s, n, W / 2, 975, f, WHITE, t=t, colors=cols)
        uu = eo3(prog(t, T4 + 2.45, T4 + 2.75))
        if uu > 0:
            wx = x0 + text_w('But ', f); ww = text_w('what', f)
            c.drawRect(R(wx, 990, ww * uu, 3), P(hexc(RED)))

# ---------------- S6 services ----------------
SERV = ['Concept Videos', 'Model Ad Shoots', 'Reels', 'Photo Posts', 'Content Calendars']
SIZES = [84, 74, 66, 58, 50]
def s6(c, t):
    u = t - T5
    c.drawPaint(P(hexc(NAVY)))
    for k, (x, y, r, col) in enumerate([(250, 500, 650, RED), (900, 1500, 700, SAND), (700, 300, 500, NAVY_L)]):
        x += 120 * math.sin(u * 1.3 + k * 2); y += 140 * math.cos(u * 1.1 + k)
        c.drawCircle(x, y, r, P(hexc(col, 0.85), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 220)))
    dt = (T6 - T5) / len(SERV)
    i = min(len(SERV) - 1, int(u / dt))
    lu = (u - i * dt) / dt
    # glass ring
    with Tx(c, rot=u * 60, px=W / 2, py=960):
        c.drawOval(R(W / 2 - 80, 960 - 430, 160, 860), SP(hexc(WHITE, 0.45), 26))
        c.drawOval(R(W / 2 - 80, 960 - 430, 160, 860), SP(hexc(WHITE, 0.7), 3))
    rad = lerp(330, 200, i / 4)
    c.drawCircle(W / 2, 960, rad, SP(hexc(WHITE, 0.8), 2.5))
    a = u * 4.5
    c.drawCircle(W / 2 + rad * math.cos(a), 960 + rad * math.sin(a), 8, P(hexc(WHITE)))
    f = font('m', SIZES[i])
    ea = eo3(clamp(lu / 0.25))
    with Layer(c, ea, (8 * (1 - ea), 0)):
        text(c, SERV[i], W / 2, cap_center_y(f, 960), f, hexc(WHITE), 'c')

# ---------------- S7 story line ----------------
def squiggle():
    p = skia.Path(); p.moveTo(820, -20)
    p.cubicTo(1150, 300, 650, 520, 760, 820); p.cubicTo(860, 1100, 1200, 1050, 980, 1400); p.cubicTo(800, 1700, 1050, 1800, 900, 1960)
    return p
SQ = squiggle()
def s7(c, t):
    u = t - T6
    c.drawPaint(P(hexc('#FFFFFF')))
    with Tx(c, math.sin(u * 0.9) * 18, 0):
        trimmed(c, SQ, SP(hexc(NAVY), 3), eio3(prog(t, T6, T6 + 1.4)))
    shift = -70 * eio3(prog(t, T6 + 1.4, T6 + 1.85))
    f = font('m', 66); fb = font('xb', 68)
    for k, s in enumerate(['Every brand', 'has a story.']):
        lu = eo5(prog(t, T6 + 0.05 + k * 0.1, T6 + 0.5 + k * 0.1))
        y = 880 + k * 84 + shift
        c.save(); c.clipRect(R(0, y - 76, W, 100)); text(c, s, 110, y + (1 - lu) * 84, f, hexc(INK)); c.restore()
    for k, s in enumerate(['We bring it', 'to the screen.']):
        lu = eo5(prog(t, T6 + 1.5 + k * 0.1, T6 + 1.95 + k * 0.1))
        y = 1070 + k * 84 + shift
        c.save(); c.clipRect(R(0, y - 76, W, 100)); text(c, s, 110, y + (1 - lu) * 84, fb, hexc(INK)); c.restore()

# ---------------- MONTAGE ----------------
CLIPS = []
def load_clips(fps):
    if CLIPS: return
    for k, (f, st) in enumerate(MONTAGE):
        d = (CUTS[k + 1] if k + 1 < len(CUTS) else T8) - CUTS[k] + 0.4
        CLIPS.append(Rn.VideoClip(os.path.join(FEED, f + '.mp4'), size=(W, H), fps=fps, start=st, dur=d))

def draw_clip(c, k, t, x, y, w, h, r=0):
    CLIPS[k].draw(c, x, y, w, h, max(0.0, t - CUTS[k]), r)

def s8(c, t):
    c.drawPaint(P(hexc('#FFFFFF')))
    k = max(i for i, ct in enumerate(CUTS) if t >= ct)
    # entry: first clip grows from a card
    if k == 0:
        s7(c, t)
        eu = eo5(prog(t, T7, T7 + 0.45))
        cw, ch = lerp(300, W, eu), lerp(533, H, eu)
        rad = lerp(36, 0, eu)
        with Tx(c, s=1.0):
            draw_clip(c, 0, t, W / 2 - cw / 2, H / 2 - ch / 2, cw, ch, rad)
    else:
        prev = k - 1
        wu = prog(t, CUTS[k], CUTS[k] + 0.24)
        ew = 1 - (1 - wu) ** 4
        # previous clip drifts up
        with Tx(c, 0, -120 * ew):
            draw_clip(c, prev, t, 0, 0, W, H)
        top = H * (1 - ew)
        c.save(); c.clipRect(R(0, top, W, H - top))
        sc = lerp(1.12, 1.0, eo5(prog(t, CUTS[k], CUTS[k] + 0.5)))
        with Tx(c, 0, top * 0.35, s=sc, px=W / 2, py=H / 2):
            draw_clip(c, k, t, 0, 0, W, H)
        c.restore()
    # overlay: minimal caption + counter
    ou = eo3(prog(t, T7 + 0.3, T7 + 0.6)) * (1 - prog(t, T8 - 0.35, T8 - 0.2))
    if ou > 0:
        sh = skia.GradientShader.MakeLinear([skia.Point(0, H - 420), skia.Point(0, H)], [hexc('#000000', 0.0), hexc('#000000', 0.45)])
        c.drawRect(R(0, H - 420, W, 420), skia.Paint(Shader=sh, Alphaf=ou))
        with Layer(c, ou):
            text(c, 'Selected work', 80, H - 150, font('m', 34), hexc(WHITE))
            text(c, f'{k + 1:02d} / {len(MONTAGE):02d}', W - 80, H - 150, font('m', 34), hexc(WHITE, 0.8), 'r')
    # exit: shrink to black
    xu = eio3(prog(t, T8 - 0.3, T8))
    if xu > 0:
        img = None
        c.drawPaint(P(hexc('#000000', xu)))

# ---------------- LOGO ----------------
_logo = None
def logo_blocks():
    global _logo
    if _logo is None:
        _logo = skia.Image.open(os.path.join(HERE, 'logo.png'))
    return _logo
BLOCKS = [(189, 369), (417, 597), (646, 826)]; BY0, BY1 = 175, 462
def s9(c, t):
    c.drawPaint(P(hexc('#000000')))
    img = logo_blocks()
    sc = 0.85 * (1 + 0.03 * eo3(prog(t, T8 + 0.8, END)))
    lw = (BLOCKS[-1][1] - BLOCKS[0][0] + 1)
    x0 = W / 2 - lw * sc / 2; ytop = 960 - (BY1 - BY0 + 1) * sc / 2
    for i, (a, b) in enumerate(BLOCKS):
        u = eo5(prog(t, T8 + 0.12 + i * 0.09, T8 + 0.72 + i * 0.09))
        if u <= 0: continue
        dx = x0 + (a - BLOCKS[0][0]) * sc; bw = (b - a + 1) * sc; bh = (BY1 - BY0 + 1) * sc
        c.save(); c.clipRect(R(dx, ytop, bw, bh))
        dy = (1 - u) * bh
        c.drawImageRect(img, R(a, BY0, b - a + 1, BY1 - BY0 + 1), R(dx, ytop + dy, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), None)
        c.restore()

def frame(c, t):
    if t < T1: s1(c, t)
    elif t < T2: s2(c, t)
    elif t < T3: s3(c, t)
    elif t < T4: s4(c, t)
    elif t < T5: s5(c, t)
    elif t < T6: s6(c, t)
    elif t < T7: s7(c, t)
    else: s9(c, t)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='reel.mp4'); ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--stills', default=''); ap.add_argument('--crf', type=int, default=17)
    a = ap.parse_args()
    surf = skia.Surface(W, H); c = surf.getCanvas()
    def render(t):
        c.clear(hexc('#000000')); c.save(); frame(c, t); c.restore()
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'reel_stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s)
            skia.Image.fromarray(render(t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'reel_stills', f'{t:06.2f}.png'))
        return
    n = int(round(END * a.fps))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        pr.stdin.write(render(i / a.fps).tobytes())
    pr.stdin.close(); pr.wait(); print('done')

if __name__ == '__main__':
    main()
