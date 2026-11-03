# Funhoods "PVC Racing Car (PVC-3301)" B2B reel -- 2160x3840 @ 60 fps. Motion graphics on the white backdrop of the
# earlier Funhoods reels; product and box shots are graded cut-outs of the client's phone photos (tools/prep_assets.py).
# How the toy works (push & let go, press the roof for lights & music) is animated -- no footage is used.
# Layout is written in a 1080x1920 design space; every primitive scales by T.K.
import sys, os, math, json, argparse, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
FONTS = os.environ.get('FONTS', os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts'))
K, DW, DH = T.K, T.DW, T.DH
W, H, FPS = DW * K, DH * K, T.FPS

RED = (210, 24, 31); DRED = (120, 6, 14); ORANGE = (255, 162, 58); YEL = (255, 212, 0)
WHITE = (255, 255, 255); CREAM = (255, 248, 236); INK = (40, 22, 22); SKY = (40, 160, 226)
GOLD = (255, 186, 0); LIME = (118, 190, 38)
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
F_IMPACT = os.path.join(FONTS, 'LuckiestGuy-Regular.ttf')
F_BODY = os.path.join(FONTS, 'Inter-ExtraBold.ttf')

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b_=1.0): return max(a, min(b_, x))
def e_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def e_in(x): x = clamp(x); return x * x
def e_inout(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def e_back(x, s=1.9):
    x = clamp(x); c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def prog(t, t0, d): return clamp((t - t0) / d)
def lerp(a, b, u): return a + (b - a) * u

class SD:
    """ImageDraw in design units. Translucent colours are drawn on a small layer and alpha-composited
    (ImageDraw on an RGBA image would overwrite the alpha instead of blending)."""
    def __init__(self, img): self.img = img; self.d = ImageDraw.Draw(img)
    def _go(self, bbox, fn, kw, grow=0):
        col = kw.get('fill') if kw.get('fill') is not None else kw.get('outline')
        if col is None or len(col) < 4 or col[3] >= 255: fn(self.d, 0, 0); return
        if col[3] <= 0: return
        g = grow + 4; x0, y0 = max(0, int(bbox[0] - g)), max(0, int(bbox[1] - g))
        x1, y1 = min(self.img.width, int(bbox[2] + g) + 1), min(self.img.height, int(bbox[3] + g) + 1)
        if x1 <= x0 or y1 <= y0: return
        lay = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0)); fn(ImageDraw.Draw(lay), x0, y0)
        self.img.alpha_composite(lay, (x0, y0))
    @staticmethod
    def _bb(pts): xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; return min(xs), min(ys), max(xs), max(ys)
    def _p(self, pts): return [(x * K, y * K) for x, y in pts]
    def polygon(self, pts, **kw):
        q = self._p(pts); self._go(self._bb(q), lambda d, ox, oy: d.polygon([(x - ox, y - oy) for x, y in q], **kw), kw)
    def ellipse(self, box, width=0, **kw):
        b = [v * K for v in box]; w_ = int(width * K)
        self._go(b, lambda d, ox, oy: d.ellipse([b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], width=w_, **kw), kw)
    def rectangle(self, box, **kw):
        b = [v * K for v in box]; self._go(b, lambda d, ox, oy: d.rectangle([b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], **kw), kw)
    def rrect(self, box, r, width=0, **kw):
        b = [v * K for v in box]; w_ = int(width * K)
        self._go(b, lambda d, ox, oy: d.rounded_rectangle([b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], r * K, width=w_, **kw), kw)
    def line(self, pts, width=1, **kw):
        q = self._p(pts); w_ = int(width * K)
        self._go(self._bb(q), lambda d, ox, oy: d.line([(x - ox, y - oy) for x, y in q], width=w_, **kw), kw, w_)
    def arc(self, box, start, end, width=1, **kw):
        b = [v * K for v in box]; w_ = int(width * K)
        self._go(b, lambda d, ox, oy: d.arc([b[0] - ox, b[1] - oy, b[2] - ox, b[3] - oy], start, end, width=w_, **kw), kw)

# ---------------------------------------------------------------- text
@functools.lru_cache(maxsize=None)
def font(path, size): return ImageFont.truetype(path, size)

@functools.lru_cache(maxsize=512)
def text_img(txt, path, size, fill=WHITE, stroke=0, stroke_fill=DRED, extrude=0, ext_fill=DRED, maxw=980):
    """size/stroke/extrude/maxw in design units"""
    fs, st, ex, mw = int(size * K), int(stroke * K), int(extrude * K), maxw * K
    f = font(path, fs)
    l, t_, r, bt = f.getbbox(txt, stroke_width=st)
    if r - l + ex > mw:
        return text_img(txt, path, size * mw / (r - l + ex) - 0.5, fill, stroke, stroke_fill, extrude, ext_fill, maxw)
    pad = st + 6 * K
    im = Image.new('RGBA', (r - l + 2 * pad + ex, bt - t_ + 2 * pad + ex), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(ex, 0, -1):
        d.text((pad - l + i, pad - t_ + i), txt, font=f, fill=ext_fill, stroke_width=st, stroke_fill=ext_fill)
    d.text((pad - l, pad - t_), txt, font=f, fill=fill, stroke_width=st, stroke_fill=stroke_fill)
    return im

@functools.lru_cache(maxsize=128)
def chip(txt, size=46, bg=YEL, fg=DRED, path=F_BODY, padx=34, pady=18, shadow=True):
    t = text_img(txt, path, size, fill=fg)
    px, py = padx * K, pady * K
    w, h = t.width + 2 * px, t.height + 2 * py; r = h // 2; o = 8 * K
    im = Image.new('RGBA', (w + 2 * o, h + 2 * o), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((o, o + 6 * K, w + o, h + o + 6 * K), r, fill=(60, 0, 0, 120))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * K)))
    ImageDraw.Draw(im).rounded_rectangle((o, o, w + o, h + o), r, fill=bg)
    im.alpha_composite(t, (o + px, o + py))
    return im

# white-theme type: red headlines with a dark-red extrude, yellow lines with a red outline
def head(txt, size=118, col=RED):
    ext = max(4, round(size * 0.05))
    if col == YEL: return text_img(txt, F_HEAD, size, YEL, 4, RED, ext + 4, DRED)
    return text_img(txt, F_HEAD, size, col, 0, DRED, ext, DRED)
def impact_txt(txt, size=250, col=YEL):
    if col == YEL: return text_img(txt, F_IMPACT, size, YEL, 6, RED, 14, DRED)
    return text_img(txt, F_IMPACT, size, col, 0, DRED, 11, DRED)
def body(txt, size=46, col=RED): return text_img(txt, F_BODY, size, col, 0)

def place(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0, sy=None):
    """cx, cy in design units; img in output pixels; sy = separate vertical scale (squash & stretch)"""
    if alpha <= 0.003 or scale <= 0.01: return
    im = img; sy = scale if sy is None else sy
    if abs(scale - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * sy))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    x, y = int(round(cx * K - im.width / 2)), int(round(cy * K - im.height / 2))
    sx, sy_ = max(0, -x), max(0, -y); x0, y0 = max(0, x), max(0, y)
    w_, h_ = min(im.width - sx, W - x0), min(im.height - sy_, H - y0)
    if w_ <= 0 or h_ <= 0: return
    canvas.alpha_composite(im, (x0, y0), (sx, sy_, sx + w_, sy_ + h_))

def pop(canvas, img, cx, cy, t, t0, t1=None, d=0.46, rot=0.0, from_scale=0.6, slide=0):
    if t < t0: return
    p = prog(t, t0, d)
    s = from_scale + (1 - from_scale) * e_back(p, 1.4)
    a = clamp(p / 0.35)
    if t1 is not None and t > t1 - 0.16:
        q = prog(t, t1 - 0.16, 0.16); s *= 1 - 0.35 * q; a *= 1 - q
    place(canvas, img, cx, cy + slide * (1 - e_out(p)), s, rot, a)

# ---------------------------------------------------------------- backgrounds
@functools.lru_cache(maxsize=1)
def halftone():
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im); g = 36 * K
    for y in range(0, H, g):
        for x in range(0, W, g):
            ox = g // 2 if (y // g) % 2 else 0
            rr = (3 + 7 * (y / H)) * K
            d.ellipse((x + ox - rr, y - rr, x + ox + rr, y + rr), fill=255)
    return im

@functools.lru_cache(maxsize=1)
def _radial():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
    return np.clip(1.08 - r * 1.05, 0.55, 1.05).astype(np.float32)

@functools.lru_cache(maxsize=3)     # consecutive frames share k; a small cache keeps 4 parallel renders in memory
def sunburst_light(k):
    S = 2300 * K; n = 24
    im = Image.new('RGB', (S, S), (255, 255, 255)); d = ImageDraw.Draw(im)
    c = S / 2; off = (k / 30) * (360 / n)
    for i in range(0, n, 2):
        a0 = math.radians(i * 360 / n + off); a1 = math.radians((i + 1) * 360 / n + off)
        d.polygon([(c, c), (c + 2 * S * math.cos(a0), c + 2 * S * math.sin(a0)), (c + 2 * S * math.cos(a1), c + 2 * S * math.sin(a1))], fill=(255, 246, 243))
    im = im.crop(((S - W) // 2, (S - H) // 2 - 120 * K, (S - W) // 2 + W, (S - H) // 2 - 120 * K + H))
    arr = np.asarray(im).astype(np.float32)
    v = np.clip(1.0 - 0.06 * np.maximum(0, (1 - _radial() / 1.05)), 0.97, 1.0)[..., None]
    arr = arr * v
    ht = np.asarray(halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.035 * ht) + np.array(RED, np.float32) * 0.035 * ht
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def bg(t): return sunburst_light(int((t * 6) % 30)).convert('RGBA')

@functools.lru_cache(maxsize=1)
def cream_bg():
    arr = np.ones((H, W, 3), np.float32) * np.array(CREAM, np.float32)
    ht = np.asarray(halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.07 * ht) + np.array(RED, np.float32) * 0.07 * ht
    return Image.fromarray(arr.astype(np.uint8)).convert('RGBA')

# ---------------------------------------------------------------- assets
@functools.lru_cache(maxsize=None)
def asset(name): return Image.open(P('assets', name)).convert('RGBA')

@functools.lru_cache(maxsize=None)
def scaled(name, h=None, w=None):
    """asset resized to a height or width given in design units"""
    im = asset(name)
    s = h * K / im.height if h else w * K / im.width
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

def drop_shadow(im, blur=18, dy=26, alpha=110, pad=60):
    pad *= K; out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (60, 0, 0, 255)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * alpha / 255)))
    lay = Image.new('RGBA', out.size, (0, 0, 0, 0)); lay.alpha_composite(sh, (pad + 10 * K, pad + dy * K))
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * K)))
    out.alpha_composite(im, (pad, pad))
    return out

@functools.lru_cache(maxsize=None)
def with_shadow(name, h, blur=18, dy=26, alpha=110):
    return drop_shadow(scaled(name, h=h), blur, dy, alpha)

@functools.lru_cache(maxsize=None)
def logo_sticker(width):
    lg = asset('logo_rgba.png'); s = width * K / lg.width
    lg = lg.resize((int(width * K), int(lg.height * s)), Image.LANCZOS)
    pad, o = 34 * K, 15 * K
    im = Image.new('RGBA', (lg.width + 2 * pad + 2 * o, lg.height + 2 * pad + 2 * o), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((o, o + 12 * K, o + lg.width + 2 * pad, o + 12 * K + lg.height + 2 * pad), 40 * K, fill=(50, 0, 0, 130))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12 * K)))
    ImageDraw.Draw(im).rounded_rectangle((o, o, o + lg.width + 2 * pad, o + lg.height + 2 * pad), 40 * K, fill=WHITE)
    im.alpha_composite(lg, (o + pad, o + pad))
    return im

@functools.lru_cache(maxsize=8)
def burst(size, spikes=18, fill=YEL, inner=WHITE, outline=DRED):
    S = size * K; im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = S / 2
    def star(r0, r1, col):
        pts = []
        for i in range(spikes * 2):
            a = math.pi * i / spikes; r = (r1 if i % 2 == 0 else r0) * (1 + 0.06 * math.sin(i * 2.3))
            pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        d.polygon(pts, fill=col)
    star(S * 0.33, S * 0.5, outline); star(S * 0.30, S * 0.46, fill); star(S * 0.20, S * 0.30, inner)
    return im
def soft_burst(size): return burst(size, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40))

def sparkles(c, t, seed, cx, cy, rx, ry, n=10, size=34):
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        x = cx + rng.uniform(-rx, rx); y = cy + rng.uniform(-ry, ry); ph = rng.uniform(0, 6.28); sp = rng.uniform(2.5, 4.5)
        a = math.sin(t * sp + ph)
        if a < 0.08: continue
        s = size * (0.4 + 0.6 * a)
        pts = [(x, y - s), (x + s * .22, y - s * .22), (x + s, y), (x + s * .22, y + s * .22), (x, y + s), (x - s * .22, y + s * .22), (x - s, y), (x - s * .22, y - s * .22)]
        sd.polygon(pts, fill=GOLD + (int(255 * a),))

@functools.lru_cache(maxsize=16)
def shadow_ell(wq):
    """soft contact shadow, wq = width in design units"""
    w, h = int(wq * K), int(wq * 0.16 * K); pad = int(30 * K)
    im = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((pad, pad, pad + w, pad + h), fill=(90, 30, 30, 120))
    return im.filter(ImageFilter.GaussianBlur(12 * K))
def ground_shadow(c, cx, gy, wd, alpha=1.0):
    place(c, shadow_ell(int(max(40, wd) // 10 * 10)), cx, gy, 1.0, 0, alpha)

def ground(c, gy, x0=40, x1=1040, alpha=1.0):
    sd = SD(c); sd.line([(x0, gy), (x1, gy)], width=6, fill=(242, 214, 208, int(255 * alpha)))

def dust(c, t, t0, x, y, n=7, seed=1, spread=130, dur=0.6, size=34, dirx=-1.0):
    if t < t0 or t > t0 + dur + 0.3: return
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        dl = rng.uniform(0, 0.12); u = prog(t, t0 + dl, dur)
        if u <= 0 or u >= 1: continue
        ang = rng.uniform(-0.9, 0.15) * math.pi * 0.5
        dx = dirx * math.cos(ang) * spread * e_out(u) * rng.uniform(0.6, 1.0); dy = math.sin(ang) * spread * 0.5 * e_out(u)
        r = size * rng.uniform(0.6, 1.2) * (0.5 + 0.8 * e_out(u))
        sd.ellipse((x + dx - r, y + dy - r, x + dx + r, y + dy + r), fill=(236, 222, 214, int(220 * (1 - u))))

def speed_lines(c, t, y0, y1, n=12, seed=3, alpha=1.0, x0=-100, x1=1180):
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        y = rng.uniform(y0, y1); ln = rng.uniform(140, 360); sp = rng.uniform(1800, 2800); ph = rng.uniform(0, 1)
        x = x1 - ((t * sp + ph * (x1 - x0)) % (x1 - x0 + ln))
        col = [RED, (250, 190, 180), GOLD][i % 3]
        sd.line([(x, y), (x + ln, y)], width=rng.uniform(5, 10), fill=col + (int(200 * alpha),))

# ---------------------------------------------------------------- vector props
def _outlined(mask_draw, size, fill, outline, ow):
    """draw a shape mask via mask_draw(ImageDraw), return RGBA with fill and an outer outline of ow px"""
    m = Image.new('L', size, 0); mask_draw(ImageDraw.Draw(m))
    o = m.filter(ImageFilter.MaxFilter(ow * 2 + 1)) if ow else m
    im = Image.new('RGBA', size, outline + (0,)); im.putalpha(o)
    f = Image.new('RGBA', size, fill + (255,)); im.alpha_composite(Image.composite(f, Image.new('RGBA', size, (0, 0, 0, 0)), m))
    return im

@functools.lru_cache(maxsize=2)
def glove(size=300):
    """cartoon glove seen from the side, palm down, fingers pointing right (size = width, design units)"""
    S = int(size * K); hgt = int(S * 0.62); u = S / 300
    def shape(d):
        d.rounded_rectangle((70 * u, 40 * u, 250 * u, 140 * u), 50 * u, fill=255)            # palm + fingers
        d.ellipse((205 * u, 52 * u, 292 * u, 138 * u), fill=255)                             # finger tips
        d.rounded_rectangle((120 * u, 6 * u, 205 * u, 62 * u), 28 * u, fill=255)             # thumb on top
        d.rounded_rectangle((8 * u, 54 * u, 96 * u, 150 * u), 18 * u, fill=255)              # cuff
    im = _outlined(shape, (S, hgt), WHITE, DRED, max(3, int(6 * u)))
    d = ImageDraw.Draw(im); lw = max(2, int(5 * u))
    for yy in (78, 102, 124):
        d.line([(196 * u, yy * u), (262 * u, yy * u)], fill=DRED, width=lw)                 # finger gaps
    d.line([(96 * u, 64 * u), (96 * u, 140 * u)], fill=DRED, width=lw)                      # cuff seam
    for yy in (78, 108):
        d.line([(20 * u, yy * u), (84 * u, yy * u)], fill=(255, 196, 196), width=lw)
    return im

@functools.lru_cache(maxsize=2)
def glove_l(size=300): return ImageOps.mirror(glove(size))       # fingers pointing left

@functools.lru_cache(maxsize=16)
def badge(kind, S=116):
    """round yellow badge with a dark-red glyph (S in design units)"""
    s = int(S * K); im = Image.new('RGBA', (s + 12 * K, s + 12 * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((6 * K, 10 * K, s + 6 * K, s + 10 * K), fill=DRED + (255,)); d.ellipse((0, 0, s, s), fill=YEL + (255,))
    c = DRED + (255,); u = s / 100
    if kind == 'shield':
        d.polygon([(50 * u, 16 * u), (78 * u, 26 * u), (75 * u, 58 * u), (50 * u, 84 * u), (25 * u, 58 * u), (22 * u, 26 * u)], fill=c)
        d.line([(37 * u, 50 * u), (47 * u, 61 * u), (65 * u, 39 * u)], fill=YEL, width=int(7 * u), joint='curve')
    elif kind == 'drop':
        d.ellipse((30 * u, 40 * u, 70 * u, 80 * u), fill=c); d.polygon([(33 * u, 52 * u), (50 * u, 16 * u), (67 * u, 52 * u)], fill=c)
        d.ellipse((40 * u, 52 * u, 52 * u, 64 * u), fill=YEL)
    elif kind == 'hand':
        d.rounded_rectangle((30 * u, 44 * u, 70 * u, 82 * u), 12 * u, fill=c)
        for i, x0 in enumerate((31, 41, 51, 61)):
            d.rounded_rectangle((x0 * u, (24 + abs(i - 1.5) * 4) * u, (x0 + 8) * u, 52 * u), 4 * u, fill=c)
        d.rounded_rectangle((18 * u, 50 * u, 32 * u, 70 * u), 6 * u, fill=c)
        d.polygon([(50 * u, 72 * u), (43 * u, 64 * u), (46 * u, 59 * u), (50 * u, 62 * u), (54 * u, 59 * u), (57 * u, 64 * u)], fill=YEL)
    elif kind == 'age':
        t = text_img('3+', F_IMPACT, S * 0.42, DRED, 0); im.alpha_composite(t, ((s - t.width) // 2, (s - t.height) // 2 + 2 * K))
    elif kind == 'battery':
        d.rounded_rectangle((20 * u, 34 * u, 74 * u, 66 * u), 6 * u, outline=c, width=int(6 * u))
        d.rectangle((74 * u, 43 * u, 82 * u, 57 * u), fill=c)
        d.rectangle((28 * u, 42 * u, 44 * u, 58 * u), fill=c)
    elif kind == 'truck':
        d.rounded_rectangle((16 * u, 32 * u, 58 * u, 64 * u), 4 * u, fill=c)
        d.polygon([(60 * u, 42 * u), (74 * u, 42 * u), (84 * u, 54 * u), (84 * u, 64 * u), (60 * u, 64 * u)], fill=c)
        for wx in (30, 72):
            d.ellipse(((wx - 8) * u, 60 * u, (wx + 8) * u, 76 * u), fill=c); d.ellipse(((wx - 3.5) * u, 64.5 * u, (wx + 3.5) * u, 71.5 * u), fill=YEL)
    elif kind == 'check':
        d.line([(28 * u, 52 * u), (44 * u, 68 * u), (74 * u, 34 * u)], fill=c, width=int(11 * u), joint='curve')
    elif kind == 'india':                                       # tricolour disc with the chakra
        m = Image.new('L', (s, s), 0); ImageDraw.Draw(m).ellipse((10 * u, 10 * u, 90 * u, 90 * u), fill=255)
        tri = Image.new('RGBA', (s, s), (0, 0, 0, 0)); td = ImageDraw.Draw(tri)
        td.rectangle((0, 0, s, 37 * u), fill=(255, 153, 51, 255)); td.rectangle((0, 37 * u, s, 63 * u), fill=WHITE + (255,))
        td.rectangle((0, 63 * u, s, s), fill=(19, 136, 8, 255)); td.ellipse((42 * u, 42 * u, 58 * u, 58 * u), outline=(0, 0, 128, 255), width=max(2, int(2.5 * u)))
        tri.putalpha(Image.fromarray(np.minimum(np.asarray(tri.getchannel('A')), np.asarray(m))))
        im.alpha_composite(tri)
    elif kind == 'box':
        d.rounded_rectangle((22 * u, 36 * u, 78 * u, 76 * u), 5 * u, fill=c)
        d.polygon([(22 * u, 36 * u), (30 * u, 24 * u), (70 * u, 24 * u), (78 * u, 36 * u)], fill=(150, 30, 20, 255))
        d.rectangle((45 * u, 24 * u, 55 * u, 50 * u), fill=YEL)
    return im

@functools.lru_cache(maxsize=16)
def badge_row(kind, txt, size=70):
    ic = badge(kind); tx = head(txt, size)
    im = Image.new('RGBA', (ic.width + 26 * K + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); im.alpha_composite(tx, (ic.width + 26 * K, (im.height - tx.height) // 2))
    return im

def _blit(canvas, img, x, y):
    """paste img centred at (x, y) design units on a prop canvas"""
    canvas.alpha_composite(img, (int(x * K - img.width / 2), int(y * K - img.height / 2)))

@functools.lru_cache(maxsize=None)
def logo_img(width):
    """the Funhoods logo on its own (no sticker behind it), width in design units"""
    lg = asset('logo_rgba.png'); return lg.resize((int(width * K), int(lg.height * width * K / lg.width)), Image.LANCZOS)

# ---------------------------------------------------------------- carton + truck
@functools.lru_cache(maxsize=2)
def carton(wd=400):
    sk, th, fh = 0.09 * wd, 0.14 * wd, 0.70 * wd
    im = Image.new('RGBA', (int((wd + sk) * K), int((th + fh) * K)), (0, 0, 0, 0)); sd = SD(im)
    sd.polygon([(0, th), (wd, th), (wd + sk, 0), (sk, 0)], fill=(226, 186, 136, 255))                 # top
    sd.polygon([(wd, th), (wd + sk, 0), (wd + sk, fh), (wd, th + fh)], fill=(176, 128, 80, 255))       # side
    sd.rectangle((0, th, wd, th + fh), fill=(206, 160, 108, 255))                                      # front
    sd.polygon([(wd * 0.44, th), (wd * 0.56, th), (wd * 0.56 + sk, 0), (wd * 0.44 + sk, 0)], fill=(238, 214, 168, 255))   # tape
    sd.rectangle((wd * 0.44, th, wd * 0.56, th + fh * 0.16), fill=(238, 214, 168, 255))
    sd.line([(0, th), (wd, th)], width=2, fill=(160, 110, 62, 255))
    _blit(im, logo_img(int(wd * 0.50)), wd * 0.5, th + fh * 0.40)                                     # printed on the board
    _blit(im, body('PVC RACING CAR  •  PVC-3301', wd * 0.054, (92, 50, 20)), wd * 0.5, th + fh * 0.68)
    _blit(im, text_img('36 PCS', F_HEAD, wd * 0.15, RED, 0, DRED, 3, DRED), wd * 0.5, th + fh * 0.85)
    return drop_shadow(im, 14, 18, 90, 30)

@functools.lru_cache(maxsize=2)
def truck(wd=560):
    hh = wd * 0.52
    im = Image.new('RGBA', (int(wd * K), int(hh * K)), (0, 0, 0, 0)); sd = SD(im)
    sd.rrect((0, 0, wd * 0.70, hh * 0.74), 18, fill=YEL + (255,), outline=(232, 176, 0, 255), width=3)
    sd.rectangle((0, hh * 0.62, wd * 0.70, hh * 0.74), fill=RED + (255,))
    _blit(im, logo_img(int(wd * 0.46)), wd * 0.35, hh * 0.31)
    sd.polygon([(wd * 0.72, hh * 0.18), (wd * 0.88, hh * 0.18), (wd, hh * 0.42), (wd, hh * 0.80), (wd * 0.72, hh * 0.80)], fill=RED + (255,))
    sd.polygon([(wd * 0.76, hh * 0.24), (wd * 0.86, hh * 0.24), (wd * 0.95, hh * 0.42), (wd * 0.76, hh * 0.42)], fill=(190, 232, 245, 255))
    sd.rectangle((wd * 0.70, hh * 0.74, wd, hh * 0.80), fill=DRED + (255,))
    for wx in (0.16, 0.50, 0.86):
        r = hh * 0.13
        sd.ellipse((wd * wx - r, hh * 0.82 - r, wd * wx + r, hh * 0.82 + r), fill=INK + (255,))
        sd.ellipse((wd * wx - r * 0.45, hh * 0.82 - r * 0.45, wd * wx + r * 0.45, hh * 0.82 + r * 0.45), fill=(200, 200, 200, 255))
    return drop_shadow(im, 10, 10, 80, 30)

@functools.lru_cache(maxsize=1)
def counter_top():
    im = Image.new('RGBA', (W, int(170 * K)), (0, 0, 0, 0)); sd = SD(im)
    sd.rectangle((0, 0, DW, 34), fill=(238, 206, 160, 255))
    sd.rectangle((0, 34, DW, 170), fill=(214, 168, 116, 255))
    for i, y in enumerate((60, 92, 128)):
        sd.line([(0, y), (DW, y + (8 if i % 2 else -6))], width=3, fill=(196, 148, 98, 255))
    sd.line([(0, 34), (DW, 34)], width=3, fill=(190, 140, 90, 255))
    return im

# ---------------------------------------------------------------- transitions
def chevron_wipe(c, t, tc, d=0.62):
    p = (t - (tc - d / 2)) / d
    if p <= 0 or p >= 1: return
    sd = SD(c)
    tip, wband = 420, DW + 2 * 420 + 120
    xr = -60 + (DW + wband + tip + 520) * e_inout(p)
    def band(x_r, w, col):
        x_l = x_r - w
        sd.polygon([(x_l - tip, 0), (x_r - tip, 0), (x_r, DH / 2), (x_r - tip, DH), (x_l - tip, DH), (x_l, DH / 2)], fill=col + (255,))
    band(xr + 300, 110, YEL); band(xr + 150, 110, ORANGE); band(xr, wband, RED); band(xr - wband - 40, 110, YEL)
    for k in range(3):
        xx = xr - 520 - k * 260
        sd.polygon([(xx - 130, DH / 2 - 230), (xx - 40, DH / 2 - 230), (xx + 110, DH / 2), (xx - 40, DH / 2 + 230), (xx - 130, DH / 2 + 230), (xx + 20, DH / 2)], fill=YEL + (255,))

def flash(c, t, tc, d=0.28, strength=0.85):
    if tc <= t < tc + d:
        c.alpha_composite(Image.new('RGBA', (W, H), (255, 255, 240, int(255 * strength * (1 - (t - tc) / d) ** 2))))

def shake_xy(t, t0, amp=18, decay=7):
    if t < t0: return 0.0, 0.0
    u = t - t0; a = amp * math.exp(-u * decay)
    return a * math.sin(t * 93), a * math.cos(t * 71)

def shift(c, dx, dy):
    if abs(dx) < 0.3 and abs(dy) < 0.3: return c
    out = Image.new('RGBA', c.size, (255, 255, 255, 255)); out.alpha_composite(c, (int(dx * K), int(dy * K))); return out


# ---------------------------------------------------------------- the car
def chevrons(c, t, x0, x1, y, direction=1, col=RED, alpha=1.0, n=3):
    """>>> arrows sliding along y between x0 and x1 (direction +1 = right)"""
    if alpha <= 0: return
    sd = SD(c); span = x1 - x0
    for k in range(n):
        u = ((t * 1.6 + k / n) % 1); x = x0 + span * (u if direction > 0 else 1 - u)
        a = int(255 * alpha * math.sin(math.pi * u)); s = 30
        pts = [(x - s * direction, y - s), (x - s * direction + 18 * direction, y - s), (x + 18 * direction, y),
               (x - s * direction + 18 * direction, y + s), (x - s * direction, y + s), (x, y)]
        sd.polygon(pts, fill=col + (a,))

# side view facing right (assets/car_side_r.png, 3340x1817): the two visible rims as ellipses (cx, cy, rx, ry), source px
RIMS = [(800, 1348, 340, 296), (2679, 1128, 168, 136)]
# front view (assets/car_front.png, 1847x2664): the light lenses on the front fenders, and the roof point the finger presses
LIGHTS_F = [(675, 2256), (1185, 2256)]
ROOF_F = (915, 900)

@functools.lru_cache(maxsize=24)
def car_r(wd, ang=0):
    """side view, width wd design units, rims turned by ang degrees (clockwise = rolling right)"""
    src = asset('car_side_r.png'); s = wd * K / src.width
    im = src.resize((int(src.width * s), int(src.height * s)), Image.LANCZOS)
    if ang % 360 == 0: return im
    for cx, cy, rx, ry in RIMS:
        cx, cy, rx, ry = cx * s, cy * s, rx * s, ry * s
        box = (int(cx - rx), int(cy - ry), int(cx + rx), int(cy + ry))
        disc = im.crop(box); d = int(2 * rx)
        disc = disc.resize((d, d), Image.BICUBIC).rotate(-ang, Image.BICUBIC).resize((box[2] - box[0], box[3] - box[1]), Image.BICUBIC)
        m = Image.new('L', disc.size, 0); ImageDraw.Draw(m).ellipse((1, 1, disc.width - 2, disc.height - 2), fill=255)
        m = m.filter(ImageFilter.GaussianBlur(1.5 * K))
        base = im.crop(box); base.paste(disc, (0, 0), m); im.paste(base, box[:2])
    return im

def car_r_h(wd): return asset('car_side_r.png').height * wd / asset('car_side_r.png').width
def rim_deg(dist, wd): return dist / (RIMS[0][2] * wd / asset('car_side_r.png').width) * 180 / math.pi
def q6(a): return int(round(a / 6.0)) * 6 % 360

def draw_car(c, x, gy, wd, dist=0.0, rot=0.0, squash=1.0, alpha=1.0, ghost=0.0):
    """side view with its tyres on ground gy, centred on x; dist = distance rolled (turns the rims)"""
    im = car_r(wd, q6(rim_deg(dist, wd))); hh = car_r_h(wd)
    cy = gy - hh / 2 * squash
    if ghost > 1:
        for i in range(4, 0, -1): place(c, im, x - ghost * i / 4, cy, 1.0, rot, alpha * 0.16 * (5 - i) / 4, sy=squash)
    place(c, im, x, cy, 1.0, rot, alpha, sy=squash)

def fitted(name, wd=None, hd=None):
    im = asset(name); return wd if wd else hd * im.width / im.height, hd if hd else wd * im.height / im.width

def spin_view(c, t, t0, t1, views, cx, cy, size, shadow_y):
    """fake 360 turntable: swap views with a horizontal squash at each change; views = [(asset, height)]"""
    n = len(views); u = clamp((t - t0) / (t1 - t0)) * n; k = min(n - 1, int(u)); f = u - k
    sx = 1.0
    if k > 0: sx = min(sx, 0.18 + 0.82 * e_out(clamp(f / 0.22)))
    if k < n - 1: sx = min(sx, 0.18 + 0.82 * e_out(clamp((1 - f) / 0.22)))
    name, hh = views[k]
    im = with_shadow(name, int(hh * size), 12, 18, 70)
    ground_shadow(c, cx, shadow_y, 0.62 * size, 0.9)
    place(c, im, cx, cy, 1.0, 0, 1.0, sy=1.0) if sx > 0.995 else place(c, im.resize((max(1, int(im.width * sx)), im.height), Image.BICUBIC), cx, cy)

def note(c, x, y, size, col, rot=0, alpha=1.0):
    S = int(size * K); im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); u = S / 100
    d.ellipse((14 * u, 62 * u, 50 * u, 90 * u), fill=col); d.rectangle((42 * u, 14 * u, 52 * u, 78 * u), fill=col)
    d.polygon([(52 * u, 14 * u), (86 * u, 34 * u), (82 * u, 48 * u), (52 * u, 30 * u)], fill=col)
    place(c, im, x, y, 1.0, rot, alpha)

def notes_burst(c, t, t0, x, y, n=8, seed=1, spread=360, dur=1.4):
    if t < t0: return
    rng = np.random.default_rng(seed)
    for i in range(n):
        dl = rng.uniform(0, 0.6); u = prog(t, t0 + dl, dur)
        if u <= 0 or u >= 1: continue
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05); dist = spread * rng.uniform(0.6, 1.0) * e_out(u)
        note(c, x + math.cos(ang) * dist, y + math.sin(ang) * dist - 60 * u, rng.uniform(56, 84),
             [RED, GOLD, SKY, (255, 120, 60)][i % 4], 12 * math.sin(t * 4 + i), 1 - prog(u, 0.7, 0.3))

@functools.lru_cache(maxsize=4)
def glow_disc(r, col=(255, 236, 150)):
    S = int(r * 4 * K); im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for k, a in ((1.0, 70), (0.6, 130), (0.32, 255)):
        rr = S / 2 * k; d.ellipse((S / 2 - rr, S / 2 - rr, S / 2 + rr, S / 2 + rr), fill=col + (a,))
    return im.filter(ImageFilter.GaussianBlur(r * 0.35 * K))

def start_lights(c, t, cx, cy):
    sd = SD(c); w_, h_ = 470, 170
    sd.rrect((cx - w_ / 2 + 8, cy - h_ / 2 + 12, cx + w_ / 2 + 8, cy + h_ / 2 + 12), 44, fill=(60, 0, 0, 90))
    sd.rrect((cx - w_ / 2, cy - h_ / 2, cx + w_ / 2, cy + h_ / 2), 44, fill=INK + (255,))
    for k, tl in enumerate(T.LIGHTS):
        x = cx - 150 + k * 150; on = t >= tl
        col = ((40, 210, 80) if k == 2 else (235, 40, 40)) if on else (78, 66, 66)
        if on: place(c, glow_disc(70, (120, 255, 150) if k == 2 else (255, 90, 80)), x, cy, 0.9 + 0.1 * math.sin(t * 20), 0, 0.85)
        sd.ellipse((x - 52, cy - 52, x + 52, cy + 52), fill=col + (255,))
        sd.ellipse((x - 30, cy - 38, x - 6, cy - 18), fill=(255, 255, 255, 90 if on else 30))

# ---------------------------------------------------------------- scenes
BOX_Y, BOX_HD = 1060, 420         # the window box in the opener (design units: centre y, height)

def scene_open(t, t1):
    """On your marks... get set... VROOM! -- the packaging opens the reel: the window box drops in under the start lights,
    then punches on VROOM"""
    c = bg(t); cx = DW / 2
    place(c, soft_burst(1100), cx, BOX_Y, 0.86 + 0.04 * math.sin(t * 2.5), (t * 10) % 360, 0.26 * prog(t, 0.2, 0.4))
    start_lights(c, t, cx, 330)
    pop(c, head('ON YOUR MARKS', 88), cx, 520, t, T.LIGHTS[0], T.LIGHTS[1] - 0.05, slide=24)
    pop(c, head('GET SET', 110), cx, 520, t, T.LIGHTS[1], T.VROOM - 0.05, slide=24)
    q = prog(t, 0.05, 0.42)                                       # box drops in and bounces
    y = BOX_Y - 1300 * (1 - e_in(q)) if t < 0.47 else BOX_Y - 30 * math.exp(-(t - 0.47) * 9) * abs(math.sin((t - 0.47) * 22))
    punch = e_out(prog(t, T.VROOM, 0.12)) * (1 - e_inout(prog(t, T.VROOM + 0.12, 0.4)))
    sx, sy = shake_xy(t, T.VROOM, 14, 6) if t >= T.VROOM else (0, 0)
    ground_shadow(c, cx, BOX_Y + BOX_HD / 2 + 40, 640, clamp(q * 3))
    place(c, with_shadow('box_q34.png', BOX_HD, 14, 18, 80), cx + sx, y + sy, 1.0 + 0.10 * punch, 0, clamp(q * 3))
    if t >= T.VROOM:
        speed_lines(c, t, BOX_Y - 300, BOX_Y + 300, 14, 5, 1 - prog(t, t1 - 0.3, 0.3))
        place(c, burst(720), cx, 545, 0.25 + 0.5 * e_back(prog(t, T.VROOM, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, t1 - 0.25, 0.25)))
    pop(c, impact_txt("VROOM!", 200, YEL), cx, 545, t, T.VROOM, t1, d=0.3, rot=-5, from_scale=1.9)
    return c

def scene_spin(t, t0, t1):
    """Say hello to the Funhoods Racing Car! -- 360 turntable"""
    c = bg(t); p = prog(t, t0, 0.4)
    place(c, soft_burst(1050), DW / 2, 1060, 0.85 + 0.04 * math.sin(t * 2.5), (t * 10) % 360, 0.26 * clamp(p * 3))
    sd = SD(c); sd.ellipse((140, 1330, 940, 1480), fill=(232, 226, 224, 255)); sd.ellipse((160, 1320, 920, 1460), fill=(246, 242, 240, 255))
    views = [('car_q34.png', 0.62), ('car_side_r.png', 0.58), ('car_back34.png', 0.70), ('car_back.png', 0.70),
             ('car_side.png', 0.62), ('car_front.png', 0.95), ('car_q34.png', 0.62)]
    pin = prog(t, t0, 0.4)
    if pin < 1:                                                  # first appearance of the car: it zooms in from the right
        ground_shadow(c, DW / 2, 1400, 520 * (0.4 + 0.6 * pin), pin)
        place(c, with_shadow('car_q34.png', int(0.62 * 840), 12, 18, 70), DW / 2 + 900 * (1 - e_out(pin)), 1100, 0.6 + 0.4 * e_back(pin, 1.4), 0, clamp(pin * 3))
        speed_lines(c, t, 900, 1300, 10, 2, 1 - pin)
    else:
        spin_view(c, t, t0 + 0.4, t1 - 0.1, views, DW / 2, 1100, 840, 1400)
    for k_ in range(2):
        a0 = (-(t - t0) * 260 + k_ * 180) % 360
        sd.arc((150, 1250, 930, 1560), a0, a0 + 70, width=10, fill=RED + (200,))
    pop(c, body('SAY HELLO TO THE', 42, RED), DW / 2, 290, t, t0 + 0.05, None, slide=20)
    pop(c, impact_txt('RACING CAR', 180, YEL), DW / 2, 420, t, T.w(2, 6) - 0.10, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, chip('PVC RACING CAR  •  PVC-3301', 38, RED, WHITE), DW / 2, 1660, t, T.w(2, 6) + 0.1, None, slide=24)
    return c

def scene_push(t, t0, t1):
    """Give it a push... let go... and watch it race! -- a glove pushes, lets go, the car races off"""
    c = bg(t); gy, WD = 1330, 760
    ground(c, gy)
    xin = lerp(-520, 430, e_out(prog(t, t0, 0.42)))
    push = e_inout(prog(t, T.PUSH0, T.RELEASE - T.PUSH0)); x = xin + 150 * push
    z = prog(t, T.RACE, 0.62); x += 1500 * z ** 2.1
    dist = (x + 520) * 1.0 + 900 * push
    if z < 1:
        ground_shadow(c, x, gy + 6, WD * 0.85)
        draw_car(c, x, gy + (1.6 * math.sin(t * 120) if 0 < push < 1 else 0), WD, dist, ghost=320 * clamp(z * 3) if z > 0 else 0)
    if z > 0:
        speed_lines(c, t, gy - 420, gy - 20, 14, 5, 1 - prog(t, t1 - 0.25, 0.25))
        dust(c, t, T.RACE + 0.02, xin + 150 - WD * 0.32, gy - 10, 9, 4, 200, 0.7, 42)
    gin = e_out(prog(t, T.PUSH0 - 0.32, 0.30)); gout = e_inout(prog(t, T.RELEASE, 0.35))
    if gin > 0 and gout < 1:                                       # glove presses on the rear deck, pushes, lifts away
        hx = xin + 150 * push - WD * 0.30 - 420 * (1 - gin) - 260 * gout
        hy = gy - car_r_h(WD) * 0.86 - 520 * (1 - gin) - 380 * gout
        place(c, glove(300), hx, hy + (5 * math.sin(t * 40) if 0 < push < 1 else 0), 1.0, -12 + 10 * gout, 1 - gout)
    chevrons(c, t, x - WD * 0.5 - 220, x - WD * 0.5 - 20, gy + 70, 1, RED, clamp((t - T.PUSH0) / 0.15) * (1 - clamp((t - T.RELEASE) / 0.1)))
    pop(c, head('GIVE IT A PUSH...', 104), DW / 2, 340, t, t0 + 0.05, T.RELEASE + 0.05, slide=30)
    pop(c, head('LET GO...', 120), DW / 2, 340, t, T.RELEASE, T.RACE, slide=30)
    if t >= T.RACE:
        place(c, burst(700), DW / 2, 420, 0.3 + 0.62 * e_back(prog(t, T.RACE, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, t1 - 0.2, 0.2)))
    pop(c, impact_txt('WATCH IT RACE!', 132, YEL), DW / 2, 420, t, T.RACE, None, d=0.3, rot=-5, from_scale=1.9)
    for k, (s_, xx) in enumerate([('FRICTION', 230), ('HAND PUSH', 540), ('INERTIA', 850)]):
        pop(c, chip(s_, 36, YEL, DRED), xx, 1600, t, T.PUSH0 + 0.15 + 0.1 * k, None, slide=24)
    return c

def scene_lights(t, t0, t1):
    """Press the roof... bright lights and loud music!"""
    c = bg(t); p = prog(t, t0, 0.45); HF = 960
    src = asset('car_front.png'); s = HF / src.height; cx, cy = DW / 2, 1080
    press = e_out(prog(t, T.PRESS, 0.16)) * (1 - e_inout(prog(t, T.GLOW - 0.1, 0.25)))
    sq = 1 - 0.025 * press
    place(c, soft_burst(1000), cx, cy, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.24 * clamp(p * 3))
    ground_shadow(c, cx, cy + HF / 2 - 30, 560, clamp(p * 3))
    place(c, with_shadow('car_front.png', HF, 12, 16, 70), cx, cy + 180 * (1 - e_back(p, 1.3)) + HF / 2 * (1 - sq), 1.0, 0, clamp(p * 3), sy=sq)
    def pt(x, y): return cx + (x - src.width / 2) * s, cy + (y - src.height / 2) * s
    g = prog(t, T.GLOW, 0.18)
    if g > 0:                                                      # headlights glow and pulse
        for x, y in LIGHTS_F:
            px, py = pt(x, y); pul = 0.85 + 0.15 * math.sin(t * 14 + x)
            place(c, glow_disc(78), px, py, (0.4 + 0.6 * e_back(g, 1.6)) * pul, 0, 0.95)
        sd = SD(c)
        for k in range(10):                                        # light rays
            a = math.radians(-160 + k * 16 + 6 * math.sin(t * 3)); x0, y0 = pt(*LIGHTS_F[k % 2]); ln = 260 * g
            sd.line([(x0 + math.cos(a) * 90, y0 + math.sin(a) * 90), (x0 + math.cos(a) * (90 + ln), y0 + math.sin(a) * (90 + ln))], width=8, fill=(255, 200, 40, int(170 * g)))
    notes_burst(c, t, T.NOTES, cx, cy - 120, n=12, seed=5, spread=430, dur=1.5)
    if T.NOTES < t < t1: notes_burst(c, t, T.NOTES + 1.1, cx, cy - 120, n=8, seed=9, spread=420, dur=1.4)
    gin = e_out(prog(t, T.PRESS - 0.32, 0.28)); gout = e_inout(prog(t, T.GLOW - 0.1, 0.3))
    if gin > 0 and gout < 1:                                       # a finger presses the roof
        rx, ry = pt(*ROOF_F)
        place(c, glove(260), rx + 120, ry - 70 - 500 * (1 - gin) - 420 * gout + 18 * press, 1.0, -62, 1 - gout)
        if press > 0.3:
            sd = SD(c); rr = 60 + 60 * prog(t, T.PRESS + 0.1, 0.4)
            sd.ellipse((rx - rr, ry - rr, rx + rr, ry + rr), width=8, outline=RED + (int(220 * (1 - prog(t, T.PRESS + 0.1, 0.4))),))
    pop(c, head('PRESS THE ROOF', 108), DW / 2, 300, t, t0 + 0.05, T.GLOW - 0.05, slide=30)
    pop(c, impact_txt('LIGHTS & MUSIC!', 128, YEL), DW / 2, 330, t, T.GLOW, None, d=0.3, rot=-4, from_scale=1.8)
    pop(c, chip('BRIGHT LIGHT', 40, RED, WHITE), 330, 1690, t, T.GLOW + 0.1, None, slide=24)
    pop(c, chip('LOUD MUSIC', 40, RED, WHITE), 750, 1690, t, T.NOTES + 0.05, None, slide=24)
    return c

def scene_4wd(t, t0, t1):
    """Four-wheel drive, a sturdy body and chunky tyres."""
    c = bg(t); p = prog(t, t0, 0.45); WD = 980; gy = 1300
    x = DW / 2 + 260 * (1 - e_out(p)); dist = (t - t0) * 420
    ground_shadow(c, x, gy + 6, WD * 0.85, clamp(p * 3))
    draw_car(c, x, gy, WD, dist, 0, 1.0, clamp(p * 3))
    src = asset('car_side_r.png'); s = WD / src.width; top = gy - car_r_h(WD)
    sd = SD(c)
    for k, (cx_, cy_, rx, ry) in enumerate(RIMS):                  # pulsing rings round the wheels
        q = ((t - t0 - 0.2) * 1.4 + k * 0.5) % 1
        if t - t0 < 0.2: continue
        px, py = x + (cx_ - src.width / 2) * s, top + cy_ * s; r = rx * s * (1.15 + 0.5 * q)
        sd.ellipse((px - r, py - r * 0.95, px + r, py + r * 0.95), width=10, outline=GOLD + (int(230 * (1 - q)),))
    def callout(tp, ax, ay, lx, ly, txt):
        q = e_out(prog(t, tp, 0.3))
        if q <= 0: return
        sd.line([(ax, ay), (lerp(ax, lx, q), lerp(ay, ly, q))], width=5, fill=RED + (255,)); sd.ellipse((ax - 10, ay - 10, ax + 10, ay + 10), fill=RED + (255,))
        pop(c, chip(txt, 38, YEL, DRED), lx, ly, t, tp + 0.15, None)
    callout(T.CALL_BODY, x + 120, top + 560 * s, 780, 640, 'STURDY BODY')
    rx0, ry0 = x + (RIMS[0][0] - src.width / 2) * s, top + RIMS[0][1] * s
    callout(T.CALL_TYRES, rx0 - 80, ry0 + 140, 300, 1560, 'CHUNKY TYRES')
    pop(c, impact_txt('FOUR-WHEEL', 168, YEL), DW / 2, 330, t, T.w(5, 0) - 0.06, None, d=0.32, from_scale=1.7, rot=-3)
    pop(c, head('DRIVE', 130), DW / 2, 480, t, T.w(5, 2) - 0.06, None, slide=30)
    return c

def scene_style(t, t0, t1):
    """Cool style, bold looks... built to race! -- the one orange car: 3/4 view, then it swings round to face the camera"""
    c = bg(t); p = prog(t, t0, 0.45)
    place(c, soft_burst(1100), DW / 2, 1020, 0.88 + 0.04 * math.sin(t * 2.5), (t * 10) % 360, 0.26 * clamp(p * 3))
    q = prog(t, T.BUILT, 0.5)                                       # on "built to race" the car swings round to face the camera
    if q < 1:
        place(c, with_shadow('car_q34.png', 520, 12, 18, 70), DW / 2 - 700 * e_in(q), 1010 + 200 * (1 - e_back(p, 1.3)) + 8 * math.sin(t * 2.2),
              1.0 + 0.02 * (t - t0), -3, clamp(p * 3) * (1 - q))
    if q > 0:
        place(c, with_shadow('car_front.png', 820, 12, 18, 70), DW / 2 + 700 * (1 - e_out(q)), 1040 + 6 * math.sin(t * 2.4), 1.0, 2 * math.sin(t * 1.5), clamp(q * 2))
        speed_lines(c, t, 820, 1240, 10, 7, 1 - q)
    sparkles(c, t, 31, DW / 2, 1020, 460, 420, n=12, size=40)
    pop(c, head('COOL STYLE', 120), DW / 2, 300, t, T.w(6, 0) - 0.06, None, slide=30)
    pop(c, impact_txt('BOLD LOOKS', 150, YEL), DW / 2, 440, t, T.LOOKS, None, d=0.32, from_scale=1.6, rot=-3)
    pop(c, chip('BUILT TO RACE!', 50, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1640, t, T.BUILT, None, slide=24)
    return c

def scene_box(t, t0, t1):
    """A bold window box that grabs every eye in the store. -- continues from the opener: the same box (front only; the
    side panels print other models / colours) sways, then lands on a shop counter that slides in"""
    c = bg(t); cx = DW / 2; land_y = 1300 - BOX_HD / 2 - 10
    pop(c, head('BOLD WINDOW BOX', 108), DW / 2, 300, t, T.w(1, 1) - 0.06, None, slide=30)
    pop(c, impact_txt('GRABS EVERY EYE!', 116, YEL), DW / 2, 430, t, T.w(1, 5) - 0.06, None, d=0.32, from_scale=1.7, rot=-3)
    place(c, soft_burst(1100), cx, BOX_Y, 0.86 + 0.04 * math.sin(t * 2.5), (t * 10) % 360, 0.26 * (1 - prog(t, T.BOX_LAND - 0.35, 0.3)))
    cp = e_out(prog(t, T.BOX_LAND - 0.35, 0.45))
    if cp > 0: place(c, counter_top(), DW / 2 - DW * (1 - cp), 1380)
    if t < T.BOX_LAND - 0.35:
        sway = math.sin((t - t0) * 1.8) * prog(t, t0, 0.4)
        ground_shadow(c, cx, BOX_Y + BOX_HD / 2 + 40, 640)
        place(c, with_shadow('box_q34.png', BOX_HD, 14, 18, 80), cx + 20 * sway, BOX_Y + 8 * math.sin((t - t0) * 2.2), 1 + 0.02 * (t - t0), -3 * sway)
        sparkles(c, t, 19, cx, BOX_Y, 460, 260, n=10, size=36)
    else:
        q = prog(t, T.BOX_LAND - 0.35, 0.35)
        y = BOX_Y + (land_y - BOX_Y) * e_in(q) if t < T.BOX_LAND else land_y - 26 * math.exp(-(t - T.BOX_LAND) * 9) * abs(math.sin((t - T.BOX_LAND) * 22))
        place(c, with_shadow('box_q34.png', BOX_HD, 14, 18, 80), cx, y)
        if t > T.BOX_LAND: sparkles(c, t, 17, cx, y, 460, 260, n=12, size=40)
    pop(c, chip('EYE-CATCHING WINDOW BOX', 44, RED, WHITE), DW / 2, 1690, t, T.BOX_LAND + 0.1, None, slide=24)
    return c

def scene_carton(t, t0, t1):
    """36 pieces per carton -- cartons drop and stack; a Funhoods truck delivers anywhere in India"""
    c = bg(t); shake = [0.0, 0.0]
    pop(c, impact_txt('36 PCS', 210, YEL), DW / 2, 320, t, T.w(7, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('PER CARTON', 104), DW / 2, 490, t, T.w(7, 2) - 0.06, None, slide=30)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for i, (x, y, tl) in enumerate(T.STACK):
        q = prog(t, tl - 0.34, 0.34)
        if q <= 0: continue
        yy = y - 1300 * (1 - q) ** 2
        if t >= tl:
            u = t - tl; yy = y - 36 * math.exp(-u * 9) * abs(math.sin(u * 22))
            a_ = 10 * math.exp(-u * 10); shake[0] += a_ * math.sin(u * 90); shake[1] += a_ * math.cos(u * 70)
        place(lay, carton(400), x, yy, 1.0, [-3, 3, -1][i] * (1 - 0.7 * clamp((t - tl) * 2)), clamp(q * 3))
    c.alpha_composite(lay)
    gy = 1610; ground(c, gy, alpha=prog(t, T.TRUCK - 0.1, 0.3))
    tp = prog(t, T.TRUCK, 0.62)
    if tp > 0:
        x = lerp(-420, DW / 2, e_out(tp)); bob = 3 * math.sin(t * 30) * (1 - tp)
        if tp < 1: speed_lines(c, t, gy - 250, gy - 30, 8, 9, 1 - tp, -100, x - 200)
        place(c, truck(560), x, gy - 150 + bob)
        dust(c, t, T.TRUCK + 0.45, x - 260, gy - 10, 6, 12, 120)
    pop(c, head('PAN INDIA DELIVERY', 92), DW / 2, 1735, t, T.w(7, 5) - 0.08, None, slide=30)
    return shift(c, shake[0], shake[1])

def scene_bulk(t, t0, t1):
    """FOR DISTRIBUTORS & WHOLESALERS -- boxes line up -- BULK ORDERS ONLY -- STOCK UP NOW!"""
    c = bg(t)
    pop(c, body('FOR', 46, RED), DW / 2, 290, t, t0 + 0.06, None, slide=20)
    pop(c, head('DISTRIBUTORS', 124), DW / 2, 392, t, T.w(8, 0) - 0.06, None, slide=30)
    pop(c, head('& WHOLESALERS', 112, YEL), DW / 2, 528, t, T.w(8, 2) - 0.06, None, slide=30)
    gy = 1130; ground(c, gy, 40, 1040)
    for i, x in enumerate((190, 540, 890)):
        q = prog(t, t0 + 0.25 + i * 0.14, 0.38)
        if q <= 0: continue
        tl = t0 + 0.25 + i * 0.14 + 0.38; yl = gy - 78
        y = yl - 1200 * (1 - e_in(q)) if t < tl else yl - 22 * math.exp(-(t - tl) * 9) * abs(math.sin((t - tl) * 22))
        ground_shadow(c, x, gy + 4, 280, clamp(q * 3))
        place(c, with_shadow('box_q34.png', 150, 10, 14, 70), x, y, 1.0, 0, clamp(q * 3))
    pop(c, chip('BULK ORDERS ONLY', 60, YEL, DRED, F_HEAD, 44, 20), DW / 2, 1300, t, T.w(8, 2) + 0.2, None, slide=30)
    if t >= T.STOCK:
        place(c, burst(760), DW / 2, 1610, 0.22 + 0.46 * e_back(prog(t, T.STOCK, 0.3), 1.6), (t * 40) % 360, 0.95 * (1 - prog(t, t1 - 0.25, 0.25)))
    pop(c, impact_txt('STOCK UP NOW!', 150, YEL), DW / 2, 1610, t, T.STOCK, None, d=0.3, rot=-5, from_scale=1.9)
    return c

def scene_end(t):
    t0 = T.S_END
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, t0, 0.5))
    sd.polygon([(0, 0), (DW, 0), (DW, 250 * p + 60), (DW / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    sd.polygon([(0, 250 * p + 60), (DW / 2, 330 * p + 60), (DW, 250 * p + 60), (DW, 250 * p + 76), (DW / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    sd.polygon([(0, DH), (DW, DH), (DW, DH - 200 * p), (0, DH - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png'); tl = T.w(9, 0) - 0.22
    place(c, lg, DW / 2, 500, (800 * K / lg.width) * (0.4 + 0.6 * e_back(prog(t, tl, 0.42), 1.6)), 0, clamp((t - tl) / 0.1))
    pb = prog(t, t0 + 0.30, 0.5)
    place(c, with_shadow('box_q34.png', 300, 12, 16, 70), 760 + 500 * (1 - e_out(pb)), 1000, 1.0, 3, clamp(pb * 3))
    pc = prog(t, t0 + 0.15, 0.5)
    place(c, with_shadow('car_q34.png', 300, 12, 16, 70), 330 - 500 * (1 - e_out(pc)), 1020 + 5 * math.sin(t * 2), 1.0, -3, clamp(pc * 3))
    pop(c, body('PVC RACING CAR  •  PVC-3301  •  AGES 3+', 34, RED), DW / 2, 1270, t, t0 + 0.45, None, slide=20)
    pop(c, chip('BULK ORDERS ONLY', 52, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1385, t, t0 + 0.6, None, slide=30)
    ca, cb_ = chip('36 PCS / CARTON', 34, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 34, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1500, t, t0 + 0.8, None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1500, t, t0 + 0.95, None, slide=20)
    pop(c, body('For Distributors  &  Wholesalers', 36, INK), DW / 2, 1605, t, t0 + 1.1, None, slide=20)
    pop(c, body('SPECIFICATIONS AND COLORS OF CONTENTS MAY VARY FROM ILLUSTRATION', 16, WHITE), DW / 2, DH - 60, t, t0 + 1.2, None)
    return c

def render(t):
    if t < T.S_BOX: c = scene_open(t, T.S_BOX)
    elif t < T.S_SPIN: c = scene_box(t, T.S_BOX, T.S_SPIN)
    elif t < T.S_PUSH: c = scene_spin(t, T.S_SPIN, T.S_PUSH)
    elif t < T.S_LIGHTS: c = scene_push(t, T.S_PUSH, T.S_LIGHTS)
    elif t < T.S_4WD: c = scene_lights(t, T.S_LIGHTS, T.S_4WD)
    elif t < T.S_STYLE: c = scene_4wd(t, T.S_4WD, T.S_STYLE)
    elif t < T.S_CARTON: c = scene_style(t, T.S_STYLE, T.S_CARTON)
    elif t < T.S_BULK: c = scene_carton(t, T.S_CARTON, T.S_BULK)
    elif t < T.S_END: c = scene_bulk(t, T.S_BULK, T.S_END)
    else: c = scene_end(t)
    if t < T.S_END:
        place(c, logo_sticker(210), 165, 150, 1.0, 0, 0.94)   # Funhoods logo top-LEFT
    for tc, kind in T.CUTS:
        if kind == 'chev': chevron_wipe(c, t, tc)
        elif kind == 'flash': flash(c, t, tc)
        elif kind == 'zoom': flash(c, t, tc, 0.14, 0.35)
    if t > T.DUR - 0.5:
        c.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * prog(t, T.DUR - 0.5, 0.5)))))
    return c.convert('RGB')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='video.mp4'); ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=T.DUR)
    ap.add_argument('--stills', default=''); ap.add_argument('--preview', action='store_true', help='stills at 1080 wide')
    ap.add_argument('--stills_dir', default=P('stills'))
    a = ap.parse_args()
    if a.stills:
        os.makedirs(a.stills_dir, exist_ok=True)
        for s in a.stills.split(','):
            im = render(float(s))
            if a.preview: im = im.resize((1080, 1920), Image.LANCZOS)
            im.save(os.path.join(a.stills_dir, 'st_%06.2f.png' % float(s)))
        sys.exit()
    n0, n1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-threads', '2', '-x264-params', 'rc-lookahead=20', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '5.2',
                           '-movflags', '+faststart', a.out], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        ff.stdin.write(render(n / FPS).tobytes())
        if n % 60 == 0: print('frame', n, flush=True)
    ff.stdin.close(); ff.wait()
