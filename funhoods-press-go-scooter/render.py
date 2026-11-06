# Funhoods "Press & Go Scooter (PL-001)" B2B reel -- 2160x3840 @ 60 fps, in the style of the Dino Car reel: white-backdrop
# motion graphics, cut to the VO. How the toy works is animated on a rig made from the client's photos (tools/prep_assets.py):
# a finger presses the head three times -- each press pushes it down over the neck and turns it (front / profile /
# other profile), as in the client's raw clips -- then lets go and the scooter shoots off. No footage is used.
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
GOLD = (255, 186, 0); LIME = (118, 190, 38); BLUE = (40, 150, 230); OR2 = (255, 110, 30)
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
F_IMPACT = os.path.join(FONTS, 'LuckiestGuy-Regular.ttf')
F_BODY = os.path.join(FONTS, 'Inter-ExtraBold.ttf')
RIG = json.load(open(P('assets', 'rig.json')))

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

@functools.lru_cache(maxsize=40)
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

def speed_lines(c, t, y0, y1, n=12, seed=3, alpha=1.0, x0=-100, x1=1180, direction=-1):
    """streaks sliding along x (direction -1 = to the left, for something moving right; +1 = to the right)"""
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        y = rng.uniform(y0, y1); ln = rng.uniform(140, 360); sp = rng.uniform(1800, 2800); ph = rng.uniform(0, 1)
        u = (t * sp + ph * (x1 - x0)) % (x1 - x0 + ln)
        x = x1 - u if direction < 0 else x0 - ln + u
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
    _blit(im, body('PRESS & GO SCOOTER  •  PL-001', wd * 0.050, (92, 50, 20)), wd * 0.5, th + fh * 0.68)
    _blit(im, text_img('240 PCS', F_HEAD, wd * 0.15, RED, 0, DRED, 3, DRED), wd * 0.5, th + fh * 0.85)
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

# ---------------------------------------------------------------- the press-and-turn rig (mouse on the blue scooter)
# body = side view of the scooter (it faces LEFT), head cut off at the chin; head poses share the chin anchor.
RIG_H = RIG['body_size'][1]                                       # 1925 source px = full toy height
NECK = (720, RIG['cut'])                                          # centre of the neck's cut on the body (source px, x 506-933)
SIDE_NECK = 432                                                   # neck centre at the bottom of the profile head
HEADS = {'F': ('rig_head_front.png', False, NECK), 'B': ('rig_head_back.png', False, NECK),
         'R': ('rig_head_side.png', False, (SIDE_NECK, RIG['anchor_side'][1])),
         'L': ('rig_head_side.png', True, (asset('rig_head_side.png').width - SIDE_NECK, RIG['anchor_side'][1]))}
CROWN = (685, 46)                                                 # top of the head where the finger presses
PADT = 90                                                         # headroom above the body canvas (source px)

@functools.lru_cache(maxsize=8)
def rig_part(name, hd, mirror=False):
    im = asset(name); s = hd * K / RIG_H
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    return ImageOps.mirror(im) if mirror else im

@functools.lru_cache(maxsize=12)
def rig_img(hd, layers, press):
    """whole toy: body + head layers [(pose, x-squash %, alpha %, x-shift in source px)], head pushed down by press (source px)"""
    s = hd * K / RIG_H; body = rig_part('rig_body.png', hd); pt = int(PADT * s)
    out = Image.new('RGBA', (body.width, body.height + pt), (0, 0, 0, 0)); out.alpha_composite(body, (0, pt))
    cap = Image.new('RGBA', out.size, (0, 0, 0, 0)); cd = ImageDraw.Draw(cap)   # rounded top of the neck
    yc = pt + NECK[1] * s
    cd.ellipse((506 * s, yc - 34 * s, 933 * s, yc + 34 * s), fill=(214, 146, 6, 255))
    cd.ellipse((540 * s, yc - 26 * s, 900 * s, yc + 20 * s), fill=(238, 176, 22, 255))
    cd.rectangle((0, yc + 2 * s, out.width, out.height), fill=(0, 0, 0, 0)); out.alpha_composite(cap)
    for pose, sxq, aq, dxq in layers:
        if aq <= 0: continue
        name, mir, (ax, ay) = HEADS[pose]; hm = rig_part(name, hd, mir); sx = sxq / 100
        if sxq < 99: hm = hm.resize((max(1, int(hm.width * sx)), hm.height), Image.BICUBIC)
        if aq < 100: hm = hm.copy(); hm.putalpha(hm.getchannel('A').point(lambda v: v * aq // 100))
        x = int(round((NECK[0] + dxq) * s - ax * s * sx)); y = int(round(pt + (NECK[1] + press) * s - ay * s))
        out.alpha_composite(hm, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))
    return out

def draw_rig(c, x, gy, hd, layers=(('F', 1.0, 1.0, 0.0),), press=0.0, alpha=1.0, ghost=0.0, scale=1.0, sq=1.0):
    """toy standing on ground gy, centred on x; ghost = trail length to the right (it drives left)"""
    lq = tuple((p_, int(round(sx_ * 50)) * 2, int(round(a_ * 25)) * 4, int(round(dx_ / 4)) * 4) for p_, sx_, a_, dx_ in layers)
    im = rig_img(hd, lq, int(round(press / 4)) * 4)
    hh = im.height / K * scale; cy = gy - hh / 2 * sq
    if ghost > 1:
        for i in range(4, 0, -1): place(c, im, x + ghost * i / 4, cy, scale, 0, alpha * 0.16 * (5 - i) / 4, sy=scale * sq)
    place(c, im, x, cy, scale, 0, alpha, sy=scale * sq)

def rig_pt(x, gy, hd, px, py):
    """source point of the body canvas -> design coordinates (toy at x, standing on gy, scale 1)"""
    s = hd / RIG_H; return x + (px - RIG['body_size'][0] / 2) * s, gy - (RIG_H - py) * s

def press_depth(t):
    """head push-down (source px): two quick presses, then the final press held until the finger lets go"""
    press = 0.0
    for tp, up_t in [(T.PRESSES[0], T.PRESSES[0] + 0.17), (T.PRESSES[1], T.PRESSES[1] + 0.17), (T.GO_PRESS, T.RELEASE)]:
        if t < tp - 0.05: break
        if t < up_t: press = 130 * e_out(prog(t, tp - 0.05, 0.10))
        elif t < up_t + 0.16: press = 130 * (1 - e_back(prog(t, up_t, 0.16), 2.2))   # springs back with a small overshoot
        else: press = 0.0
    return press

def head_layers(t):
    """the head turning a full 360 on its own between TURN0 and TURN1 (no finger, no press): each quarter is a
    cross-fade between neighbouring poses with a small squash and slide in the turning direction"""
    if t <= T.TURN0 or t >= T.TURN1: return (('F', 1.0, 1.0, 0.0),)
    th = 4 * e_inout(prog(t, T.TURN0, T.TURN1 - T.TURN0)); k = min(3, int(th)); f = th - k
    out_, in_ = T.POSES[k], T.POSES[k + 1]; sm = f * f * (3 - 2 * f)
    lo = (out_, 1 - 0.28 * f, 1.0, -60 * f); li = (in_, 0.72 + 0.28 * f, 1.0, 60 * (1 - f))
    if f < 0.5: return (lo, (li[0], li[1], sm, li[3]))           # the outgoing pose underneath, the next fading in on top
    return (li, (lo[0], lo[1], 1 - sm, lo[3]))                    # past half way: swap, so the head never goes see-through

def glove_at(c, tipx, tipy, size=280, rot=78, alpha=1.0):
    """left-pointing glove turned so its finger tips point down; (tipx, tipy) = where the finger tips touch"""
    a = math.radians(rot); ox, oy = -142 * size / 300, 2 * size / 300
    dx, dy = ox * math.cos(a) + oy * math.sin(a), -ox * math.sin(a) + oy * math.cos(a)
    place(c, glove_l(size), tipx - dx, tipy - dy, 1.0, rot, alpha)

def turn_ring(c, t, cx, cy, rx, ry, a_, front):
    """animated 360 arrows round the head: the back half is drawn behind the toy, the front half over it"""
    if a_ <= 0: return
    sd = SD(c)
    for k in range(2):
        a0 = (t * 300 + k * 180) % 360
        for a in np.arange(a0, a0 + 120, 4.0):
            am = a % 360
            if (am < 180) != front: continue
            r0, r1 = math.radians(a), math.radians(a + 4.5)
            sd.line([(cx + rx * math.cos(r0), cy + ry * math.sin(r0)), (cx + rx * math.cos(r1), cy + ry * math.sin(r1))], width=13, fill=RED + (int(235 * a_),))
        ae = math.radians(a0 + 120)
        if ((a0 + 120) % 360 < 180) == front:                     # arrow head at the leading end
            px, py = cx + rx * math.cos(ae), cy + ry * math.sin(ae)
            tx, ty = -rx * math.sin(ae), ry * math.cos(ae); n_ = math.hypot(tx, ty); tx, ty = tx / n_, ty / n_
            sd.polygon([(px + tx * 38, py + ty * 38), (px - ty * 26, py + tx * 26), (px + ty * 26, py - tx * 26)], fill=RED + (int(235 * a_),))

def honk(c, t, cx, cy, r0=250):
    sd = SD(c)
    for tb in T.BEEPS:
        if not tb <= t < tb + 0.5: continue
        for k_ in range(3):
            q = prog(t, tb + k_ * 0.06, 0.4)
            if q <= 0 or q >= 1: continue
            rr = r0 + 170 * q; a = int(235 * (1 - q))
            for a0, a1 in ((145, 215), (-35, 35)):
                sd.arc((cx - rr, cy - rr * 0.8, cx + rr, cy + rr * 0.8), a0, a1, width=14, fill=RED + (a,))

def bounce_in(t, tl, h=1300):
    """y offset for something dropping in and landing at tl, plus its squash"""
    if t < tl: return -h * (1 - e_in(prog(t, tl - 0.30, 0.30))), 1.0
    u = t - tl; return 0.0, 1 - 0.08 * math.exp(-u * 9) * math.cos(u * 34)

def hop(t, th, amp=70):
    """little jump at th"""
    u = t - th
    if u < 0 or u > 0.42: return 0.0
    return -amp * 4 * (u / 0.42) * (1 - u / 0.42)

def toy(c, name, x, gy, h, t, alpha=1.0, rot=0.0, sq=1.0, dy=0.0, shadow=True):
    """product cut-out of height h standing on gy"""
    if shadow: ground_shadow(c, x, gy + 6, 0.62 * asset(name).width * h / asset(name).height + 60, alpha * clamp(1 + dy / 300))
    hq = max(40, int(round(h / 40)) * 40); k = h / hq                 # cache a few sizes, scale the rest (memory)
    place(c, with_shadow(name, hq, 12, 16, 70), x, gy - h / 2 * sq - 20 + dy, k, rot, alpha, sy=k * sq)

# ---------------------------------------------------------------- scenes
def scene_hero(t):
    """(horn: beep beep) Meet the Funhoods Press and Go Scooter! -- the orange mouse scooter (client infographic, sharp) drops in and honks"""
    c = bg(t); cx, gy, Hc = DW / 2, 1500, 800
    place(c, soft_burst(1050), cx, 1080, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.30 * clamp(t / 0.3))
    dy, sq = bounce_in(t, T.LAND0, 1500)
    beep = max([math.exp(-max(0, t - b) * 9) * (t >= b) for b in T.BEEPS] + [0])
    sc = 1 + 0.035 * beep + 0.008 * max(0, t - T.LAND0)
    toy(c, 'mouse_orange_hero.png', cx, gy, Hc * sc, t, 1.0, 2.0 * math.sin(t * 2.1) * (t > T.LAND0), sq, dy)
    dust(c, t, T.LAND0, cx - 200, gy, 6, 2, 160, dirx=-1); dust(c, t, T.LAND0, cx + 200, gy, 6, 3, 160, dirx=1)
    honk(c, t, cx, gy - Hc * 0.72, 260)
    pop(c, impact_txt('BEEP BEEP!', 130, YEL), cx, 1690, t, T.BEEPS[0], None, d=0.3, rot=-5, from_scale=1.8)
    pop(c, body('MEET THE', 46, RED), cx, 300, t, T.w(0, 0) - 0.04, None, slide=20)
    pop(c, impact_txt('PRESS & GO', 186, YEL), cx, 430, t, T.w(0, 3) - 0.06, None, d=0.34, from_scale=1.6, rot=-3)
    pop(c, head('SCOOTER', 128), cx, 592, t, T.w(0, 6) - 0.04, None, slide=30)
    return c

def scene_press(t, t0, t1):
    """Just press the head... watch it turn... and off it goes! -- kept apart, one action at a time:
    1) a finger presses the head down twice (down only); 2) the finger lifts away and the head turns a full 360 on its
    own (front, left, back, right, front); 3) the finger presses once more, holds, lets go -- the scooter shoots off left"""
    c = bg(t); gy, HD = 1500, 820; x0 = 560
    ground(c, gy)
    p = prog(t, t0, 0.35)
    press = press_depth(t); layers = head_layers(t)
    z = prog(t, T.RELEASE + 0.03, 0.5); x = x0 - 1450 * z ** 2.1
    sc = 0.86 + 0.14 * e_back(p, 1.4)
    hx, _ = rig_pt(x0, gy, HD, NECK[0], 0); ring_y = rig_pt(x0, gy, HD, 0, 935)[1]   # round the neck
    ring_a = clamp((t - T.TURN0 + 0.12) / 0.15) * (1 - clamp((t - T.TURN1 - 0.05) / 0.15))
    turn_ring(c, t, hx, ring_y, 250, 52, ring_a, False)
    if z < 1:
        ground_shadow(c, x, gy + 6, 560, clamp(p * 3))
        draw_rig(c, x, gy, HD, layers, press, clamp(p * 3), ghost=300 * clamp(z * 3) if z > 0 else 0, scale=sc,
                 sq=1 - 0.018 * press / 130)
    turn_ring(c, t, hx, ring_y, 250, 52, ring_a, True)
    if z > 0:
        speed_lines(c, t, gy - 520, gy - 30, 14, 5, 1 - prog(t, t1 - 0.25, 0.25), direction=1)
        dust(c, t, T.RELEASE + 0.03, x0 + 230, gy - 10, 9, 4, 210, 0.7, 42, dirx=1)
    # the finger: in for the two presses, away while the head turns, back for the final press, then lets go
    g1 = e_out(prog(t, T.PRESSES[0] - 0.40, 0.32)) * (1 - e_inout(prog(t, T.PRESSES[1] + 0.20, 0.30)))
    g2 = e_out(prog(t, T.TURN1 - 0.06, 0.26)) * (1 - e_inout(prog(t, T.RELEASE - 0.02, 0.32)))
    g = max(g1, g2)
    if g > 0.001:
        hover = 28 * e_inout(prog(t, T.PRESSES[0] + 0.17, 0.12)) * (1 - e_inout(prog(t, T.PRESSES[1] - 0.16, 0.10)))
        tx, ty = rig_pt(x0, gy, HD, CROWN[0], CROWN[1] + max(0, press))
        glove_at(c, tx + 360 * (1 - g), ty - 4 - hover - 500 * (1 - g), 280, 78 - 18 * (1 - g), clamp(g * 1.5))
        for tp in T.PRESSES + [T.GO_PRESS]:                        # a ring on the crown at each press
            q = prog(t, tp + 0.03, 0.35)
            if 0 < q < 1:
                sd = SD(c); rr = 50 + 70 * q
                sd.ellipse((tx - rr, ty - rr * 0.5, tx + rr, ty + rr * 0.5), width=8, outline=RED + (int(220 * (1 - q)),))
    pop(c, head('PRESS THE HEAD', 112), DW / 2, 310, t, T.w(1, 0) - 0.04, T.TURN0 - 0.02, slide=30)
    pop(c, head('WATCH IT TURN!', 118, YEL), DW / 2, 310, t, T.TURN0 - 0.02, T.RELEASE + 0.02, slide=30)
    if t >= T.RELEASE:
        place(c, burst(700), DW / 2, 420, 0.3 + 0.62 * e_back(prog(t, T.RELEASE, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, t1 - 0.2, 0.2)))
    pop(c, impact_txt('OFF IT GOES!', 140, YEL), DW / 2, 420, t, T.RELEASE + 0.02, None, d=0.3, rot=-5, from_scale=1.9)
    pop(c, chip('PRESS DOWN', 46, YEL, DRED, F_HEAD, 36, 16), DW / 2, 1640, t, T.PRESSES[0] + 0.05, T.TURN0 - 0.02, slide=24)
    pop(c, chip('HEAD TURNS 360°', 46, RED, WHITE, F_HEAD, 36, 16), DW / 2, 1640, t, T.TURN0 + 0.02, T.RELEASE + 0.1, slide=24)
    pop(c, chip('PRESS & GO ACTION', 46, YEL, DRED, F_HEAD, 36, 16), DW / 2, 1640, t, T.RELEASE + 0.1, None, slide=24)
    return c

def scene_riders(t, t0, t1):
    """Two cute riders, a little mouse and a happy duck! -- both slide in, each jumps on its word"""
    c = bg(t); gy = 1440
    pop(c, impact_txt('2 CUTE', 190, YEL), DW / 2, 330, t, T.w(2, 0) - 0.06, None, d=0.34, from_scale=1.6, rot=-3)
    pop(c, head('RIDERS', 130), DW / 2, 500, t, T.w(2, 2) - 0.06, None, slide=30)
    sd = SD(c)
    for i, (name, x, h, lbl, col, tw, side) in enumerate([('mouse_blue_front.png', 300, 700, 'MOUSE', BLUE, T.MOUSE, -1),
                                                           ('duck_blue_front2.png', 790, 720, 'DUCK', OR2, T.DUCK, 1)]):
        q = e_out(prog(t, t0 + 0.15 + 0.12 * i, 0.5))
        if q <= 0: continue
        on = e_back(prog(t, tw, 0.4), 1.5)
        if on > 0:
            r = 280 * on; sd.ellipse((x - r, gy - h * 0.5 - r, x + r, gy - h * 0.5 + r), fill=col + (50,))
        sc = 1 + 0.10 * math.exp(-max(0, t - tw) * 5) * (t > tw)
        toy(c, name, x + side * 700 * (1 - q), gy, h * sc, t, 1.0, (-3 if i == 0 else 3) * math.sin((t - t0) * 2.2) * (1 - 0.5 * on),
            1.0, hop(t, tw - 0.02, 90))
        if t > tw: sparkles(c, t, 7 + i, x, gy - h * 0.55, 230, 300, n=7, size=36)
        pop(c, chip(lbl, 50, col, WHITE, F_HEAD, 36, 14), x, gy + 105, t, tw + 0.04, None, slide=24)
    return c

SKYB = (60, 186, 236)
def scene_colours(t, t0, t1):
    """Bright blue, red and orange scooters. -- the 4 colours (client infographic): blue, red, sky blue, orange pop in"""
    c = bg(t); sd = SD(c)
    pop(c, head('BRIGHT', 104), DW / 2, 290, t, T.w(3, 0) - 0.06, None, slide=30)
    pop(c, impact_txt('4 COLOURS', 170, YEL), DW / 2, 440, t, T.w(3, 1) - 0.06, None, d=0.34, from_scale=1.6, rot=-3)
    spots = [(290, 990, 'c4_blue.png', 'BLUE', BLUE), (790, 990, 'c4_red.png', 'RED', RED),
             (290, 1570, 'c4_skyblue.png', 'SKY BLUE', SKYB), (790, 1570, 'c4_orange.png', 'ORANGE', OR2)]
    for i, ((x, gy, name, lbl, col), tp) in enumerate(zip(spots, T.COL_POPS)):
        q = e_back(prog(t, t0 + 0.25 + i * 0.08, 0.4), 1.5)                 # colour blob behind each slot
        if q > 0:
            r = 200 * q; sd.ellipse((x - r, gy - 215 - r, x + r, gy - 215 + r), fill=col + (55,))
        if t >= tp - 0.04:
            pp = prog(t, tp - 0.04, 0.42)
            toy(c, name, x, gy, 420 * (0.6 + 0.4 * e_back(pp, 1.5)), t, clamp(pp * 3), (-3 if i % 2 else 3) * math.sin(t * 1.7 + i),
                1.0, 150 * (1 - e_back(pp, 1.3)) + hop(t, T.w(3, 5) + 0.06 * i, 30))
    for (x, gy, name, lbl, col), tp in zip(spots, T.COL_POPS):          # labels over the toys
        pop(c, chip(lbl, 40, col, WHITE, F_HEAD, 30, 12), x, gy + 48, t, tp + 0.06, None, slide=20)
    return c

def scene_safe(t, t0, t1):
    """BIS certified, Made in India and non-toxic."""
    c = bg(t); p = prog(t, t0, 0.5); gy = 1110
    place(c, soft_burst(1000), DW / 2, 770, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.28 * clamp(p * 3))
    for i, (name, x, h) in enumerate([('mouse_red_front.png', 365, 600), ('duck_blue_front2.png', 720, 640)]):
        pi = prog(t, t0 + 0.05 + 0.1 * i, 0.5)
        toy(c, name, x, gy, h, t, clamp(pi * 3), (3 if i else -3) * math.sin((t - t0) * 1.6 + i), 1.0, 200 * (1 - e_back(pi, 1.3)))
    sparkles(c, t, 11, DW / 2, 760, 430, 330, n=10)
    rows = [('shield', 'BIS CERTIFIED'), ('india', 'MADE IN INDIA'), ('check', 'NON-TOXIC'), ('age', '3+ YEARS')]
    for i, ((k, txt), tp) in enumerate(zip(rows, T.SAFE_POPS)):
        im = badge_row(k, txt, 70)
        pop(c, im, 120 + im.width / K / 2, 1210 + i * 134, t, tp - 0.04, None, slide=30)
    w0 = badge_row('shield', 'BIS CERTIFIED', 70).width / K; tx = body('IS 9873 (PART-1)', 30, DRED)
    pop(c, tx, 120 + w0 + 22 + tx.width / K / 2, 1214, t, T.SAFE_POPS[0] + 0.3, None, slide=10)
    return c

PACK_H = 960
def hook(c, x, y):
    sd = SD(c)
    sd.rrect((x - 46, y - 34, x + 46, y + 6), 10, fill=(150, 150, 160, 255))
    sd.line([(x, y - 14), (x, y + 30)], width=16, fill=(120, 120, 132, 255)); sd.line([(x - 3, y - 14), (x - 3, y + 26)], width=4, fill=(205, 205, 215, 255))

def hung(c, name, px, py, h, ang, alpha=1.0, dy=0.0):
    """pouch hanging from a peg at (px, py), swung by ang degrees"""
    d = h / 2; a = math.radians(ang); hq = max(40, int(round(h / 40)) * 40)
    place(c, with_shadow(name, hq, 14, 18, 80), px + d * math.sin(a), py + dy + d * math.cos(a), h / hq, ang, alpha)

def swing(t, tl, amp=9.0):
    if t < tl: return 0.0
    u = t - tl; return amp * math.exp(-u * 2.2) * math.sin(u * 7)

def scene_pouch(t, t0, t1):
    """In a see-through pouch that shows off every rider. -- the new transparent pouch (client infographic) drops onto a peg and swings"""
    c = bg(t); px, py = DW / 2, 585; tl = t0 + 0.38
    pop(c, head('SEE-THROUGH POUCH', 104), DW / 2, 300, t, T.w(5, 2) - 0.06, None, slide=30)
    hook(c, px, py)
    q = prog(t, tl - 0.34, 0.34)
    if q > 0:
        dy = -1300 * (1 - e_in(q)) if t < tl else 0.0
        sc = 1 + 0.012 * max(0, t - tl)
        hung(c, 'pack_new.png', px, py + 22, PACK_H * sc, swing(t, tl), clamp(q * 3), dy)
    if t >= T.SHOWS:                                               # the rider shows through the window
        sd = SD(c); u = prog(t, T.SHOWS, 0.5); cx_, cy_ = px, py + 22 + PACK_H * 0.64
        for k_ in range(2):
            qq = ((t - T.SHOWS) * 1.2 + k_ * 0.5) % 1
            r = 250 + 90 * qq
            sd.ellipse((cx_ - r, cy_ - r * 1.05, cx_ + r, cy_ + r * 1.05), width=10, outline=GOLD + (int(230 * (1 - qq) * clamp(u * 3)),))
        sparkles(c, t, 23, cx_, cy_, 330, 360, n=10, size=40)
    pop(c, impact_txt('SHOWS EVERY RIDER!', 104, YEL), DW / 2, 1680, t, T.SHOWS, None, d=0.3, rot=-4, from_scale=1.8)
    return c

def scene_carton(t, t0, t1):
    """240 pieces per carton -- cartons drop and stack; a Funhoods truck delivers anywhere in India"""
    c = bg(t); shake = [0.0, 0.0]
    pop(c, impact_txt('240 PCS', 210, YEL), DW / 2, 320, t, T.w(6, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('PER CARTON', 104), DW / 2, 490, t, T.w(6, 2) - 0.06, None, slide=30)
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
    pop(c, head('PAN INDIA DELIVERY', 92), DW / 2, 1735, t, T.TRUCK - 0.03, None, slide=30)
    return shift(c, shake[0], shake[1])

PEGS = [(220, 690), (540, 690), (860, 690), (220, 1070), (540, 1070), (860, 1070)]
def scene_bulk(t, t0, t1):
    """Distributors and wholesalers, fill your shelves with Press and Go! -- a peg wall fills up with pouches"""
    c = bg(t); sd = SD(c)
    pop(c, body('FOR', 46, RED), DW / 2, 290, t, t0 + 0.06, None, slide=20)
    pop(c, head('DISTRIBUTORS', 124), DW / 2, 392, t, T.w(7, 0) - 0.06, None, slide=30)
    pop(c, head('& WHOLESALERS', 112, YEL), DW / 2, 528, t, T.w(7, 2) - 0.06, None, slide=30)
    q = e_out(prog(t, t0 + 0.25, 0.4))
    if q > 0:                                                      # peg board slides up
        oy = 900 * (1 - q)
        sd.rrect((60 + 8, 620 + oy + 14, 1020 + 8, 1450 + oy + 14), 28, fill=(60, 0, 0, 70))
        sd.rrect((60, 620 + oy, 1020, 1450 + oy), 28, fill=(238, 206, 160, 255))
        for yy in range(660, 1440, 52):
            for xx in range(100, 1000, 52): sd.ellipse((xx - 5, yy + oy - 5, xx + 5, yy + oy + 5), fill=(200, 160, 112, 255))
        for i, (x, y) in enumerate(PEGS):
            hook(c, x, y + oy)
    for i, ((x, y), tp) in enumerate(zip(PEGS, T.FILL)):
        pp = prog(t, tp - 0.2, 0.2)
        if pp <= 0: continue
        dy = -700 * (1 - e_out(pp))
        hung(c, 'pack_new.png', x, y + 20, 340, swing(t, tp, 7), clamp(pp * 3), dy)
    pop(c, chip('BULK ORDERS ONLY', 56, YEL, DRED, F_HEAD, 44, 20), DW / 2, 1545, t, T.w(7, 2) + 0.2, None, slide=30)
    tf = T.w(7, 3) - 0.06
    pop(c, impact_txt('FILL YOUR SHELVES!', 112, YEL), DW / 2, 1700, t, tf, None, d=0.3, rot=-4, from_scale=1.8)
    return c

def scene_end(t):
    t0 = T.S_END
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, t0, 0.5))
    sd.polygon([(0, 0), (DW, 0), (DW, 250 * p + 60), (DW / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    sd.polygon([(0, 250 * p + 60), (DW / 2, 330 * p + 60), (DW, 250 * p + 60), (DW, 250 * p + 76), (DW / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    sd.polygon([(0, DH), (DW, DH), (DW, DH - 200 * p), (0, DH - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png'); tl = T.w(8, 0) - 0.22
    place(c, lg, DW / 2, 520, (800 * K / lg.width) * (0.4 + 0.6 * e_back(prog(t, tl, 0.42), 1.6)), 0, clamp((t - tl) / 0.1))
    for i, (a, x, h_, dl, rot) in enumerate([('c4_blue.png', 185, 300, 0.25, 5), ('c4_red.png', 895, 300, 0.35, -5)]):
        pb = prog(t, t0 + dl, 0.5); side = -1 if x < DW / 2 else 1
        place(c, with_shadow(a, h_, 10, 12, 70), x + side * 500 * (1 - e_out(pb)), 1060 + 5 * math.sin(t * 2.2 + i), 1.0, rot, clamp(pb * 3))
    pf = prog(t, t0 + 0.15, 0.5)
    place(c, with_shadow('mouse_orange_hero.png', 470, 12, 16, 80), DW / 2, 1000 + 260 * (1 - e_back(pf, 1.3)) + 5 * math.sin(t * 2), 1.0, 0, clamp(pf * 3))
    pop(c, body('PRESS & GO SCOOTER  •  PL-001  •  3+ YEARS', 36, RED), DW / 2, 1300, t, t0 + 0.45, None, slide=20)
    pop(c, chip('BULK ORDERS ONLY', 52, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1415, t, t0 + 0.6, None, slide=30)
    ca, cb_ = chip('240 PCS / CARTON', 34, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 34, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1530, t, t0 + 0.8, None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1530, t, t0 + 0.95, None, slide=20)
    pop(c, body('For Distributors  &  Wholesalers', 36, INK), DW / 2, 1630, t, t0 + 1.1, None, slide=20)
    return c

def render(t):
    if t < T.S_PRESS: c = scene_hero(t)
    elif t < T.S_RIDERS: c = scene_press(t, T.S_PRESS, T.S_RIDERS)
    elif t < T.S_COLOURS: c = scene_riders(t, T.S_RIDERS, T.S_COLOURS)
    elif t < T.S_SAFE: c = scene_colours(t, T.S_COLOURS, T.S_SAFE)
    elif t < T.S_POUCH: c = scene_safe(t, T.S_SAFE, T.S_POUCH)
    elif t < T.S_CARTON: c = scene_pouch(t, T.S_POUCH, T.S_CARTON)
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
