"""TFS promo renderer: 60s, 16:9, animation + feed clips.
Usage: python3 render.py --out out.mp4 [--w 1920] [--fps 30] [--start 0 --end 60] [--stills t1,t2,...]
"""
import argparse, math, os, random, subprocess, sys, glob
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
TF = {k: skia.Typeface.MakeFromFile(os.path.join(FD, v)) for k, v in {
    'head': 'ArchivoBlack.ttf', 'cond': 'Anton.ttf', 'xb': 'Inter-ExtraBold.ttf',
    'b': 'Inter-Bold.ttf', 'm': 'Inter-Medium.ttf'}.items()}
_fonts = {}
def font(k, size):
    key = (k, round(size, 1))
    if key not in _fonts:
        f = skia.Font(TF[k], size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        _fonts[key] = f
    return _fonts[key]

def hexc(h, a=1.0):
    h = h.lstrip('#'); r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)

BG, NAVY, RED, SAND, WHITE = '#0A0A0C', '#2C5272', '#C9302C', '#E6C688', '#F4F1EA'
G1, G2, G3, G4 = '#1C1C20', '#2B2B31', '#4A4A52', '#8A8A94'
NAVY_L = '#4A7BA6'
W0, H0 = 1920, 1080

# ---------------- easing ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def lerp(a, b, u): return a + (b - a) * u
def eo3(u): return 1 - (1 - u) ** 3
def eo5(u): return 1 - (1 - u) ** 5
def ei3(u): return u ** 3
def eio3(u): return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def eback(u, s=1.7):
    u -= 1; return u * u * ((s + 1) * u + s) + 1
def eexpo(u): return 1 if u >= 1 else 1 - 2 ** (-10 * u)

# ---------------- primitives ----------------
def P(color, aa=True, **kw): return skia.Paint(AntiAlias=aa, Color=color, **kw)
def SP(color, w, cap=skia.Paint.kRound_Cap, **kw):
    return skia.Paint(AntiAlias=True, Color=color, Style=skia.Paint.kStroke_Style, StrokeWidth=w, StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join, **kw)
def R(x, y, w, h): return skia.Rect.MakeXYWH(x, y, w, h)
def rrect(c, x, y, w, h, r, paint): c.drawRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), paint)

def text(c, s, x, y, f, color, align='l', track=0.0):
    """y is baseline. track in px between chars."""
    if track == 0:
        wdt = f.measureText(s)
        if align == 'c': x -= wdt / 2
        elif align == 'r': x -= wdt
        c.drawString(s, x, y, f, P(color))
        return wdt
    ws = [f.measureText(ch) for ch in s]; wdt = sum(ws) + track * (len(s) - 1)
    if align == 'c': x -= wdt / 2
    elif align == 'r': x -= wdt
    for ch, cw in zip(s, ws):
        c.drawString(ch, x, y, f, P(color)); x += cw + track
    return wdt

def text_w(s, f, track=0.0):
    return sum(f.measureText(ch) for ch in s) + track * (len(s) - 1) if track else f.measureText(s)

def cap_center_y(f, cy):
    """baseline such that cap-height is vertically centered at cy"""
    return cy + f.getMetrics().fCapHeight / 2

class Layer:
    def __init__(self, c, alpha=1.0, blur=(0, 0)):
        self.c, self.alpha, self.blur = c, alpha, blur
    def __enter__(self):
        p = skia.Paint()
        if self.blur[0] > 0.3 or self.blur[1] > 0.3:
            p.setImageFilter(skia.ImageFilters.Blur(self.blur[0], self.blur[1]))
        p.setAlphaf(clamp(self.alpha))
        self.c.saveLayer(None, p)
        return self.c
    def __exit__(self, *a): self.c.restore()

class Tx:
    def __init__(self, c, x=0, y=0, s=1.0, rot=0.0, px=None, py=None):
        self.c, self.x, self.y, self.s, self.rot, self.px, self.py = c, x, y, s, rot, px, py
    def __enter__(self):
        c = self.c; c.save(); c.translate(self.x, self.y)
        if self.s != 1.0 or self.rot:
            px = self.px if self.px is not None else 0; py = self.py if self.py is not None else 0
            c.translate(px, py)
            if self.rot: c.rotate(self.rot)
            if self.s != 1.0: c.scale(self.s, self.s)
            c.translate(-px, -py)
        return c
    def __exit__(self, *a): self.c.restore()

# ---------------- clip sources ----------------
PALS = [(NAVY, '#13283B'), (RED, '#5A1512'), ('#B8934A', '#3D2E10'), (NAVY_L, '#1B2F44'),
        ('#7A3E8E', '#2A1233'), ('#2E8A6A', '#0F2E24'), ('#C26A2A', '#45210A'), ('#5B5BB8', '#1D1D45')]
CATS = {'restaurant': 0, 'gym': 1, 'coaching': 2, 'events': 3, 'retail': 4, 'reel': 5}

class Placeholder:
    def __init__(self, idx, label):
        self.idx, self.label = idx, label
        a, b = PALS[idx % len(PALS)]
        self.ca, self.cb = a, b
        self.cache = {}
    def draw(self, c, x, y, w, h, t, r=0):
        """draw 'cover' into rect"""
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), True)
        ph = (t * 0.35 + self.idx * 0.37) % 2.0
        off = (ph if ph < 1 else 2 - ph)
        sh = skia.GradientShader.MakeLinear([skia.Point(x - w * 0.3 + w * 0.6 * off, y), skia.Point(x + w * 0.7 + w * 0.6 * off, y + h)],
                                            [hexc(self.ca), hexc(self.cb)])
        c.drawRect(R(x, y, w, h), skia.Paint(Shader=sh))
        # soft light blob moving
        bx = x + w * (0.3 + 0.4 * math.sin(t * 0.9 + self.idx)); by = y + h * (0.35 + 0.25 * math.cos(t * 0.7 + self.idx))
        rs = skia.GradientShader.MakeRadial(skia.Point(bx, by), max(w, h) * 0.55, [hexc('#FFFFFF', 0.22), hexc('#FFFFFF', 0.0)])
        c.drawRect(R(x, y, w, h), skia.Paint(Shader=rs))
        # play icon + label
        s = min(w, h)
        if s > 90:
            cx, cy = x + w / 2, y + h / 2
            c.drawCircle(cx, cy, s * 0.11, P(hexc('#000000', 0.25)))
            tri = skia.Path(); rr = s * 0.05
            tri.moveTo(cx - rr * 0.6, cy - rr); tri.lineTo(cx + rr, cy); tri.lineTo(cx - rr * 0.6, cy + rr); tri.close()
            c.drawPath(tri, P(hexc(WHITE, 0.9)))
            fs = clamp(s * 0.075, 9, 40)
            text(c, self.label, cx, y + h - fs * 1.4, font('b', fs), hexc(WHITE, 0.75), 'c', track=fs * 0.12)
        c.restore()

class VideoClip:
    """real clip, decoded to memory at a target size; looped."""
    def __init__(self, path, size=(540, 960), fps=30, start=0.0, dur=8.0):
        w, h = size
        cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(dur), '-i', path,
               '-vf', f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps}',
               '-pix_fmt', 'rgba', '-f', 'rawvideo', '-']
        raw = subprocess.run(cmd, capture_output=True).stdout
        n = len(raw) // (w * h * 4)
        self.frames = np.frombuffer(raw[:n * w * h * 4], np.uint8).reshape(n, h, w, 4) if n else np.zeros((1, h, w, 4), np.uint8)
        self.fps, self.w, self.h, self.cache = fps, w, h, {}
    def image(self, t):
        i = int(t * self.fps) % len(self.frames)
        if i not in self.cache:
            if len(self.cache) > 64: self.cache.clear()
            self.cache[i] = skia.Image.fromarray(np.ascontiguousarray(self.frames[i]), colorType=skia.kRGBA_8888_ColorType)
        return self.cache[i]
    def draw(self, c, x, y, w, h, t, r=0):
        img = self.image(t)
        sw, sh = self.w, self.h
        # cover
        sc = max(w / sw, h / sh); cw, ch = w / sc, h / sc
        src = R((sw - cw) / 2, (sh - ch) / 2, cw, ch)
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), True)
        c.drawImageRect(img, src, R(x, y, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), None)
        c.restore()

CLIPS = {}
def clip(slot):
    """slot -> clip source. Real files: clips/<slot>.mp4 or clips/NN.mp4 assigned via clips/map.txt"""
    if slot in CLIPS: return CLIPS[slot]
    src = None
    mp = os.path.join(HERE, 'clips', 'map.txt')
    if os.path.exists(mp):
        for line in open(mp):
            if line.strip() and not line.startswith('#'):
                k, v = line.split(None, 1)
                if k == slot:
                    parts = v.split(); f = parts[0]; st = float(parts[1]) if len(parts) > 1 else 0.0
                    src = VideoClip(os.path.join(HERE, 'clips', f), start=st)
    if src is None:
        cat = slot.split('_')[0]
        idx = CATS.get(cat, abs(hash(slot)) % 8)
        n = slot.split('_')[-1]
        src = Placeholder(idx + (int(n) if n.isdigit() else 0) * 3, (cat.upper() + ' CLIP') if cat in CATS else 'FEED CLIP')
    CLIPS[slot] = src
    return src

# ---------------- shared elements ----------------
LOGO_BW, LOGO_BH, LOGO_GAP = 181, 288, 47
def draw_logo(c, cx, cy, sc=1.0, blocks=None, letters_a=1.0):
    """blocks: list of 3 dicts {dy, a, s} per block"""
    cols = [NAVY, RED, SAND]; lets = 'TFS'
    total = 3 * LOGO_BW + 2 * LOGO_GAP
    f = font('head', 163 / 0.688 * sc)  # cap height 163
    for i in range(3):
        b = blocks[i] if blocks else {'dy': 0, 'a': 1, 's': 1}
        if b['a'] <= 0.001: continue
        bx = cx + (-total / 2 + i * (LOGO_BW + LOGO_GAP)) * sc
        bw, bh = LOGO_BW * sc, LOGO_BH * sc
        bcx, bcy = bx + bw / 2, cy + b['dy']
        with Layer(c, b['a']):
            with Tx(c, s=b['s'], px=bcx, py=bcy):
                c.drawRect(R(bcx - bw / 2, bcy - bh / 2, bw, bh), P(hexc(cols[i])))
                if letters_a > 0:
                    text(c, lets[i], bcx, cap_center_y(f, bcy), f, hexc('#FFFFFF', letters_a), 'c')

def mini_logo(c, x, y, h):
    bw = h * LOGO_BW / LOGO_BH; g = h * LOGO_GAP / LOGO_BH
    for i, col in enumerate([NAVY, RED, SAND]):
        c.drawRect(R(x + i * (bw + g), y, bw, h), P(hexc(col)))

def check_path(cx, cy, s):
    p = skia.Path(); p.moveTo(cx - s * 0.5, cy); p.lineTo(cx - s * 0.12, cy + s * 0.38); p.lineTo(cx + s * 0.55, cy - s * 0.42); return p
def cross_paths(cx, cy, s):
    a = skia.Path(); a.moveTo(cx - s / 2, cy - s / 2); a.lineTo(cx + s / 2, cy + s / 2)
    b = skia.Path(); b.moveTo(cx + s / 2, cy - s / 2); b.lineTo(cx - s / 2, cy + s / 2)
    return a, b
def trimmed(c, path, paint, u):
    if u <= 0: return
    if u >= 0.999: c.drawPath(path, paint); return
    p = skia.Paint(paint); p.setPathEffect(skia.TrimPathEffect.Make(0, clamp(u))); c.drawPath(path, p)

def heart_path(cx, cy, s):
    p = skia.Path()
    p.moveTo(cx, cy + s * 0.35)
    p.cubicTo(cx - s * 0.6, cy - s * 0.05, cx - s * 0.35, cy - s * 0.55, cx, cy - s * 0.2)
    p.cubicTo(cx + s * 0.35, cy - s * 0.55, cx + s * 0.6, cy - s * 0.05, cx, cy + s * 0.35)
    p.close(); return p

def flash(c, a, col='#FFFFFF'):
    if a > 0.002: c.drawPaint(P(hexc(col, a)))

# ---------------- beat grid ----------------
BEAT = 60 / 123.0
def beat(k): return 16.43 + k * BEAT  # k may be negative

# ======================================================================
# SCENE 1: HOOK (0 - 8.1)
# ======================================================================
PH_H = 860; PH_W = PH_H * 9 / 19.5
POST_W = PH_W - 28 - 24
POST_H = 64 + POST_W * 1.25 + 56
TARGET = 11
def scroll_pos(t):
    u = prog(t, 0.15, 2.0)
    return TARGET * POST_H * eo3(u) if u < 1 else TARGET * POST_H

def draw_post(c, x, y, w, i, t, color=False):
    hh = 64; ih = w * 1.25
    if color:
        mini_logo(c, x + 8, y + 20, 26)
        text(c, 'thefilmyspace', x + 64, y + 40, font('b', 17), hexc(WHITE))
        clip('reel_1').draw(c, x, y + hh, w, ih, t, 6)
        # footer
        u = prog(t, 3.0, 3.25)
        hs = 26 * (1 + 0.45 * math.sin(math.pi * u)) if 0 < u < 1 else 26
        c.drawPath(heart_path(x + 22, y + hh + ih + 28, hs), P(hexc(RED if t >= 3.0 else G4)))
        if u > 0:
            for k in range(8):
                ang = k * math.pi / 4; rr = 18 + 26 * eo3(u)
                c.drawCircle(x + 22 + math.cos(ang) * rr, y + hh + ih + 26 + math.sin(ang) * rr, 3.2 * (1 - u), P(hexc(SAND, 1 - u)))
        for k in (1, 2):
            c.drawCircle(x + 22 + k * 44, y + hh + ih + 28, 10, SP(hexc(G4), 3))
    else:
        c.drawCircle(x + 26, y + 33, 17, P(hexc(G3)))
        rrect(c, x + 54, y + 22, 120 + (i * 37) % 60, 10, 5, P(hexc(G3)))
        rrect(c, x + 54, y + 38, 70, 8, 4, P(hexc(G2)))
        sh = skia.GradientShader.MakeLinear([skia.Point(x, y + hh), skia.Point(x + w, y + hh + ih)], [hexc('#34343A'), hexc('#24242A')])
        rrect(c, x, y + hh, w, ih, 6, skia.Paint(AntiAlias=True, Shader=sh))
        # dull content shapes
        c.drawCircle(x + w * (0.3 + 0.4 * ((i * 0.61) % 1)), y + hh + ih * 0.45, w * 0.18, P(hexc('#3E3E46')))
        rrect(c, x + w * 0.15, y + hh + ih * 0.72, w * 0.7, 14, 7, P(hexc('#3A3A42')))
        for k in range(3):
            c.drawCircle(x + 22 + k * 44, y + hh + ih + 28, 10, SP(hexc(G3), 3))

def draw_phone(c, cx, cy, t, sc=1.0, grey_all=False):
    with Tx(c, s=sc, px=cx, py=cy):
        x, y = cx - PH_W / 2, cy - PH_H / 2
        # shadow
        c.drawRRect(skia.RRect.MakeRectXY(R(x + 10, y + 30, PH_W, PH_H), 60, 60), P(hexc('#000000', 0.55), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
        rrect(c, x, y, PH_W, PH_H, 60, P(hexc('#141417')))
        c.drawRRect(skia.RRect.MakeRectXY(R(x + 1, y + 1, PH_W - 2, PH_H - 2), 59, 59), SP(hexc('#3C3C44'), 2))
        sx, sy, sw, shh = x + 14, y + 14, PH_W - 28, PH_H - 28
        c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(sx, sy, sw, shh), 47, 47), True)
        c.drawRect(R(sx, sy, sw, shh), P(hexc('#0E0E11')))
        pos = scroll_pos(t)
        vel = (scroll_pos(t + 1 / 60) - scroll_pos(t - 1 / 60)) * 30
        blur = clamp(vel / 180, 0, 16)
        # top bar
        top = sy + 70
        with Layer(c, 1.0, (0, blur)):
            base = top + (shh - 70) / 2 - POST_H / 2 - TARGET * POST_H + (TARGET * POST_H - pos)
            # draw visible posts
            for i in range(TARGET + 3):
                py_ = base + i * POST_H + (TARGET * POST_H)  # careful: base already includes offset
                py_ = top + (shh - 70) / 2 - POST_H / 2 + i * POST_H - pos
                if py_ > sy + shh or py_ + POST_H < sy: continue
                draw_post(c, sx + 12, py_, POST_W, i, t, color=(i == TARGET and not grey_all))
        # app top bar
        c.drawRect(R(sx, sy, sw, 70), P(hexc('#0E0E11', 0.96)))
        text(c, 'Instagram', sx + 22, sy + 52, font('xb', 24), hexc(WHITE, 0.9))
        c.drawRect(R(sx + sw / 2 - 50, sy + 10, 100, 26), P(hexc('#000000')))  # island
        c.restore()

def scene_hook(c, t):
    c.drawPaint(P(hexc(BG)))
    # phone position
    u = eio3(prog(t, 1.95, 2.55))
    pcx = lerp(960, 1290, u)
    z = 1.0 + 0.07 * prog(t, 2.6, 7.4)
    a_in = eo3(prog(t, 0.0, 0.35))
    # exit: slide up with blur
    ex = ei3(prog(t, 7.45, 8.0))
    dy = -1300 * ex
    with Layer(c, 1.0, (0, 40 * ex)):
        with Tx(c, 0, dy + (1 - a_in) * 120):
            draw_phone(c, pcx, 540, t, z)
        # left text
        if t >= 2.0:
            lx = 560
            # "1 SECOND"
            a1 = 1 - prog(t, 6.0, 6.25)
            if a1 > 0:
                pu = eback(prog(t, 2.0, 2.35))
                with Layer(c, a1 * clamp(prog(t, 2.0, 2.12) * 1.5)):
                    with Tx(c, s=lerp(0.6, 1.0, pu), px=lx, py=470):
                        f1 = font('cond', 330)
                        text(c, '1', lx, cap_center_y(f1, 420), f1, hexc(SAND), 'c')
                        # timer ring - depletes in exactly 1 second
                        ru = prog(t, 2.0, 3.0)
                        c.drawCircle(lx, 420, 190, SP(hexc('#FFFFFF', 0.08), 10))
                        c.drawArc(R(lx - 190, 420 - 190, 380, 380), -90 + 360 * ru, 360 * (1 - ru), False, SP(hexc(RED), 10))
                        f2 = font('head', 92)
                        text(c, 'SECOND', lx, 760, f2, hexc(WHITE), 'c', track=6)
            if t >= 6.15:
                f3 = font('head', 112)
                lines = [('TO', WHITE), ('STOP THE', None), ('SCROLL.', WHITE)]
                for k, (s, col) in enumerate(lines):
                    uu = eo3(prog(t, 6.15 + k * 0.08, 6.5 + k * 0.08))
                    with Layer(c, uu):
                        y = 380 + k * 135 + (1 - uu) * 60
                        if s == 'STOP THE':
                            w1 = text_w('STOP ', f3)
                            tw = text_w('STOP THE', f3)
                            text(c, 'STOP', lx - tw / 2, y, f3, hexc(RED))
                            text(c, 'THE', lx - tw / 2 + w1, y, f3, hexc(WHITE))
                        else:
                            text(c, s, lx, y, f3, hexc(col), 'c')

# ======================================================================
# SCENE 2: PROBLEM (8.0 - 13.75) + riser to 15.7
# ======================================================================
def scene_problem(c, t):
    c.drawPaint(P(hexc(BG)))
    rows = [('PRODUCT', 8.16, 'check'), ('SERVICE', 9.90, 'check'), ('INSTAGRAM', 11.38, 'cross')]
    f = font('head', 118)
    dim = 1 - 0.88 * eo3(prog(t, 12.45, 12.75))
    out = prog(t, 13.45, 13.8)
    for k, (s, t0, kind) in enumerate(rows):
        if t < t0: continue
        u = eo3(prog(t, t0, t0 + 0.32))
        y = 330 + k * 190 + (1 - u) * 50
        shake = 0
        if kind == 'cross':
            su = prog(t, 11.86, 12.26)
            shake = math.sin(su * math.pi * 7) * 16 * (1 - su) if 0 < su < 1 else 0
        tw = text_w(s, f)
        x0 = 960 - (tw + 150) / 2 + shake
        col = WHITE if kind == 'cross' else '#9A9AA2'
        with Layer(c, u * dim * (1 - out)):
            text(c, s, x0, cap_center_y(f, y), f, hexc(col))
            ix = x0 + tw + 95
            cu = prog(t, t0 + 0.18, t0 + 0.45)
            if kind == 'check':
                c.drawCircle(ix, y, 46, SP(hexc('#9A9AA2', 0.35), 5))
                trimmed(c, check_path(ix, y, 48), SP(hexc('#C9C9CF'), 11), eo3(cu))
            else:
                c.drawCircle(ix, y, 46, P(hexc(RED, 0.18 * cu)))
                c.drawCircle(ix, y, 46, SP(hexc(RED, cu), 5))
                a_, b_ = cross_paths(ix, y, 40)
                trimmed(c, a_, SP(hexc(RED), 11), eo3(prog(cu, 0, 0.6) if cu < 1 else 1))
                trimmed(c, b_, SP(hexc(RED), 11), eo3(clamp((cu - 0.4) / 0.6)))
    # "nobody stops" - a dull post card that gets scrolled past
    if 12.45 <= t < 13.9:
        a = eo3(prog(t, 12.45, 12.7))
        fly = ei3(prog(t, 12.95, 13.35))
        y = 560 + (1 - a) * 80 - fly * 1100
        with Layer(c, a, (0, 60 * fly)):
            cw, ch = 520, 300
            x = 960 - cw / 2
            rrect(c, x, y - ch / 2, cw, ch, 22, P(hexc(G1)))
            c.drawRRect(skia.RRect.MakeRectXY(R(x, y - ch / 2, cw, ch), 22, 22), SP(hexc(G2), 2))
            c.drawPath(heart_path(x + 80, y - 20, 50), SP(hexc(G4), 5))
            fb = font('head', 64)
            text(c, '3', x + 130, cap_center_y(fb, y - 20), fb, hexc(G4))
            text(c, 'LIKES', x + 185, cap_center_y(font('b', 30), y - 20), font('b', 30), hexc(G3), track=3)
            c.drawCircle(x + 330, y - 20, 22, SP(hexc(G4), 5)); c.drawCircle(x + 330, y - 20, 7, P(hexc(G4)))
            text(c, '0', x + 375, cap_center_y(fb, y - 20), fb, hexc(G4))
            rrect(c, x + 50, y + 55, cw - 100, 14, 7, P(hexc(G2)))
            rrect(c, x + 50, y + 85, (cw - 100) * 0.6, 14, 7, P(hexc(G2)))

def scene_riser(c, t):
    c.drawPaint(P(hexc(BG)))
    u = prog(t, 13.8, 15.62)
    if u <= 0: return
    cols = [NAVY, RED, SAND]
    e = ei3(u)
    for i, col in enumerate(cols):
        x = 960 + (i - 1) * lerp(520, 228, e)
        h = lerp(0, 760, eo3(prog(t, 13.8 + i * 0.12, 15.1)))
        w = lerp(3, 10, e)
        with Layer(c, 0.35 + 0.65 * u):
            c.drawRect(R(x - w / 2, 540 - h / 2, w, h), P(hexc(col), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2 + 14 * e)))
            c.drawRect(R(x - w / 4, 540 - h / 2, w / 2, h), P(hexc(col)))
    # converge flash
    fu = prog(t, 15.5, 15.7)
    if fu > 0:
        c.drawCircle(960, 540, 600 * ei3(fu), P(hexc('#FFFFFF', 0.25 * fu), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 80)))

# ======================================================================
# SCENE 3: LOGO SLAM (15.7 - 20.45)
# ======================================================================
SLAM = 15.70
def scene_logo(c, t):
    c.drawPaint(P(hexc(BG)))
    # glow
    gu = eo3(prog(t, SLAM, SLAM + 0.8))
    rs = skia.GradientShader.MakeRadial(skia.Point(960, 500), 900, [hexc(NAVY, 0.35 * gu), hexc(BG, 0.0)])
    c.drawPaint(skia.Paint(Shader=rs))
    # burst lines
    bu = prog(t, SLAM, SLAM + 0.6)
    if 0 < bu < 1:
        for k in range(18):
            ang = k * 2 * math.pi / 18 + 0.1
            r0 = 300 + 900 * eo3(bu); r1 = r0 + 140 * (1 - bu)
            col = [NAVY_L, RED, SAND][k % 3]
            c.drawLine(960 + math.cos(ang) * r0, 500 + math.sin(ang) * r0, 960 + math.cos(ang) * r1, 500 + math.sin(ang) * r1, SP(hexc(col, 1 - bu), 6))
    shk = prog(t, SLAM, SLAM + 0.45)
    sx = math.sin(shk * 60) * 16 * (1 - shk) if 0 < shk < 1 else 0
    sy = math.cos(shk * 47) * 12 * (1 - shk) if 0 < shk < 1 else 0
    # exit morph to panels
    mu = eio3(prog(t, 19.72, 20.12))
    blocks = []
    for i in range(3):
        t0 = SLAM - 0.20 + i * 0.06
        u = prog(t, t0, t0 + 0.22)
        dy = -700 * (1 - eo3(u)) if u < 1 else 0
        blocks.append({'dy': dy, 'a': 1.0 if u > 0 else 0.0, 's': 1.0})
    with Tx(c, sx, sy):
        if mu <= 0:
            draw_logo(c, 960, 500, 1.0, blocks)
        else:
            total = 3 * LOGO_BW + 2 * LOGO_GAP
            for i, col in enumerate([NAVY, RED, SAND]):
                bx0 = 960 - total / 2 + i * (LOGO_BW + LOGO_GAP); by0 = 500 - LOGO_BH / 2
                x = lerp(bx0, i * 640, mu); y = lerp(by0, 0, mu); w = lerp(LOGO_BW, 641, mu); h = lerp(LOGO_BH, 1080, mu)
                c.drawRect(R(x, y, w, h), P(hexc(col)))
                if mu < 0.5:
                    f = font('head', 163 / 0.688)
                    text(c, 'TFS'[i], x + w / 2, cap_center_y(f, y + h / 2), f, hexc('#FFFFFF', 1 - mu * 2), 'c')
    # name reveal
    if 18.05 <= t < 19.9:
        f = font('xb', 46)
        s = 'THE FILMY SPACE'
        tw = text_w(s, f, 14)
        ru = eo3(prog(t, 18.05, 18.6))
        with Layer(c, 1 - prog(t, 19.6, 19.8)):
            c.save(); c.clipRect(R(960 - tw / 2 - 10, 700, (tw + 20) * ru, 90))
            text(c, s, 960, 770, f, hexc(WHITE), 'c', track=14)
            c.restore()
            c.drawRect(R(960 - tw / 2, 795, tw * ru, 4), P(hexc(SAND)))
    # slam flash
    fl = prog(t, SLAM, SLAM + 0.28)
    if 0 < fl < 1: flash(c, 0.55 * (1 - fl))

def panels_wipe(c, t):
    """three panels slide down revealing what is underneath"""
    for i, col in enumerate([NAVY, RED, SAND]):
        u = ei3(prog(t, 20.12 + i * 0.06, 20.45 + i * 0.06))
        if u >= 1: continue
        c.drawRect(R(i * 640, 1080 * u, 641, 1080), P(hexc(col)))

# ======================================================================
# SCENE 4: PROCESS (20.12 - 27.4)
# ======================================================================
STEPS = [('01', 'SCRIPT', 'Your brand story, written first.', NAVY_L, 20.23, 22.24),
         ('02', 'SHOOT', 'Shot with intent.', RED, 22.24, 23.48),
         ('03', 'EDIT', 'Cut to the beat.', SAND, 23.48, 24.28),
         ('04', 'POST', 'Published on plan. Every month.', '#6FB38A', 24.28, 27.4)]

def illo_script(c, t, t0, col):
    with Tx(c, 1340, 500, rot=-3):
        rrect(c, -270, -330, 540, 660, 18, P(hexc('#F4F1EA')))
        c.drawRect(R(-270, -330, 540, 80), P(hexc(NAVY)))
        text(c, 'SCRIPT  ·  BRAND STORY', -240, -278, font('b', 24), hexc(WHITE), track=2)
        lines = [0.9, 0.75, 0.85, 0.6, 0.0, 0.8, 0.9, 0.7, 0.5]
        tt = t - t0 - 0.1; cps = 24.0
        acc = 0.0
        for k, L in enumerate(lines):
            y = -200 + k * 56
            if L == 0: acc += 0.15; continue
            dur = L / 1.0 * (1.0 / cps) * 6
            u = clamp((tt - acc) / dur)
            acc += dur
            if u > 0:
                rrect(c, -230, y, 460 * L * u, 16, 8, P(hexc('#B9B4A8' if k != 0 else NAVY)))
                if 0 < u < 1:
                    c.drawRect(R(-230 + 460 * L * u + 6, y - 8, 4, 32), P(hexc(RED)))

def illo_shoot(c, t, t0, col):
    cx, cy = 1340, 500
    w, h = 430, 764 * 0.86
    x, y = cx - w / 2, cy - h / 2
    clip('restaurant_2').draw(c, x, y, w, h, t, 10)
    c.drawRect(R(x, y, w, h), P(hexc('#000000', 0.12)))
    L = 50
    for (px, py, dx, dy) in [(x - 20, y - 20, 1, 1), (x + w + 20, y - 20, -1, 1), (x - 20, y + h + 20, 1, -1), (x + w + 20, y + h + 20, -1, -1)]:
        p = skia.Path(); p.moveTo(px, py + dy * L); p.lineTo(px, py); p.lineTo(px + dx * L, py)
        c.drawPath(p, SP(hexc(WHITE), 6, cap=skia.Paint.kSquare_Cap))
    if int((t - t0) * 2.5) % 2 == 0:
        c.drawCircle(x + 34, y + 38, 11, P(hexc(RED)))
    text(c, 'REC', x + 54, y + 48, font('xb', 28), hexc(WHITE))
    fr = int((t - t0) * 30)
    text(c, f'00:00:{fr // 30:02d}:{fr % 30:02d}', x + w - 24, y + 48, font('b', 24), hexc(WHITE), 'r')
    # focus box snaps at shutter
    fu = prog(t, 22.36, 22.5)
    fs = lerp(220, 130, eback(fu))
    c.drawRect(R(cx - fs / 2, cy - fs / 2, fs, fs), SP(hexc('#FFD54A' if fu >= 1 else WHITE), 4, cap=skia.Paint.kSquare_Cap))
    fl = prog(t, 22.48, 22.68)
    if 0 < fl < 1: c.drawRect(R(x, y, w, h), P(hexc('#FFFFFF', 0.7 * (1 - fl))))

def illo_edit(c, t, t0, col):
    # monitor
    mx, my, mw, mh = 1340 - 210, 160, 420, 240
    rrect(c, mx - 12, my - 12, mw + 24, mh + 24, 14, P(hexc(G1)))
    clip('events_3').draw(c, mx, my, mw, mh, t, 6)
    # timeline panel
    px, py, pw, ph = 900, 450, 880, 360
    rrect(c, px, py, pw, ph, 18, P(hexc(G1)))
    c.drawRRect(skia.RRect.MakeRectXY(R(px, py, pw, ph), 18, 18), SP(hexc(G2), 2))
    tracks = ['V2', 'V1', 'A1']
    for k, nm in enumerate(tracks):
        ty = py + 40 + k * 100
        text(c, nm, px + 24, ty + 42, font('b', 22), hexc(G4))
        c.drawRect(R(px + 80, ty, pw - 110, 70), P(hexc('#16161A')))
    blocks = [(0, 0.00, 0.30, NAVY_L), (0, 0.38, 0.22, RED), (1, 0.0, 0.18, SAND), (1, 0.2, 0.34, NAVY_L), (1, 0.56, 0.28, RED), (2, 0.0, 0.86, '#6FB38A'), (0, 0.64, 0.2, SAND)]
    for j, (tr, st, ln, cc) in enumerate(blocks):
        u = prog(t, t0 + 0.04 + j * 0.07, t0 + 0.3 + j * 0.07)
        if u <= 0: continue
        x = px + 80 + (pw - 110) * st + (1 - eback(u, 2.2)) * 500
        y = py + 40 + tr * 100
        with Layer(c, clamp(u * 3)):
            rrect(c, x + 2, y + 6, (pw - 110) * ln - 4, 58, 8, P(hexc(cc)))
            if tr == 2:
                for q in range(60):
                    hh = 8 + 18 * abs(math.sin(q * 0.7 + 1.3) * math.cos(q * 0.23))
                    c.drawRect(R(x + 12 + q * 12, y + 35 - hh / 2, 5, hh), P(hexc('#0E2A1B', 0.6)))
    ph_x = px + 80 + (pw - 110) * prog(t, t0, t0 + 3.0)
    c.drawRect(R(ph_x - 2, py + 22, 4, ph - 40), P(hexc(WHITE)))
    c.drawCircle(ph_x, py + 22, 9, P(hexc(WHITE)))

POST_DAYS = [1, 3, 5, 8, 10, 12, 15, 17, 19, 22, 24, 26, 29]
def illo_post(c, t, t0, col):
    x, y, w, h = 930, 170, 820, 660
    rrect(c, x, y, w, h, 22, P(hexc(G1)))
    c.drawRRect(skia.RRect.MakeRectXY(R(x, y, w, h), 22, 22), SP(hexc(G2), 2))
    text(c, 'CONTENT CALENDAR', x + 36, y + 62, font('xb', 30), hexc(WHITE), track=3)
    text(c, 'THIS MONTH', x + w - 36, y + 62, font('b', 22), hexc(G4), 'r', track=2)
    days = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
    cw = (w - 72) / 7; chh = 92
    for k, d in enumerate(days):
        text(c, d, x + 36 + cw * k + cw / 2, y + 120, font('b', 20), hexc(G4), 'c')
    for d in range(1, 31):
        r_, k = divmod(d - 1 + 2, 7)
        cx_ = x + 36 + cw * k; cy_ = y + 140 + r_ * chh
        is_post = d in POST_DAYS
        pi = POST_DAYS.index(d) if is_post else -1
        tick_t = 24.70 + pi * 0.13
        u = prog(t, tick_t, tick_t + 0.18) if is_post else 0
        base = '#232329'
        rrect(c, cx_ + 4, cy_ + 4, cw - 8, chh - 8, 10, P(hexc(base)))
        if u > 0:
            with Tx(c, s=lerp(0.6, 1.0, eback(u)), px=cx_ + cw / 2, py=cy_ + chh / 2):
                rrect(c, cx_ + 4, cy_ + 4, cw - 8, chh - 8, 10, P(hexc(col, 0.95)))
                trimmed(c, check_path(cx_ + cw / 2, cy_ + chh / 2 + 6, 26), SP(hexc('#0B1A11'), 6), prog(t, tick_t + 0.05, tick_t + 0.25))
        text(c, str(d), cx_ + 14, cy_ + 30, font('b', 17), hexc('#0B1A11' if u > 0.5 else G4))
    # notification
    nu = prog(t, 26.35, 26.6)
    if nu > 0:
        ny = lerp(-160, 60, eback(nu))
        with Layer(c, clamp(nu * 2)):
            rrect(c, 1340 - 300, ny, 600, 110, 26, P(hexc('#F4F1EA')))
            mini_logo(c, 1340 - 270, ny + 34, 42)
            text(c, 'thefilmyspace', 1340 - 180, ny + 50, font('xb', 26), hexc('#111111'))
            text(c, 'Your post is live  ·  just now', 1340 - 180, ny + 84, font('m', 22), hexc('#555555'))

ILLOS = [illo_script, illo_shoot, illo_edit, illo_post]

def scene_process(c, t):
    c.drawPaint(P(hexc(BG)))
    cur = 0
    for k, s in enumerate(STEPS):
        if t >= s[4]: cur = k
    # step labels (left)
    for k, (num, name, sub, col, t0, t1) in enumerate(STEPS):
        a_in = eo3(prog(t, t0, t0 + 0.3)); a_out = prog(t, t1 - 0.05, t1 + 0.2) if k < 3 else 0
        if a_in <= 0 or a_out >= 1: continue
        with Layer(c, a_in * (1 - a_out)):
            dx = (1 - a_in) * -60 - a_out * 60
            fN = font('cond', 120)
            text(c, num, 150 + dx, 360, fN, hexc(col))
            fH = font('head', 150 if name != 'SCRIPT' else 138)
            text(c, name, 150 + dx, 540, fH, hexc(WHITE))
            text(c, sub, 154 + dx, 610, font('m', 36), hexc(G4))
        # illustration
        with Layer(c, a_in * (1 - a_out)):
            with Tx(c, (1 - a_in) * 220 - a_out * 220, 0):
                ILLOS[k](c, t, t0, col)
    # bottom track
    xs = [180, 520, 860, 1200]
    y = 900
    c.drawLine(xs[0], y, xs[-1], y, SP(hexc(G2), 4))
    fill_to = 0
    for k, s in enumerate(STEPS):
        if t >= s[4]: fill_to = k + eo3(prog(t, s[4], s[4] + 0.3)) - 1 if k > 0 else 0
    fill_to = clamp(fill_to, 0, 3)
    xf = lerp(xs[int(fill_to)], xs[min(3, int(fill_to) + 1)], fill_to - int(fill_to)) if fill_to < 3 else xs[3]
    c.drawLine(xs[0], y, xf, y, SP(hexc(WHITE), 4))
    for k, (num, name, sub, col, t0, t1) in enumerate(STEPS):
        on = t >= t0
        c.drawCircle(xs[k], y, 13, P(hexc(col if on else G2)))
        if k == cur: c.drawCircle(xs[k], y, 22, SP(hexc(col, 0.6), 3))
        text(c, name, xs[k], y + 52, font('xb', 22), hexc(WHITE if on else G3), 'c', track=3)
    # exit
    ex = prog(t, 27.05, 27.4)
    if ex > 0: flash(c, ei3(ex) * 0.0)

# ======================================================================
# SCENE 5: PROOF (27.3 - 37.15)
# ======================================================================
CATSEQ = [('RESTAURANTS', 28.92, 'restaurant'), ('GYMS', 29.90, 'gym'), ('COACHING', 30.72, 'coaching'), ('EVENTS', 32.10, 'events')]
CARD_W, CARD_H = 400, 711
def three_cards(c, t, slots, enter_ts, scale=1.0, alpha=1.0, swap_t=None):
    xs = [560, 960, 1360]
    for k in range(3):
        u = eo5(prog(t, enter_ts[k], enter_ts[k] + 0.45)) if enter_ts else 1
        if u <= 0: continue
        y = 540 + (1 - u) * 900
        rot = (k - 1) * 3.0 * (1 - u)
        with Layer(c, alpha):
            with Tx(c, rot=rot, s=scale, px=xs[k], py=y):
                c.drawRRect(skia.RRect.MakeRectXY(R(xs[k] - CARD_W / 2 + 8, y - CARD_H / 2 + 24, CARD_W, CARD_H), 24, 24),
                            P(hexc('#000000', 0.6), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 24)))
                clip(slots[k]).draw(c, xs[k] - CARD_W / 2, y - CARD_H / 2, CARD_W, CARD_H, t + k * 0.7, 24)

def scene_proof(c, t):
    c.drawPaint(P(hexc(BG)))
    if t < 33.0:
        # category behind text
        cat = None
        for name, t0, key in CATSEQ:
            if t >= t0: cat = (name, t0, key)
        if cat:
            name, t0, key = cat
            slots = [f'{key}_{i}' for i in (1, 2, 3)]
        else:
            slots = ['reel_2', 'reel_3', 'reel_4']
        ent = [27.33, beat(-10) if False else 27.70, 28.08]
        # swap punch on category change
        punch = 0
        for _, t0, _ in CATSEQ:
            pu = prog(t, t0, t0 + 0.25)
            if 0 < pu < 1: punch = math.sin(pu * math.pi) * 0.04
        ex = prog(t, 32.75, 33.05)
        three_cards(c, t, slots, ent, scale=1.0 + punch - 0.15 * ei3(ex), alpha=1 - ex)
        if cat:
            name, t0, key = cat
            u = eo3(prog(t, t0, t0 + 0.28))
            sh = skia.GradientShader.MakeLinear([skia.Point(0, 640), skia.Point(0, 1080)], [hexc(BG, 0.0), hexc(BG, 0.92)])
            c.drawRect(R(0, 640, 1920, 440), skia.Paint(Shader=sh, Alphaf=1 - ex))
            f = font('cond', 210)
            with Layer(c, u * (1 - ex)):
                with Tx(c, s=lerp(1.15, 1.0, u), px=960, py=900):
                    text(c, name, 960 + 6, 968 + 6, f, hexc('#000000', 0.5), 'c', track=8)
                    text(c, name, 960, 968, f, hexc(SAND), 'c', track=8)
    else:
        # grid of 20 brand tiles + counter
        n_vis = int(clamp(20 * eo3(prog(t, 33.0, 34.4)) + 0.0001, 0, 20))
        cnt = int(round(20 * eo3(prog(t, 33.0, 34.4))))
        tw_, th_, g = 150, 266, 16
        cols = 10
        x0 = 960 - (cols * tw_ + (cols - 1) * g) / 2; y0 = 540 - (2 * th_ + g) / 2
        dim = 0.32 + 0.68 * eo3(prog(t, 35.95, 36.3))
        zu = eio3(prog(t, 36.8, 37.15))
        with Tx(c, s=1 + 2.6 * zu, px=960, py=540):
            for i in range(20):
                ti = 33.0 + 1.4 * (1 - (1 - i / 20) ** (1 / 3)) if i else 33.0
                u = eback(prog(t, ti, ti + 0.25))
                if prog(t, ti, ti + 0.25) <= 0: continue
                r_, k = divmod(i, cols)
                x = x0 + k * (tw_ + g); y = y0 + r_ * (th_ + g)
                with Tx(c, s=lerp(0.5, 1.0, u), px=x + tw_ / 2, py=y + th_ / 2):
                    clip(f'tile_{i}').draw(c, x, y, tw_, th_, t + i * 0.3, 12)
                    c.drawRRect(skia.RRect.MakeRectXY(R(x, y, tw_, th_), 12, 12), P(hexc(BG, 1 - dim)))
        ca = 1 - eo3(prog(t, 35.9, 36.25))
        if ca > 0:
            with Layer(c, ca):
                f = font('cond', 400)
                s = f'{cnt}+' if cnt >= 20 else f'{cnt}'
                text(c, s, 960, cap_center_y(f, 500), f, hexc(SAND), 'c')
                text(c, 'BRANDS', 960, 800, font('head', 96), hexc(WHITE), 'c', track=10)

# ======================================================================
# SCENE 6: BEAT MONTAGE (37.1 - 39.62) and SCENE 8 BURST (45.25-50.3)
# ======================================================================
def beat_cut_index(t, t_start):
    k0 = math.ceil((t_start - 16.43) / BEAT)
    k = int(math.floor((t - 16.43) / BEAT))
    return max(0, k - k0), beat(k)

def montage_frame(c, t, slot, layout, tk):
    c.drawPaint(P(hexc(BG)))
    cu = prog(t, tk, tk + 0.35)
    z = 1.06 - 0.06 * eo3(cu)
    src = clip(slot)
    if layout == 'center':
        # blurred bg
        with Layer(c, 0.55, (40, 40)):
            src.draw(c, -100, -100, 2120, 1280, t)
        with Tx(c, s=z, px=960, py=540):
            src.draw(c, 960 - 304, 0, 608, 1080, t)
    elif layout == 'full':
        with Tx(c, s=z, px=960, py=540):
            src.draw(c, 0, 0, 1920, 1080, t)
    elif layout == 'three':
        for k in range(3):
            clip(slot + f'_{k}').draw(c, 40 + k * 627, 40, 587, 1000, t + k * 0.5, 18)
    f = prog(t, tk, tk + 0.12)
    if f < 1: flash(c, 0.35 * (1 - f))

MONT1 = ['reel_5', 'gym_4', 'restaurant_4', 'coaching_4', 'events_4', 'reel_6']
def scene_montage1(c, t):
    i, tk = beat_cut_index(t, 37.10)
    slot = MONT1[i % len(MONT1)]
    montage_frame(c, t, slot, 'center', max(tk, 37.10))

BURST = [('reel_7', 'full'), ('restaurant_5', 'center'), ('burst_a', 'three'), ('gym_5', 'full'), ('events_5', 'center'),
         ('coaching_5', 'full'), ('burst_b', 'three'), ('reel_8', 'center'), ('retail_1', 'full'), ('events_6', 'full'), ('reel_9', 'center')]
def scene_burst(c, t):
    i, tk = beat_cut_index(t, 45.25)
    slot, lay = BURST[i % len(BURST)]
    montage_frame(c, t, slot, lay, max(tk, 45.25))
    # end fade to black
    e = prog(t, 49.9, 50.3)
    if e > 0: c.drawPaint(P(hexc('#000000', ei3(e))))

# ======================================================================
# SCENE 7: SERVICES (39.62 - 45.25)
# ======================================================================
SERV = [('CONCEPT', 'VIDEOS', 39.65, NAVY, 'reel_10'), ('MODEL AD', 'SHOOTS', 40.68, RED, 'reel_11'),
        ('REELS', '', 42.38, SAND, 'reel_12'), ('PHOTO', 'POSTS', 43.04, NAVY_L, 'reel_13')]
def scene_services(c, t):
    c.drawPaint(P(hexc(BG)))
    xs = [300, 740, 1180, 1620]
    gather = eio3(prog(t, 43.9, 44.5))
    for k, (l1, l2, t0, col, slot) in enumerate(SERV):
        u = eo5(prog(t, t0, t0 + 0.45))
        if u <= 0: continue
        cw, ch = 390, 560
        x = lerp(xs[k], 960 + (k - 1.5) * 60, gather)
        rot = lerp(0, (k - 1.5) * 7, gather)
        y = 520 + (1 - u) * 700 + gather * 20
        with Layer(c, clamp(u * 2) * (1 - 0.0 * gather)):
            with Tx(c, rot=rot, s=lerp(1, 0.92, gather), px=x, py=y + 300):
                c.drawRRect(skia.RRect.MakeRectXY(R(x - cw / 2 + 6, y - ch / 2 + 20, cw, ch), 22, 22),
                            P(hexc('#000000', 0.6), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)))
                c.save(); c.clipRRect(skia.RRect.MakeRectXY(R(x - cw / 2, y - ch / 2, cw, ch), 22, 22), True)
                clip(slot).draw(c, x - cw / 2, y - ch / 2, cw, ch - 150, t + k)
                c.drawRect(R(x - cw / 2, y + ch / 2 - 150, cw, 150), P(hexc(col)))
                tc = '#111111' if col == SAND else WHITE
                f = font('head', 42)
                if l2:
                    text(c, l1, x - cw / 2 + 28, y + ch / 2 - 88, f, hexc(tc))
                    text(c, l2, x - cw / 2 + 28, y + ch / 2 - 36, f, hexc(tc))
                else:
                    text(c, l1, x - cw / 2 + 28, y + ch / 2 - 62, f, hexc(tc))
                c.restore()
    # ONE TEAM
    ou = prog(t, 44.82, 45.1)
    if ou > 0:
        with Layer(c, eo3(ou)):
            c.drawPaint(P(hexc(BG, 0.55 * eo3(ou))))
            f = font('head', 170)
            s1 = 'ONE TEAM'
            tw = text_w(s1 + '.', f)
            with Tx(c, s=lerp(1.25, 1.0, eo3(ou)), px=960, py=540):
                text(c, s1, 960 - tw / 2, cap_center_y(f, 540), f, hexc(WHITE))
                text(c, '.', 960 - tw / 2 + text_w(s1, f), cap_center_y(f, 540), f, hexc(RED))

# ======================================================================
# SCENE 9: END LOGO (50.3 - 60)
# ======================================================================
END_DROPS = [beat(70), beat(71), beat(72)]  # ~50.58, 51.06, 51.55
def scene_end(c, t):
    c.drawPaint(P(hexc('#000000')))
    blocks = []
    for i in range(3):
        u = prog(t, END_DROPS[i] - 0.18, END_DROPS[i])
        blocks.append({'dy': -620 * (1 - eo3(u)) if u < 1 else 0, 'a': 1.0 if u > 0 else 0.0,
                       's': 1.0 + 0.06 * math.sin(math.pi * prog(t, END_DROPS[i], END_DROPS[i] + 0.2))})
    z = 1.0 + 0.045 * eo3(prog(t, END_DROPS[2], 60.0))
    shk = prog(t, END_DROPS[2], END_DROPS[2] + 0.35)
    sx = math.sin(shk * 50) * 10 * (1 - shk) if 0 < shk < 1 else 0
    with Tx(c, sx, 0, s=z, px=960, py=540):
        draw_logo(c, 960, 540, 1.0, blocks)
    fl = prog(t, END_DROPS[2], END_DROPS[2] + 0.3)
    if 0 < fl < 1: flash(c, 0.35 * (1 - fl))

# ======================================================================
# timeline
# ======================================================================
def draw_frame(c, t):
    if t < 8.0:
        scene_hook(c, t)
        if t >= 7.75:  # crossfade into problem bg
            pass
    elif t < 13.8:
        scene_problem(c, t)
    elif t < SLAM - 0.2:
        scene_riser(c, t)
    elif t < 20.12:
        if t < SLAM:
            scene_riser(c, t)
            # blocks start dropping during last 0.2s handled by logo; overlay
            with Layer(c, 1.0):
                scene_logo_blocks_only(c, t)
        else:
            scene_logo(c, t)
    elif t < 20.6:
        scene_process(c, t)
        panels_wipe(c, t)
    elif t < 27.33:
        scene_process(c, t)
        e = prog(t, 27.05, 27.33)
        if e > 0:
            c.drawPaint(P(hexc(BG, ei3(e))))
    elif t < 37.10:
        scene_proof(c, t)
    elif t < 39.62:
        scene_montage1(c, t)
    elif t < 45.25:
        scene_services(c, t)
        s = prog(t, 39.62, 39.8)
        if s < 1: flash(c, 0.4 * (1 - s))
    elif t < 50.3:
        scene_burst(c, t)
    else:
        scene_end(c, t)

def scene_logo_blocks_only(c, t):
    blocks = []
    for i in range(3):
        t0 = SLAM - 0.20 + i * 0.06
        u = prog(t, t0, t0 + 0.22)
        blocks.append({'dy': -700 * (1 - eo3(u)) if u < 1 else 0, 'a': 1.0 if u > 0 else 0.0, 's': 1.0})
    draw_logo(c, 960, 500, 1.0, blocks)

# ---------------- finishing: grain + vignette ----------------
_grain = None
def finishing(c, t, W, H):
    global _grain
    if _grain is None:
        rng = np.random.default_rng(7)
        _grain = []
        for k in range(6):
            n = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
            a = np.stack([n, n, n, np.full_like(n, 255)], -1)
            _grain.append(skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType))
    g = _grain[int(t * 24) % len(_grain)]
    p = skia.Paint(BlendMode=skia.BlendMode.kOverlay); p.setAlphaf(0.07)
    c.drawImageRect(g, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    rs = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.62, [hexc('#000000', 0.0), hexc('#000000', 0.0), hexc('#000000', 0.5)], [0.0, 0.62, 1.0])
    c.drawPaint(skia.Paint(Shader=rs))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='out.mp4'); ap.add_argument('--w', type=int, default=1920)
    ap.add_argument('--fps', type=int, default=30); ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=60)
    ap.add_argument('--stills', default=''); ap.add_argument('--crf', type=int, default=18)
    a = ap.parse_args()
    W = a.w; H = W * 9 // 16; S = W / W0
    surf = skia.Surface(W, H); c = surf.getCanvas()
    def render(t):
        c.save(); c.scale(S, S)
        c.clear(hexc(BG)); draw_frame(c, t)
        c.restore(); finishing(c, t, W, H)
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s); arr = render(t)
            skia.Image.fromarray(arr, colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'stills', f'{t:06.2f}.png'))
        return
    n0 = int(round(a.start * a.fps)); n1 = int(round(a.end * a.fps))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        t = n / a.fps
        pr.stdin.write(render(t).tobytes())
        if n % (a.fps * 5) == 0: print(f'{t:.1f}s', flush=True)
    pr.stdin.close(); pr.wait()

if __name__ == '__main__':
    main()
