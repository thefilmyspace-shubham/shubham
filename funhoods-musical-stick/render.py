# Funhoods "Cartoon Fun Story Musical Stick" B2B reel -- 2160x3840 @ 60 fps.
# Layout is written in a 1080x1920 design space; every primitive scales by T.K.
import sys, os, re, math, json, argparse, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
FONTS = os.environ.get('FONTS', os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts'))
K, DW, DH = T.K, T.DW, T.DH
W, H, FPS = DW * K, DH * K, T.FPS
b = T.b

RED = (210, 24, 31); DRED = (120, 6, 14); ORANGE = (255, 162, 58); YEL = (255, 212, 0)
WHITE = (255, 255, 255); CREAM = (255, 248, 236); INK = (40, 22, 22); SKY = (40, 160, 226)
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
F_IMPACT = os.path.join(FONTS, 'LuckiestGuy-Regular.ttf')
F_BODY = os.path.join(FONTS, 'Inter-ExtraBold.ttf')
GEOM = json.load(open(P('assets', 'geom.json')))

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b_=1.0): return max(a, min(b_, x))
def e_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def e_inout(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def e_back(x, s=1.9):
    x = clamp(x); c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def prog(t, t0, d): return clamp((t - t0) / d)

class SD:
    """ImageDraw in design units."""
    def __init__(self, img): self.d = ImageDraw.Draw(img)
    def _p(self, pts): return [(x * K, y * K) for x, y in pts]
    def polygon(self, pts, **kw): self.d.polygon(self._p(pts), **kw)
    def ellipse(self, box, width=0, **kw): self.d.ellipse([v * K for v in box], width=int(width * K), **kw)
    def rectangle(self, box, **kw): self.d.rectangle([v * K for v in box], **kw)
    def line(self, pts, width=1, **kw): self.d.line(self._p(pts), width=int(width * K), **kw)
    def arc(self, box, start, end, width=1, **kw): self.d.arc([v * K for v in box], start, end, width=int(width * K), **kw)

# ---------------------------------------------------------------- text
@functools.lru_cache(maxsize=None)
def font(path, size): return ImageFont.truetype(path, size)

@functools.lru_cache(maxsize=256)
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

@functools.lru_cache(maxsize=64)
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

def place(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    """cx, cy in design units; img in output pixels"""
    if alpha <= 0.003 or scale <= 0.01: return
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    x, y = int(round(cx * K - im.width / 2)), int(round(cy * K - im.height / 2))
    sx, sy = max(0, -x), max(0, -y); x0, y0 = max(0, x), max(0, y)
    w_, h_ = min(im.width - sx, W - x0), min(im.height - sy, H - y0)
    if w_ <= 0 or h_ <= 0: return
    canvas.alpha_composite(im, (x0, y0), (sx, sy, sx + w_, sy + h_))

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
    return np.clip(1.08 - r * 1.05, 0.55, 1.05)[..., None].astype(np.float32)

@functools.lru_cache(maxsize=30)
def sunburst(k):
    S = 2300 * K; n = 24
    im = Image.new('RGB', (S, S), (196, 16, 26)); d = ImageDraw.Draw(im)
    c = S / 2; off = (k / 30) * (360 / n)
    for i in range(0, n, 2):
        a0 = math.radians(i * 360 / n + off); a1 = math.radians((i + 1) * 360 / n + off)
        d.polygon([(c, c), (c + 2 * S * math.cos(a0), c + 2 * S * math.sin(a0)), (c + 2 * S * math.cos(a1), c + 2 * S * math.sin(a1))], fill=(222, 34, 42))
    im = im.crop(((S - W) // 2, (S - H) // 2 - 120 * K, (S - W) // 2 + W, (S - H) // 2 - 120 * K + H))
    arr = np.asarray(im).astype(np.float32) * _radial()
    ht = np.asarray(halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.10 * ht) + np.array([90, 0, 6]) * 0.10 * ht
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def red_bg(t): return sunburst(int((t * 6) % 30)).convert('RGBA')

@functools.lru_cache(maxsize=1)
def cream_bg():
    arr = np.ones((H, W, 3), np.float32) * np.array(CREAM, np.float32)
    ht = np.asarray(halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.07 * ht) + np.array(RED, np.float32) * 0.07 * ht
    return Image.fromarray(arr.astype(np.uint8)).convert('RGBA')

@functools.lru_cache(maxsize=1)
def grad_bottom():
    y = np.arange(H) / K
    a = (np.clip((y - 1020) / 700, 0, 1) ** 1.3 * 0.72)[:, None].repeat(W, 1)
    im = Image.new('RGBA', (W, H), (20, 0, 0, 0)); im.putalpha(Image.fromarray((a * 255).astype(np.uint8))); return im

@functools.lru_cache(maxsize=1)
def grad_top():
    y = np.arange(H) / K
    a = (np.clip(1 - y / 520, 0, 1) ** 1.5 * 0.55)[:, None].repeat(W, 1)
    im = Image.new('RGBA', (W, H), (20, 0, 0, 0)); im.putalpha(Image.fromarray((a * 255).astype(np.uint8))); return im

# ---------------------------------------------------------------- assets
@functools.lru_cache(maxsize=None)
def asset(name): return Image.open(P('assets', name)).convert('RGBA')

@functools.lru_cache(maxsize=None)
def scaled(name, h=None, w=None):
    """asset resized to a height or width given in design units"""
    im = asset(name)
    if h: s = h * K / im.height
    else: s = w * K / im.width
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

@functools.lru_cache(maxsize=None)
def with_shadow(name, h, blur=18, dy=26, alpha=120):
    im = scaled(name, h=h); pad = 60 * K
    out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (60, 0, 0, 255)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * alpha / 255)))
    lay = Image.new('RGBA', out.size, (0, 0, 0, 0)); lay.alpha_composite(sh, (pad + 10 * K, pad + dy * K))
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur * K)))
    out.alpha_composite(im, (pad, pad))
    return out

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

@functools.lru_cache(maxsize=16)
def note_img(size, col, kind=0):
    """vector music note (kind 0: eighth, 1: beamed pair), size in design units"""
    S = int(size * K); im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sw = max(2, int(S * 0.09)); hr = S * 0.17
    if kind == 0:
        hx, hy = S * 0.36, S * 0.78
        d.ellipse((hx - hr * 1.25, hy - hr, hx + hr * 1.25, hy + hr), fill=col)
        sx = hx + hr * 1.05; d.rectangle((sx - sw, S * 0.12, sx, hy), fill=col)
        d.polygon([(sx - sw, S * 0.12), (sx + S * 0.28, S * 0.36), (sx + S * 0.26, S * 0.47), (sx - sw, S * 0.28)], fill=col)
    else:
        for hx in (S * 0.24, S * 0.70):
            hy = S * 0.80 if hx < S / 2 else S * 0.72
            d.ellipse((hx - hr * 1.2, hy - hr, hx + hr * 1.2, hy + hr), fill=col)
            sx = hx + hr * 1.0; d.rectangle((sx - sw, S * 0.16 if hx < S / 2 else S * 0.08, sx, hy), fill=col)
        d.polygon([(S * 0.24 + hr - sw, S * 0.16), (S * 0.70 + hr, S * 0.08), (S * 0.70 + hr, S * 0.22), (S * 0.24 + hr - sw, S * 0.30)], fill=col)
    out = Image.new('RGBA', (S + 8 * K, S + 8 * K), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (90, 0, 0, 255)); sh.putalpha(im.getchannel('A').point(lambda v: v // 2))
    out.alpha_composite(sh, (5 * K, 6 * K)); out.alpha_composite(im, (0, 0))
    return out

NOTE_COLS = [YEL, WHITE, (120, 210, 255), (255, 150, 60)]
def notes_burst(c, t, t0, cx, cy, n=10, spread=420, dur=1.6, seed=1, size=(56, 96)):
    """music notes flying out of a point"""
    if t < t0: return
    rng = np.random.default_rng(seed)
    for i in range(n):
        ang = rng.uniform(-math.pi * 0.95, -math.pi * 0.05); dist = rng.uniform(0.55, 1.0) * spread
        dl = rng.uniform(0, 0.25); sz = rng.uniform(*size); kind = int(rng.integers(0, 2)); col = NOTE_COLS[i % len(NOTE_COLS)]
        u = prog(t, t0 + dl, dur)
        if u <= 0 or u >= 1: continue
        e = e_out(u)
        x = cx + math.cos(ang) * dist * e + 18 * math.sin(t * 5 + i)
        y = cy + math.sin(ang) * dist * e - 60 * u
        place(c, note_img(int(sz), col, kind), x, y, 0.5 + 0.5 * e_back(prog(t, t0 + dl, 0.3)), 12 * math.sin(t * 4 + i), 1 - prog(u, 0.7, 0.3))

# ---------------------------------------------------------------- footage (Kling clips, placeholders = start frames)
CLIP_SRC = {'k1': 'sf1_box_table.png', 'k2': 'sf1_box_table.png', 'k3': 'sf2_stick.png', 'k4': 'sf3_sticks_close.png'}

@functools.lru_cache(maxsize=4)
def clip_info(name):
    d = P('clips', name)
    if os.path.isdir(d):
        fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
        fps = float(open(os.path.join(d, 'fps.txt')).read()) if os.path.exists(os.path.join(d, 'fps.txt')) else 24.0
        if fs: return d, len(fs), fps
    return None

@functools.lru_cache(maxsize=1)
def _vig():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    v = np.clip(1.04 - 0.22 * r ** 2, 0.78, 1.0)
    return Image.fromarray((np.repeat(v[..., None], 3, 2) * 255).astype(np.uint8))

@functools.lru_cache(maxsize=1)
def _luts():
    x = np.arange(256) / 255; base = (x - 0.5) * 1.06 + 0.5 + 0.01; lut = []
    for g in (1.02, 1.0, 0.98): lut += list(np.clip(base * g * 255 + 0.5, 0, 255).astype(int))
    return lut

def grade(img):
    img = img.point(_luts()); img = ImageEnhance.Color(img).enhance(1.10)
    return ImageChops.multiply(img, _vig())

@functools.lru_cache(maxsize=12)
def clip_frame_img(name, n):
    info = clip_info(name)
    if info:
        d, cnt, fps = info
        im = Image.open(os.path.join(d, '%05d.png' % min(max(n, 0), cnt - 1))).convert('RGB')
    else:
        im = Image.open(P('sf', CLIP_SRC[name])).convert('RGB')
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2 * K, 70, 2))
    return grade(im)

def camera(img, scale=1.0, dx=0.0, dy=0.0, rot=0.0):
    if abs(scale - 1) < 1e-3 and abs(dx) < 0.5 and abs(dy) < 0.5 and abs(rot) < 0.01: return img
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    a = c / scale; b_ = s_ / scale; d = -s_ / scale; e = c / scale
    cx, cy = W / 2, H / 2
    return img.transform((W, H), Image.AFFINE, (a, b_, cx - a * (cx + dx) - b_ * (cy + dy), d, e, cy - d * (cx + dx) - e * (cy + dy)), Image.BICUBIC)

def clip_frame(name, src_t):
    info = clip_info(name)
    if info:
        _, cnt, fps = info
        fn = src_t * fps; n0 = int(math.floor(fn)); fr = fn - n0
        a = clip_frame_img(name, n0)
        if fr < 0.2: return a
        if fr > 0.8: return clip_frame_img(name, n0 + 1)
        return Image.blend(a, clip_frame_img(name, n0 + 1), fr)
    # placeholder: the start frame with a slow move matching the Kling prompt
    img = clip_frame_img(name, 0); u = src_t / 5.0
    if name == 'k1': return camera(img, 1.0 + 0.10 * u, 0, -40 * K * u)
    if name == 'k2': return camera(img, 1.08, (-70 + 140 * u) * K, 0, -1.2 + 2.4 * u)
    if name == 'k3': return camera(img, 1.0 + 0.06 * u, 0, 14 * K * math.sin(u * 5), 2.5 * math.sin(u * 4))
    if name == 'k4': return camera(img, 1.12, (60 - 120 * u) * K, 0)
    return img

def seg_at(t):
    for sg in T.SEG:
        if sg[0] <= t < sg[1]: return sg
    return None

def footage(t, shake=(0, 0)):
    v0, v1, name, s0, s1 = seg_at(t)
    u = (t - v0) / (v1 - v0)
    img = clip_frame(name, s0 + (s1 - s0) * u)
    sc = 1.0 + 0.03 * u + 0.05 * (1 - e_out(prog(t, v0, 0.45)))
    return camera(img, sc, shake[0] * K, shake[1] * K).convert('RGBA')

# ---------------------------------------------------------------- shared blocks
def head(txt, size=118, fill=WHITE, ext=10, stroke=5): return text_img(txt, F_HEAD, size, fill, stroke, DRED, ext, DRED)
def impact_txt(txt, size=250, fill=YEL): return text_img(txt, F_IMPACT, size, fill, 8, DRED, 16, DRED)
def body(txt, size=46, fill=WHITE): return text_img(txt, F_BODY, size, fill, 0)

def lower(c, t, t0, t1, l1, l2=None, s1=112, s2=96):
    c.alpha_composite(grad_bottom())
    pop(c, head(l1, s1, WHITE), W / K / 2, 1350, t, t0, t1, slide=40)
    if l2: pop(c, head(l2, s2, YEL, 9, 5), DW / 2, 1470, t, t0 + 0.35, t1, slide=40)

def header_chip(c, t, txt, t0, t1, y=268, bg=YEL, fg=DRED):
    if t < t0 or t > t1: return
    im = chip(txt, 44, bg, fg); hw = im.width / K / 2
    p = e_back(prog(t, t0, 0.5), 1.4)
    x = -hw + (DW / 2 + hw) * p; a = 1.0
    if t > t1 - 0.2:
        q = e_out(prog(t, t1 - 0.2, 0.2)); x += q * (DW / 2 + hw); a = 1 - q
    place(c, im, x, y, 1.0, 0, a)

_cache = {}
def check_line(txt, size=92, fill=WHITE):
    key = ('chk', txt, size)
    if key in _cache: return _cache[key]
    tx = head(txt, size, fill, 8, 4); s = int(size * K)
    ic = Image.new('RGBA', (s + 20 * K, s + 20 * K), (0, 0, 0, 0)); d = ImageDraw.Draw(ic)
    d.ellipse((4 * K, 10 * K, s + 4 * K, s + 10 * K), fill=DRED); d.ellipse((0, 4 * K, s, s + 4 * K), fill=YEL)
    d.line([(s * 0.24, s * 0.55), (s * 0.43, s * 0.74), (s * 0.78, s * 0.33)], fill=DRED, width=max(6, s // 9), joint='curve')
    im = Image.new('RGBA', (ic.width + 24 * K + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); im.alpha_composite(tx, (ic.width + 24 * K, (im.height - tx.height) // 2))
    _cache[key] = im; return im

def step_badge(num, txt):
    key = ('step', num, txt)
    if key in _cache: return _cache[key]
    n = text_img(str(num), F_IMPACT, 96, DRED, 0); tx = head(txt, 116, WHITE, 9, 5); D = 150 * K
    ci = Image.new('RGBA', (D + 12 * K, D + 12 * K), (0, 0, 0, 0)); d = ImageDraw.Draw(ci)
    d.ellipse((8 * K, 12 * K, D + 8 * K, D + 12 * K), fill=DRED); d.ellipse((0, 0, D, D), fill=YEL)
    ci.alpha_composite(n, ((D - n.width) // 2, (D - n.height) // 2 + 4 * K))
    im = Image.new('RGBA', (ci.width + 26 * K + tx.width, max(ci.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ci, (0, (im.height - ci.height) // 2)); im.alpha_composite(tx, (ci.width + 26 * K, (im.height - tx.height) // 2))
    _cache[key] = im; return im

@functools.lru_cache(maxsize=8)
def icon_button(idx, size):
    """one of the panel's round buttons, cut from the cleaned panel graphic (size = diameter, design units)"""
    x, y, r = GEOM['panel_buttons'][idx]; r *= 1.03
    im = asset('panel.png').crop((int(x - r), int(y - r), int(x + r), int(y + r)))
    m = Image.new('L', (im.width * 2, im.height * 2), 0); ImageDraw.Draw(m).ellipse((0, 0, im.width * 2 - 1, im.height * 2 - 1), fill=255)
    im.putalpha(ImageChops.multiply(im.getchannel('A'), m.resize(im.size, Image.LANCZOS)))
    S = int(size * K); im = im.resize((S, S), Image.LANCZOS)
    out = Image.new('RGBA', (S + 24 * K, S + 24 * K), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    d.ellipse((8 * K, 14 * K, S + 16 * K, S + 22 * K), fill=(90, 0, 0, 150))
    d.ellipse((2 * K, 2 * K, S + 10 * K, S + 10 * K), fill=YEL)
    out.alpha_composite(im, (6 * K, 6 * K))
    return out

# button indices in GEOM order (sorted top-to-bottom, left-to-right):
# 0 cat, 1 drum, 2 note, 3 clef, 4 '1', 5 book, 6 panda, 7 prev, 8 next, 9 power
B_CAT, B_DRUM, B_NOTE, B_CLEF, B_ONE, B_BOOK, B_PANDA, B_PREV, B_NEXT, B_POWER = range(10)

@functools.lru_cache(maxsize=4)
def icon_label(idx, txt):
    ic = icon_button(idx, 112); tx = head(txt, 56, WHITE, 6, 4)
    im = Image.new('RGBA', (ic.width + 22 * K + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); im.alpha_composite(tx, (ic.width + 22 * K, (im.height - tx.height) // 2))
    return im

@functools.lru_cache(maxsize=4)
def icon_row(kind, txt, size=74):
    S = 116 * K
    ic = Image.new('RGBA', (S + 10 * K, S + 10 * K), (0, 0, 0, 0)); d = ImageDraw.Draw(ic)
    d.ellipse((6 * K, 10 * K, S + 6 * K, S + 10 * K), fill=DRED + (255,)); d.ellipse((0, 0, S, S), fill=YEL + (255,))
    col = DRED + (255,)
    if kind == 'box':
        d.rounded_rectangle((0.22 * S, 0.36 * S, 0.78 * S, 0.76 * S), 5 * K, fill=col)
        d.polygon([(0.22 * S, 0.36 * S), (0.30 * S, 0.24 * S), (0.70 * S, 0.24 * S), (0.78 * S, 0.36 * S)], fill=(150, 30, 20, 255))
        d.rectangle((0.45 * S, 0.24 * S, 0.55 * S, 0.50 * S), fill=YEL + (255,))
    else:
        d.rounded_rectangle((0.16 * S, 0.32 * S, 0.58 * S, 0.64 * S), 4 * K, fill=col)
        d.polygon([(0.60 * S, 0.42 * S), (0.74 * S, 0.42 * S), (0.84 * S, 0.54 * S), (0.84 * S, 0.64 * S), (0.60 * S, 0.64 * S)], fill=col)
        d.polygon([(0.64 * S, 0.46 * S), (0.72 * S, 0.46 * S), (0.78 * S, 0.53 * S), (0.64 * S, 0.53 * S)], fill=YEL + (255,))
        for wx in (0.30, 0.72):
            d.ellipse(((wx - 0.08) * S, 0.60 * S, (wx + 0.08) * S, 0.76 * S), fill=col)
            d.ellipse(((wx - 0.035) * S, 0.645 * S, (wx + 0.035) * S, 0.715 * S), fill=YEL + (255,))
    tx = head(txt, size, WHITE, 8, 4)
    im = Image.new('RGBA', (ic.width + 26 * K + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); im.alpha_composite(tx, (ic.width + 26 * K, (im.height - tx.height) // 2))
    return im

# ---------------------------------------------------------------- transitions
def chevron_wipe(c, t, tc, d=0.72):
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

# ---------------------------------------------------------------- scenes
def scene_intro(t):
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, 0.0, 0.5))
    sd.polygon([(0, 0), (DW * p, 0), (DW * p - 260, 300), (0, 380)], fill=RED + (255,))
    sd.polygon([(DW, DH), (DW - DW * p, DH), (DW - DW * p + 260, DH - 300), (DW, DH - 380)], fill=RED + (255,))
    sd.polygon([(0, 380), (DW * p - 260, 300), (DW * p - 250, 318), (0, 400)], fill=ORANGE + (255,))
    lg = asset('logo_rgba.png'); s = 980 * K / lg.width
    place(c, lg, DW / 2, 800, s * (0.35 + 0.65 * e_back(prog(t, 0.0, 0.42), 1.6)), 3 * math.sin(t * 5) * (1 - prog(t, 0, 1.2)), clamp(t / 0.12))
    pop(c, chip('NEW LAUNCH', 64, RED, WHITE, F_HEAD, 44, 18), DW / 2, 1180, t, b(1.5), None, rot=-3)
    pop(c, body('For Distributors  &  Wholesalers', 42, INK), DW / 2, 1300, t, b(2.5), None, slide=30)
    return c

def scene_product(t, t0, t1):
    """INTRODUCING -- the musical stick pops up and plays notes"""
    c = red_bg(t)
    p = prog(t, t0 + 0.1, 0.6)
    place(c, burst(1000, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40)), DW / 2, 1000, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.30 * clamp(p * 3))
    notes_burst(c, t, t0 + 0.35, DW / 2 + 20, 900, n=9, spread=430, dur=1.8, seed=3)
    st = with_shadow('stick.png', 980)
    place(c, st, DW / 2 + 10, 1010 + 260 * (1 - e_back(p, 1.3)) + 10 * math.sin(t * 2.3), 1.0, -6 + 3 * math.sin(t * 1.8), clamp(p * 3))
    pop(c, body('INTRODUCING', 44, YEL), DW / 2, 205, t, t0 + 0.05, t1)
    pop(c, head('CARTOON FUN STORY', 104, WHITE, 9, 5), DW / 2, 300, t, t0 + b(0.5), t1)
    pop(c, head('MUSICAL STICK', 132, YEL, 11, 6), DW / 2, 420, t, t0 + b(1), t1)
    pop(c, chip('PACK OF 12 PCS  •  AGES 3+', 44, YEL, DRED), DW / 2, 1690, t, t0 + b(2), t1, slide=30)
    return c

def scene_panel(t, t0, t1):
    """feature 01: the 10-button panel, buttons light up in turn"""
    c = red_bg(t)
    p = prog(t, t0, 0.5)
    pan = scaled('panel.png', w=860); S_ = 860 / asset('panel.png').width
    cx, cy = DW / 2, 820
    sc = 0.7 + 0.3 * e_back(p, 1.4) + 0.012 * (t - t0)
    place(c, pan, cx, cy, sc, 4 * (1 - e_out(p)), clamp(p * 3))
    order = [B_BOOK, B_NOTE, B_CAT, B_DRUM, B_PANDA, B_CLEF, B_ONE, B_PREV, B_POWER, B_NEXT]
    k = int((t - t0 - 0.45) / 0.16)
    if t - t0 > 0.45:
        idx = order[k % len(order)]
        x, y, r = GEOM['panel_buttons'][idx]
        aw, ah = asset('panel.png').size
        bx = cx + (x - aw / 2) * S_ * sc; by = cy + (y - ah / 2) * S_ * sc; br = r * S_ * sc
        q = ((t - t0 - 0.45) % 0.16) / 0.16
        sd = SD(c); rr = br * (1.05 + 0.25 * q)
        sd.ellipse((bx - rr, by - rr, bx + rr, by + rr), width=10, outline=(255, 255, 255, int(255 * (1 - q))))
    return c

def scene_stick(t, t0, step):
    """steps 2 + 3: big stick; taps on the chest buttons; then notes and sound icons fly out"""
    c = red_bg(t)
    SH = 960
    st = with_shadow('stick.png', SH)
    sw, sh = asset('stick.png').size; s = SH / sh
    mv = e_inout(prog(t, b(28) - 0.15, 0.5))          # step 3: stick slides left to make room for the icons
    cx, cy = DW / 2 + 20 - 300 * mv, 900
    bob = 6 * math.sin(t * 2.2); rot = -4 + 2 * math.sin(t * 1.6)
    p = prog(t, b(24), 0.5)
    place(c, st, cx, cy + bob + 200 * (1 - e_back(p, 1.3)), 1.0, rot, clamp(p * 3))
    # chest-button cluster in design units (rotation is small; ignore it for the tap ring)
    bx = cx + (GEOM['stick_buttons'][0] - sw / 2) * s
    by = cy + bob + (GEOM['stick_buttons'][1] - sh / 2) * s
    br = GEOM['stick_buttons_r'] * s
    sd = SD(c)
    if step == 2:
        for tt in T.TAPS:
            q = prog(t, tt, 0.5)
            if 0 < q < 1:
                for k_ in range(2):
                    qq = clamp(q * 1.2 - k_ * 0.25)
                    if qq <= 0: continue
                    rr = br * (0.4 + 1.3 * e_out(qq))
                    sd.ellipse((bx - rr, by - rr, bx + rr, by + rr), width=12, outline=(255, 255, 255, int(230 * (1 - qq))))
            # finger: a soft white dot pressing in
            fq = prog(t, tt - 0.18, 0.18) * (1 - prog(t, tt + 0.12, 0.2))
            if fq > 0:
                fr = 34 * (1.25 - 0.25 * fq)
                sd.ellipse((bx + 20 - fr, by + 30 - fr, bx + 20 + fr, by + 30 + fr), fill=(255, 255, 255, int(170 * fq)))
        for i, tt in enumerate(T.TAPS):
            notes_burst(c, t, tt + 0.05, bx, by - 40, n=4, spread=300, dur=1.1, seed=10 + i, size=(48, 72))
    else:
        for k_ in range(3):   # sound waves both sides
            q = ((t - b(28)) * 0.9 + k_ / 3) % 1
            a = int(200 * (1 - q) * mv); rr = 200 + 200 * q
            sd.arc((bx - rr, by - rr, bx + rr, by + rr), 150, 205, width=12, fill=(255, 255, 255, a))
        notes_burst(c, t, b(28.1), bx, by - 160, n=10, spread=420, dur=2.2, seed=21)
        for i, (idx, lbl, y, dl) in enumerate([(B_BOOK, 'STORIES', 560, 28.6), (B_NOTE, 'SONGS', 800, 29.3), (B_CAT, 'ANIMAL SOUNDS', 1040, 30.0)]):
            im = icon_label(idx, lbl)
            pop(c, im, min(DW - 24 - im.width / K / 2, 490 + im.width / K / 2), y, t, b(dl), b(32), rot=[-3, 2, -2][i], slide=30)
    return c

def scene_bulk(t, t0, t1):
    c = red_bg(t)
    pop(c, head('BULK ORDERS ONLY', 124, YEL, 11, 6), DW / 2, 330, t, t0 + 0.1, t1, slide=-30)
    p = prog(t, t0 + b(0.5), 0.6)
    if p > 0:
        place(c, burst(980, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40)), DW / 2, 790, 0.95 + 0.02 * math.sin(t * 2), (t * 8) % 360, 0.28 * clamp(p * 3))
        place(c, with_shadow('box_open.png', 720), DW / 2, 820 + 6 * math.sin(t * 1.8) + 140 * (1 - e_back(p, 1.3)), 0.75 + 0.25 * e_back(p, 1.3), -2 + 1.5 * math.sin(t * 1.5), clamp(p * 3))
    pop(c, icon_row('box', '12 PCS PER DISPLAY BOX'), DW / 2, 1230, t, t0 + b(2), t1, slide=30)
    pop(c, icon_row('truck', 'PAN INDIA DELIVERY'), DW / 2, 1370, t, t0 + b(3.5), t1, slide=30)
    pop(c, chip('DISTRIBUTORS', 42, WHITE, RED, F_BODY, 30, 15), DW / 2 - 200, 1530, t, t0 + b(5), t1)
    pop(c, chip('WHOLESALERS', 42, WHITE, RED, F_BODY, 30, 15), DW / 2 + 200, 1530, t, t0 + b(5.5), t1)
    return c

def scene_end(t):
    t0 = T.END_HIT
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, t0, 0.5))
    sd.polygon([(0, 0), (DW, 0), (DW, 250 * p + 60), (DW / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    sd.polygon([(0, 250 * p + 60), (DW / 2, 330 * p + 60), (DW, 250 * p + 60), (DW, 250 * p + 76), (DW / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    sd.polygon([(0, DH), (DW, DH), (DW, DH - 200 * p), (0, DH - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png')
    place(c, lg, DW / 2, 540, (860 * K / lg.width) * (0.4 + 0.6 * e_back(prog(t, t0, 0.42), 1.6)), 0, clamp((t - t0) / 0.1))
    pb = prog(t, t0 + b(1), 0.5)
    place(c, with_shadow('box_open.png', 470), DW / 2 + 150 + 600 * (1 - e_out(pb)), 1010, 1.0, 4 - 8 * (1 - e_out(pb)), clamp(pb * 3))
    ps = prog(t, t0 + b(1.5), 0.5)
    place(c, with_shadow('stick.png', 560), DW / 2 - 230 - 600 * (1 - e_out(ps)), 1010 + 5 * math.sin(t * 2.2), 1.0, -10 + 12 * (1 - e_out(ps)), clamp(ps * 3))
    pop(c, text_img('BULK ORDERS ONLY', F_HEAD, 100, RED, 0), DW / 2, 1385, t, t0 + b(2), None, slide=30)
    ca, cb_ = chip('12 PCS / BOX', 36, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 36, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1495, t, t0 + b(3), None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1495, t, t0 + b(3.5), None, slide=20)
    pop(c, chip('DM US FOR TRADE PRICING', 46, RED, WHITE, F_BODY, 40, 22), DW / 2, 1620, t, t0 + b(4.5), None)
    pop(c, body('Cartoon Fun Story Musical Stick  •  Ages 3+', 34, WHITE), DW / 2, DH - 120, t, t0 + b(5), None)
    return c


# ---------------------------------------------------------------- box motion graphics (v2)
LIP = 0.79   # top of the box's front lip, as a fraction of the box height

@functools.lru_cache(maxsize=8)
def box_lip(h):
    """the front lip of the box on a canvas matching with_shadow('box_open.png', h)"""
    sh = with_shadow('box_open.png', h); im = scaled('box_open.png', h=h); pad = 60 * K
    y = int(im.height * LIP)
    out = Image.new('RGBA', sh.size, (0, 0, 0, 0)); out.paste(im.crop((0, y, im.width, im.height)), (pad, pad + y))
    return out

def sparkles(c, t, seed, cx, cy, rx, ry, n=10, size=34):
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        x = cx + rng.uniform(-rx, rx); y = cy + rng.uniform(-ry, ry); ph = rng.uniform(0, 6.28); sp = rng.uniform(2.5, 4.5)
        a = math.sin(t * sp + ph)
        if a < 0.08: continue
        s = size * (0.4 + 0.6 * a)
        pts = [(x, y - s), (x + s * .22, y - s * .22), (x + s, y), (x + s * .22, y + s * .22), (x, y + s), (x - s * .22, y + s * .22), (x - s, y), (x - s * .22, y - s * .22)]
        sd.polygon(pts, fill=(255, 246, 200, int(255 * a)))

def box_float(t, t0):
    """gentle idle motion for a hero box: bob, sway, slow breathe"""
    return 8 * math.sin((t - t0) * 2.0), -2.5 + 2.0 * math.sin((t - t0) * 1.4), 1 + 0.012 * math.sin((t - t0) * 1.7)

def scene_box_hero(t, t0, t1):
    """STORIES, MUSIC & FUN -- the display box bounces in, notes pour out of it"""
    c = red_bg(t)
    p = prog(t, t0, 0.55)
    place(c, burst(1100, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40)), DW / 2, 720, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.30 * clamp(p * 3))
    bob, rot, br = box_float(t, t0)
    place(c, with_shadow('box_open.png', 860), DW / 2, 770 + bob + 300 * (1 - e_back(p, 1.3)), (0.7 + 0.3 * e_back(p, 1.5)) * br * (1 + 0.025 * (t - t0)), rot, clamp(p * 3))
    notes_burst(c, t, t0 + 0.45, DW / 2, 420, n=11, spread=470, dur=1.9, seed=41)
    sparkles(c, t, 5, DW / 2, 720, 470, 420, n=12)
    return c

def scene_pick(t, t0, t1):
    """1 PICK A PAL -- one stick pops up out of the box"""
    c = red_bg(t)
    H_BOX = 820; bx, by = DW / 2, 1080
    bob, rot, br = box_float(t, t0)
    p = prog(t, t0, 0.45)
    yb = by + bob + 160 * (1 - e_out(p))
    place(c, with_shadow('box_open.png', H_BOX), bx, yb, br, rot * 0.5, clamp(p * 3))
    ts, dur = T.PICK_RISE
    q = prog(t, ts, dur)
    if q > 0:
        e = e_back(q, 0.9)
        y_hidden = yb - H_BOX / 2 + H_BOX * LIP + 350 + 10      # stick top just under the lip edge
        sy = y_hidden + (735 - y_hidden) * e + 8 * math.sin((t - ts) * 2.6) * q
        srot = 14 * (1 - e) - 6 + 3 * math.sin((t - ts) * 2.0) * q
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        place(lay, with_shadow('stick.png', 700), bx + 10, sy, 1.0, srot, 1.0)
        box_bottom = yb + H_BOX / 2 - 6
        lay.paste((0, 0, 0, 0), (0, int(box_bottom * K), W, H))
        c.alpha_composite(lay)
        place(c, box_lip(H_BOX), bx, yb, br, rot * 0.5, 1.0)
        notes_burst(c, t, ts + dur * 0.55, bx, 420, n=8, spread=380, dur=1.5, seed=43)
        sparkles(c, t, 7, bx, 640, 330, 300, n=9, size=40)
    return c

def scene_box_drop(t, shake):
    """PRESS & PLAY! -- the box punches in on the drop"""
    c = red_bg(t)
    p = prog(t, T.DROP, 0.35)
    place(c, burst(1200, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40)), DW / 2, 700, 1.0, (t * 30) % 360, 0.35)
    bob, rot, br = box_float(t, T.DROP)
    sc = (1.35 - 0.35 * e_out(p)) * br
    place(c, with_shadow('box_open.png', 780), DW / 2 + shake[0], 690 + bob + shake[1], sc, rot, 1.0)
    return c

def scene_why(t, t0, t1):
    c = red_bg(t)
    p = prog(t, t0, 0.6)
    bob, rot, br = box_float(t, t0)
    sway = math.sin((t - t0) * 0.9)
    place(c, with_shadow('box_open.png', 900), DW / 2 + 20 * sway, 790 + bob + 200 * (1 - e_back(p, 1.3)), (0.8 + 0.2 * e_back(p, 1.4)) * br * (1 + 0.012 * (t - t0)), rot + 2.5 * sway, clamp(p * 3))
    sparkles(c, t, 9, DW / 2, 760, 480, 440, n=10)
    return c

def scene_stack(t, t0):
    """STOCK UP NOW! -- display boxes drop in and stack up"""
    c = red_bg(t)
    shake = [0.0, 0.0]
    for i, (x, y, tl) in enumerate(T.STACK):
        q = prog(t, tl - 0.35, 0.35)
        if q <= 0: continue
        yy = y - 1300 * (1 - q) ** 2                       # falls in, accelerating
        if t >= tl:
            u = t - tl; yy = y - 40 * math.exp(-u * 9) * abs(math.sin(u * 22))   # bounce on landing
            amp = 10 * math.exp(-u * 10); shake[0] += amp * math.sin(u * 90); shake[1] += amp * math.cos(u * 70)
        place(c, with_shadow('box_open.png', 560), x, yy, 1.0, [-3, 3, -1][i] * (1 - 0.6 * clamp((t - tl) * 2)), clamp(q * 3))
    if any(t >= tl for _, _, tl in T.STACK):
        c = camera(c, 1.0, shake[0] * K, shake[1] * K)
    return c

def render(t):
    if t < b(4):
        c = scene_intro(t)
    elif t < b(8):
        c = scene_product(t, b(4), b(8))
    elif t < b(12):
        c = scene_box_hero(t, b(8), b(12))
        lower(c, t, b(8), b(12), 'STORIES, MUSIC & FUN', 'IN EVERY PRESS!', 100, 92)
    elif t < b(20):
        k = int((t - b(12)) // b(4)); t0 = b(12) + k * b(4); t1 = t0 + b(4)
        c = scene_panel(t, t0, t1) if k == 0 else footage(t)
        c.alpha_composite(grad_top())
        header_chip(c, t, 'KEY FEATURES', b(12), b(20))
        lab = [('STORIES, SONGS', '& ANIMAL SOUNDS'), ('CUTE, LIGHTWEIGHT', '& EASY TO HOLD')][k]
        c.alpha_composite(grad_bottom())
        pop(c, body('0%d / 02' % (k + 1), 40, YEL), DW / 2, 1300, t, t0, t1)
        pop(c, head(lab[0], 108), DW / 2, 1405, t, t0 + 0.1, t1, slide=40)
        pop(c, head(lab[1], 92, YEL, 8, 5), DW / 2, 1517, t, t0 + 0.35, t1, slide=40)
    elif t < b(32):
        if t < b(24):
            c = scene_pick(t, b(20), b(24)); c.alpha_composite(grad_bottom())
            pop(c, step_badge(1, 'PICK A PAL'), DW / 2, 1580, t, b(20), b(24), slide=40)
        else:
            step = 2 if t < b(28) else 3
            c = scene_stick(t, b(24), step)
            c.alpha_composite(grad_bottom())
            if step == 2: pop(c, step_badge(2, 'PRESS A BUTTON'), DW / 2, 1560, t, b(24), b(28), slide=40)
            else: pop(c, step_badge(3, 'LISTEN & LEARN'), DW / 2, 1560, t, b(28), b(32), slide=40)
        header_chip(c, t, 'HOW IT WORKS', b(20), b(32))
    elif t < b(36):
        u = t - T.DROP; amp = 22 * math.exp(-u * 6)
        sh = (amp * math.sin(t * 93), amp * math.cos(t * 71))
        c = scene_box_drop(t, sh); c.alpha_composite(grad_bottom())
        place(c, burst(760), DW / 2, 1440, 0.3 + 0.75 * e_back(prog(t, T.DROP, 0.3), 1.6), (t * 40) % 360, 0.95 * (1 - prog(t, b(35.4), 0.25)))
        pop(c, impact_txt('PRESS', 200, WHITE), DW / 2 + sh[0] * 0.5, 1340 + sh[1] * 0.5, t, T.DROP, b(36), d=0.3, rot=-6, from_scale=1.9)
        pop(c, impact_txt('& PLAY!', 210, YEL), DW / 2 + sh[0] * 0.5, 1560 + sh[1] * 0.5, t, T.DROP + 0.12, b(36), d=0.3, rot=-6, from_scale=1.9)
        notes_burst(c, t, T.DROP + 0.05, DW / 2, 1300, n=14, spread=600, dur=1.7, seed=31)
    elif t < b(44):
        c = scene_why(t, b(36), b(44)); c.alpha_composite(grad_bottom())
        header_chip(c, t, 'WHY STOCK IT', b(36), b(44), bg=WHITE, fg=RED)
        for i, (txt, dl) in enumerate([('READY-TO-DISPLAY BOX', 36.5), ('12 PCS IN EVERY BOX', 38.5), ('EDUCATIONAL & FUN', 40.5)]):
            pop(c, check_line(txt, 70), DW / 2, 1440 + i * 100, t, b(dl), b(44), slide=30)
    elif t < b(52):
        c = scene_bulk(t, b(44), b(52))
    elif t < b(56):
        c = scene_stack(t, b(52))
        for i, (wd, dl, col, sz) in enumerate([('STOCK', 52, WHITE, 190), ('UP', 53, YEL, 210), ('NOW!', 54, WHITE, 220)]):
            pop(c, impact_txt(wd, sz, col), DW / 2, 370 + i * 185, t, b(dl), None, d=0.3, rot=-4, from_scale=1.8)
    else:
        c = scene_end(t)
    if b(4) <= t < b(56):
        place(c, logo_sticker(210), 165, 150, 1.0, 0, 0.92)   # Funhoods logo top-LEFT
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
    a = ap.parse_args()
    if a.stills:
        os.makedirs(P('stills'), exist_ok=True)
        for s in a.stills.split(','):
            im = render(float(s))
            if a.preview: im = im.resize((1080, 1920), Image.LANCZOS)
            im.save(P('stills', 'st_%06.2f.png' % float(s)))
        sys.exit()
    n0, n1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '5.2',
                           '-movflags', '+faststart', a.out], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        ff.stdin.write(render(n / FPS).tobytes())
        if n % 60 == 0: print('frame', n, flush=True)
    ff.stdin.close(); ff.wait()
