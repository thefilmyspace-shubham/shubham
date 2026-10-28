# Funhoods "Fighter Jets (6 in 1 pack)" B2B reel -- 2160x3840 @ 60 fps. Motion graphics on the white backdrop of the
# Dino Car reel; the product shots are cut-outs of the client's 360° product view and "what's in the box" infographics,
# colour graded (contrast, vibrance, clarity). How the toy works (pull back, let go) is animated -- no footage is used.
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
GOLD = (255, 186, 0); CAMO = (46, 128, 52)
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
    _blit(im, body('FIGHTER JETS  •  6 IN 1', wd * 0.058, (92, 50, 20)), wd * 0.5, th + fh * 0.68)
    _blit(im, text_img('144 PCS', F_HEAD, wd * 0.15, RED, 0, DRED, 3, DRED), wd * 0.5, th + fh * 0.85)
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


# ---------------------------------------------------------------- jets
DESIGNS = ['d1.png', 'd2.png', 'd3.png', 'd4.png', 'd5.png', 'd6.png']   # fire red, white, purple, black-blue, yellow, camo

def puffs(c, pts, col=(214, 222, 234)):
    """contrail: pts = [(x, y, age 0..1)], older puffs bigger and fainter"""
    sd = SD(c)
    for x, y, a in pts:
        if a >= 1: continue
        r = 16 + 46 * a
        sd.ellipse((x - r, y - r, x + r, y + r), fill=col + (int(200 * (1 - a) ** 1.5),))

def ghosted(c, im, x, y, trail, rot=0.0, n=4):
    """image with a motion trail of length `trail` (design units, + = trail to the right)"""
    for i in range(n, 0, -1):
        place(c, im, x + trail * i / n, y, 1.0, rot, 0.16 * (n + 1 - i) / n)
    place(c, im, x, y, 1.0, rot)

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

# ---------------------------------------------------------------- scenes
def scene_hero(t):
    """Ready for take-off? Meet the Funhoods Fighter Jet Squad! -- the fire jet swoops in and hovers"""
    c = bg(t); WJ = 860
    place(c, soft_burst(1050), DW / 2, 1080, 0.85 + 0.04 * math.sin(t * 2.5), (t * 10) % 360, 0.28 * prog(t, 0.5, 0.4))
    im = with_shadow('jet_q34.png', int(WJ * asset('jet_q34.png').height / asset('jet_q34.png').width), 14, 40, 70)
    def path(tt):
        u = e_out(prog(tt, T.FLY_IN, 0.80))
        return lerp(1350, 545, u) + 6 * math.sin(tt * 1.7), lerp(160, 1070, u) + 14 * math.sin(tt * 2.2) * prog(tt, 0.9, 0.5)
    pts = []
    for k in range(1, 14):                                         # contrail from the tail (upper right)
        tt = t - k * 0.045
        if tt < T.FLY_IN: break
        px, py = path(tt); pts.append((px + 300, py - 150, k / 14 + prog(t, 1.2, 1.0)))
    puffs(c, pts)
    x, y = path(t); sp = 1 - prog(t, T.FLY_IN + 0.3, 0.6)
    ground_shadow(c, x - 20, 1500, 520 * (0.5 + 0.5 * prog(t, 0.2, 0.7)), 0.7 * prog(t, 0.2, 0.7))
    ghosted(c, im, x, y, 240 * sp, -4 + 2 * math.sin(t * 1.6), 4 if sp > 0.05 else 0)
    if sp > 0: speed_lines(c, t, 820, 1350, 10, 3, sp)
    pop(c, head('READY FOR', 104), DW / 2, 300, t, T.w(0, 0), T.TITLE_SWAP, slide=30)
    pop(c, impact_txt('TAKE-OFF?', 190, YEL), DW / 2, 445, t, T.w(0, 2) - 0.08, T.TITLE_SWAP, d=0.34, from_scale=1.6, rot=-3)
    pop(c, body('MEET THE', 44, RED), DW / 2, 285, t, T.TITLE_SWAP + 0.08, None, slide=20)
    pop(c, head('FIGHTER JET', 124), DW / 2, 385, t, T.w(0, 5) - 0.08, None, slide=30)
    pop(c, impact_txt('SQUAD!', 200, YEL), DW / 2, 540, t, T.w(0, 7) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    return c

def scene_six(t, t0, t1):
    """Six jets, six bold designs, all in one pack! -- the six designs take off into a 3 x 2 grid"""
    c = bg(t)
    for i, (a, tp) in enumerate(zip(DESIGNS, T.SIX_POPS)):
        q = prog(t, tp, 0.5)
        if q <= 0: continue
        x, y = [215, 540, 865][i % 3], [905, 1305][i // 3]
        ground_shadow(c, x, y + 200, 200, clamp(q * 2) * 0.6)
        place(c, with_shadow(DESIGNS[i], 330, 10, 26, 70), x, y + 8 * math.sin(t * 2.4 + i) + 700 * (1 - e_back(q, 1.1)),
              0.8 + 0.2 * e_out(q), 3 * math.sin(t * 1.8 + i * 1.3), clamp(q * 3))
    pop(c, impact_txt('6 JETS', 190, YEL), DW / 2, 330, t, T.w(1, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('6 BOLD DESIGNS', 104), DW / 2, 500, t, T.w(1, 2) - 0.06, None, slide=30)
    pop(c, chip('ALL IN 1 PACK', 56, RED, WHITE, F_HEAD, 44, 18), DW / 2, 1660, t, T.w(1, 5) - 0.06, None, slide=30)
    return c

def scene_pull(t, t0, t1):
    """Pull it back... and let it fly! -- a glove pulls the jet back, lets go, it zooms off (pull-back motor)"""
    c = bg(t); gy, WJ = 1330, 860
    ground(c, gy)
    im = scaled('jet_side.png', w=WJ); HJ = im.height / K
    xin = lerp(-500, 420, e_out(prog(t, t0, 0.42)))
    pull = e_inout(prog(t, T.PULL0, T.PULL1 - T.PULL0)); x = xin + 190 * pull
    if T.PULL1 < t < T.RELEASE: x += 2.0 * math.sin(t * 120)                    # held back, the motor ticking
    z = prog(t, T.RELEASE + 0.02, 0.50); x -= 1900 * z ** 2.2
    if z < 1:
        ground_shadow(c, x, gy + 6, WJ * 0.8)
        ghosted(c, im, x, gy - HJ / 2, 300 * clamp(z * 3), 0, 4 if z > 0 else 0)
    if z > 0:
        speed_lines(c, t, gy - 420, gy - 20, 14, 5, 1 - prog(t, t1 - 0.25, 0.25))
        dust(c, t, T.RELEASE + 0.03, xin + 190 + WJ * 0.18, gy - 10, 8, 4, 190, 0.7, 40, dirx=1)
    chevrons(c, t, x + 120, x + 360, gy + 75, 1, RED, clamp((t - T.PULL0) / 0.15) * (1 - clamp((t - T.RELEASE) / 0.1)))
    chevrons(c, t, 160, 900, gy + 75, -1, GOLD, clamp((t - T.RELEASE) / 0.1) * (1 - prog(t, t1 - 0.25, 0.25)))
    gin = e_out(prog(t, T.HAND_IN, 0.30)); gout = e_inout(prog(t, T.RELEASE, 0.35))
    if gin > 0 and gout < 1:                                       # glove grips the tail and pulls back
        hx = xin + 190 * pull + WJ * 0.30 + 380 * (1 - gin) + 220 * gout
        hy = gy - HJ * 0.95 - 420 * (1 - gin) - 360 * gout
        place(c, glove_l(300), hx, hy, 1.0, 12 - 10 * gout, 1 - gout)
    pop(c, head('PULL IT BACK', 120), DW / 2, 360, t, T.PULL0 - 0.06, T.RELEASE + 0.05, slide=30)
    if t >= T.RELEASE:
        place(c, burst(700), DW / 2, 520, 0.3 + 0.7 * e_back(prog(t, T.RELEASE, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, t1 - 0.2, 0.2)))
    pop(c, impact_txt('LET IT FLY!', 170, YEL), DW / 2, 520, t, T.RELEASE + 0.02, None, d=0.3, rot=-5, from_scale=1.9)
    pop(c, chip('PULL-BACK & GO ACTION', 44, YEL, DRED), DW / 2, 1600, t, T.PULL0 + 0.15, None, slide=30)
    return c

def scene_designs(t, t0, t1):
    """A fire jet, a camo jet and four more colourful flyers"""
    c = bg(t)
    pop(c, head('SAME BASE,', 84), DW / 2, 285, t, t0 + 0.08, None, slide=24)
    pop(c, head('DIFFERENT DESIGNS', 96, YEL), DW / 2, 395, t, t0 + 0.30, None, slide=24)
    for x, a, tp, lbl, col in [(290, 'd1.png', T.FIRE, 'FIRE JET', RED), (790, 'd6.png', T.CAMO, 'CAMO JET', CAMO)]:
        q = prog(t, tp, 0.45)
        if q <= 0: continue
        place(c, soft_burst(640), x, 840, 0.7 + 0.05 * math.sin(t * 3), (t * 20) % 360, 0.25 * clamp(q * 3))
        place(c, with_shadow(a, 560, 12, 30, 80), x, 850 + 8 * math.sin(t * 2.2 + x) + 500 * (1 - e_back(q, 1.2)), 1.0, -4 if x < 540 else 4, clamp(q * 3))
        pop(c, chip(lbl, 46, col, WHITE, F_HEAD, 34, 14), x, 1175, t, tp + 0.10, None, slide=20)
    for i, (a, tp) in enumerate(zip(DESIGNS[1:5], T.FOUR)):
        q = prog(t, tp, 0.42)
        if q <= 0: continue
        x = 165 + i * 250
        place(c, with_shadow(a, 300, 10, 22, 70), x, 1450 + 6 * math.sin(t * 2.6 + i) + 520 * (1 - e_back(q, 1.2)), 1.0, 3 * math.sin(t * 2 + i), clamp(q * 3))
    pop(c, chip('+ 4 MORE COLOURFUL FLYERS', 40, YEL, DRED), DW / 2, 1720, t, T.FOUR[0] + 0.25, None, slide=20)
    return c

def scene_safe(t, t0, t1):
    """BIS certified, safe & non-toxic, BPA free, Made in India"""
    c = bg(t); p = prog(t, t0, 0.5)
    place(c, soft_burst(980), DW / 2, 700, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.28 * clamp(p * 3))
    WJ = 780; hj = int(WJ * asset('jet_q34.png').height / asset('jet_q34.png').width)
    place(c, with_shadow('jet_q34.png', hj, 14, 30, 70), DW / 2 + 160 * (1 - e_out(p)), 720 + 12 * math.sin((t - t0) * 2.2) - 120 * (1 - e_out(p)),
          (0.85 + 0.15 * e_back(p, 1.4)), -3 + 2 * math.sin((t - t0) * 1.6), clamp(p * 3))
    sparkles(c, t, 11, DW / 2, 720, 430, 300, n=10)
    rows = [('shield', 'BIS CERTIFIED – IS 9873'), ('check', 'SAFE & NON-TOXIC'), ('drop', 'BPA FREE'), ('india', 'MADE IN INDIA')]
    for i, ((k, txt), tp) in enumerate(zip(rows, T.SAFE_POPS)):
        im = badge_row(k, txt, 64)
        pop(c, im, 100 + im.width / K / 2, 1150 + i * 132, t, tp - 0.04, None, slide=30)
    return c

def scene_pack(t, t0, t1):
    """Bright, eye-catching packs that fly off the shelves!"""
    c = bg(t); shelf = 1470
    pop(c, head('BRIGHT, EYE-CATCHING', 92), DW / 2, 290, t, T.w(5, 0) - 0.06, None, slide=30)
    pop(c, impact_txt('PACKS', 170, YEL), DW / 2, 430, t, T.w(5, 3) - 0.06, None, d=0.34, from_scale=1.6, rot=-3)
    cp = e_out(prog(t, t0 + 0.05, 0.45))
    if cp > 0: place(c, counter_top(), DW / 2 - DW * (1 - cp), shelf + 85)
    for i, (x, hh, dl) in enumerate([(205, 620, 0.16), (875, 620, 0.26), (540, 800, 0.0)]):   # side packs first (behind)
        q = prog(t, T.PACK_LAND - 0.34 + dl, 0.34)
        if q <= 0: continue
        yl = shelf - hh / 2 + 4
        if t < T.PACK_LAND + dl: y = yl - 1300 * (1 - e_in(q))
        else:
            u = t - T.PACK_LAND - dl; y = yl - 26 * math.exp(-u * 9) * abs(math.sin(u * 22))
        f = prog(t, T.FLY_OFF + [0.10, 0.18, 0.0][i], 0.55)                          # ...and they fly off the shelf
        y -= 2300 * e_in(f); rot = [-4, 4, 0][i] * (1 - prog(t, T.PACK_LAND, 0.4)) + [-14, 14, -6][i] * e_in(f)
        place(c, with_shadow('pack.png', hh, 14, 22, 80), x, y, 1.0, rot)
    if t > T.PACK_LAND and t < T.FLY_OFF: sparkles(c, t, 21, DW / 2, 1050, 470, 380, n=12, size=40)
    if t > T.FLY_OFF:
        sd = SD(c)
        for k in range(10):                                        # vertical speed streaks as they shoot up
            rng = np.random.default_rng(k); xx = rng.uniform(80, 1000); ln = rng.uniform(200, 420)
            yy = 1500 - ((t - T.FLY_OFF) * rng.uniform(2200, 3200)) % 1700
            sd.line([(xx, yy), (xx, yy + ln)], width=8, fill=[RED, GOLD, (250, 190, 180)][k % 3] + (int(190 * (1 - prog(t, t1 - 0.2, 0.2))),))
    pop(c, impact_txt('FLY OFF THE SHELVES!', 112, YEL), DW / 2, 1690, t, T.FLY_OFF, None, d=0.3, rot=-4, from_scale=1.8)
    return c

def scene_carton(t, t0, t1):
    """144 per carton -- cartons drop and stack; a Funhoods truck delivers anywhere in India"""
    c = bg(t); shake = [0.0, 0.0]
    pop(c, impact_txt('144 PCS', 200, YEL), DW / 2, 320, t, T.w(6, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('PER CARTON', 104), DW / 2, 490, t, T.w(6, 1) - 0.06, None, slide=30)
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
    pop(c, head('PAN INDIA DELIVERY', 92), DW / 2, 1735, t, T.w(6, 4) - 0.08, None, slide=30)
    return shift(c, shake[0], shake[1])

def scene_bulk(t, t0, t1):
    """FOR DISTRIBUTORS & WHOLESALERS -- the squad flies in formation -- BULK ORDERS ONLY -- BOOK NOW!"""
    c = bg(t)
    pop(c, body('FOR', 46, RED), DW / 2, 290, t, t0 + 0.06, None, slide=20)
    pop(c, head('DISTRIBUTORS', 124), DW / 2, 392, t, T.w(7, 0) - 0.06, None, slide=30)
    pop(c, head('& WHOLESALERS', 112, YEL), DW / 2, 528, t, T.w(7, 2) - 0.06, None, slide=30)
    V = [(540, 760), (370, 900), (710, 900), (200, 1040), (880, 1040), (540, 1060)]
    for i, (x, y) in enumerate(V):                                 # V formation climbing in from below
        q = prog(t, t0 + 0.20 + i * 0.07, 0.7)
        if q <= 0: continue
        place(c, with_shadow(DESIGNS[i], 250 if i else 290, 10, 20, 60), x, y + 1300 * (1 - e_out(q)) + 8 * math.sin(t * 2.4 + i), 1.0, 0, clamp(q * 3))
    pop(c, chip('BULK ORDERS ONLY', 60, YEL, DRED, F_HEAD, 44, 20), DW / 2, 1300, t, T.w(7, 5) - 0.06, None, slide=30)
    to = T.w(7, 7) - 0.10
    if t >= to:
        place(c, burst(760), DW / 2, 1630, 0.22 + 0.46 * e_back(prog(t, to, 0.3), 1.6), (t * 40) % 360, 0.95 * (1 - prog(t, t1 - 0.25, 0.25)))
    pop(c, impact_txt('BOOK NOW!', 170, YEL), DW / 2, 1630, t, to, None, d=0.3, rot=-5, from_scale=1.9)
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
    for i, (a, x, rot, dl) in enumerate([('d1.png', 150, 18, 0.30), ('d6.png', 930, -18, 0.40)]):
        pb = prog(t, t0 + dl, 0.5); side = -1 if x < DW / 2 else 1
        place(c, with_shadow(a, 300, 10, 14, 60), x + side * 500 * (1 - e_out(pb)), 1010 + 6 * math.sin(t * 2.2 + i), 1.0, rot, clamp(pb * 3))
    pf = prog(t, t0 + 0.15, 0.5); WJ = 620; hj = int(WJ * asset('jet_q34.png').height / asset('jet_q34.png').width)
    place(c, with_shadow('jet_q34.png', hj, 12, 24, 70), DW / 2 + 400 * (1 - e_out(pf)), 1020 - 300 * (1 - e_out(pf)) + 6 * math.sin(t * 2), 1.0, -3, clamp(pf * 3))
    pop(c, body('FIGHTER JETS  •  6 IN 1 PACK  •  AGES 3+', 36, RED), DW / 2, 1290, t, t0 + 0.45, None, slide=20)
    pop(c, chip('BULK ORDERS ONLY', 52, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1405, t, t0 + 0.6, None, slide=30)
    ca, cb_ = chip('144 PCS / CARTON', 34, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 34, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1520, t, t0 + 0.8, None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1520, t, t0 + 0.95, None, slide=20)
    pop(c, body('For Distributors  &  Wholesalers', 36, INK), DW / 2, 1625, t, t0 + 1.1, None, slide=20)
    return c

def render(t):
    if t < T.S_SIX: c = scene_hero(t)
    elif t < T.S_PULL: c = scene_six(t, T.S_SIX, T.S_PULL)
    elif t < T.S_DESIGNS: c = scene_pull(t, T.S_PULL, T.S_DESIGNS)
    elif t < T.S_SAFE: c = scene_designs(t, T.S_DESIGNS, T.S_SAFE)
    elif t < T.S_PACK: c = scene_safe(t, T.S_SAFE, T.S_PACK)
    elif t < T.S_CARTON: c = scene_pack(t, T.S_PACK, T.S_CARTON)
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
