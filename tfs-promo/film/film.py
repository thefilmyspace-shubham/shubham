"""TFS motion-graphic film: 'Every brand deserves a blockbuster.'
Pure motion graphics (no footage). 1080x1920 design space, rendered at --scale (2 -> 4K), 60 fps.
Usage: python3 film.py --out out.mp4 [--scale 2] [--start 0 --end END] [--stills t1,t2]
"""
import argparse, json, math, os, random, subprocess
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
W, H = 1080, 1920

TF = {k: skia.Typeface.MakeFromFile(os.path.join(FD, v)) for k, v in {
    'cin': 'Cinzel-ExtraBold.ttf', 'cins': 'Cinzel-SemiBold.ttf', 'mono': 'CourierPrime-Regular.ttf',
    'monob': 'CourierPrime-Bold.ttf', 'tl': 'InterTight-Light.ttf', 'tm': 'InterTight-Medium.ttf',
    'tx': 'InterTight-ExtraBold.ttf', 'anton': 'Anton.ttf', 'bebas': 'BebasNeue.ttf'}.items()}
_fonts = {}
def font(k, size):
    key = (k, round(size, 2))
    if key not in _fonts:
        f = skia.Font(TF[k], size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        f.setHinting(skia.FontHinting.kNone)
        _fonts[key] = f
    return _fonts[key]

def hexc(h, a=1.0):
    h = h.lstrip('#'); r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)

NAVY, RED, SAND, WHITE, INK = '#2C5272', '#C9302C', '#E6C688', '#F4F1EA', '#08090B'
GREY = '#8A8F98'

# ---------------- timing (music beat grid) ----------------
_bj = json.load(open(os.path.join(HERE, 'beats680.json')))['beats']
I_END = 207                            # final hit of the track (90.86 s)
N_MUS = 84                             # music beats from entry to final hit
_k = np.arange(N_MUS + 1); _b = np.array(_bj[I_END - N_MUS:I_END + 1])
_T, _A = np.polyfit(_k, _b, 1)         # straight tempo fit -> no jitter
M0 = _A                                # track time where music enters
B0 = _T                                # cold open uses the same tempo
V0 = 12 * B0                           # video time where music enters
def G(k):
    """video time of global beat k (0..96, fractional ok)."""
    return k * B0 if k <= 12 else V0 + (k - 12) * _T
END = G(96) + 3.3

# ---------------- easing ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, u): return a + (b - a) * u
def eo3(u): return 1 - (1 - u) ** 3
def eo5(u): return 1 - (1 - u) ** 5
def ei3(u): return u ** 3
def eio3(u): return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def eio5(u): return 16 * u ** 5 if u < .5 else 1 - (-2 * u + 2) ** 5 / 2
def eexpo(u): return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def eback(u, s=1.6):
    u -= 1; return u * u * ((s + 1) * u + s) + 1
def pb(t, k0, k1, ease=eo3):
    """eased progress between beats k0..k1"""
    return ease(prog(t, G(k0), G(k1)))

# ---------------- primitives ----------------
def P(color, **kw): return skia.Paint(AntiAlias=True, Color=color, **kw)
def SP(color, w, cap=skia.Paint.kRound_Cap, **kw):
    return skia.Paint(AntiAlias=True, Color=color, Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=cap,
                      StrokeJoin=skia.Paint.kRound_Join, **kw)
def R(x, y, w, h): return skia.Rect.MakeXYWH(x, y, w, h)
def rrect(c, x, y, w, h, r, paint): c.drawRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), paint)

def text_w(s, f, track=0.0):
    return sum(f.measureText(ch) for ch in s) + track * (len(s) - 1) if track else f.measureText(s)

def capc(f, cy): return cy + f.getMetrics().fCapHeight / 2

def text(c, s, x, y, f, color, align='l', track=0.0, paint=None):
    p = paint or P(color)
    wdt = text_w(s, f, track)
    if align == 'c': x -= wdt / 2
    elif align == 'r': x -= wdt
    if track == 0:
        c.drawString(s, x, y, f, p)
    else:
        for ch in s:
            c.drawString(ch, x, y, f, p); x += f.measureText(ch) + track
    return wdt

class Layer:
    def __init__(self, c, alpha=1.0, blur=(0, 0), bounds=None):
        self.c, self.alpha, self.blur, self.bounds = c, alpha, blur, bounds
    def __enter__(self):
        p = skia.Paint()
        if self.blur[0] > 0.25 or self.blur[1] > 0.25:
            p.setImageFilter(skia.ImageFilters.Blur(max(self.blur[0], 0.01), max(self.blur[1], 0.01)))
        p.setAlphaf(clamp(self.alpha))
        self.c.saveLayer(self.bounds, p)
        return self.c
    def __exit__(self, *a): self.c.restore()

class Tx:
    def __init__(self, c, x=0, y=0, s=1.0, rot=0.0, px=0, py=0, sx=None, sy=None):
        self.c, self.x, self.y, self.s, self.rot, self.px, self.py = c, x, y, s, rot, px, py
        self.sx, self.sy = sx, sy
    def __enter__(self):
        c = self.c; c.save(); c.translate(self.x + self.px, self.y + self.py)
        if self.rot: c.rotate(self.rot)
        sx = self.sx if self.sx is not None else self.s; sy = self.sy if self.sy is not None else self.s
        if sx != 1 or sy != 1: c.scale(sx, sy)
        c.translate(-self.px, -self.py)
        return c
    def __exit__(self, *a): self.c.restore()

# ---------------- text animations (each scene uses a different one) ----------------
def t_unblur(c, s, x, y, f, col, u, align='c', track=0.0, rise=18, blur=14):
    """fade + rise + defocus -> sharp"""
    if u <= 0: return
    w = text_w(s, f, track); h = f.getSize()
    bx = x - (w / 2 if align == 'c' else (w if align == 'r' else 0))
    bnd = R(bx - 60, y - h * 1.3 - 60, w + 120, h * 1.8 + 120)
    with Layer(c, u, (blur * (1 - u), blur * (1 - u)), bnd):
        text(c, s, x, y + rise * (1 - u), f, col, align, track)

def t_trackin(c, s, x, y, f, col, u, align='c', track0=60, track1=6):
    if u <= 0: return
    tr = lerp(track0, track1, eo5(u))
    with Layer(c, clamp(u * 1.4), (8 * (1 - u), 0)):
        text(c, s, x, y, f, col, align, tr)

def t_mask(c, s, x, y, f, col, u, align='c', track=0.0):
    """text rises from behind its own baseline"""
    if u <= 0: return
    w = text_w(s, f, track); h = f.getMetrics().fCapHeight
    bx = x - (w / 2 if align == 'c' else (w if align == 'r' else 0))
    c.save(); c.clipRect(R(bx - 20, y - h * 1.6, w + 40, h * 1.6 + h * 0.45))
    text(c, s, x, y + h * 1.25 * (1 - eo5(u)), f, col, align, track)
    c.restore()

def t_type(c, s, x, y, f, col, u, caret=True, t=0.0):
    n = int(round(len(s) * clamp(u)))
    text(c, s[:n], x, y, f, col)
    if caret and 0 < u < 1.15 and (u < 1 or int(t * 3) % 2 == 0):
        cx = x + text_w(s[:n], f) + 3
        c.drawRect(R(cx, y - f.getSize() * 0.78, f.getSize() * 0.08, f.getSize() * 0.92), P(col))

# ---------------- textures ----------------
_rng = np.random.default_rng(7)
GRAIN = []
for i in range(6):
    n = (_rng.normal(0.5, 0.18, (480, 270)).clip(0, 1) * 255).astype(np.uint8)
    rgba = np.dstack([n, n, n, np.full_like(n, 255)])
    GRAIN.append(skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType))

def grain(c, t, amt=0.07):
    img = GRAIN[int(t * 24) % len(GRAIN)]
    p = skia.Paint(); p.setAlphaf(amt); p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawImageRect(img, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)

def vignette(c, a=0.55, r=1250):
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), r, [hexc('#000000', 0), hexc('#000000', a)], [0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))

def lin(x0, y0, x1, y1, cols, pos=None):
    return skia.GradientShader.MakeLinear([skia.Point(x0, y0), skia.Point(x1, y1)], cols, pos)
def rad(x, y, r, cols, pos=None):
    return skia.GradientShader.MakeRadial(skia.Point(x, y), r, cols, pos)

LOGO = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(HERE, 'logo.png')))
LB = [(189, 369), (417, 597), (646, 826)]; BY0, BY1 = 175, 462
LS = 1.30                                    # logo display scale
LX = W / 2 - 1017 * LS / 2; LY = H / 2 - 638 * LS / 2
PAPER = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(HERE, 'paper.jpg')))

# ---------------- letterbox ----------------
BAR = 330
def bar_h(t):
    if t < G(12): return 0.0
    if t < G(88): return BAR * eo5(prog(t, G(12), G(12) + 0.55))
    return BAR * (1 - eio5(prog(t, G(88), G(88) + 0.7)))

SCN_LABEL = [(12, 'SC.01  IN A WORLD'), (20, 'SC.02  EXTRAS'), (24, 'SC.03  THE LEAD'), (32, 'SC.04  SLATE'),
             (36, 'SC.05  WRITTEN BY'), (44, 'SC.06  DIRECTED BY'), (52, 'SC.07  SHOT BY'), (60, 'SC.08  EDITED FOR'),
             (68, 'SC.09  STARRING'), (80, 'SC.10  NOW SHOWING')]
def draw_bars(c, t):
    bh = bar_h(t)
    if bh < 0.5: return
    c.drawRect(R(0, 0, W, bh), P(hexc('#000000')))
    c.drawRect(R(0, H - bh, W, bh), P(hexc('#000000')))
    a = clamp((bh - 200) / 130)
    if a <= 0: return
    f = font('tm', 19); col = hexc('#6B707A', a); tr = 5
    lab = [l for k, l in SCN_LABEL if t >= G(k)]
    text(c, 'TFS PICTURES', 60, bh - 36, f, col, 'l', tr)
    text(c, 'REEL 01', W - 60, bh - 36, f, col, 'r', tr)
    if lab: text(c, lab[-1], 60, H - bh + 54, f, col, 'l', tr)
    fr = int(t * 24) % 24; s = int(t)
    text(c, f'TC 00:00:{s:02d}:{fr:02d}', W - 60, H - bh + 54, font('mono', 21), col, 'r', 2)
    # thin screen edge glow
    c.drawRect(R(0, bh - 1, W, 1), P(hexc('#FFFFFF', 0.06 * a)))
    c.drawRect(R(0, H - bh, W, 1), P(hexc('#FFFFFF', 0.06 * a)))


# =====================================================================
# SCENES   each: fn(c, t)  (draw full frame in design space)
# =====================================================================

# ---- S0  green band (0 .. G6) ----
def s_band(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, H / 2, 1250, [hexc('#23864A'), hexc('#0E4A27'), hexc('#06210F')], [0, 0.6, 1])))
    f1 = font('tm', 33); fb = font('cin', 122); fr = font('tx', 31); fl = font('tl', 26)
    t_unblur(c, 'THE FOLLOWING PREVIEW HAS BEEN', W / 2, 700, f1, hexc(WHITE, 0.92), u=eo3(prog(t, 0.20, 0.62)), track=5)
    t_unblur(c, 'APPROVED FOR', W / 2, 752, f1, hexc(WHITE, 0.92), u=eo3(prog(t, 0.30, 0.72)), track=5)
    u = prog(t, 0.45, 1.05)
    t_trackin(c, 'ALL BRANDS', W / 2, capc(fb, 900), fb, hexc(WHITE), u, track0=70, track1=4)
    t_unblur(c, 'BY  THE FILMY SPACE', W / 2, 1050, f1, hexc(WHITE, 0.92), u=eo3(prog(t, 0.75, 1.15)), track=5)
    # rating box: border draws, then content
    ub = eo3(prog(t, 0.95, 1.55))
    if ub > 0:
        x, y, w, h = 150, 1175, 780, 170
        pth = skia.Path(); pth.addRect(R(x, y, w, h))
        meas = skia.PathMeasure(pth, False); L = meas.getLength()
        seg = skia.Path(); meas.getSegment(0, L * ub, seg, True)
        c.drawPath(seg, SP(hexc(WHITE, 0.9), 3, cap=skia.Paint.kSquare_Cap))
        ui = eo3(prog(t, 1.3, 1.75))
        with Layer(c, ui):
            c.drawRect(R(x + 22, y + 22, 126, 126), P(hexc(WHITE)))
            fS = font('cin', 104); text(c, 'S', x + 85, capc(fS, y + 85), fS, hexc('#0E4A27'), 'c')
            text(c, 'RATED  S  —  SCROLL-STOPPING', x + 176, y + 76, fr, hexc(WHITE), 'l', 1.5)
            text(c, 'for hooks, cuts & stories people', x + 176, y + 116, fl, hexc(WHITE, 0.85), 'l', 0.5)
            text(c, 'actually watch till the end.', x + 176, y + 148, fl, hexc(WHITE, 0.85), 'l', 0.5)
    vignette(c, 0.6)
    # projector flicker + fade in/out
    fl_ = 0.035 * (0.5 + 0.5 * math.sin(t * 61.0)) * (0.6 + 0.4 * math.sin(t * 13.7))
    a_in = 1 - eo3(prog(t, 0, 0.35)); a_out = eio3(prog(t, G(6) - 0.22, G(6)))
    c.drawPaint(P(hexc('#000000', max(a_in, a_out) + fl_)))

# ---- S1  film leader countdown (G6 .. G12) ----
LEAD_COL = [NAVY, RED, SAND]
def s_count(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, H / 2, 1100, [hexc('#1A1C21'), hexc('#0B0C0F')])))
    i = min(2, int((t - G(6)) / (2 * B0))); t0 = G(6 + 2 * i); d = 2 * B0
    u = clamp((t - t0) / d)
    cx, cy, r = W / 2, H / 2, 400
    # sweep wedge
    ang = 360 * eio3(u)
    if ang > 0.5:
        pth = skia.Path(); pth.moveTo(cx, cy); pth.arcTo(R(cx - 1400, cy - 1400, 2800, 2800), -90, ang, False); pth.close()
        c.save(); c.clipRect(R(0, 0, W, H))
        c.drawPath(pth, P(hexc(LEAD_COL[i], 0.92)))
        c.restore()
    # leader graphics
    c.drawLine(0, cy, W, cy, SP(hexc('#000000', 0.55), 4))
    c.drawLine(cx, 0, cx, H, SP(hexc('#000000', 0.55), 4))
    c.drawCircle(cx, cy, r, SP(hexc(WHITE, 0.85), 7))
    c.drawCircle(cx, cy, r - 50, SP(hexc(WHITE, 0.45), 3))
    # sweep edge line
    a = math.radians(-90 + ang)
    if 0.5 < ang < 359.5:
        c.drawLine(cx, cy, cx + 1400 * math.cos(a), cy + 1400 * math.sin(a), SP(hexc(WHITE, 0.6), 3))
    # number
    fN = font('anton', 520); s = '321'[i]
    pop = 1 + 0.10 * (1 - eo3(prog(t, t0, t0 + 0.22)))
    with Tx(c, s=pop, px=cx, py=cy):
        with Layer(c, 1.0, bounds=R(cx - 300, cy - 360, 600, 720)):
            text(c, s, cx, capc(fN, cy), fN, hexc(WHITE), 'c')
    text(c, 'PICTURE  START', cx, H - 250, font('tm', 22), hexc(WHITE, 0.5), 'c', 8)
    text(c, 'TFS', cx, 260, font('cin', 40), hexc(WHITE, 0.5), 'c', 14)
    vignette(c, 0.7)
    # scratches
    rnd = random.Random(int(t * 24))
    for _ in range(2):
        x = rnd.uniform(80, W - 80)
        c.drawLine(x, 0, x + rnd.uniform(-12, 12), H, SP(hexc(WHITE, rnd.uniform(0.03, 0.09)), rnd.uniform(1, 2.5)))
    if t > G(12) - 0.06: c.drawPaint(P(hexc('#000000', prog(t, G(12) - 0.06, G(12)))))

# ---- feed of grey 'extras' (S2, S3, S4 share it) ----
CW, CH, GAP = 300, 470, 28
COLX = [60, 390, 720]
V_SCR = 1650.0
TD = 0.95
def scroll_pos(t):
    t0, tA = G(12), G(20)
    if t < tA: return V_SCR * (t - t0)
    u = clamp((t - tA) / TD)
    return V_SCR * (tA - t0) + V_SCR * TD / 3 * (1 - (1 - u) ** 3)
def scroll_speed(t):
    tA = G(20)
    if t < tA: return V_SCR
    u = clamp((t - tA) / TD); return V_SCR * (1 - u) ** 2

def skel_card(c, x, y, w, h, a=1.0, sh=0.0):
    rrect(c, x, y, w, h, 26, P(hexc('#1E2127', a)))
    rrect(c, x + 0.5, y + 0.5, w - 1, h - 1, 26, SP(hexc('#333740', a), 1.5))
    c.drawCircle(x + 40, y + 40, 20, P(hexc('#363A43', a)))
    rrect(c, x + 72, y + 26, w * 0.42, 12, 6, P(hexc('#363A43', a)))
    rrect(c, x + 72, y + 46, w * 0.26, 10, 5, P(hexc('#24272D', a)))
    rrect(c, x + 16, y + 80, w - 32, h - 160, 16, P(hexc('#262930', a)))
    cx_, cy_ = x + w / 2, y + 80 + (h - 160) / 2
    tri = skia.Path(); tri.moveTo(cx_ - 14, cy_ - 18); tri.lineTo(cx_ + 20, cy_); tri.lineTo(cx_ - 14, cy_ + 18); tri.close()
    c.drawPath(tri, P(hexc('#3A3E47', a)))
    rrect(c, x + 16, y + h - 64, w * 0.6, 12, 6, P(hexc('#262930', a)))
    rrect(c, x + 16, y + h - 42, w * 0.35, 10, 5, P(hexc('#22252B', a)))

def feed(c, t, dim=0.0, hide_center=False):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, H * 0.48, 1300, [hexc('#121419'), hexc('#07080A')])))
    pos = scroll_pos(t); v = scroll_speed(t)
    blur = min(26, v * 0.011)
    # back layer (parallax, smaller, softer)
    with Layer(c, 0.45, (blur * 0.5 + 4, blur * 0.5 + 4)):
        with Tx(c, s=0.62, px=W / 2, py=H / 2):
            for j in range(4):
                x = -160 + j * 360
                off = (pos * 0.55 + j * 190) % (CH + GAP)
                for k in range(-1, 8):
                    skel_card(c, x, -200 + k * (CH + GAP) - off, CW, CH)
    with Layer(c, 1.0, (0, blur)):
        for j, x in enumerate(COLX):
            sp = (1.0, 1.12, 0.94)[j]
            off = (pos * sp + j * 170) % (CH + GAP)
            for k in range(-1, 6):
                y = -120 + k * (CH + GAP) - off
                if hide_center and j == 1 and abs(y + CH / 2 - 1000) < CH * 0.6: continue
                skel_card(c, x, y, CW, CH)
    if dim > 0: c.drawPaint(P(hexc('#000000', dim)))

def s_world(c, t):
    feed(c, t)
    # readable band behind text
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 935, 620, [hexc('#000000', 0.82), hexc('#000000', 0.0)])))
    fo = eio3(prog(t, G(19.4), G(20)))
    with Layer(c, 1 - fo):
        fW = font('cins', 74)
        t_trackin(c, 'IN A WORLD', W / 2, capc(fW, 900), fW, hexc(WHITE), prog(t, G(12.6), G(14.6)), track0=46, track1=12)
        fL = font('tl', 40)
        t_unblur(c, 'OF ENDLESS SCROLLING...', W / 2, 990, fL, hexc(WHITE, 0.82), eo3(prog(t, G(15), G(16.6))), track=7)

def s_extras(c, t):
    feed(c, t)
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 960, 640, [hexc('#000000', 0.85), hexc('#000000', 0.0)])))
    fM = font('tm', 40); fE = font('cin', 158)
    t_mask(c, 'MOST BRANDS ARE JUST', W / 2, 860, fM, hexc(WHITE, 0.85), prog(t, G(20.1), G(21)), track=6)
    u = prog(t, G(21), G(21) + 0.42)
    if u > 0:
        s = 1 + 0.14 * (1 - eo5(u))
        with Tx(c, s=s, px=W / 2, py=1010):
            with Layer(c, eo3(u), (16 * (1 - eo3(u)), 16 * (1 - eo3(u)))):
                text(c, 'EXTRAS.', W / 2, capc(fE, 1010), fE, hexc(WHITE), 'c', 4)
    ul = eo3(prog(t, G(22), G(23)))
    if ul > 0:
        wE = text_w('EXTRAS.', fE, 4)
        c.drawLine(W / 2 - wE / 2, 1112, W / 2 - wE / 2 + wE * ul, 1112, SP(hexc(RED), 7, cap=skia.Paint.kButt_Cap))

# lead card
def lead_card(c, x, y, w, h, col_u, glow):
    if glow > 0:
        with Layer(c, glow * 0.8, (40, 40)):
            rrect(c, x - 10, y - 10, w + 20, h + 20, 34, P(hexc(SAND)))
    rrect(c, x, y, w, h, 26, P(hexc('#17191E')))
    if col_u > 0:
        with Layer(c, col_u):
            c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(x, y, w, h), 26, 26), True)
            c.drawRect(R(x, y, w, h), skia.Paint(Shader=lin(x, y, x + w, y + h, [hexc(NAVY), hexc('#15283A')])))
            # three logo-coloured stripes as the 'content'
            sw = w / 3
            for i, col in enumerate([NAVY, RED, SAND]):
                c.drawRect(R(x + i * sw, y + h * 0.17, sw, h * 0.66), P(hexc(col, 0.95)))
            c.drawRect(R(x, y + h * 0.17, w, h * 0.66), skia.Paint(Shader=lin(x, y, x, y + h, [hexc('#FFFFFF', 0.18), hexc('#000000', 0.25)])))
            cx_, cy_ = x + w / 2, y + h / 2
            c.drawCircle(cx_, cy_, w * 0.16, P(hexc('#000000', 0.35)))
            tri = skia.Path(); r_ = w * 0.075
            tri.moveTo(cx_ - r_ * 0.7, cy_ - r_); tri.lineTo(cx_ + r_ * 1.05, cy_); tri.lineTo(cx_ - r_ * 0.7, cy_ + r_); tri.close()
            c.drawPath(tri, P(hexc(WHITE)))
            c.drawCircle(x + 40, y + 40, 20, P(hexc(WHITE, 0.9)))
            rrect(c, x + 72, y + 28, w * 0.42, 12, 6, P(hexc(WHITE, 0.85)))
            rrect(c, x + 16, y + h - 64, w * 0.6, 12, 6, P(hexc(WHITE, 0.8)))
            c.restore()
    rrect(c, x + 0.5, y + 0.5, w - 1, h - 1, 26, SP(hexc(SAND, 0.4 + 0.6 * col_u), 2.5))

DUST = [(random.Random(i).uniform(-1, 1), random.Random(i + 99).uniform(0, 1), random.Random(i + 7).uniform(0.4, 1.0)) for i in range(70)]
def s_lead(c, t):
    on = prog(t, G(24.3), G(24.3) + 0.5)
    flick = 1.0 if on >= 1 else (0.0 if on < 0.15 else (0.55 if on < 0.3 else (0.1 if on < 0.42 else 0.85)))
    feed(c, t, dim=0.55 + 0.25 * eo3(prog(t, G(24), G(24.6))), hide_center=True)
    cy = 1000
    # spotlight cone
    if flick > 0:
        bh = bar_h(t)
        cone = skia.Path(); cone.moveTo(W / 2 - 50, bh); cone.lineTo(W / 2 + 50, bh); cone.lineTo(W / 2 + 380, cy + 330); cone.lineTo(W / 2 - 380, cy + 330); cone.close()
        with Layer(c, flick, (18, 18)):
            c.drawPath(cone, skia.Paint(AntiAlias=True, Shader=lin(0, bh, 0, cy + 330, [hexc('#FFF4DC', 0.30), hexc('#FFF4DC', 0.07)])))
        c.drawOval(R(W / 2 - 400, cy + 280, 800, 120), skia.Paint(AntiAlias=True, Shader=rad(W / 2, cy + 340, 400, [hexc('#FFF4DC', 0.22 * flick), hexc('#FFF4DC', 0)])))
        for (dx, dy, s) in DUST:
            yy = bh + ((dy + t * 0.05 * s) % 1.0) * (cy + 300 - bh)
            spread = 50 + (yy - bh) / (cy + 330 - bh) * 330
            c.drawCircle(W / 2 + dx * spread * 0.9, yy, 1.6 * s, P(hexc('#FFF4DC', 0.35 * flick * s)))
    # the lead card lifts and gets colour
    ul = eo5(prog(t, G(25), G(27)))
    s = 1 + 0.36 * ul
    w, h = CW, CH
    with Tx(c, s=s, px=W / 2, py=cy):
        lead_card(c, W / 2 - w / 2, cy - h / 2, w, h, eo3(prog(t, G(25.5), G(27))), eo3(prog(t, G(26), G(28))) * flick)
    fM = font('tm', 40); fL = font('cin', 148)
    t_unblur(c, 'ONE AGENCY', W / 2, 470, fM, hexc(WHITE, 0.9), eo3(prog(t, G(24.6), G(26))), track=9)
    t_unblur(c, 'TURNS THEM INTO', W / 2, 528, fM, hexc(WHITE, 0.9), eo3(prog(t, G(26), G(27.4))), track=9)
    u = prog(t, G(28), G(28) + 0.5)
    if u > 0:
        sh = lin(0, 1400, 0, 1560, [hexc('#F7E2A8'), hexc('#C9A55A')])
        p = skia.Paint(AntiAlias=True, Shader=sh)
        with Layer(c, eo3(u), (12 * (1 - eo3(u)), 12 * (1 - eo3(u)))):
            text(c, 'THE LEAD.', W / 2, 1520 + 30 * (1 - eo5(u)), fL, None, 'c', 4, paint=p)

# ---- S5  clapperboard (G32 .. G36) ----
STRIPE = [WHITE, '#111111', RED, '#111111', SAND, '#111111', NAVY, '#111111']
def stripes(c, x, y, w, h, off):
    c.save(); c.clipRect(R(x, y, w, h))
    c.drawRect(R(x, y, w, h), P(hexc('#111111')))
    k = 0; sw = 70
    xx = x - 200 + off
    while xx < x + w + 200:
        col = STRIPE[k % len(STRIPE)]
        if col != '#111111':
            pth = skia.Path(); pth.moveTo(xx, y + h); pth.lineTo(xx + sw, y + h); pth.lineTo(xx + sw + h * 0.8, y); pth.lineTo(xx + h * 0.8, y); pth.close()
            c.drawPath(pth, P(hexc(col)))
        xx += sw; k += 1
    c.restore()

def s_slate(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 900, 1100, [hexc('#1D2733'), hexc('#07080A')])))
    ue = prog(t, G(32), G(32) + 0.55)
    yoff = 900 * (1 - eo5(ue)); rot = -7 * (1 - eback(ue, 1.2))
    push = 1 + 0.05 * prog(t, G(32), G(36))
    snap = G(34)
    if t < snap - 0.16: ang = -26 * eo3(prog(t, G(32.3), G(33)))
    elif t < snap: ang = -26 * (1 - ei3(prog(t, snap - 0.16, snap)))
    else:
        v = prog(t, snap, snap + 0.25); ang = -3.5 * math.sin(v * math.pi) * (1 - v)
    bx, by, bw, bh = 160, 820, 760, 520
    with Tx(c, s=push, px=W / 2, py=1000):
        with Tx(c, y=yoff, rot=rot, px=W / 2, py=1080):
            # shadow
            with Layer(c, 0.6, (30, 30)):
                rrect(c, bx + 10, by + 40, bw, bh, 24, P(hexc('#000000')))
            rrect(c, bx, by, bw, bh, 22, P(hexc('#15171B')))
            rrect(c, bx + 1, by + 1, bw - 2, bh - 2, 22, SP(hexc('#2A2D33'), 2))
            # lower stripe bar (fixed)
            stripes(c, bx, by, bw, 96, 0)
            # chalk grid
            gp = SP(hexc(WHITE, 0.55), 3, cap=skia.Paint.kButt_Cap)
            c.drawLine(bx + 30, by + 220, bx + bw - 30, by + 220, gp)
            c.drawLine(bx + 30, by + 360, bx + bw - 30, by + 360, gp)
            c.drawLine(bx + bw * 0.5, by + 220, bx + bw * 0.5, by + 500, gp)
            fl = font('tm', 24); fv = font('tx', 46); fv2 = font('tx', 64)
            lab = hexc(WHITE, 0.6); val = hexc(WHITE, 0.95)
            text(c, 'PRODUCTION', bx + 40, by + 140, fl, lab, 'l', 4)
            text(c, 'THE FILMY SPACE', bx + 40, by + 196, fv, val, 'l', 2)
            text(c, 'SCENE', bx + 40, by + 262, fl, lab, 'l', 4)
            text(c, 'YOUR BRAND', bx + 40, by + 330, fv, hexc(SAND), 'l', 1)
            text(c, 'TAKE', bx + bw * 0.5 + 30, by + 262, fl, lab, 'l', 4)
            text(c, '01', bx + bw * 0.5 + 30, by + 334, fv2, val, 'l', 2)
            text(c, 'ROLL', bx + 40, by + 410, fl, lab, 'l', 4)
            text(c, 'A', bx + 40, by + 476, fv2, val, 'l')
            text(c, 'DATE', bx + bw * 0.5 + 30, by + 410, fl, lab, 'l', 4)
            text(c, 'TODAY', bx + bw * 0.5 + 30, by + 470, fv, val, 'l', 2)
            # clapstick (hinged at left top)
            with Tx(c, rot=ang, px=bx + 8, py=by - 4):
                with Layer(c, 0.55, (12, 12)):
                    rrect(c, bx, by - 100, bw, 90, 10, P(hexc('#000000')))
                c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(bx, by - 104, bw, 92), 10, 10), True)
                stripes(c, bx, by - 104, bw, 92, 35)
                c.restore()
            c.drawCircle(bx + 22, by - 6, 11, P(hexc('#8A8F98')))
    if snap <= t < snap + 0.07: c.drawPaint(P(hexc('#FFFFFF', 0.55 * (1 - prog(t, snap, snap + 0.07)))))

# ---- S6  written by (G36 .. G44) ----
def credit_label(c, s, y, u, col=SAND):
    if u <= 0: return
    f = font('tm', 25); w = text_w(s, f, 11)
    with Layer(c, eo3(u)):
        text(c, s, W / 2, y, f, hexc(col), 'c', 11)
    L = 150 * eo5(u); y0 = y - 9
    c.drawLine(W / 2 - w / 2 - 30, y0, W / 2 - w / 2 - 30 - L, y0, SP(hexc(col, 0.8), 2, cap=skia.Paint.kButt_Cap))
    c.drawLine(W / 2 + w / 2 + 30, y0, W / 2 + w / 2 + 30 + L, y0, SP(hexc(col, 0.8), 2, cap=skia.Paint.kButt_Cap))

SCRIPT = [('FADE IN:', 'mono', 36.4, 36.9), ('INT. YOUR FEED - DAY', 'monob', 37.0, 38.1),
          ('A thumb scrolls past a', 'mono', 38.4, 39.6), ('hundred posts.', 'mono', 39.6, 40.3),
          ('Then it stops.', 'mono', 40.6, 41.4)]
def s_written(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 760, 1200, [hexc('#1B2E42'), hexc('#0A1119')])))
    credit_label(c, 'WRITTEN BY', 470, prog(t, G(36.2), G(37.4)))
    rot = lerp(-2.6, -1.2, prog(t, G(36), G(44))); s = lerp(1.0, 1.035, prog(t, G(36), G(44)))
    ue = eo5(prog(t, G(36), G(36) + 0.5))
    px, py, pw, ph = 150, 560, 780, 760
    with Tx(c, y=380 * (1 - ue), s=s, rot=rot, px=W / 2, py=py + ph / 2):
        with Layer(c, 0.7, (34, 34)):
            c.drawRect(R(px + 14, py + 30, pw, ph), P(hexc('#000000')))
        p = skia.Paint(AntiAlias=True); p.setAlphaf(1.0)
        c.drawImageRect(PAPER, R(0, 0, PAPER.width(), PAPER.height() * ph / pw), R(px, py, pw, ph), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        c.drawRect(R(px, py, pw, ph), P(hexc('#F4F0E6', 0.78)))
        f = font('mono', 38); fb = font('monob', 38)
        y = py + 120
        for (s_, fk, k0, k1) in SCRIPT:
            ff = fb if fk == 'monob' else f
            x = px + 80 + (0 if not s_.startswith('FADE') else 0)
            if s_.startswith('INT'): y += 26
            if s_.startswith('A thumb'): y += 30
            uu = prog(t, G(k0), G(k1))
            caret = (t < G(k1) + 0.35) and (s_ == SCRIPT[-1][0] or t < G(k1))
            # red marker under 'it stops.'
            if s_ == 'Then it stops.':
                um = eo3(prog(t, G(41.6), G(42.3)))
                if um > 0:
                    x0 = x + text_w('Then ', ff); wm = text_w('it stops.', ff)
                    rrect(c, x0 - 8, y - 34, (wm + 16) * um, 46, 6, P(hexc(RED, 0.85)))
            t_type(c, s_, x, y, ff, hexc('#1E1E1E'), uu, caret=caret and uu > 0, t=t)
            y += 58
        text(c, '1.', px + pw - 70, py + 70, f, hexc('#1E1E1E', 0.7))
    fB = font('tx', 70)
    u2 = prog(t, G(42), G(42) + 0.45)
    t_mask(c, 'HOOKS THAT', W / 2, 1450, fB, hexc(WHITE), u2, track=2)
    u3 = prog(t, G(42.5), G(42.5) + 0.45)
    if u3 > 0:
        f2 = fB; a, b_, cc = 'STOP ', 'THE THUMB.', ''
        wt = text_w('STOP THE THUMB.', f2, 2); x0 = W / 2 - wt / 2
        c.save(); c.clipRect(R(0, 1450, W, 120))
        yy = 1532 + 90 * (1 - eo5(u3))
        text(c, 'STOP', x0, yy, f2, hexc(RED), 'l', 2)
        text(c, ' THE THUMB.', x0 + text_w('STOP', f2, 2), yy, f2, hexc(WHITE), 'l', 2)
        c.restore()

# ---- S7  directed by: viewfinder (G44 .. G52) ----
def iris(c, cx, cy, r, R_=1600, n=8, alpha=1.0):
    """black screen with an n-blade iris hole of radius r"""
    th = math.radians((1 - clamp(r / 900)) * 55)
    outer = skia.Path(); outer.addRect(R(-200, -200, W + 400, H + 400))
    hole = skia.Path()
    pts = [(cx + r * math.cos(th + 2 * math.pi * i / n), cy + r * math.sin(th + 2 * math.pi * i / n)) for i in range(n)]
    if r > 0.5:
        hole.moveTo(*pts[0])
        for p_ in pts[1:]: hole.lineTo(*p_)
        hole.close()
        shape = skia.Op(outer, hole, skia.PathOp.kDifference_PathOp)
    else:
        shape = outer
    c.drawPath(shape, P(hexc('#0C0D10', alpha)))
    if r > 0.5:
        for i in range(n):
            x0, y0 = pts[i]; x1, y1 = pts[(i + 1) % n]
            dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy) + 1e-6
            c.drawLine(x0, y0, x0 + dx / L * 1600, y0 + dy / L * 1600, SP(hexc('#3A3D44', alpha), 2.5))

def s_directed(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 960, 1100, [hexc('#151A20'), hexc('#06070A')])))
    bh = max(bar_h(t), 0)
    top, bot = bh + 70, H - bh - 70
    # frame brackets
    bp = SP(hexc(WHITE, 0.85), 4, cap=skia.Paint.kSquare_Cap); L = 70
    for (x, y, sx, sy) in [(70, top, 1, 1), (W - 70, top, -1, 1), (70, bot, 1, -1), (W - 70, bot, -1, -1)]:
        c.drawLine(x, y, x + L * sx, y, bp); c.drawLine(x, y, x, y + L * sy, bp)
    c.drawLine(W / 2 - 22, 960, W / 2 + 22, 960, SP(hexc(WHITE, 0.35), 2)); c.drawLine(W / 2, 938, W / 2, 982, SP(hexc(WHITE, 0.35), 2))
    fh = font('tm', 24); col = hexc(WHITE, 0.8)
    if int(t * 2) % 2 == 0: c.drawCircle(108, top + 52, 11, P(hexc(RED)))
    text(c, 'REC', 128, top + 61, fh, col, 'l', 3)
    text(c, '4K  60P', W - 110, top + 61, fh, col, 'r', 3)
    text(c, 'ISO 800    1/120    f/2.8', W / 2, bot - 40, fh, hexc(WHITE, 0.6), 'c', 3)
    # audio meters
    for i in range(2):
        lv = 0.5 + 0.45 * abs(math.sin(t * (7.3 + i * 2.1) + i))
        for k in range(10):
            on_ = k / 10 < lv
            colm = RED if k >= 8 else (SAND if k >= 6 else '#5BC07A')
            c.drawRect(R(110 + i * 18, bot - 70 - k * 14, 12, 10), P(hexc(colm, 0.9 if on_ else 0.15)))
    credit_label(c, 'DIRECTED BY', top + 150, prog(t, G(44.2), G(45.4)))
    # STRATEGY: focus pull
    fS = font('tx', 132)
    a_ = eo3(prog(t, G(44.3), G(45)))
    fu = eo3(prog(t, G(46), G(46) + 0.4))
    bl = 22 * (1 - fu)
    with Layer(c, a_, (bl, bl)):
        text(c, 'STRATEGY.', W / 2, capc(fS, 900), fS, hexc(WHITE), 'c', 1)
    # focus box: travels then locks
    wS = text_w('STRATEGY.', fS, 1) + 60
    um = eio3(prog(t, G(44.8), G(45.9)))
    bx_ = lerp(640, W / 2 - wS / 2, um); by_ = lerp(1180, 900 - 105, um); bw_ = lerp(180, wS, um); bhh = lerp(140, 210, um)
    lock = t >= G(46)
    fc = hexc('#5BC07A' if lock else WHITE, 0.95 if a_ > 0 else 0)
    k = 26
    if a_ > 0:
        for (x, y, sx, sy) in [(bx_, by_, 1, 1), (bx_ + bw_, by_, -1, 1), (bx_, by_ + bhh, 1, -1), (bx_ + bw_, by_ + bhh, -1, -1)]:
            c.drawLine(x, y, x + k * sx, y, SP(fc, 3)); c.drawLine(x, y, x, y + k * sy, SP(fc, 3))
    # NOT GUESSWORK stays out of focus
    fG = font('tl', 64)
    ug = eo3(prog(t, G(47.5), G(48.5)))
    with Layer(c, ug * 0.75, (7, 7)):
        text(c, 'NOT GUESSWORK.', W / 2, 1090, fG, hexc('#B9BDC6'), 'c', 6)
    # iris closes at the end -> handover to SHOT BY
    ui = prog(t, G(51), G(52))
    if ui > 0:
        iris(c, W / 2, 960, 1250 * (1 - eio3(ui)))

# ---- S8  shot by: lens / aperture (G52 .. G60) ----
FSTOPS = ['f/16', 'f/11', 'f/8', 'f/5.6', 'f/4', 'f/2.8', 'f/2', 'f/1.8']
def s_shot(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 900, 1250, [hexc('#D5372F'), hexc('#8E211C'), hexc('#3D0D0B')], [0, 0.55, 1])))
    cx, cy = W / 2, 960
    rot = 40 * eio3(prog(t, G(52), G(60)))
    # lens barrel rings + distance scale
    with Tx(c, rot=rot, px=cx, py=cy):
        c.drawCircle(cx, cy, 430, SP(hexc('#000000', 0.25), 30))
        c.drawCircle(cx, cy, 395, SP(hexc(WHITE, 0.35), 2))
        for i in range(120):
            a = math.radians(i * 3); r0 = 405; r1 = 418 if i % 5 else 432
            c.drawLine(cx + r0 * math.cos(a), cy + r0 * math.sin(a), cx + r1 * math.cos(a), cy + r1 * math.sin(a), SP(hexc(WHITE, 0.45), 2))
        f = font('tm', 24)
        for i, lab in enumerate(['∞', '10', '5', '3', '2', '1.5', '1.2', '1', '0.8', '0.7', '0.6', '0.5']):
            a = -90 + i * 30
            with Tx(c, rot=a + 90, px=cx, py=cy):
                text(c, lab, cx, cy - 452, f, hexc(WHITE, 0.75), 'c', 1)
    c.drawCircle(cx, cy, 380, SP(hexc('#000000', 0.18), 3))
    credit_label(c, 'SHOT BY', 610, prog(t, G(52.6), G(53.8)), col=WHITE)
    fB = font('tx', 96)
    t_unblur(c, 'OUR OWN', W / 2, 935, fB, hexc(WHITE), eo3(prog(t, G(53.2), G(54.4))), track=2, blur=18)
    t_unblur(c, 'CREW.', W / 2, 1050, fB, hexc(WHITE), eo3(prog(t, G(54), G(55.2))), track=2, blur=18)
    fs = font('tm', 30)
    t_unblur(c, 'IN-HOUSE  ·  ON-SET  ·  ON-TIME', W / 2, 1140, fs, hexc('#FFE3DF', 0.9), eo3(prog(t, G(55.4), G(56.6))), track=4)
    # f-stop readout stepping on half beats
    k = int(clamp((t - G(52.5)) / (_T / 2), 0, len(FSTOPS) - 1))
    fF = font('mono', 44)
    with Layer(c, eo3(prog(t, G(52.5), G(53.2)))):
        text(c, FSTOPS[k], W / 2, 1310, fF, hexc(WHITE, 0.95), 'c', 2)
    # shutter flash at G57
    if G(57) <= t < G(57) + 0.09: c.drawPaint(P(hexc('#FFFFFF', 0.6 * (1 - prog(t, G(57), G(57) + 0.09)))))
    # iris opens at scene start
    uo = prog(t, G(52), G(53.2))
    if uo < 1: iris(c, cx, cy, 1250 * eio3(uo))

# ---- S9  edited for: NLE timeline (G60 .. G68) ----
WAVE = np.abs(np.convolve(np.random.default_rng(3).normal(0, 1, 400), np.ones(5) / 5, 'same'))
CLIPS = [  # track, start(sec on ruler), length, colour, beat it snaps in
    (0, 0.0, 1.1, NAVY, 60.5), (0, 1.1, 0.8, RED, 61.0), (0, 1.9, 1.1, SAND, 61.5), (0, 3.0, 1.6, NAVY, 62.0),
    (1, 0.4, 1.2, '#3E6E96', 62.5), (1, 2.2, 1.3, '#A84540', 63.0), (0, 4.6, 1.5, RED, 63.5)]
def s_edited(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 800, 1200, [hexc('#181B22'), hexc('#08090C')])))
    credit_label(c, 'EDITED FOR', 470, prog(t, G(60.2), G(61.4)))
    fT = font('tm', 50); fN = font('anton', 360); fS = font('tx', 86)
    t_mask(c, 'THE FIRST', W / 2, 590, fT, hexc(WHITE, 0.9), prog(t, G(60.5), G(61.3)), track=10)
    u3 = prog(t, G(61), G(61) + 0.5)
    if u3 > 0:
        s = 1 + 0.25 * (1 - eo5(u3))
        with Tx(c, s=s, px=W / 2, py=800):
            with Layer(c, eo3(u3), (14 * (1 - eo3(u3)), 14 * (1 - eo3(u3)))):
                text(c, '3', W / 2, capc(fN, 800), fN, hexc(RED), 'c')
    t_mask(c, 'SECONDS.', W / 2, 1060, fS, hexc(WHITE), prog(t, G(61.8), G(62.6)), track=8)
    # timeline panel
    px, py, pw, ph = 70, 1150, 940, 360
    ue = eo5(prog(t, G(60), G(60) + 0.6))
    with Tx(c, y=260 * (1 - ue)):
        rrect(c, px, py, pw, ph, 18, P(hexc('#101217', 0.96)))
        rrect(c, px, py, pw, ph, 18, SP(hexc('#2A2E37'), 2))
        sec = 140.0; x0 = px + 110
        fr = font('mono', 20)
        for s_ in range(0, 7):
            xx = x0 + s_ * sec
            if xx > px + pw - 20: break
            c.drawLine(xx, py + 22, xx, py + 44, SP(hexc(WHITE, 0.5), 2))
            text(c, f'00:0{s_}', xx + 6, py + 40, fr, hexc(WHITE, 0.55))
            for q in range(1, 4):
                xq = xx + q * sec / 4
                if xq < px + pw - 20: c.drawLine(xq, py + 34, xq, py + 44, SP(hexc(WHITE, 0.25), 1.5))
        labs = ['V2', 'V1', 'A1']; ty = [py + 70, py + 150, py + 238]
        for i, lb in enumerate(labs):
            text(c, lb, px + 30, ty[i] + 44, font('tm', 24), hexc(WHITE, 0.6))
            c.drawLine(px + 90, ty[i] + 72, px + pw - 20, ty[i] + 72, SP(hexc(WHITE, 0.06), 1))
        c.save(); c.clipRect(R(px + 100, py + 50, pw - 120, ph - 60))
        for (tr_, st, ln, col, kb) in CLIPS:
            u = eo5(prog(t, G(kb), G(kb) + 0.28))
            if u <= 0: continue
            yy = ty[1 - tr_] + 8
            xx = x0 + st * sec + 300 * (1 - u)
            with Layer(c, u):
                rrect(c, xx + 2, yy, ln * sec - 4, 60, 8, P(hexc(col)))
                rrect(c, xx + 2, yy, ln * sec - 4, 60, 8, SP(hexc('#FFFFFF', 0.25), 1.5))
                c.drawRect(R(xx + 10, yy + 10, min(60, ln * sec - 24), 40), P(hexc('#000000', 0.18)))
        # waveform on A1
        ua = eo3(prog(t, G(60.5), G(62)))
        for i in range(int(len(WAVE) * ua)):
            xx = x0 + i * 2.2
            if xx > px + pw - 20: break
            a_ = WAVE[i] * 26
            c.drawLine(xx, ty[2] + 38 - a_, xx, ty[2] + 38 + a_, SP(hexc('#5BC07A', 0.8), 1.4))
        # first-3-seconds highlight
        uh = eo3(prog(t, G(64), G(64.8)))
        if uh > 0:
            c.drawRect(R(x0, py + 50, 3 * sec * uh, ph - 60), P(hexc(SAND, 0.14)))
            c.drawRect(R(x0 + 3 * sec * uh - 3, py + 50, 6, ph - 60), P(hexc(SAND, 0.9)))
        c.restore()
        # playhead
        tp = prog(t, G(60.6), G(67.6))
        xp = x0 + (pw - 140) * eio3(tp)
        c.drawLine(xp, py + 12, xp, py + ph - 10, SP(hexc(RED), 3))
        tri = skia.Path(); tri.moveTo(xp - 12, py + 10); tri.lineTo(xp + 12, py + 10); tri.lineTo(xp, py + 26); tri.close()
        c.drawPath(tri, P(hexc(RED)))
        # razor marks on beats
        for kb in (62, 63, 64, 65, 66, 67):
            ur = prog(t, G(kb), G(kb) + 0.22)
            if 0 < ur < 1:
                xr = x0 + ((kb - 60) * 0.55) * sec
                c.drawLine(xr, py + 50, xr, py + ph - 10, SP(hexc(WHITE, 0.9 * (1 - ur)), 3))

# ---- S10  starring (G68 .. G80) ----
CLIENTS = ['THE FIVE ELEMENTS', 'PHULWARI', 'FUNHOODS', 'HOUSE OF STRENGTH', 'SWAD EXOTICA', 'R.O.W',
           'SCIENCE ACADEMY', 'GHUNGHAT GHAR', 'JALSARA', 'TEQUILA', 'BATTLE & BOUNCE', 'EMINENCE',
           'IBRAHIM FOOTWEARS', 'COLSEE PAINTS', 'SAI SHREE ACADEMY', 'HALLBERD', 'TRENDSPIRE']
def s_starring(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 420, 1300, [hexc('#1E2633'), hexc('#07080A')])))
    # top light
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 330, 700, [hexc('#FFF4DC', 0.10), hexc('#FFF4DC', 0.0)])))
    drift = -40 * prog(t, G(68), G(80))
    fS = font('cin', 100)
    u = prog(t, G(68), G(70))
    with Tx(c, y=drift * 0.5):
        sh = lin(0, 520, 0, 600, [hexc('#F7E2A8'), hexc('#C9A55A')])
        if u > 0:
            tr = lerp(60, 14, eo5(u))
            with Layer(c, clamp(u * 1.5), (10 * (1 - u), 0)):
                text(c, 'STARRING', W / 2, capc(fS, 560), fS, None, 'c', tr, paint=skia.Paint(AntiAlias=True, Shader=sh))
        c.drawLine(W / 2 - 220 * eo5(u), 640, W / 2 + 220 * eo5(u), 640, SP(hexc(SAND, 0.7), 2, cap=skia.Paint.kButt_Cap))
    with Tx(c, y=drift):
        for i, nm in enumerate(CLIENTS):
            col_, row = i % 2, i // 2
            if i == 16: x, y = W / 2, 722 + 8 * 88
            else: x, y = (290 if col_ == 0 else 790), 722 + row * 88
            k0 = 69 + i * 0.5
            uu = eo3(prog(t, G(k0), G(k0) + 0.45))
            fk = 'cins' if i % 3 == 0 else 'tm'
            sz = 42 if fk == 'cins' else 38
            f = font(fk, sz); tr = 1.5 if fk == 'cins' else 4
            wmax = 450
            if text_w(nm, f, tr) > wmax: f = font(fk, sz * wmax / text_w(nm, f, tr))
            t_unblur(c, nm, x, y, f, hexc(WHITE, 0.92), uu, track=tr, rise=14, blur=10)
    # light sweep over names
    us = prog(t, G(77.5), G(79.3))
    if 0 < us < 1:
        xs = lerp(-500, W + 500, eio3(us))
        p = skia.Paint(Shader=lin(xs - 220, 0, xs + 220, 300, [hexc('#FFFFFF', 0), hexc('#FFF4DC', 0.16), hexc('#FFFFFF', 0)]))
        p.setBlendMode(skia.BlendMode.kScreen)
        c.drawRect(R(0, 650, W, 900), p)
    fA = font('tx', 50)
    ua = prog(t, G(78), G(78.6))
    if ua > 0:
        with Tx(c, y=drift, s=1 + 0.1 * (1 - eo5(ua)), px=W / 2, py=1490):
            with Layer(c, eo3(ua)):
                text(c, '& 20+ BRANDS', W / 2, capc(fA, 1490), fA, hexc(SAND), 'c', 8)

# ---- S11  now showing: split-flap (G80 .. G88) ----
FLAP_CH = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
NCELL = 12; CWID, CHGT, CGAP = 76, 116, 6
ROWY = [790, 960, 1130]
def flap_seq(old, new, i, row):
    rnd = random.Random(i * 31 + row * 7 + ord(new) + ord(old))
    mid = [rnd.choice(FLAP_CH) for _ in range(3 + rnd.randint(0, 3))]
    return [old] + mid + [new]
def flap_cell(c, x, y, ch_a, ch_b, u, txtcol=WHITE):
    """flip from ch_a to ch_b, u in 0..1 (top half falls, then bottom half lands)"""
    w, h = CWID, CHGT; f = font('bebas', 112)
    def half(ch, top, sy=1.0, shade=0.0):
        c.save()
        c.clipRect(R(x, y, w, h / 2 - 1) if top else R(x, y + h / 2 + 1, w, h / 2 - 1))
        with Tx(c, sy=sy, sx=1.0, px=x + w / 2, py=y + h / 2):
            rrect(c, x, y, w, h, 8, P(hexc('#16181C')))
            c.drawRect(R(x, y if top else y + h / 2, w, h / 2), skia.Paint(Shader=lin(0, y, 0, y + h, [hexc('#FFFFFF', 0.04), hexc('#000000', 0.12)])))
            if ch.strip(): text(c, ch, x + w / 2, capc(f, y + h / 2), f, hexc(txtcol), 'c')
            if shade > 0: c.drawRect(R(x, y, w, h), P(hexc('#000000', shade)))
        c.restore()
    if u <= 0:
        half(ch_a, True); half(ch_a, False)
    elif u >= 1:
        half(ch_b, True); half(ch_b, False)
    else:
        half(ch_b, True); half(ch_a, False)
        if u < 0.5: half(ch_a, True, sy=max(0.001, 1 - u * 2), shade=u)
        else: half(ch_b, False, sy=max(0.001, (u - 0.5) * 2), shade=(1 - u) * 0.6)
    c.drawLine(x, y + h / 2, x + w, y + h / 2, SP(hexc('#000000'), 2, cap=skia.Paint.kButt_Cap))

def board_row(c, row, y, txt_from, txt_to, k0, t, col=WHITE):
    a_ = txt_from.center(NCELL); b_ = txt_to.center(NCELL)
    x0 = W / 2 - (NCELL * (CWID + CGAP) - CGAP) / 2
    for i in range(NCELL):
        seq = flap_seq(a_[i], b_[i], i, row) if a_[i] != b_[i] else [a_[i]]
        st = G(k0) + i * 0.035; per = 0.075
        n = len(seq) - 1
        if n == 0: flap_cell(c, x0 + i * (CWID + CGAP), y, seq[0], seq[0], 1, col); continue
        e = (t - st) / per
        if e <= 0: flap_cell(c, x0 + i * (CWID + CGAP), y, seq[0], seq[0], 1, col)
        elif e >= n: flap_cell(c, x0 + i * (CWID + CGAP), y, seq[-1], seq[-1], 1, col)
        else:
            j = int(e); flap_cell(c, x0 + i * (CWID + CGAP), y, seq[j], seq[j + 1], e - j, col)

def s_nowshowing(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 960, 1100, [hexc('#1A1410'), hexc('#060505')])))
    ue = eo5(prog(t, G(80), G(80) + 0.5))
    with Tx(c, s=lerp(0.92, 1.0, ue), px=W / 2, py=960):
        with Layer(c, ue):
            bx, by, bw, bh = 40, 700, 1000, 580
            rrect(c, bx, by, bw, bh, 26, P(hexc('#0D0E11')))
            rrect(c, bx, by, bw, bh, 26, SP(hexc('#2B2E35'), 3))
            # marquee bulbs, chase after the music returns
            n = 34; per = 2 * (bw + bh)
            for i in range(n):
                d = i / n * per
                if d < bw: x, y = bx + d, by
                elif d < bw + bh: x, y = bx + bw, by + (d - bw)
                elif d < 2 * bw + bh: x, y = bx + bw - (d - bw - bh), by + bh
                else: x, y = bx, by + bh - (d - 2 * bw - bh)
                chase = t >= G(84)
                lit = (0.35 + 0.65 * (((i + int(t * 12)) % 3) == 0)) if chase else 0.25
                if lit > 0.5:
                    with Layer(c, 0.6, (8, 8)): c.drawCircle(x, y, 13, P(hexc('#FFD98A')))
                c.drawCircle(x, y, 8, P(hexc('#FFE7B0', lit)))
            board_row(c, 0, ROWY[0] - 40, '', 'COMING SOON', 80.2, t)
            if t >= G(82): board_row(c, 1, ROWY[0] - 40, 'COMING SOON', 'NOW SHOWING', 82, t)
            board_row(c, 2, ROWY[1] - 40, '', '', 80, t) if t < G(84) else board_row(c, 3, ROWY[1] - 40, '', 'ON YOUR FEED', 84, t, col=SAND)
            fsm = font('tm', 22)
            text(c, 'SCREEN 01  ·  ALL SHOWS  ·  EVERY DAY', W / 2, ROWY[2] + 20, fsm, hexc(WHITE, 0.45), 'c', 5)

# ---- S12  blockbuster (G88 .. G94) + S13 logo (G94 ..) ----
def light_rays(c, t, a=1.0):
    for i in range(9):
        ang = -90 + (i - 4) * 9 + 3 * math.sin(t * 0.6 + i)
        L = 2200; x1 = W / 2 + L * math.cos(math.radians(ang)); y1 = 1900 + L * math.sin(math.radians(ang))
        pth = skia.Path(); pth.moveTo(W / 2 - 14, 1900); pth.lineTo(W / 2 + 14, 1900)
        pth.lineTo(x1 + 90, y1); pth.lineTo(x1 - 90, y1); pth.close()
        with Layer(c, a * 0.5, (30, 30)):
            c.drawPath(pth, skia.Paint(AntiAlias=True, Shader=lin(W / 2, 1900, x1, y1, [hexc('#FFE2A6', 0.16), hexc('#FFE2A6', 0)])))

def s_blockbuster(c, t):
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 1150, 1400, [hexc('#24344A'), hexc('#0C121B'), hexc('#05070A')], [0, 0.5, 1])))
    light_rays(c, t, eo3(prog(t, G(88), G(89))))
    fo = eio3(prog(t, G(94.3), G(95.6)))
    with Layer(c, 1 - fo):
        fM = font('tm', 54)
        t_trackin(c, 'EVERY BRAND', W / 2, 740, fM, hexc(WHITE, 0.92), prog(t, G(88.4), G(89.6)), track0=50, track1=12)
        t_trackin(c, 'DESERVES A', W / 2, 822, fM, hexc(WHITE, 0.92), prog(t, G(89.4), G(90.6)), track0=50, track1=12)
        fB = font('anton', 214); fB = font('anton', 214 * min(1.0, 960 / text_w('BLOCKBUSTER.', fB, 2)))
        u = prog(t, G(90), G(90) + 0.5)
        if u > 0:
            s = 1 + 0.18 * (1 - eo5(u))
            y = capc(fB, 1010)
            sh = lin(0, 900, 0, 1110, [hexc('#FFF1C9'), hexc('#E6C688'), hexc('#B98E43')], [0, 0.5, 1])
            with Tx(c, s=s, px=W / 2, py=1010):
                with Layer(c, eo3(u), (16 * (1 - eo3(u)), 16 * (1 - eo3(u)))):
                    text(c, 'BLOCKBUSTER.', W / 2, y, fB, None, 'c', 2, paint=skia.Paint(AntiAlias=True, Shader=sh))
                    # shine sweep
                    us = prog(t, G(91), G(92.5))
                    if 0 < us < 1:
                        xs = lerp(-300, W + 300, eio3(us))
                        p = skia.Paint(AntiAlias=True, Shader=lin(xs - 120, 0, xs + 120, 120, [hexc('#FFFFFF', 0), hexc('#FFFFFF', 0.85), hexc('#FFFFFF', 0)]))
                        p.setBlendMode(skia.BlendMode.kSrcATop)
                        c.drawRect(R(0, 850, W, 300), p)
            # anamorphic flare on the hit
            uf = prog(t, G(90), G(90) + 0.9)
            if 0 < uf < 1:
                a = (1 - uf) * 0.9
                with Layer(c, a, (60, 6)):
                    c.drawRect(R(-100, 1000, W + 200, 10), P(hexc('#FFE7B8')))
                c.drawPaint(skia.Paint(Shader=rad(W / 2, 1000, 520 * (0.6 + uf), [hexc('#FFE7B8', 0.22 * (1 - uf)), hexc('#FFE7B8', 0)])))

# film strip that stops on the T / F / S frames
PITCH = (LB[1][0] - LB[0][0]) * LS
FW_ = (LB[0][1] - LB[0][0]) * LS; FH_ = (BY1 - BY0) * LS
FX0 = LX + LB[0][0] * LS; FY0 = LY + BY0 * LS
NPRE = 7
def strip_offset(t):
    """x offset of strip; 0 = locked on logo."""
    t0, t1 = G(94), G(96)
    if t >= t1:
        v = prog(t, t1, t1 + 0.35); return -7 * math.sin(v * math.pi) * (1 - v)
    u = prog(t, t0, t1)
    return (NPRE + 4.5) * PITCH * (1 - eo5(u)) + 0 * u

def mini_icon(c, kind, x, y, w, h):
    cx, cy = x + w / 2, y + h / 2; col = hexc(WHITE, 0.55); s = w * 0.28
    if kind == 0:   # countdown circle
        c.drawCircle(cx, cy, s, SP(col, 3)); text(c, '3', cx, capc(font('anton', s * 1.3), cy), font('anton', s * 1.3), col, 'c')
    elif kind == 1:  # play
        tri = skia.Path(); tri.moveTo(cx - s * 0.5, cy - s * 0.7); tri.lineTo(cx + s * 0.7, cy); tri.lineTo(cx - s * 0.5, cy + s * 0.7); tri.close(); c.drawPath(tri, P(col))
    elif kind == 2:  # slate
        c.drawRect(R(cx - s, cy - s * 0.4, s * 2, s * 1.2), SP(col, 3)); c.drawLine(cx - s, cy - s * 0.75, cx + s, cy - s * 0.95, SP(col, 6))
    elif kind == 3:  # aperture
        for i in range(6):
            a = math.radians(i * 60)
            c.drawLine(cx + s * math.cos(a), cy + s * math.sin(a), cx + s * math.cos(a + 1.6), cy + s * math.sin(a + 1.6), SP(col, 3))
    elif kind == 4:  # timeline
        for i in range(3): c.drawRect(R(cx - s, cy - s * 0.6 + i * s * 0.45, s * (1.2 + 0.4 * (i % 2)), s * 0.3), P(col))
    elif kind == 5:  # star
        pth = skia.Path()
        for i in range(10):
            r_ = s if i % 2 == 0 else s * 0.45; a = math.radians(-90 + i * 36)
            (pth.moveTo if i == 0 else pth.lineTo)(cx + r_ * math.cos(a), cy + r_ * math.sin(a))
        pth.close(); c.drawPath(pth, P(col))
    else:  # flap
        c.drawRect(R(cx - s * 0.6, cy - s * 0.8, s * 1.2, s * 1.6), SP(col, 3)); c.drawLine(cx - s * 0.6, cy, cx + s * 0.6, cy, SP(col, 3))

def film_strip(c, t, base_a=1.0, others_a=1.0):
    off = strip_offset(t)
    yT, yB = FY0 - 92, FY0 + FH_ + 92
    v = 0.0
    if G(94) <= t < G(96):
        dt = 1 / 120; v = abs(strip_offset(t + dt) - strip_offset(t - dt)) / (2 * dt)
    mb = min(40, v * 0.012)
    with Layer(c, 1.0, (mb, 0)):
        if base_a > 0:
            c.drawRect(R(-50, yT, W + 100, yB - yT), P(hexc('#0E0F12', base_a)))
            # sprockets
            sp_ = 52
            x = (off % sp_) - sp_
            while x < W + sp_:
                rrect(c, x + 12, yT + 22, 26, 34, 6, P(hexc('#2A2C31', base_a)))
                rrect(c, x + 12, yB - 56, 26, 34, 6, P(hexc('#2A2C31', base_a)))
                x += sp_
            fe = font('mono', 18)
            for i in range(-NPRE - 6, 6):
                xx = FX0 + i * PITCH + off
                if -300 < xx < W + 300:
                    text(c, f'TFS {abs(i) + 12:02d}', xx + 4, yT + 82, fe, hexc(SAND, 0.5 * base_a))
        for i in range(-NPRE - 6, 6):
            xx = FX0 + i * PITCH + off
            if xx > W + 50 or xx + FW_ < -50: continue
            if 0 <= i <= 2:   # the real logo blocks
                src = skia.Rect.MakeLTRB(LB[i][0], BY0, LB[i][1], BY1)
                c.drawImageRect(LOGO, src, R(xx, FY0, FW_, FH_), skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(AntiAlias=True))
            elif others_a > 0:
                col = [NAVY, RED, SAND][i % 3]
                with Layer(c, others_a):
                    c.drawRect(R(xx, FY0, FW_, FH_), P(hexc('#1A1C21')))
                    c.drawRect(R(xx, FY0, FW_, FH_), P(hexc(col, 0.22)))
                    mini_icon(c, (i * 3) % 7, xx, FY0, FW_, FH_)

def s_logo(c, t):
    if t < G(96):
        s_blockbuster(c, t)
        film_strip(c, t)
        return
    c.drawPaint(P(hexc('#000000')))
    k = prog(t, G(96) + 0.25, G(96) + 1.2)
    fade = eio3(k)
    if fade < 1:
        film_strip(c, t, base_a=1 - fade, others_a=1 - fade)
    if fade > 0:
        with Layer(c, fade):
            c.drawImageRect(LOGO, R(LX, LY, 1017 * LS, 638 * LS), skia.SamplingOptions(skia.FilterMode.kLinear), skia.Paint(AntiAlias=True))
    # soft glow + gloss sweep over the blocks
    ug = prog(t, G(96) + 1.4, G(96) + 2.6)
    if 0 < ug < 1:
        xs = lerp(FX0 - 200, FX0 + 2 * PITCH + FW_ + 200, eio3(ug))
        c.save(); c.clipRect(R(FX0, FY0, 2 * PITCH + FW_, FH_))
        p = skia.Paint(AntiAlias=True, Shader=lin(xs - 90, FY0, xs + 90, FY0 + 60, [hexc('#FFFFFF', 0), hexc('#FFFFFF', 0.28), hexc('#FFFFFF', 0)]))
        p.setBlendMode(skia.BlendMode.kScreen)
        c.drawRect(R(FX0, FY0, 2 * PITCH + FW_, FH_), p)
        c.restore()
    # hit flash
    if G(96) <= t < G(96) + 0.1: c.drawPaint(P(hexc('#FFFFFF', 0.45 * (1 - prog(t, G(96), G(96) + 0.1)))))

# ---------------- scene table + transitions ----------------
SCENES = [(0, s_band), (6, s_count), (12, s_world), (20, s_extras), (24, s_lead), (32, s_slate), (36, s_written),
          (44, s_directed), (52, s_shot), (60, s_edited), (68, s_starring), (80, s_nowshowing), (88, s_blockbuster), (94, s_logo)]
SB = [G(k) for k, _ in SCENES]
TRANS = {32: ('zoom_in', 0.34), 36: ('push_left', 0.40), 44: ('whip_up', 0.30), 60: ('whip_left', 0.30), 68: ('blur_cross', 0.40), 80: ('zoom_out', 0.36),
         88: ('blur_cross', 0.36)}

def scene_at(t):
    i = 0
    for j, b in enumerate(SB):
        if t >= b: i = j
    return i

PUSH = [(0, 6, 0.025), (6, 12, 0.02), (12, 32, 0.05), (36, 44, 0.03), (44, 52, 0.03), (52, 60, 0.025), (60, 68, 0.03),
        (68, 80, 0.035), (80, 88, 0.03)]
def draw_scene(c, i, t):
    s = 1.0
    for k0, k1, amt in PUSH:
        if G(k0) <= t < G(k1): s = 1 + amt * eio3(prog(t, G(k0), G(k1)))
    if s != 1.0:
        c.save(); c.translate(W / 2, H / 2); c.scale(s, s); c.translate(-W / 2, -H / 2)
        SCENES[i][1](c, t); c.restore()
    else:
        SCENES[i][1](c, t)

def post(c, t):
    draw_bars(c, t)
    grain(c, t, 0.075)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='film.mp4'); ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--scale', type=float, default=2); ap.add_argument('--start', type=float, default=0)
    ap.add_argument('--end', type=float, default=END); ap.add_argument('--stills', default='')
    ap.add_argument('--crf', type=int, default=16)
    a = ap.parse_args()
    S = a.scale; OW, OH = int(W * S), int(H * S)
    surf = skia.Surface(OW, OH); c = surf.getCanvas()
    sA = skia.Surface(OW, OH)
    def offscreen(sf, i, t):
        cc = sf.getCanvas(); cc.clear(hexc('#000000')); cc.save(); cc.scale(S, S); draw_scene(cc, i, t); cc.restore()
        return sf.makeImageSnapshot()
    def blit(img, dx=0.0, dy=0.0, sc=1.0, bx=0.0, by=0.0, alpha=1.0):
        p = skia.Paint(); p.setAlphaf(clamp(alpha))
        if bx > 0.5 or by > 0.5: p.setImageFilter(skia.ImageFilters.Blur(max(bx, 0.01), max(by, 0.01)))
        c.save(); c.translate(OW / 2 + dx, OH / 2 + dy); c.scale(sc, sc); c.translate(-OW / 2, -OH / 2)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
        c.restore()
    def render(t):
        c.clear(hexc('#000000'))
        tr = None
        for k, (kind, d) in TRANS.items():
            b = G(k)
            if b - d / 2 <= t < b + d / 2: tr = (k, b, kind, d)
        if tr is None:
            c.save(); c.scale(S, S); draw_scene(c, scene_at(t), t); post(c, t); c.restore()
            return surf.makeImageSnapshot().toarray()
        k, b, kind, d = tr
        p = (t - (b - d / 2)) / d
        i_new = [kk for kk, _ in SCENES].index(k); i_old = i_new - 1
        q = p * 2 if p < 0.5 else p * 2 - 1
        blur = 60 * S
        if kind == 'push_left':
            e = eio5(p); v = abs(eio5(min(1, p + 0.02)) - eio5(max(0, p - 0.02))) / 0.04
            A_ = offscreen(sA, i_old, t); blit(A_, dx=-OW * e, bx=v * 26 * S)
            B_ = offscreen(sA, i_new, t); blit(B_, dx=OW * (1 - e), bx=v * 26 * S)
        elif kind == 'blur_cross':
            A_ = offscreen(sA, i_old, t); blit(A_, bx=30 * S * p, by=30 * S * p)
            B_ = offscreen(sA, i_new, t); blit(B_, bx=30 * S * (1 - p), by=30 * S * (1 - p), alpha=eio3(p))
        else:
            img = offscreen(sA, i_old if p < 0.5 else i_new, t)
            if kind == 'whip_up':
                if p < 0.5: blit(img, dy=-OH * 0.55 * ei3(q), by=blur * q)
                else: blit(img, dy=OH * 0.55 * (1 - eo3(q)), by=blur * (1 - q))
            elif kind == 'whip_left':
                if p < 0.5: blit(img, dx=-OW * 0.6 * ei3(q), bx=blur * q)
                else: blit(img, dx=OW * 0.6 * (1 - eo3(q)), bx=blur * (1 - q))
            elif kind == 'zoom_in':
                if p < 0.5: blit(img, sc=1 + 0.8 * ei3(q), bx=blur * 0.5 * q, by=blur * 0.5 * q)
                else: blit(img, sc=1 + 0.45 * (1 - eo3(q)), bx=blur * 0.5 * (1 - q), by=blur * 0.5 * (1 - q))
            elif kind == 'zoom_out':
                if p < 0.5: blit(img, sc=1 - 0.25 * ei3(q), bx=blur * 0.4 * q, by=blur * 0.4 * q, alpha=1 - 0.3 * q)
                else: blit(img, sc=1 + 0.3 * (1 - eo3(q)), bx=blur * 0.4 * (1 - q), by=blur * 0.4 * (1 - q))
        c.save(); c.scale(S, S); post(c, t); c.restore()
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        od = os.path.join(HERE, 'stills'); os.makedirs(od, exist_ok=True)
        for s in a.stills.split(','):
            t = float(s)
            skia.Image.fromarray(render(t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(od, f'{t:06.2f}.png'))
        return
    n0, n1 = int(round(a.start * a.fps)), int(round(a.end * a.fps))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{OW}x{OH}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-x264-params', 'threads=2', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        pr.stdin.write(render(n / a.fps).tobytes())
    pr.stdin.close(); pr.wait()

if __name__ == '__main__':
    main()
