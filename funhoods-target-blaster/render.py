# Funhoods "Target Blaster" B2B reel -- 1080x1920, 30 fps, motion graphics over cleaned AI footage.
import sys, os, re, math, argparse, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T
from shots import SRC, SHOTS

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
W, H, FPS = T.W, T.H, T.FPS
b = T.b

RED = (210, 24, 31); DRED = (120, 6, 14); ORANGE = (255, 162, 58); YEL = (255, 212, 0)
WHITE = (255, 255, 255); CREAM = (255, 248, 236); INK = (40, 22, 22); NAVY = (24, 36, 92)
F_HEAD = P('fonts', 'LilitaOne-Regular.ttf')
F_IMPACT = P('fonts', 'LuckiestGuy-Regular.ttf')
F_BODY = P('fonts', 'Inter-ExtraBold.ttf')

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b_=1.0): return max(a, min(b_, x))
def e_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def e_inout(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def e_back(x, s=1.9):
    x = clamp(x); c3 = s + 1
    return 1 + c3 * (x - 1) ** 3 + s * (x - 1) ** 2
def prog(t, t0, d): return clamp((t - t0) / d)

# ---------------------------------------------------------------- text
@functools.lru_cache(maxsize=None)
def font(path, size): return ImageFont.truetype(path, size)

@functools.lru_cache(maxsize=256)
def text_img(txt, path, size, fill=WHITE, stroke=0, stroke_fill=DRED, extrude=0, ext_fill=DRED, maxw=980):
    f = font(path, size)
    l, t_, r, bt = f.getbbox(txt, stroke_width=stroke)
    if r - l + extrude > maxw:  # auto-fit
        return text_img(txt, path, int(size * maxw / (r - l + extrude)) - 1, fill, stroke, stroke_fill, extrude, ext_fill, maxw)
    pad = stroke + 6
    im = Image.new('RGBA', (r - l + 2 * pad + extrude, bt - t_ + 2 * pad + extrude), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(extrude, 0, -1):
        d.text((pad - l + i, pad - t_ + i), txt, font=f, fill=ext_fill, stroke_width=stroke, stroke_fill=ext_fill)
    d.text((pad - l, pad - t_), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    return im

@functools.lru_cache(maxsize=64)
def chip(txt, size=46, bg=YEL, fg=DRED, path=F_BODY, padx=34, pady=18, radius=None, shadow=True):
    t = text_img(txt, path, size, fill=fg)
    w, h = t.width + 2 * padx, t.height + 2 * pady
    r = radius if radius is not None else h // 2
    im = Image.new('RGBA', (w + 16, h + 16), (0, 0, 0, 0))
    if shadow:
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((8, 14, w + 8, h + 14), r, fill=(60, 0, 0, 120))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(im).rounded_rectangle((8, 8, w + 8, h + 8), r, fill=bg)
    im.alpha_composite(t, (8 + padx, 8 + pady))
    return im

def place(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.003 or scale <= 0.01: return
    im = img
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 0.999:
        a = im.getchannel('A').point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    x, y = int(round(cx - im.width / 2)), int(round(cy - im.height / 2))
    sx, sy = max(0, -x), max(0, -y)
    x0, y0 = max(0, x), max(0, y)
    w_, h_ = min(im.width - sx, W - x0), min(im.height - sy, H - y0)
    if w_ <= 0 or h_ <= 0: return
    canvas.alpha_composite(im, (x0, y0), (sx, sy, sx + w_, sy + h_))

def pop(canvas, img, cx, cy, t, t0, t1=None, d=0.34, rot=0.0, from_scale=0.45, slide=0):
    """Element pops in at t0 (back-ease) and exits quickly at t1."""
    if t < t0: return
    p = prog(t, t0, d)
    s = from_scale + (1 - from_scale) * e_back(p)
    a = clamp(p / 0.35)
    if t1 is not None and t > t1 - 0.16:
        q = prog(t, t1 - 0.16, 0.16); s *= 1 - 0.35 * q; a *= 1 - q
    place(canvas, img, cx, cy + slide * (1 - e_out(p)), s, rot, a)

# ---------------------------------------------------------------- backgrounds
@functools.lru_cache(maxsize=1)
def halftone():
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for y in range(0, H, 36):
        for x in range(0, W, 36):
            ox = 18 if (y // 36) % 2 else 0
            rr = 3 + 7 * (y / H)
            d.ellipse((x + ox - rr, y - rr, x + ox + rr, y + rr), fill=255)
    return im

@functools.lru_cache(maxsize=40)
def sunburst(k):
    """Brand red sunburst, k in 0..29 -> rotation phase."""
    S = 2300; n = 24
    im = Image.new('RGB', (S, S), (196, 16, 26)); d = ImageDraw.Draw(im)
    c = S / 2; off = (k / 30) * (360 / n)
    for i in range(n):
        if i % 2: continue
        a0 = math.radians(i * 360 / n + off); a1 = math.radians((i + 1) * 360 / n + off)
        d.polygon([(c, c), (c + 2 * S * math.cos(a0), c + 2 * S * math.sin(a0)), (c + 2 * S * math.cos(a1), c + 2 * S * math.sin(a1))], fill=(222, 34, 42))
    im = im.crop(((S - W) // 2, (S - H) // 2 - 120, (S - W) // 2 + W, (S - H) // 2 - 120 + H))
    # radial vignette
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
    v = np.clip(1.08 - r * 1.05, 0.55, 1.05)[..., None]
    arr = np.asarray(im).astype(np.float32) * v
    ht = np.asarray(halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.10 * ht) + np.array([90, 0, 6]) * 0.10 * ht
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def red_bg(t):
    return sunburst(int((t * 6) % 30)).convert('RGBA')

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
def card(name, width, border=16, radius=34):
    src = Image.open(P('cat_sr', name)).convert('RGB')
    h = int(src.height * width / src.width)
    src = src.resize((width, h), Image.LANCZOS)
    pad = 60
    im = Image.new('RGBA', (width + 2 * border + 2 * pad, h + 2 * border + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad + 10, pad + 26, pad + width + 2 * border + 10, pad + h + 2 * border + 26), radius, fill=(40, 0, 0, 150))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(im).rounded_rectangle((pad, pad, pad + width + 2 * border, pad + h + 2 * border), radius, fill=WHITE)
    m = Image.new('L', src.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, width, h), radius - border // 2, fill=255)
    im.paste(src, (pad + border, pad + border), m)
    return im

@functools.lru_cache(maxsize=None)
def logo_sticker(width):
    lg = asset('logo_rgba.png'); s = width / lg.width
    lg = lg.resize((width, int(lg.height * s)), Image.LANCZOS)
    pad = 34
    im = Image.new('RGBA', (lg.width + 2 * pad + 30, lg.height + 2 * pad + 30), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((15, 27, 15 + lg.width + 2 * pad, 27 + lg.height + 2 * pad), 40, fill=(50, 0, 0, 130))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(im).rounded_rectangle((15, 15, 15 + lg.width + 2 * pad, 15 + lg.height + 2 * pad), 40, fill=WHITE)
    im.alpha_composite(lg, (15 + pad, 15 + pad))
    return im

@functools.lru_cache(maxsize=4)
def burst(size, spikes=18, fill=YEL, inner=WHITE, outline=DRED):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = size / 2
    def star(r0, r1, col, wob=0.0):
        pts = []
        for i in range(spikes * 2):
            a = math.pi * i / spikes; r = r1 if i % 2 == 0 else r0
            r *= 1 + wob * math.sin(i * 2.3)
            pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        d.polygon(pts, fill=col)
    star(size * 0.33, size * 0.5, outline, 0.06)
    star(size * 0.30, size * 0.46, fill, 0.06)
    star(size * 0.20, size * 0.30, inner, 0.05)
    return im

# ---------------------------------------------------------------- footage
SRMAP = {}
def _scan_sr():
    for f in os.listdir(P('sr_out')):
        m = re.match(r'\d+_([ABC])(\d+)\.png$', f)
        if m and os.path.getsize(P('sr_out', f)) > 0: SRMAP[(m.group(1), int(m.group(2)))] = P('sr_out', f)
_scan_sr()
LOWQ = False

@functools.lru_cache(maxsize=24)
def src_frame(s, n):
    lo = Image.open(P('dec', s, '%05d.png' % n)).convert('RGB')
    lz = lo.resize((W, H), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    if not LOWQ and (s, n) in SRMAP:
        sr = Image.open(SRMAP[(s, n)]).convert('RGB')
        if sr.size != (W, H): sr = sr.resize((W, H), Image.LANCZOS)
        img = Image.blend(lz, sr, 0.72)
    else:
        img = lz
    return grade(img)

@functools.lru_cache(maxsize=1)
def _vig():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    v = np.clip(1.04 - 0.22 * r ** 2, 0.78, 1.0)
    return Image.fromarray((np.repeat(v[..., None], 3, 2) * 255).astype(np.uint8))

@functools.lru_cache(maxsize=1)
def _luts():
    x = np.arange(256) / 255
    base = (x - 0.5) * 1.07 + 0.5 + 0.01
    lut = []
    for g in (1.02, 1.0, 0.975):
        lut += list(np.clip(base * g * 255 + 0.5, 0, 255).astype(int))
    return lut

def grade(img):
    from PIL import ImageEnhance, ImageChops
    img = img.point(_luts())
    img = ImageEnhance.Color(img).enhance(1.14)
    return ImageChops.multiply(img, _vig())

def shot_frame(shot, src_t):
    s, t0, t1 = SHOTS[shot]
    fps = SRC[s][1]
    src_t = min(max(src_t, t0), t1)
    fn = src_t * fps
    n0 = int(math.floor(fn)); fr = fn - n0
    a = src_frame(s, n0)
    if 0.25 < fr < 0.75:  # soften judder on slow segments
        return Image.blend(a, src_frame(s, n0 + 1), fr)
    return a if fr <= 0.25 else src_frame(s, n0 + 1)

def seg_at(t):
    for sg in T.SEG:
        if sg[0] <= t < sg[1]: return sg
    return None

def camera(img, scale=1.0, dx=0.0, dy=0.0, rot=0.0):
    if abs(scale - 1) < 1e-3 and abs(dx) < 0.5 and abs(dy) < 0.5 and abs(rot) < 0.01: return img
    # inverse affine around the frame centre
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    a = c / scale; b_ = s_ / scale; d = -s_ / scale; e = c / scale
    cx, cy = W / 2, H / 2
    xo = cx - a * (cx + dx) - b_ * (cy + dy)
    yo = cy - d * (cx + dx) - e * (cy + dy)
    return img.transform((W, H), Image.AFFINE, (a, b_, xo, d, e, yo), Image.BICUBIC)

def footage(t, extra_scale=1.0, shake=(0, 0)):
    sg = seg_at(t)
    if sg is None: return None
    v0, v1, shot, sin, sp = sg
    img = shot_frame(shot, sin + (t - v0) * sp)
    u = (t - v0) / (v1 - v0)
    sc = 1.0 + 0.05 * u                      # slow push-in
    sc += 0.10 * (1 - e_out(prog(t, v0, 0.28)))  # punch on cut
    return camera(img, sc * extra_scale, shake[0], shake[1]).convert('RGBA')

@functools.lru_cache(maxsize=1)
def grad_bottom():
    a = np.zeros((H, W), np.float32); y = np.arange(H)
    a[:] = np.clip((y - 1020) / 700, 0, 1)[:, None] ** 1.3 * 0.72
    im = Image.new('RGBA', (W, H), (20, 0, 0, 0)); im.putalpha(Image.fromarray((a * 255).astype(np.uint8))); return im

@functools.lru_cache(maxsize=1)
def grad_top():
    a = np.zeros((H, W), np.float32); y = np.arange(H)
    a[:] = np.clip(1 - y / 520, 0, 1)[:, None] ** 1.5 * 0.55
    im = Image.new('RGBA', (W, H), (20, 0, 0, 0)); im.putalpha(Image.fromarray((a * 255).astype(np.uint8))); return im

# ---------------------------------------------------------------- shared text blocks
def head(txt, size=118, fill=WHITE, ext=10, stroke=5): return text_img(txt, F_HEAD, size, fill, stroke, DRED, ext, DRED)
def impact_txt(txt, size=250, fill=YEL): return text_img(txt, F_IMPACT, size, fill, 8, DRED, 16, DRED)
def body(txt, size=46, fill=WHITE): return text_img(txt, F_BODY, size, fill, 0)

def lower_third(c, t, lines, t_start, t_end, y0=1330, gap=118):
    """lines: list of (img, delay_beats)."""
    for i, (im, dl) in enumerate(lines):
        pop(c, im, W / 2, y0 + i * gap, t, t_start + b(dl), t_end, slide=40)

def header_chip(c, t, txt, t0, t1, y=268, bg=YEL, fg=DRED):
    if t < t0 or t > t1: return
    im = chip(txt, 44, bg, fg)
    p = e_back(prog(t, t0, 0.4), 1.4)
    x = -im.width / 2 + (W / 2 + im.width / 2) * p
    a = 1.0
    if t > t1 - 0.18:
        q = e_out(prog(t, t1 - 0.18, 0.18)); x += q * (W / 2 + im.width); a = 1 - q
    place(c, im, x, y, 1.0, 0, a)

def check_line(txt, size=92, fill=WHITE):
    key = ('chk', txt, size, fill)
    if key in _cache: return _cache[key]
    tx = head(txt, size, fill, 8, 4)
    ic = Image.new('RGBA', (size + 20, size + 20), (0, 0, 0, 0)); d = ImageDraw.Draw(ic)
    d.ellipse((4, 10, size + 4, size + 10), fill=DRED); d.ellipse((0, 4, size, size + 4), fill=YEL)
    s = size
    d.line([(s * 0.24, s * 0.55), (s * 0.43, s * 0.74), (s * 0.78, s * 0.33)], fill=DRED, width=max(6, s // 9), joint='curve')
    im = Image.new('RGBA', (ic.width + 24 + tx.width, max(ic.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ic, (0, (im.height - ic.height) // 2)); im.alpha_composite(tx, (ic.width + 24, (im.height - tx.height) // 2))
    _cache[key] = im; return im
_cache = {}

def step_badge(num, txt):
    key = ('step', num, txt)
    if key in _cache: return _cache[key]
    n = text_img(str(num), F_IMPACT, 96, DRED, 0)
    tx = head(txt, 116, WHITE, 9, 5)
    D = 150
    ci = Image.new('RGBA', (D + 12, D + 12), (0, 0, 0, 0)); d = ImageDraw.Draw(ci)
    d.ellipse((8, 12, D + 8, D + 12), fill=DRED); d.ellipse((0, 0, D, D), fill=YEL)
    ci.alpha_composite(n, ((D - n.width) // 2, (D - n.height) // 2 + 4))
    im = Image.new('RGBA', (ci.width + 26 + tx.width, max(ci.height, tx.height)), (0, 0, 0, 0))
    im.alpha_composite(ci, (0, (im.height - ci.height) // 2)); im.alpha_composite(tx, (ci.width + 26, (im.height - tx.height) // 2))
    _cache[key] = im; return im

# ---------------------------------------------------------------- transitions
def chevron_wipe(c, t, tc, d=0.56):
    """Brand chevron band sweeps left->right; it fully covers the frame exactly at tc (the cut)."""
    p = (t - (tc - d / 2)) / d
    if p <= 0 or p >= 1: return
    d_ = ImageDraw.Draw(c)
    tip, wband = 420, W + 2 * 420 + 120
    travel = W + wband + tip + 520
    xr = -60 + travel * e_inout(p)               # tip of the red band
    def band(x_r, w, col):
        x_l = x_r - w
        d_.polygon([(x_l - tip, 0), (x_r - tip, 0), (x_r, H / 2), (x_r - tip, H), (x_l - tip, H), (x_l, H / 2)], fill=col + (255,))
    band(xr + 300, 110, YEL)       # leading stripes
    band(xr + 150, 110, ORANGE)
    band(xr, wband, RED)
    band(xr - wband - 40, 110, YEL)  # trailing stripe
    for k in range(3):             # chevrons printed on the band
        xx = xr - 520 - k * 260
        d_.polygon([(xx - 130, H / 2 - 230), (xx - 40, H / 2 - 230), (xx + 110, H / 2), (xx - 40, H / 2 + 230), (xx - 130, H / 2 + 230), (xx + 20, H / 2)], fill=YEL + (255,))

def flash(c, t, tc, d=0.28, strength=0.85):
    if tc <= t < tc + d:
        a = strength * (1 - (t - tc) / d) ** 2
        ov = Image.new('RGBA', (W, H), (255, 255, 240, int(255 * a))); c.alpha_composite(ov)

def whip_blur(img, amount):
    """horizontal motion blur by averaging shifted copies"""
    if amount < 2: return img
    x = np.asarray(img.convert('RGB')).astype(np.float32)
    acc = np.zeros_like(x); n = 9
    for i in range(n):
        acc += np.roll(x, int((i / (n - 1) - 0.5) * amount), axis=1)
    return Image.fromarray((acc / n).astype(np.uint8)).convert('RGBA')

# ---------------------------------------------------------------- scenes
def scene_intro(t):
    c = cream_bg().copy()
    # red diagonal bands
    p = e_out(prog(t, 0.0, 0.5))
    d = ImageDraw.Draw(c)
    d.polygon([(0, 0), (W * p, 0), (W * p - 260, 300), (0, 380)], fill=RED + (255,))
    d.polygon([(W, H), (W - W * p, H), (W - W * p + 260, H - 300), (W, H - 380)], fill=RED + (255,))
    d.polygon([(0, 380), (W * p - 260, 300), (W * p - 250, 318), (0, 400)], fill=ORANGE + (255,))
    lg = asset('logo_rgba.png')
    s = 980 / lg.width
    sc = s * (0.35 + 0.65 * e_back(prog(t, 0.0, 0.42), 1.6))
    wob = 3 * math.sin(t * 5) * (1 - prog(t, 0, 1.2))
    place(c, lg, W / 2, 800, sc, wob, clamp(t / 0.12))
    pop(c, chip('NEW LAUNCH', 64, RED, WHITE, F_HEAD, 44, 18), W / 2, 1180, t, b(1.5), None, rot=-3)
    pop(c, body('For Retailers  •  Distributors  •  Wholesalers', 40, INK), W / 2, 1300, t, b(2.5), None, slide=30)
    return c

def scene_pack(t, t0, t1, top=True, label=None):
    c = red_bg(t)
    cd = card('pack4.png', 600)
    p = prog(t, t0, 0.5)
    y = 980 + 700 * (1 - e_back(p, 1.3))
    rot = -10 + 6 * e_out(p) + 1.2 * math.sin((t - t0) * 2.2)
    place(c, cd, W / 2 + 10, y, 1.0 + 0.04 * (t - t0), rot, clamp(p * 4))
    if top:
        pop(c, body('INTRODUCING', 44, YEL), W / 2, 225, t, t0 + 0.05, t1)
        pop(c, head('TARGET BLASTER', 132, WHITE, 11, 5), W / 2, 330, t, t0 + b(1), t1)
        pop(c, chip('FOAM DART BLASTER  •  AGES 3+', 44, YEL, DRED), W / 2, 1640, t, t0 + b(2), t1, slide=30)
    return c

def scene_card(t, t0, t1, name, width, rot0):
    c = red_bg(t)
    cd = card(name, width)
    p = prog(t, t0, 0.42)
    sc = 0.6 + 0.4 * e_back(p, 1.5) + 0.03 * (t - t0)
    place(c, cd, W / 2, 790, sc, rot0 + 3 * (1 - e_out(p)), clamp(p * 4))
    return c

def lower(c, t, t0, t1, l1, l2=None, l2col=YEL, s1=112, s2=96):
    c.alpha_composite(grad_bottom())
    lines = [(head(l1, s1, WHITE), 0)]
    if l2: lines.append((head(l2, s2, l2col, 9, 5), 0.5 if t1 - t0 > b(2.5) else 0.35))
    lower_third(c, t, lines, t0, t1, 1350, 120)

@functools.lru_cache(maxsize=1)
def styled_pack():
    im = Image.open(P('cat_sr', 'pack_styled.png')).convert('RGBA')
    return im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)

def scene_styled(t, t0, t1):
    """Original Funhoods packet shot (4 darts), slow push-in on brand red."""
    c = red_bg(t)
    im = styled_pack()
    p = prog(t, t0, 0.45)
    sc = 0.9 + 0.03 * (t - t0) + 0.08 * (1 - e_out(p))
    place(c, im, W / 2, 345 + im.height * 0.45, sc, 0, clamp(p * 3))
    return c

@functools.lru_cache(maxsize=2)
def dart_img(d=80, foam=330):
    """Vector foam dart, horizontal: foam end on the left, orange suction cup on the right. d = diameter (px)."""
    k = 3  # supersample
    D, L = d * k, foam * k
    neck, cup = int(0.22 * D), int(0.42 * D)
    Wd, Hd = L + neck + cup + 4 * k, int(D * 1.5) + 8 * k
    im = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
    cy = Hd / 2
    # foam body with cylinder shading (vertical gradient)
    yy = np.arange(Hd)[:, None].astype(np.float32)
    u = np.clip((yy - (cy - D / 2)) / D, 0, 1)
    shade = 1 - 0.35 * (u - 0.32) ** 2 * 3.2
    hi = np.exp(-((u - 0.28) / 0.10) ** 2) * 0.35
    base = np.array([255, 205, 20], np.float32)
    col = np.clip(base[None, None, :] * shade[..., None] + 255 * hi[..., None] * np.array([0, 0.25, 0.9]), 0, 255)
    body = Image.fromarray(np.repeat(col, Wd, 1).astype(np.uint8), 'RGB').convert('RGBA')
    m = Image.new('L', (Wd, Hd), 0); md = ImageDraw.Draw(m)
    md.rounded_rectangle((2 * k, cy - D / 2, 2 * k + L, cy + D / 2), int(D * 0.18), fill=255)
    im.paste(body, (0, 0), m)
    dd = ImageDraw.Draw(im)
    # matte foam grain
    rng = np.random.default_rng(3)
    grain = (rng.random((Hd, Wd)) < 0.035).astype(np.uint8) * 22
    gl_ = Image.fromarray(grain, 'L').filter(ImageFilter.GaussianBlur(k))
    tint = Image.new('RGBA', (Wd, Hd), (200, 140, 0, 255)); tint.putalpha(Image.fromarray(np.minimum(np.asarray(gl_), np.asarray(m)), 'L'))
    im.alpha_composite(tint)
    # neck + flared suction cup
    x0 = 2 * k + L
    dd.rectangle((x0 - 2 * k, cy - D * 0.36, x0 + neck, cy + D * 0.36), fill=(232, 72, 18, 255))
    x1 = x0 + neck
    dd.polygon([(x1, cy - D * 0.38), (x1 + cup, cy - D * 0.72), (x1 + cup, cy + D * 0.72), (x1, cy + D * 0.38)], fill=(255, 98, 30, 255))
    dd.polygon([(x1, cy - D * 0.38), (x1 + cup, cy - D * 0.72), (x1 + cup, cy - D * 0.45), (x1 + 2 * k, cy - D * 0.18)], fill=(255, 140, 70, 255))
    dd.rounded_rectangle((x1 + cup - 5 * k, cy - D * 0.74, x1 + cup + 2 * k, cy + D * 0.74), 3 * k, fill=(214, 58, 10, 255))
    im = im.resize((Wd // k, Hd // k), Image.LANCZOS)
    # soft drop shadow
    sh = Image.new('RGBA', (im.width + 40, im.height + 50), (0, 0, 0, 0))
    a = im.getchannel('A').point(lambda v: int(v * 0.45))
    blk = Image.new('RGBA', im.size, (60, 0, 0, 255)); blk.putalpha(a)
    sh.alpha_composite(blk, (20, 34)); sh = sh.filter(ImageFilter.GaussianBlur(8))
    sh.alpha_composite(im, (20, 20))
    return sh

GUN_UPPER = (1671, 400)   # upper-barrel tip on gun_side.png (x of muzzle face, y of barrel axis)

def scene_load(t):
    """LOAD DARTS: a foam dart slides into the UPPER barrel of the catalogue blaster cut-out."""
    v0, v1 = T.LOAD
    u = t - v0
    c = red_bg(t)
    g = asset('gun_side.png')
    gs = 760 / g.width
    gl, gt = 0, 610                       # gun top-left on the canvas
    tip_x = gl + GUN_UPPER[0] * gs
    up_y = gt + GUN_UPPER[1] * gs
    seat = T.LOAD_SEAT
    # dart: slides in from the right, foam end first, and seats 90 px deep in the upper barrel
    dimg = dart_img()
    pad_l, foam_left_in = 20 + 2, 120
    x_end = tip_x - foam_left_in
    x_start = W + 60
    p = e_inout(prog(u, 0.25, seat - 0.25))
    xl = x_start + (x_end - x_start) * p
    kick = 6 * math.exp(-max(0, u - seat) * 18) * (u >= seat)
    gp = prog(u, 0, 0.4)
    gsc = 0.88 + 0.12 * e_back(gp, 1.4)
    # speed lines while the dart moves
    if 0.3 < u < seat:
        d = ImageDraw.Draw(c)
        for i, dy in enumerate((-22, 0, 22)):
            x_a = xl + dimg.width - 20 + 30 + i * 18
            d.line([(x_a, up_y + dy), (x_a + 120 + 40 * (1 - p), up_y + dy)], fill=(255, 255, 255, 150), width=6)
    place(c, dimg, xl - pad_l + dimg.width / 2, up_y + 7, 1.0, 0, clamp(u / 0.2))   # +7: shadow pad offset (20 top vs 34 bottom)
    gcx, gcy = gl + g.width * gs / 2, gt + g.height * gs / 2
    place(c, g, gcx + kick, gcy, gs * gsc, 0, clamp(gp * 3))
    if u >= seat:
        q = e_back(prog(u, seat, 0.18), 1.7)
        r = 96 * q + 4 * math.sin(u * 14)
        hx, hy = tip_x - 10, up_y
        d = ImageDraw.Draw(c)
        d.ellipse((hx - r - 5, hy - r - 5, hx + r + 5, hy + r + 5), outline=DRED + (255,), width=14)
        d.ellipse((hx - r, hy - r, hx + r, hy + r), outline=YEL + (255,), width=10)
        place(c, chip('UPPER BARREL', 38, YEL, DRED), hx + 30, hy - r - 66, q, -4, clamp(q))
    return c

def render(t):
    # ---- base layer by section (beats)
    if t < b(4):
        c = scene_intro(t)
    elif t < b(8):
        c = scene_pack(t, b(4), b(8))
    elif t < b(12):
        c = footage(t)
        lower(c, t, b(8), b(12), 'BUILT TO FLY', 'OFF YOUR SHELVES!')
    elif t < b(20):
        k = int((t - b(12)) // b(2)); t0 = b(12) + k * b(2); t1 = t0 + b(2)
        if k == 2: c = scene_card(t, t0, t1, 'grip.png', 820, -4)
        elif k == 3: c = scene_card(t, t0, t1, 'darts4.png', 760, 3)
        else: c = footage(t)
        c.alpha_composite(grad_top())
        header_chip(c, t, 'KEY FEATURES', b(12), b(20))
        lab = [('BOLD YELLOW', 'NOZZLE DESIGN'), ('POLICE BADGE', 'DESIGN'), ('TEXTURED', 'EASY GRIP'), ('4 SOFT FOAM DARTS', 'WITH SUCTION TIPS')][k]
        c.alpha_composite(grad_bottom())
        pop(c, body('0%d / 04' % (k + 1), 40, YEL), W / 2, 1255, t, t0, t1)
        pop(c, head(lab[0], 112), W / 2, 1360, t, t0 + 0.04, t1, slide=40)
        pop(c, head(lab[1], 92, YEL, 8, 5), W / 2, 1472, t, t0 + 0.16, t1, slide=40)
    elif t < b(32):
        if b(24) <= t < b(28):
            c = scene_load(t)
        else:
            c = footage(t)
            c.alpha_composite(grad_top()); c.alpha_composite(grad_bottom())
        header_chip(c, t, 'HOW IT WORKS', b(20), b(32))
        if t < b(24): pop(c, step_badge(1, 'PULL BACK'), W / 2, 1420, t, b(20), b(24), slide=40)
        elif t < b(28):
            pop(c, step_badge(2, 'LOAD DARTS'), W / 2, 1478, t, b(24), b(28), slide=40)
            pop(c, chip('INTO THE UPPER BARREL', 44, WHITE, DRED), W / 2, 1630, t, b(24.5), b(28), slide=30)
        else:
            pop(c, step_badge(3, 'AIM...'), W / 2, 1420, t, b(28), b(32), slide=40)
            pop(c, chip('READY?', 54, WHITE, DRED, F_HEAD), W / 2, 1270, t, b(29), b(32))
    elif t < b(36):
        # FIRE! on the drop -- one dart, slow motion
        u = t - T.DROP
        amp = 26 * math.exp(-u * 6)
        sh = (amp * math.sin(t * 93), amp * math.cos(t * 71))
        c = footage(t, 1.0, sh)
        c.alpha_composite(grad_bottom())
        sc = 0.3 + 0.75 * e_back(prog(t, T.DROP, 0.3), 1.6)
        place(c, burst(720), W / 2, 1490, sc, (t * 40) % 360, 0.95 * (1 - prog(t, b(35.4), 0.25)))
        pop(c, impact_txt('FIRE!', 230), W / 2 + sh[0] * 0.5, 1490 + sh[1] * 0.5, t, T.DROP, b(36), d=0.3, rot=-6, from_scale=1.9)
    elif t < b(44):
        c = scene_styled(t, b(36), b(44))
        c.alpha_composite(grad_bottom())
        header_chip(c, t, 'WHY RETAILERS STOCK IT', b(36), b(44), bg=WHITE, fg=RED)
        for i, (txt, dl) in enumerate([('EYE-CATCHING RETAIL PACK', 36), ('4 FOAM DARTS INCLUDED', 38), ('PERFECT FOR GIFTING', 40)]):
            pop(c, check_line(txt, 66), W / 2, 1495 + i * 88, t, b(dl), b(44), slide=30)
    elif t < b(52):
        c = red_bg(t)
        g = asset('gun_side.png')
        p = prog(t, b(44), 0.55)
        x = W / 2 + 900 * (1 - e_out(p)); rot = -8 + 20 * (1 - e_out(p)) + 1.5 * math.sin(t * 2.4)
        place(c, burst(1150, 24, (255, 196, 40), (255, 230, 120), (232, 60, 40)), W / 2, 790, 0.95 + 0.03 * math.sin(t * 3), (t * 12) % 360, 0.35 * clamp(p * 3))
        place(c, g, x, 790 + 10 * math.sin(t * 2.1), 0.52, rot, clamp(p * 3))
        pop(c, logo_sticker(380), W / 2, 228, t, b(44), b(52), rot=-3)
        pop(c, head('NOW TAKING', 104, WHITE), W / 2, 1150, t, b(44.5), b(52), slide=40)
        pop(c, head('BULK ORDERS', 150, YEL, 12, 6), W / 2, 1290, t, b(45), b(52), slide=40)
        for i, (txt, dl) in enumerate([('RETAILERS', 46), ('DISTRIBUTORS', 47), ('WHOLESALERS', 48)]):
            pop(c, chip(txt, 42, WHITE, RED, F_BODY, 30, 15), W / 2, 1430 + i * 92, t, b(dl), b(52))
    elif t < b(56):
        c = footage(t)
        ov = Image.new('RGBA', (W, H), (60, 0, 0, 90)); c.alpha_composite(ov)
        for i, (wd, dl, col, sz) in enumerate([('STOCK', 52, WHITE, 200), ('UP', 53, YEL, 220), ('NOW!', 54, WHITE, 230)]):
            pop(c, impact_txt(wd, sz, col), W / 2, 760 + i * 230, t, b(dl), None, d=0.26, rot=-4, from_scale=1.8)
    else:
        c = scene_end(t)
    if b(4) <= t < b(44) or b(52) <= t < b(56):
        place(c, logo_sticker(210), W - 150, 150, 1.0, 0, 0.92)
    # ---- transitions
    for tc, kind in T.CUTS:
        if kind == 'chev': chevron_wipe(c, t, tc)
        elif kind == 'flash': flash(c, t, tc)
        elif kind == 'zoom': flash(c, t, tc, 0.12, 0.35)
    for tc, kind in T.CUTS:
        if kind == 'whip' and abs(t - tc) < 0.12:
            amt = 260 * (1 - abs(t - tc) / 0.12)
            c = whip_blur(c, amt)
    if t > T.DUR - 0.5:
        c.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * prog(t, T.DUR - 0.5, 0.5)))))
    return c.convert('RGB')

def scene_end(t):
    t0 = T.END_HIT
    c = cream_bg().copy(); d = ImageDraw.Draw(c)
    p = e_out(prog(t, t0, 0.5))
    d.polygon([(0, 0), (W, 0), (W, 250 * p + 60), (W / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    d.polygon([(0, 250 * p + 60), (W / 2, 330 * p + 60), (W, 250 * p + 60), (W, 250 * p + 76), (W / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    d.polygon([(0, H), (W, H), (W, H - 200 * p), (0, H - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png')
    sc = (900 / lg.width) * (0.4 + 0.6 * e_back(prog(t, t0, 0.42), 1.6))
    place(c, lg, W / 2, 560, sc, 0, clamp((t - t0) / 0.1))
    g = asset('gun_side.png')
    pg = prog(t, t0 + b(1), 0.5)
    place(c, g, W / 2 - 170 + 600 * (1 - e_out(pg)), 1050 + 6 * math.sin(t * 2.2), 0.31, -6 + 10 * (1 - e_out(pg)), clamp(pg * 3))
    pk = card('pack4.png', 300, 10, 22)
    pp = prog(t, t0 + b(1.5), 0.5)
    place(c, pk, W / 2 + 255 - 600 * (1 - e_out(pp)), 1050, 1.0, 6 - 10 * (1 - e_out(pp)), clamp(pp * 3))
    pop(c, text_img('BULK & WHOLESALE', F_HEAD, 92, RED, 0), W / 2, 1360, t, t0 + b(2), None, slide=30)
    pop(c, text_img('ENQUIRIES OPEN', F_HEAD, 92, RED, 0), W / 2, 1455, t, t0 + b(2.5), None, slide=30)
    pop(c, chip('DM US FOR TRADE PRICING', 46, RED, WHITE, F_BODY, 40, 22), W / 2, 1585, t, t0 + b(4), None)
    pop(c, body('Target Blaster  •  Foam Dart Blaster  •  Ages 3+', 34, WHITE), W / 2, H - 120, t, t0 + b(5), None)
    return c

# ---------------------------------------------------------------- main
if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='video.mp4'); ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=T.DUR)
    ap.add_argument('--stills', default=''); ap.add_argument('--lowq', action='store_true')
    a = ap.parse_args(); LOWQ = a.lowq
    if a.stills:
        os.makedirs(P('stills'), exist_ok=True)
        for s in a.stills.split(','):
            render(float(s)).save(P('stills', 'st_%06.2f.png' % float(s)))
        sys.exit()
    n0, n1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.out], stdin=subprocess.PIPE)
    for n in range(n0, n1):
        ff.stdin.write(render(n / FPS).tobytes())
        if n % 30 == 0: print('frame', n, flush=True)
    ff.stdin.close(); ff.wait()
