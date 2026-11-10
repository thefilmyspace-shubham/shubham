# Funhoods "Dino Car (MT-03)" -- the shop story. B2B reel, 2160x3840 @ 60 fps, all drawn in code: a quiet toy shop
# gets the Dino Car display box, kids crowd in, the box empties, the dealer reorders -- then the B2B facts.
# The toy is the rig from the Dino Car reel (../funhoods-dino-car: cut-outs of the client's mockup, rims spin, the
# head chomps on its hinge); the shop, the dealer and the kids are flat illustrations drawn here (shop.py).
# Layout is written in a 1080x1920 design space; every primitive scales by T.K.
import sys, os, math, json, argparse, subprocess, functools
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T

ROOT = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(ROOT, *a)
FONTS = os.environ.get('FONTS', os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts'))
K, DW, DH = T.K, T.DW, T.DH
W, H, FPS = DW * K, DH * K, T.FPS

RED = (210, 24, 31); DRED = (120, 6, 14); ORANGE = (255, 162, 58); YEL = (255, 212, 0)
WHITE = (255, 255, 255); CREAM = (255, 248, 236); INK = (40, 22, 22); SKY = (40, 160, 226)
TEAL = (0, 150, 163); DTEAL = (0, 84, 96); GOLD = (255, 186, 0)
PINK = (240, 100, 112); LIME = (118, 190, 38)
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
F_IMPACT = os.path.join(FONTS, 'LuckiestGuy-Regular.ttf')
F_BODY = os.path.join(FONTS, 'Inter-ExtraBold.ttf')
DINO = lambda *a: os.path.join(ROOT, '..', 'funhoods-dino-car', 'assets', *a)   # the Dino Car reel's assets
GEO = json.load(open(DINO('geom.json')))

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
def asset(name): return Image.open(DINO(name)).convert('RGBA')

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

def speed_lines(c, t, y0, y1, n=12, seed=3, alpha=1.0, x0=-100, x1=1180):
    rng = np.random.default_rng(seed); sd = SD(c)
    for i in range(n):
        y = rng.uniform(y0, y1); ln = rng.uniform(140, 360); sp = rng.uniform(1800, 2800); ph = rng.uniform(0, 1)
        x = x1 - ((t * sp + ph * (x1 - x0)) % (x1 - x0 + ln))
        col = [RED, (250, 190, 180), GOLD][i % 3]
        sd.line([(x, y), (x + ln, y)], width=rng.uniform(5, 10), fill=col + (int(200 * alpha),))

# ---------------------------------------------------------------- the car (side view, faces right)
PAD = 380        # headroom above the side view for the lifted head
TYRE_R = 390     # tyre radius in source pixels (source car height = GEO['size'][1])

@functools.lru_cache(maxsize=1)
def side_src():
    w, h = GEO['size']
    def padded(name):
        im = Image.new('RGBA', (w, h + PAD), (0, 0, 0, 0)); im.alpha_composite(asset(name), (0, PAD)); return im
    return padded('car_shell.png'), padded('car_body.png'), padded('car_head.png'), asset('car_base.png'), asset('rim.png')

def _rot_pt(x, y, cx, cy, ang):
    """point rotated like PIL's Image.rotate(ang) (counter-clockwise on screen), image coords"""
    a = math.radians(ang); dx, dy = x - cx, y - cy
    return cx + dx * math.cos(a) + dy * math.sin(a), cy - dx * math.sin(a) + dy * math.cos(a)

def _interp(poly, x):
    for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
        if x0 <= x <= x1: return y0 + (y1 - y0) * (x - x0) / max(1e-6, x1 - x0)
    return poly[-1][1]

@functools.lru_cache(maxsize=12)
def car_side(hd, wheel=0, jaw=0.0, pad=False):
    """side view of height hd (design units, without headroom); wheel = rim angle (deg, + = rolling right);
       jaw = head lift in degrees -- as on the real toy only the head moves: it hinges at its back-top
       (GEO head_pivot) and the mouth opens over the fixed lower jaw; pad keeps the headroom canvas"""
    shp, body_, head, base, rim = side_src(); w, h = GEO['size']; r = GEO['rim_r']
    c = Image.new('RGBA', (w, h + PAD), (0, 0, 0, 0))
    px, py = GEO['head_pivot']; py += PAD
    if jaw > 0.05:
        back = [(x, y + PAD) for x, y in GEO['head_back'] if y >= 400]           # head's rear edge below the spikes
        seam = [(x, y + PAD) for x, y in GEO['seam'] if x > back[-1][0]]         # head's lower edge, back to snout
        chain = back + seam; rot = [_rot_pt(x, y, px, py, jaw) for x, y in chain if x <= 1790]
        lower = [p for p in chain if p[0] <= 1690] + [(1702, 885 + PAD)]         # stops at the tip of the lower jaw
        d = ImageDraw.Draw(c)
        d.polygon(lower + rot[::-1], fill=(72, 34, 12, 255))                     # inside of the mouth
        nb = [p for p in chain if p[0] <= 1150]; nr = [_rot_pt(x, y, px, py, jaw) for x, y in nb]
        d.polygon(nb + nr[::-1], fill=(206, 150, 22, 255))                       # neck / hinge, head-coloured plastic
        up = sorted(_rot_pt(x, y, px, py, jaw) for x, y in seam)
        for k in range(6):                                                       # upper teeth
            x0 = 1290 + k * 76; ya, yb = _interp(up, x0), _interp(up, x0 + 46)
            d.polygon([(x0, ya - 6), (x0 + 46, yb - 6), (x0 + 23, (ya + yb) / 2 + 42)], fill=(255, 226, 120, 255), outline=(214, 160, 30, 255))
    c.alpha_composite(base, (0, PAD))
    rr = rim.rotate(-wheel, Image.BICUBIC) if wheel % 360 else rim
    for hx, hy in GEO['hubs']: c.alpha_composite(rr, (hx - r, hy - r + PAD))
    if jaw > 0.05:
        c.alpha_composite(body_); c.alpha_composite(head.rotate(jaw, Image.BICUBIC, center=(px, py)))
    else:
        c.alpha_composite(shp)
    if not pad: c = c.crop((0, PAD, w, h + PAD))
    s = hd * K / h
    return c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS)

def car_w(hd): return hd * GEO['size'][0] / GEO['size'][1]
def wheel_deg(dist, hd): return dist / (TYRE_R / GEO['size'][1] * hd) * 180 / math.pi
def wq(a): return int(round(a / 4.0)) * 4 % 360

def draw_car(c, x, gy, hd, dist=0.0, rot=0.0, lift=0.0, squash=1.0, alpha=1.0, ghost=0.0):
    """car with its tyres on ground line gy at centre x; dist = distance rolled (spins the rims); lift = height above
       the ground; rot = body rotation about its centre; ghost = motion-trail length (design units)"""
    im = car_side(hd, wq(wheel_deg(dist, hd)))
    cy = gy - lift - hd / 2 * squash
    if ghost > 1:
        for i in range(4, 0, -1):
            place(c, im, x - ghost * i / 4, cy, 1.0, rot, alpha * 0.16 * (5 - i) / 4, sy=squash)
    place(c, im, x, cy, 1.0, rot, alpha, sy=squash)

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

@functools.lru_cache(maxsize=8)
def no_battery(S=250):
    """battery with a red 'no' ring across it"""
    s = int(S * K); u = s / 100; im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((18 * u, 32 * u, 76 * u, 68 * u), 8 * u, fill=WHITE, outline=INK, width=int(5 * u))
    d.rectangle((76 * u, 42 * u, 84 * u, 58 * u), fill=INK)
    d.rounded_rectangle((25 * u, 39 * u, 46 * u, 61 * u), 3 * u, fill=LIME)
    d.text((50 * u, 50 * u), '+', font=font(F_IMPACT, int(22 * u)), fill=INK, anchor='mm')
    d.ellipse((6 * u, 6 * u, 94 * u, 94 * u), outline=RED, width=int(9 * u))
    d.line([(19 * u, 81 * u), (81 * u, 19 * u)], fill=RED, width=int(9 * u))
    return drop_shadow(im, 10, 10, 70, 20)

BOX_COLS = ['c_pink.png', 'c_blue.png', 'c_green.png', 'c_yellow.png']

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
    _blit(im, body('DINO CAR  •  MT-03', wd * 0.058, (92, 50, 20)), wd * 0.5, th + fh * 0.68)
    _blit(im, text_img('192 PCS', F_HEAD, wd * 0.15, RED, 0, DRED, 3, DRED), wd * 0.5, th + fh * 0.85)
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

# ================================================================ the shop story: flat illustration (drawn in code)
WOOD = (196, 138, 84); WOOD_L = (226, 180, 124); WOOD_D = (150, 98, 56)
WALL = (255, 234, 202); WALL_D = (244, 214, 176)
SKIN = (236, 184, 138); SKIN_D = (214, 156, 112); HAIR = (38, 28, 30)
KURTA = (46, 132, 196); KURTA_L = (110, 176, 228)

def mix(c1, c2, u): return tuple(int(a + (b - a) * u) for a, b in zip(c1, c2))
def dull(col, d):
    """desaturate + darken a colour by d (0 = as is, 1 = dull grey) -- the shop before the Dino Car arrives"""
    g = sum(col) / 3; return mix(col, (g * 0.92, g * 0.92, g * 0.92), d)

def arc_pts(cx, cy, rx, ry, a0, a1, n=24):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]

def limb(sd, p0, p1, wd, col):
    sd.line([p0, p1], width=wd, fill=col + (255,)); r = wd / 2
    for x, y in (p0, p1): sd.ellipse((x - r, y - r, x + r, y + r), fill=col + (255,))

def blink(t, seed):
    ph = (t + seed * 0.77) % 3.1
    return ph < 0.11

def face(sd, cx, cy, r, mood, t, seed=0):
    """cartoon face on a head of radius r centred at (cx, cy); mood: neutral, smile, wow, happy, sleepy, grin"""
    ex, ey, er = r * 0.36, cy - r * 0.02, r * 0.13
    shut = mood in ('happy', 'sleepy') or blink(t, seed)
    for sx_ in (-1, 1):
        x = cx + sx_ * ex
        if mood == 'happy':
            sd.arc((x - er * 1.3, ey - er * 0.6, x + er * 1.3, ey + er * 1.6), 200, 340, width=max(3, r * 0.07), fill=INK + (255,))
        elif shut:
            sd.line([(x - er * 1.1, ey + er * 0.3), (x + er * 1.1, ey + er * 0.3)], width=max(3, r * 0.06), fill=INK + (255,))
        else:
            big = 1.25 if mood == 'wow' else 1.0
            sd.ellipse((x - er * big, ey - er * 1.25 * big, x + er * big, ey + er * 1.25 * big), fill=INK + (255,))
            sd.ellipse((x - er * 0.25, ey - er * 0.85, x + er * 0.35, ey - er * 0.2), fill=(255, 255, 255, 255))
    for sx_ in (-1, 1):                                            # cheeks
        x = cx + sx_ * r * 0.55
        sd.ellipse((x - r * 0.15, cy + r * 0.22, x + r * 0.15, cy + r * 0.38), fill=(255, 120, 120, 90))
    my = cy + r * 0.42
    if mood in ('wow',):
        sd.ellipse((cx - r * 0.13, my - r * 0.12, cx + r * 0.13, my + r * 0.16), fill=(120, 30, 30, 255))
    elif mood == 'sleepy':
        sd.ellipse((cx - r * 0.09, my - r * 0.04, cx + r * 0.09, my + r * 0.12), fill=(120, 30, 30, 255))
    elif mood in ('happy', 'grin'):
        sd.pieslice_ = None
        pts = [(cx - r * 0.3, my - r * 0.06)] + arc_pts(cx, my - r * 0.06, r * 0.3, r * 0.28, 0, 180)[::-1] + [(cx + r * 0.3, my - r * 0.06)]
        sd.polygon(arc_pts(cx, my - r * 0.06, r * 0.3, r * 0.28, 0, 180), fill=(130, 30, 34, 255))
        sd.ellipse((cx - r * 0.14, my + r * 0.06, cx + r * 0.14, my + r * 0.22), fill=(236, 96, 100, 255))
    elif mood == 'smile':
        sd.arc((cx - r * 0.24, my - r * 0.22, cx + r * 0.24, my + r * 0.12), 20, 160, width=max(3, r * 0.06), fill=(120, 30, 30, 255))
    else:
        sd.line([(cx - r * 0.14, my), (cx + r * 0.14, my)], width=max(3, r * 0.05), fill=(120, 30, 30, 255))

def dealer(c, x, y, s=1.0, mood='smile', pose='rest', t=0.0, held=None):
    """the shopkeeper behind his counter; (x, y) = middle of the counter-top line (his lower body is hidden by it).
    pose: rest, yawn, wow, present, thumb"""
    sd = SD(c); bob = 4 * s * math.sin(t * 2.2)
    hx, hy, hr = x, y - 430 * s + bob, 104 * s
    sd.rrect((x - 132 * s, y - 310 * s + bob, x + 132 * s, y + 80 * s), 70 * s, fill=KURTA + (255,))
    sd.polygon([(x - 34 * s, y - 300 * s + bob), (x + 34 * s, y - 300 * s + bob), (x, y - 210 * s + bob)], fill=KURTA_L + (255,))
    for k in range(3): sd.ellipse((x - 6 * s, y - 190 * s + k * 42 * s + bob, x + 6 * s, y - 178 * s + k * 42 * s + bob), fill=(240, 240, 250, 255))
    sd.rectangle((x - 30 * s, y - 340 * s + bob, x + 30 * s, y - 296 * s + bob), fill=SKIN_D + (255,))
    for sx_ in (-1, 1): sd.ellipse((hx + sx_ * hr * 0.98 - 22 * s, hy - 26 * s, hx + sx_ * hr * 0.98 + 22 * s, hy + 26 * s), fill=SKIN_D + (255,))
    sd.ellipse((hx - hr, hy - hr * 1.06, hx + hr, hy + hr * 1.02), fill=SKIN + (255,))
    cap = arc_pts(hx, hy - 4 * s, hr * 1.04, hr * 1.12, 188, 352)
    sd.polygon(cap + [(hx + hr * 0.80, hy - hr * 0.42), (hx + hr * 0.2, hy - hr * 0.52), (hx - hr * 0.5, hy - hr * 0.46), (hx - hr * 0.84, hy - hr * 0.40)], fill=HAIR + (255,))
    face(sd, hx, hy + 6 * s, hr, mood, t, 1)
    if mood not in ('wow',):                                       # moustache
        my = hy + hr * 0.30
        sd.polygon([(hx, my - 8 * s), (hx + 22 * s, my - 14 * s), (hx + 54 * s, my - 4 * s), (hx + 62 * s, my + 10 * s), (hx + 30 * s, my + 6 * s), (hx, my + 4 * s),
                    (hx - 30 * s, my + 6 * s), (hx - 62 * s, my + 10 * s), (hx - 54 * s, my - 4 * s), (hx - 22 * s, my - 14 * s)], fill=HAIR + (255,))
    br = -10 * s if mood == 'wow' else 0
    for sx_ in (-1, 1):                                            # eyebrows
        sd.line([(hx + sx_ * hr * 0.20, hy - hr * 0.28 + br), (hx + sx_ * hr * 0.52, hy - hr * 0.32 + br)], width=10 * s, fill=HAIR + (255,))
    sh = [(x - 118 * s, y - 250 * s + bob), (x + 118 * s, y - 250 * s + bob)]
    arm = 54 * s
    def hand(p, thumb=False):
        sd.ellipse((p[0] - 32 * s, p[1] - 32 * s, p[0] + 32 * s, p[1] + 32 * s), fill=SKIN + (255,))
        if thumb: sd.rrect((p[0] - 10 * s, p[1] - 72 * s, p[0] + 12 * s, p[1] - 10 * s), 11 * s, fill=SKIN + (255,))
    if pose == 'rest':
        for k, sx_ in enumerate((-1, 1)):
            el = (x + sx_ * 170 * s, y - 70 * s + bob); hd = (x + sx_ * 70 * s, y - 20 * s)
            limb(sd, sh[k], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA); hand(hd)
    elif pose == 'yawn':
        el = (x - 170 * s, y - 70 * s + bob); limb(sd, sh[0], el, arm, KURTA); limb(sd, el, (x - 70 * s, y - 20 * s), arm * 0.9, KURTA); hand((x - 70 * s, y - 20 * s))
        el = (x + 175 * s, y - 200 * s + bob); hd = (hx + 20 * s, hy + hr * 0.45)
        limb(sd, sh[1], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA); hand(hd)
    elif pose == 'wow':
        for k, sx_ in enumerate((-1, 1)):
            el = (x + sx_ * 200 * s, y - 210 * s + bob); hd = (hx + sx_ * hr * 1.25, hy + hr * 0.2)
            limb(sd, sh[k], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA); hand(hd)
    elif pose == 'present':
        for k, sx_ in enumerate((-1, 1)):
            el = (x + sx_ * 220 * s, y - 120 * s + bob); hd = (x + sx_ * 300 * s, y - 70 * s)
            limb(sd, sh[k], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA); hand(hd)
    elif pose == 'thumb':
        el = (x - 190 * s, y - 120 * s + bob); hd = (x - 150 * s, y - 40 * s)
        limb(sd, sh[0], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA)
        if held is not None: held(c, hd)                           # e.g. the reorder slip
        hand(hd)
        el = (x + 220 * s, y - 280 * s + bob); hd = (x + 250 * s, y - 420 * s + bob)
        limb(sd, sh[1], el, arm, KURTA); limb(sd, el, hd, arm * 0.9, KURTA); hand(hd, True)

KID_STYLE = [dict(shirt=(230, 64, 60), legs=(60, 80, 150), hair='short', skin=(226, 170, 124)),
             dict(shirt=(255, 196, 40), legs=(255, 196, 40), hair='pigtails', skin=(236, 186, 140)),
             dict(shirt=(80, 180, 90), legs=(70, 70, 90), hair='cap', skin=(210, 150, 104))]

def kid(c, x, yf, s, v, pose='walk', t=0.0, mood='smile', back=False):
    """chibi kid standing on yf, centred on x. pose: walk, stand, cheer, reach. back = seen from behind"""
    st = KID_STYLE[v]; sd = SD(c); ph = t * 9 + v * 1.7
    step = math.sin(ph) if pose == 'walk' else 0.0; bob = -abs(step) * 8 * s if pose == 'walk' else (-14 * s * abs(math.sin(t * 7 + v)) if pose == 'cheer' else 0)
    hx, hy, hr = x, yf - 290 * s + bob, 80 * s
    for sx_, k in ((-1, 0), (1, 1)):                               # legs + shoes
        lift = max(0, step if k == 0 else -step) * 22 * s
        lx = x + sx_ * 26 * s + (step * 14 * s if k == 0 else -step * 14 * s)
        if st['hair'] == 'pigtails': sd.rectangle((lx - 12 * s, yf - 110 * s + bob, lx + 12 * s, yf - 18 * s - lift), fill=st['skin'] + (255,))
        else: sd.rectangle((lx - 20 * s, yf - 110 * s + bob, lx + 20 * s, yf - 18 * s - lift), fill=st['legs'] + (255,))
        sd.ellipse((lx - 28 * s, yf - 30 * s - lift, lx + 30 * s, yf - lift), fill=(50, 40, 40, 255))
    if st['hair'] == 'pigtails':                                   # frock
        sd.polygon([(x - 50 * s, yf - 215 * s + bob), (x + 50 * s, yf - 215 * s + bob), (x + 82 * s, yf - 95 * s + bob), (x - 82 * s, yf - 95 * s + bob)], fill=st['shirt'] + (255,))
    else:
        sd.rrect((x - 58 * s, yf - 220 * s + bob, x + 58 * s, yf - 100 * s + bob), 30 * s, fill=st['shirt'] + (255,))
        sd.rectangle((x - 56 * s, yf - 128 * s + bob, x + 56 * s, yf - 100 * s + bob), fill=st['legs'] + (255,))
    sh = [(x - 52 * s, yf - 200 * s + bob), (x + 52 * s, yf - 200 * s + bob)]
    def arm(k, hd):
        limb(sd, sh[k], hd, 30 * s, st['shirt']); sd.ellipse((hd[0] - 18 * s, hd[1] - 18 * s, hd[0] + 18 * s, hd[1] + 18 * s), fill=st['skin'] + (255,))
    if pose == 'walk':
        arm(0, (x - 76 * s - step * 12 * s, yf - 120 * s + bob)); arm(1, (x + 76 * s + step * 12 * s, yf - 120 * s + bob))
    elif pose == 'cheer':
        w_ = 8 * s * math.sin(t * 12 + v)
        arm(0, (x - 110 * s + w_, yf - 330 * s + bob)); arm(1, (x + 110 * s - w_, yf - 330 * s + bob))
    elif pose == 'reach':
        arm(0, (x - 70 * s, yf - 120 * s + bob)); arm(1, (x + 60 * s, yf - 360 * s + bob))
    else:
        arm(0, (x - 72 * s, yf - 120 * s + bob)); arm(1, (x + 72 * s, yf - 120 * s + bob))
    sd.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(HAIR if back else st['skin']) + (255,))
    for sx_ in (-1, 1): sd.ellipse((hx + sx_ * hr - 14 * s, hy - 14 * s, hx + sx_ * hr + 14 * s, hy + 18 * s), fill=st['skin'] + (255,))
    if st['hair'] == 'pigtails':
        for sx_ in (-1, 1): sd.ellipse((hx + sx_ * hr * 1.1 - 30 * s, hy - 40 * s, hx + sx_ * hr * 1.1 + 30 * s, hy + 20 * s), fill=HAIR + (255,))
    if not back:
        if st['hair'] == 'cap':
            sd.polygon(arc_pts(hx, hy - 4 * s, hr * 1.04, hr * 1.04, 185, 355) + [(hx + hr * 1.5, hy - hr * 0.30), (hx - hr, hy - hr * 0.30)], fill=(240, 120, 30, 255))
        else:
            sd.polygon(arc_pts(hx, hy, hr * 1.04, hr * 1.06, 190, 350) + [(hx + hr * 0.6, hy - hr * 0.5), (hx - hr * 0.2, hy - hr * 0.62), (hx - hr * 0.7, hy - hr * 0.45)], fill=HAIR + (255,))
        face(sd, hx, hy + 6 * s, hr, mood, t, v + 2)

# ---------------------------------------------------------------- the shop interior (full frame), the street front
def shelf_items(sd, ys, x0, x1, seed, d):
    """generic toys standing on a shelf top at ys (boxes, balls, teddies, blocks) -- dull by d"""
    rng = np.random.default_rng(seed); x = x0
    pal = [(232, 90, 80), (80, 150, 220), (250, 190, 60), (120, 190, 90), (190, 110, 200), (250, 140, 70)]
    while x < x1 - 60:
        kind = rng.integers(0, 4); col = dull(pal[rng.integers(0, len(pal))], d); col2 = dull(pal[rng.integers(0, len(pal))], d)
        if kind == 0:                                              # a toy box
            w_, h_ = rng.uniform(80, 130), rng.uniform(120, 190)
            sd.rectangle((x, ys - h_, x + w_, ys), fill=col + (255,)); sd.rectangle((x + 10, ys - h_ + 14, x + w_ - 10, ys - h_ * 0.45), fill=mix(col, (255, 255, 255), 0.45) + (255,))
            sd.ellipse((x + w_ / 2 - 16, ys - h_ * 0.35 - 16, x + w_ / 2 + 16, ys - h_ * 0.35 + 16), fill=col2 + (255,))
        elif kind == 1:                                            # a ball
            w_ = rng.uniform(70, 100); sd.ellipse((x, ys - w_, x + w_, ys), fill=col + (255,))
            sd.arc((x + 6, ys - w_ + 6, x + w_ - 6, ys - 6), 200, 340, width=10, fill=mix(col, (255, 255, 255), 0.5) + (255,))
        elif kind == 2:                                            # a teddy
            w_ = 96; tc = dull((176, 120, 70), d)
            sd.ellipse((x + 10, ys - 92, x + w_ - 10, ys), fill=tc + (255,)); sd.ellipse((x + 18, ys - 150, x + w_ - 18, ys - 82), fill=tc + (255,))
            for ex_ in (x + 16, x + w_ - 16): sd.ellipse((ex_ - 14, ys - 160, ex_ + 14, ys - 132), fill=tc + (255,))
            for ex_ in (x + 38, x + w_ - 38): sd.ellipse((ex_ - 4, ys - 124, ex_ + 4, ys - 116), fill=INK + (255,))
        else:                                                      # stacked blocks
            w_ = 90
            for k in range(3): sd.rectangle((x + k * 8, ys - 44 * (k + 1), x + w_ - 16 + k * 2, ys - 44 * k), fill=dull(pal[(k + seed) % 6], d) + (255,))
        x += w_ + rng.uniform(16, 34)

def clock(sd, cx, cy, r, hour):
    sd.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=WOOD_D + (255,)); sd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 252, 240, 255))
    for k in range(12):
        a = math.radians(k * 30); sd.line([(cx + math.cos(a) * r * 0.78, cy + math.sin(a) * r * 0.78), (cx + math.cos(a) * r * 0.9, cy + math.sin(a) * r * 0.9)], width=5, fill=INK + (255,))
    ah = math.radians(hour * 30 - 90); am = math.radians((hour % 1) * 360 - 90)
    sd.line([(cx, cy), (cx + math.cos(ah) * r * 0.5, cy + math.sin(ah) * r * 0.5)], width=10, fill=INK + (255,))
    sd.line([(cx, cy), (cx + math.cos(am) * r * 0.75, cy + math.sin(am) * r * 0.75)], width=6, fill=INK + (255,))
    sd.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=RED + (255,))

COUNTER_Y = 1270
def interior(t, d=0.0, ev=0.0, hour=9.0, lamp=0.0, dealer_mood='smile', dealer_pose='rest', counter=True, held=None, dx=540, lx=540):
    """the inside of the toy shop, full frame. d = dullness of the shelves, ev = evening light, hour = wall clock,
    lamp = spotlight on the counter (0..1), aimed at x = lx; dx = where the dealer stands"""
    c = Image.new('RGBA', (W, H), WALL + (255,)); sd = SD(c)
    for yy in range(0, 1300, 64):                                  # wallpaper stripes
        sd.rectangle((0, yy, DW, yy + 30), fill=mix(WALL_D, WALL, 0.4) + (255,))
    sd.rectangle((0, 0, DW, 110), fill=(236, 200, 156, 255)); sd.rectangle((0, 104, DW, 116), fill=WOOD_D + (255,))
    sky = mix((150, 210, 245), (255, 150, 80), ev)                  # window, top right: morning -> evening
    sd.rrect((740, 160, 1010, 400), 16, fill=WOOD_D + (255,)); sd.rectangle((760, 180, 990, 380), fill=sky + (255,))
    if ev > 0: sd.ellipse((880, 300, 960, 380), fill=(255, 220, 120, int(255 * ev)))
    sd.rectangle((870, 180, 880, 380), fill=WOOD_D + (255,)); sd.rectangle((760, 275, 990, 285), fill=WOOD_D + (255,))
    clock(sd, 190, 270, 88, hour)
    for ys, seed in ((660, 3), (960, 5)):                          # two shelves with generic toys
        shelf_items(sd, ys, 40, 1040, seed, d)
        sd.rectangle((24, ys, 1056, ys + 26), fill=WOOD + (255,)); sd.rectangle((24, ys + 26, 1056, ys + 36), fill=WOOD_D + (255,))
    # lamp
    sd.line([(540, 0), (540, 150)], width=6, fill=(60, 50, 50, 255))
    sd.polygon([(470, 230), (610, 230), (575, 150), (505, 150)], fill=mix((240, 150, 40), (255, 210, 60), lamp) + (255,))
    sd.ellipse((515, 216, 565, 250), fill=mix((255, 240, 200), (255, 255, 220), lamp) + (255,))
    if lamp > 0:                                                   # the spotlight cone onto the counter
        cone = Image.new('RGBA', (W, H), (0, 0, 0, 0)); cd = SD(cone)
        cd.polygon([(500, 240), (580, 240), (lx + 330, COUNTER_Y + 10), (lx - 330, COUNTER_Y + 10)], fill=(255, 240, 160, int(110 * lamp)))
        c.alpha_composite(cone.filter(ImageFilter.GaussianBlur(18 * K)))
    dealer(c, dx, COUNTER_Y, 1.0, dealer_mood, dealer_pose, t, held)
    if counter:
        sd.polygon([(0, COUNTER_Y - 30), (DW, COUNTER_Y - 30), (DW, COUNTER_Y + 20), (0, COUNTER_Y + 20)], fill=WOOD_L + (255,))
        sd.rectangle((0, COUNTER_Y + 20, DW, COUNTER_Y + 50), fill=WOOD_D + (255,))
        sd.rectangle((0, COUNTER_Y + 50, DW, DH), fill=WOOD + (255,))
        sd.rrect((90, COUNTER_Y + 120, 990, COUNTER_Y + 470), 18, fill=(200, 230, 240, 255), outline=WOOD_D + (255,), width=10)
        for k, col in enumerate([(232, 90, 80), (80, 150, 220), (250, 190, 60), (120, 190, 90)]):   # toys inside the glass
            xx = 170 + k * 210; sd.rrect((xx, COUNTER_Y + 300, xx + 140, COUNTER_Y + 450), 12, fill=dull(col, d) + (255,))
        sd.polygon([(120, COUNTER_Y + 140), (200, COUNTER_Y + 140), (110, COUNTER_Y + 300)], fill=(255, 255, 255, 110))
        for yy in (COUNTER_Y + 560, COUNTER_Y + 600): sd.line([(0, yy), (DW, yy)], width=4, fill=WOOD_D + (255,))
    if ev > 0: c.alpha_composite(Image.new('RGBA', (W, H), (255, 120, 40, int(46 * ev))))
    return c

@functools.lru_cache(maxsize=4)
def interior_cached(key):
    d, ev, hour, lamp, mood, pose = key[:6]; dx, lx = key[6:] if len(key) > 6 else (540, 540)
    return interior(0.0, d, ev, hour, lamp, mood, pose, dx=dx, lx=lx)

def street(t, shutter=1.0, inside=None, sky_ev=0.0):
    """street view of the shop front. shutter = how far it is open (0 shut .. 1 open); inside = the interior image"""
    c = Image.new('RGBA', (W, H), (0, 0, 0, 255)); sd = SD(c)
    for k in range(12):                                            # sky
        u = k / 11; sd.rectangle((0, k * 56, DW, k * 56 + 58), fill=mix((140, 205, 245), (210, 236, 252), u) + (255,))
    for cx_, cy_, r_ in ((180, 120, 60), (300, 105, 75), (420, 125, 55), (820, 150, 50), (920, 140, 65)):
        sd.ellipse((cx_ - r_, cy_ - r_ * 0.7, cx_ + r_, cy_ + r_ * 0.7), fill=(255, 255, 255, 230))
    sd.rectangle((0, 190, DW, 1360), fill=(250, 222, 170, 255))       # facade + bricks
    for row, yy in enumerate(range(190, 1360, 46)):
        off = 0 if row % 2 else 60
        for xx in range(-off, DW, 120): sd.rectangle((xx, yy, xx + 116, yy + 42), outline=(238, 204, 150, 255), width=3)
    for x0 in (30, 960): sd.rectangle((x0, 190, x0 + 90, 1360), fill=(236, 196, 140, 255))
    sd.rrect((100, 240, 980, 450), 18, fill=RED + (255,), outline=YEL + (255,), width=10)     # signboard
    place(c, text_img('TOY SHOP', F_IMPACT, 116, YEL, 5, DRED, 9, DRED), 540, 328)
    place(c, body('TOYS  •  GAMES  •  GIFTS', 30, WHITE), 540, 412)
    for k in range(12):                                            # striped awning with scallops
        x0 = 100 + k * 73.4; col = RED if k % 2 == 0 else WHITE
        sd.polygon([(x0, 470), (x0 + 73.4, 470), (x0 + 73.4 + 8, 545), (x0 + 8, 545)], fill=col + (255,))
        sd.ellipse((x0 + 8, 515, x0 + 81.4, 580), fill=col + (255,))
    ox0, oy0, ox1, oy1 = 150, 580, 930, 1340                          # the shop opening
    if inside is not None:
        crop = inside.crop((0, int(250 * K), W, int(1330 * K))).resize((int((ox1 - ox0) * K), int((oy1 - oy0) * K)), Image.BILINEAR)
        c.alpha_composite(crop, (int(ox0 * K), int(oy0 * K)))
    sy = oy0 + (oy1 - oy0) * (1 - shutter)                          # shutter, rolled up into the box
    if shutter < 0.999:
        sd.rectangle((ox0, oy0, ox1, sy), fill=(176, 182, 190, 255))
        for yy in np.arange(oy0 + 14, sy, 26): sd.line([(ox0, yy), (ox1, yy)], width=4, fill=(140, 146, 156, 255))
        sd.rectangle((ox0, sy - 26, ox1, sy), fill=(120, 126, 136, 255)); sd.rrect((520, sy - 20, 560, sy - 6), 6, fill=(90, 94, 104, 255))
    sd.rectangle((ox0 - 20, oy0 - 26, ox1 + 20, oy0 + 6), fill=(130, 136, 146, 255))
    sd.rectangle((0, 1340, DW, 1660), fill=(214, 214, 210, 255))       # footpath, kerb, road
    for xx in range(0, DW, 108): sd.line([(xx, 1340), (xx - 40, 1660)], width=3, fill=(196, 196, 192, 255))
    for k in range(14): sd.rectangle((k * 80, 1660, k * 80 + 80, 1690), fill=((40, 40, 40) if k % 2 else (250, 210, 0)) + (255,))
    sd.rectangle((0, 1690, DW, DH), fill=(84, 86, 94, 255))
    for xx in range(-60, DW, 200): sd.rectangle((xx + ((t * 0) % 200), 1800, xx + 110, 1814), fill=(240, 240, 240, 255))
    return c

# ---------------------------------------------------------------- story props
@functools.lru_cache(maxsize=4)
def box_img(h, empty_cols=0):
    """the 12-pc display box, h design units tall; the first empty_cols colour columns (pink, blue, green, yellow) are empty"""
    full = asset('box_real.png')
    if empty_cols:
        emp = Image.open(P('assets', 'box_empty.png')).convert('RGBA'); xs = [0, 750, 1175, 1605, full.width][:empty_cols + 1]
        m = Image.new('L', full.size, 0); ImageDraw.Draw(m).rectangle((0, 0, xs[-1] if empty_cols < 4 else full.width, full.height), fill=255)
        full = Image.composite(emp, full, m)
    s = h * K / full.height
    return drop_shadow(full.resize((int(full.width * s), int(full.height * s)), Image.LANCZOS), 16, 20, 90)

def box_cols(t):
    """how many colour columns are already empty (3 grabs per column)"""
    return sum(1 for j in range(4) if t >= T.GRABS[3 * j + 2] + 0.25)

@functools.lru_cache(maxsize=1)
def stamp_img():
    S_ = int(520 * K); im = Image.new('RGBA', (S_, int(240 * K)), (0, 0, 0, 0)); sd = SD(im)
    sd.rrect((10, 10, 510, 230), 30, outline=RED + (255,), width=16)
    _blit(im, text_img('SOLD OUT!', F_IMPACT, 104, RED, 0), 260, 124)
    return im

def reorder_slip(c, hd):
    x, y = hd; sd = SD(c)
    sd.polygon([(x - 20, y - 230), (x + 170, y - 250), (x + 190, y - 10), (x, y + 10)], fill=(255, 255, 255, 255))
    place(c, logo_img(130), x + 92, y - 192, 1.0, 5)
    for k in range(3): sd.line([(x + 30, y - 120 + k * 36), (x + 160, y - 128 + k * 36)], width=6, fill=(170, 170, 180, 255))
    sd.line([(x + 40, y - 40), (x + 70, y - 14), (x + 130, y - 78)], width=12, fill=(40, 170, 80, 255))

@functools.lru_cache(maxsize=2)
def blurred_interior(key, blur):
    return interior_cached(key).filter(ImageFilter.GaussianBlur(blur * K))

def roar_arcs(c, t, t0, cx, cy, amp=1.0):
    sd = SD(c)
    for k_ in range(3):
        q = ((t - t0) * 2.4 + k_ / 3) % 1; rr = 140 + 110 * q; a = int(230 * (1 - q) * amp)
        sd.arc((cx - rr, cy - rr, cx + rr, cy + rr), -40, 40, width=12, fill=RED + (a,))

def jaw_angle(t):
    a = 0.0
    for t0, amp, hold in T.CHOMPS:
        up = e_back(prog(t, t0, 0.16), 1.2); down = e_in(prog(t, t0 + 0.16 + hold, 0.10))
        a = max(a, amp * up * (1 - down))
    return a

# ---------------------------------------------------------------- scenes
def scene_street(t):
    """Morning at the toy shop. Full shelves... but nobody stops. / Then the Funhoods Dino Car arrives!"""
    arrived = t >= T.CARTON_LAND - 0.2
    mood, pose = ('wow', 'wow') if arrived else (('sleepy', 'yawn') if 1.3 < t < 2.6 else ('neutral', 'rest'))
    inside = interior_cached((0.7, 0.0, 9.0, 0.0, mood, pose))
    c = street(t, e_inout(prog(t, *T.SHUTTER)), inside)
    for k, v in enumerate((0, 1, 2)):                               # kids walk past without stopping
        u = prog(t, T.KIDS_PASS[0] + k * 0.45, T.KIDS_PASS[1] - T.KIDS_PASS[0] - 0.9)
        if 0 < u < 1: kid(c, lerp(-160, 1240, u), 1600 + k * 18, 0.80, v, 'walk', t, 'neutral')
    if t >= T.S_ARRIVE - 0.2:                                     # the Funhoods truck pulls up
        q = prog(t, T.S_ARRIVE - 0.2, T.TRUCK_STOP - T.S_ARRIVE + 0.2)
        x = lerp(-380, 640, e_out(q)); bob = 3 * math.sin(t * 30) * (1 - q)
        if q < 1: speed_lines(c, t, 1700, 1880, 6, 9, 1 - q, -100, x - 220)
        place(c, truck(560), x, 1745 + bob)
        tl = T.CARTON_LAND
        if t >= tl - 0.42:                                          # a carton hops from the truck to the shop door
            u = prog(t, tl - 0.42, 0.42); cx_ = lerp(x - 120, 540, u); cy_ = lerp(1700, 1440, u) - 260 * 4 * u * (1 - u)
            if t >= tl: cy_ = 1440 - 22 * math.exp(-(t - tl) * 9) * abs(math.sin((t - tl) * 22))
            place(c, carton(240), cx_, cy_, 1.0, -8 * (1 - u))
            if t >= tl:
                place(c, soft_burst(520), 540, 1440, 0.4 + 0.6 * e_back(prog(t, tl, 0.3), 1.6), (t * 40) % 360, 0.45 * (1 - prog(t, tl + 0.6, 0.3)))
                sparkles(c, t, 4, 540, 1400, 260, 120, n=10, size=40)
    pop(c, chip('FUNHOODS DINO CAR', 50, YEL, DRED, F_HEAD, 40, 18), DW / 2, 1590, t, T.CARTON_LAND + 0.08, None, slide=24)
    return c

BOX_H = 560
BOX_X, DEALER_X = 330, 770                                        # the box on the counter's left, the dealer on the right
def scene_counter(t, t0, t1):
    """Twelve dinos in a bright display box, right on the counter. -- the box lands, the shop lights up"""
    lit = e_inout(prog(t, T.BOX_LAND, 0.5)); lamp = e_out(prog(t, T.SPOT, 0.3))
    mood, pose = ('wow', 'wow') if t < T.BOX_LAND else ('happy', 'present')
    c = interior(t, 0.7 * (1 - lit), 0.0, 9.5, lamp, mood, pose, dx=DEALER_X, lx=BOX_X)
    q = prog(t, T.BOX_LAND - 0.34, 0.34); cy = COUNTER_Y - BOX_H / 2 + 20
    if q > 0:
        y = cy - 1400 * (1 - e_in(q)) if t < T.BOX_LAND else cy - 26 * math.exp(-(t - T.BOX_LAND) * 9) * abs(math.sin((t - T.BOX_LAND) * 22))
        place(c, box_img(BOX_H), BOX_X, y)
    if t > T.BOX_LAND: sparkles(c, t, 17, BOX_X, cy, 330, 330, n=12, size=40)
    pop(c, chip('12 PCS DISPLAY BOX', 54, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1600, t, T.BOX_LAND + 0.12, None, slide=30)
    pop(c, head('RIGHT ON THE COUNTER', 78, RED), DW / 2, 1720, t, T.w(2, 7) - 0.05, None, slide=24)
    return c

DEMO_GY = 1330; DEMO_HC = 290
RAMP = (470, 700, 150)                                              # ramp foot x, lip x, height (books under the lip)
def scene_demo(t, t0, t1):
    """One push, and off it goes! A full 360 flip... and that dino mouth opens wide! -- on the counter"""
    c = blurred_interior((0.0, 0.0, 10.5, 1.0, 'happy', 'rest'), 9).copy(); sd = SD(c)
    c.alpha_composite(Image.new('RGBA', (W, H), (255, 246, 230, 70)))
    gy, Hc = DEMO_GY, DEMO_HC
    sd.polygon([(0, gy - 70), (DW, gy - 70), (DW, gy + 40), (0, gy + 40)], fill=WOOD_L + (255,))      # counter top (close)
    sd.rectangle((0, gy + 40, DW, gy + 80), fill=WOOD_D + (255,)); sd.rectangle((0, gy + 80, DW, DH), fill=WOOD + (255,))
    rx0, rx1, rh = RAMP
    for k, col in enumerate([(220, 70, 70), (60, 130, 210), (250, 190, 40)]):                          # a stack of books
        sd.rrect((rx1 - 40 - k * 6, gy - (k + 1) * 50, rx1 + 150 - k * 10, gy - k * 50 - 4), 6, fill=col + (255,))
        sd.rectangle((rx1 + 120 - k * 10, gy - (k + 1) * 50 + 8, rx1 + 146 - k * 10, gy - k * 50 - 12), fill=(250, 246, 236, 255))
    sd.polygon([(rx0 - 10, gy + 2), (rx1, gy - rh), (rx1 + 16, gy - rh), (rx1 + 16, gy - rh + 18), (rx0 + 20, gy + 2)], fill=WOOD_D + (255,))  # plank
    x_in = 240; push = e_inout(prog(t, T.PUSH0, T.RELEASE - T.PUSH0)); slope = math.degrees(math.atan2(rh, rx1 - rx0))
    ta = T.LAUNCH - 0.42                                            # reaches the ramp foot
    if t < T.RELEASE:
        x = x_in + 80 * push; draw_car(c, x, gy, Hc, x * 1.0); ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
    elif t < ta:
        u = e_inout(prog(t, T.RELEASE, ta - T.RELEASE)); x = lerp(x_in + 80, rx0 - car_w(Hc) * 0.30, u)
        draw_car(c, x, gy, Hc, x * 1.6, ghost=60 * (1 - abs(2 * u - 1))); ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
    elif t < T.LAUNCH:
        u = prog(t, ta, T.LAUNCH - ta); xc = lerp(rx0, rx1, u); yc = gy - (xc - rx0) / (rx1 - rx0) * rh
        sl = slope * e_out(clamp(u * 3)); th = math.radians(sl)
        place(c, car_side(Hc, wq(wheel_deg(700 + u * 300, Hc))), xc - math.sin(th) * Hc / 2, yc - math.cos(th) * Hc / 2, 1.0, sl)
    elif t < T.LAND:
        u = prog(t, T.LAUNCH, T.LAND - T.LAUNCH)
        x0_, y0_ = rx1 - math.sin(math.radians(slope)) * Hc / 2, gy - rh - Hc / 2 * math.cos(math.radians(slope))
        x1_, y1_ = 880, gy - Hc / 2
        x = lerp(x0_, x1_, u); y = lerp(y0_, y1_, u) - 330 * 4 * u * (1 - u); rot = slope - (slope + 360) * e_inout(u)
        ground_shadow(c, x, gy + 6, car_w(Hc) * (0.4 + 0.4 * u), 0.6)
        place(c, car_side(Hc, wq(wheel_deg(1000 + u * 800, Hc))), x, y, 1.0, rot)
        ring = 1 - abs(2 * u - 1) ** 3; ra = 230
        for k_ in range(2):
            a0 = (-u * 540 + k_ * 180) % 360
            sd.arc((x - ra, y - ra, x + ra, y + ra), a0, a0 + 120, width=14, fill=RED + (int(230 * ring),))
    else:
        u = t - T.LAND; x = 880; sq = 1 - 0.10 * math.exp(-u * 10) * math.cos(u * 30)
        ja = jaw_angle(t); ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
        im = car_side(Hc, 0, round(ja * 4) / 4, True)
        place(c, im, x, gy - (Hc + PAD * Hc / GEO['size'][1]) / 2 * sq, 1.0, 0, 1.0, sy=sq)
        dust(c, t, T.LAND, x - 120, gy, 7, 6, 150); dust(c, t, T.LAND, x + 120, gy, 7, 7, 150, dirx=1)
        if ja > 1: roar_arcs(c, t, T.CHOMPS[0][0], x + car_w(Hc) * 0.5 + 10, gy - Hc * 0.62, min(1, ja / 8))
    gin = e_out(prog(t, T.PUSH0 - 0.32, 0.30)); gout = e_inout(prog(t, T.RELEASE, 0.35))       # a kid's hand pushes
    if gin > 0 and gout < 1:
        hx = x_in + 80 * push - car_w(Hc) * 0.24 - 30 - 420 * (1 - gin) - 260 * gout; hy = gy - Hc - 2 - 560 * (1 - gin) - 380 * gout
        place(c, glove(300), hx, hy + (6 * math.sin(t * 40) if 0 < push < 1 else 0), 1.0, -14 + 10 * gout, 1 - gout)
    cheer = t > T.LAUNCH                                             # kids watching from the front
    kid(c, 120, 2240, 1.55, 1, 'cheer' if cheer else 'stand', t, 'happy' if t > T.LAND else ('wow' if cheer else 'smile'))
    kid(c, 960, 2240, 1.55, 2, 'cheer' if cheer else 'stand', t + 0.3, 'happy' if t > T.LAND else ('wow' if cheer else 'smile'))
    pop(c, chip('PUSH & GO', 52, YEL, DRED, F_HEAD, 40, 18), DW / 2, 300, t, T.PUSH0, T.LAUNCH - 0.1, slide=24)
    if t >= T.LAUNCH:
        place(c, burst(620), DW / 2, 380, 0.3 + 0.6 * e_back(prog(t, T.LAUNCH, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, T.CHOMPS[1][0] - 0.2, 0.2)))
    pop(c, impact_txt('360° FLIP!', 170, YEL), DW / 2, 380, t, T.LAUNCH, T.CHOMPS[1][0], d=0.3, rot=-4, from_scale=1.8)
    pop(c, head('MOUTH OPENS WIDE!', 100, RED), DW / 2, 380, t, T.CHOMPS[1][0], None, slide=30)
    pop(c, body('DINOSAUR MOUTH CAN BE OPENED UP AND DOWN', 30, RED), DW / 2, 480, t, T.CHOMPS[1][0] + 0.2, None, slide=16)
    return c

def scene_rush(t, t0, t1):
    """Kids crowd in... and by evening, the box is empty. Time to reorder!"""
    ev = e_inout(prog(t, T.EVENING, 1.0)); hour = 10.5 + (18.3 - 10.5 - 12 * 0) * ev
    reorder = t >= T.REORDER
    c = interior(t, 0.0, ev, hour if hour <= 12 else hour - 12, 0.6, 'grin' if not reorder else 'happy', 'thumb' if reorder else 'rest',
                 held=reorder_slip if reorder else None, dx=DEALER_X, lx=BOX_X)
    cy = COUNTER_Y - BOX_H / 2 + 20; cols = box_cols(t)
    place(c, box_img(BOX_H, cols), BOX_X, cy)
    kx = [220, 540, 860]
    for i, tg in enumerate(T.GRABS):                                 # the dinos hop out into the kids' hands
        u = prog(t, tg, 0.5)
        if 0 < u < 1:
            j = i // 3; sx = BOX_X + (-195 + j * 130); sy = cy - 40; tx, ty = kx[i % 3] + 60, 1500
            x = lerp(sx, tx, u); y = lerp(sy, ty, u) - 380 * 4 * u * (1 - u)
            place(c, scaled(BOX_COLS[[0, 1, 2, 3][j]], h=150), x, y, 1.0 - 0.2 * u, 360 * u * (1 if i % 2 else -1), 1 - prog(u, 0.85, 0.15))
    for k, v in enumerate((0, 1, 2)):
        kid(c, kx[k], 2060 + 20 * (k % 2), 1.42, v, 'cheer', t + k * 0.21, back=True)
    if t >= T.SOLD:                                                  # SOLD OUT stamp on the empty box
        q = prog(t, T.SOLD, 0.22); s = 1.8 - 0.8 * e_out(q)
        place(c, stamp_img(), BOX_X, cy - 40, s, -12, clamp(q * 4))
    pop(c, impact_txt('TIME TO REORDER!', 116, YEL), DW / 2, 330, t, T.REORDER, None, d=0.3, rot=-4, from_scale=1.8)
    pop(c, chip('KIDS LOVE IT', 46, RED, WHITE, F_HEAD, 36, 16), DW / 2, 330, t, T.S_RUSH + 0.3, T.REORDER, slide=24)
    return shift(c, *shake_xy(t, T.SOLD, 12, 9)) if t >= T.SOLD else c

def scene_facts(t, t0, t1):
    """Four colours, BIS approved, safe for little hands."""
    c = blurred_interior((0.0, 0.0, 10.5, 1.0, 'happy', 'rest'), 12).copy()
    c.alpha_composite(Image.new('RGBA', (W, H), (255, 250, 240, 120))); sd = SD(c)
    pop(c, head('AVAILABLE IN 4 COLORS', 86), DW / 2, 290, t, t0 + 0.08, None, slide=30)
    ys = 860; sd.rectangle((30, ys, 1050, ys + 30), fill=WOOD + (255,)); sd.rectangle((30, ys + 30, 1050, ys + 42), fill=WOOD_D + (255,))
    for i, (a, col) in enumerate(zip(BOX_COLS, [PINK, SKY, LIME, (255, 176, 0)])):
        tp = T.FACT_POPS[0] + 0.12 * i; pp = prog(t, tp, 0.42)
        if pp <= 0: continue
        x = 150 + i * 260
        sd.ellipse((x - 120, ys - 260, x + 120, ys - 20), fill=col + (int(60 * clamp(pp * 3)),))
        place(c, with_shadow(a, 230, 10, 12, 70), x, ys - 120 - 120 * (1 - e_back(pp, 1.4)) + 4 * math.sin(t * 2.4 + i), 1.0, -3 + 3 * math.sin(t * 2 + i), clamp(pp * 3))
    sd.rrect((70, 1040, 1010, 1600), 40, fill=(255, 255, 255, 200))
    rows = [('shield', 'BIS APPROVED'), ('hand', 'SAFE FOR LITTLE HANDS'), ('age', '3+ AGES')]
    for i, ((k, txt), tp) in enumerate(zip(rows, T.FACT_POPS[1:])):
        im = badge_row(k, txt, 64)
        pop(c, im, 130 + im.width / K / 2, 1150 + i * 160, t, tp - 0.04, None, slide=30)
    return c

def scene_carton(t, t0, t1):
    """192 pieces per carton, pan India delivery."""
    c = bg(t); shake = [0.0, 0.0]
    pop(c, impact_txt('192 PCS', 200, YEL), DW / 2, 320, t, T.w(6, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
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

@functools.lru_cache(maxsize=2)
def mini_shop(lit):
    """a small shop front for the route scene; lit = its window shows the Dino display box on the counter"""
    ins = interior(0.0, 0.0 if lit else 0.7, 0.0, 10.0, 1.0 if lit else 0.0, 'happy' if lit else 'neutral', 'present' if lit else 'rest',
                   dx=DEALER_X if lit else 540, lx=BOX_X)
    if lit: place(ins, box_img(BOX_H), BOX_X, COUNTER_Y - BOX_H / 2 + 20)
    im = street(0.0, 1.0, ins).crop((0, int(190 * K), W, int(1360 * K)))
    return im.resize((int(330 * K), int(330 * K * im.height / im.width)), Image.LANCZOS)

def scene_route(t, t0, t1):
    """Distributors and wholesalers, put the Dino Car in every shop on your route!"""
    c = Image.new('RGBA', (W, H), (0, 0, 0, 255)); sd = SD(c)
    for k in range(20): sd.rectangle((0, k * 70, DW, k * 70 + 72), fill=mix((150, 210, 246), (226, 242, 252), k / 19) + (255,))
    pop(c, body('FOR', 46, RED), DW / 2, 290, t, t0 + 0.06, None, slide=20)
    pop(c, head('DISTRIBUTORS', 120), DW / 2, 390, t, T.w(7, 0) - 0.06, None, slide=30)
    pop(c, head('& WHOLESALERS', 108, YEL), DW / 2, 520, t, T.w(7, 2) - 0.06, None, slide=30)
    sd.rectangle((0, 1180, DW, 1330), fill=(214, 214, 210, 255)); sd.rectangle((0, 1330, DW, 1350), fill=(250, 210, 0, 255))
    sd.rectangle((0, 1350, DW, 1560), fill=(84, 86, 94, 255))
    for xx in range(-40, DW, 180): sd.rectangle((xx, 1450, xx + 100, 1462), fill=(240, 240, 240, 255))
    sd.rectangle((0, 1560, DW, 1580), fill=(250, 210, 0, 255)); sd.rectangle((0, 1580, DW, DH), fill=(226, 226, 222, 255))   # far footpath
    for i, x in enumerate((190, 540, 890)):
        lit = t >= T.ROUTE_LIT[i]; im = mini_shop(lit)
        q = e_back(prog(t, t0 + 0.15 + 0.1 * i, 0.4), 1.3)
        place(c, im, x, 1180 - im.height / K / 2 + 200 * (1 - q), 1.0, 0, clamp(q * 3))
        if lit:
            u = prog(t, T.ROUTE_LIT[i], 0.5)
            place(c, soft_burst(420), x, 1000, 0.3 + 0.7 * e_back(u, 1.5), (t * 30) % 360, 0.5 * (1 - u))
            sparkles(c, t, 30 + i, x, 980, 150, 120, n=6, size=30)
    # the truck drives along the route and passes each shop as it lights up
    v = (890 - 190) / (T.ROUTE_LIT[2] - T.ROUTE_LIT[0]); x = 190 + (t - T.ROUTE_LIT[0]) * v
    place(c, truck(380), x, 1445 + 2 * math.sin(t * 30))
    pop(c, chip('BULK ORDERS ONLY', 56, YEL, DRED, F_HEAD, 44, 20), DW / 2, 1660, t, T.w(7, 3) - 0.05, None, slide=30)
    pop(c, impact_txt('EVERY SHOP ON YOUR ROUTE!', 92, YEL), DW / 2, 1790, t, T.w(7, 8) - 0.05, None, d=0.3, rot=-3, from_scale=1.7)
    return c

def scene_end(t):
    t0 = T.S_END
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, t0, 0.5))
    sd.polygon([(0, 0), (DW, 0), (DW, 250 * p + 60), (DW / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    sd.polygon([(0, 250 * p + 60), (DW / 2, 330 * p + 60), (DW, 250 * p + 60), (DW, 250 * p + 76), (DW / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    sd.polygon([(0, DH), (DW, DH), (DW, DH - 200 * p), (0, DH - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png'); tl = T.w(8, 0) - 0.22
    place(c, lg, DW / 2, 500, (800 * K / lg.width) * (0.4 + 0.6 * e_back(prog(t, tl, 0.42), 1.6)), 0, clamp((t - tl) / 0.1))
    pb = prog(t, t0 + 0.15, 0.5)
    place(c, box_img(420), DW / 2, 1010 + 260 * (1 - e_back(pb, 1.3)), 1.0, 0, clamp(pb * 3))
    for i, (a, x, dl, rot) in enumerate([('c_pink.png', 150, 0.30, 6), ('c_blue.png', 930, 0.38, -6)]):
        pc = prog(t, t0 + dl, 0.5); side = -1 if x < DW / 2 else 1
        place(c, with_shadow(a, 230, 10, 12, 70), x + side * 400 * (1 - e_out(pc)), 1110 + 5 * math.sin(t * 2.2 + i), 1.0, rot, clamp(pc * 3))
    pop(c, body('DINO CAR  •  MT-03  •  3+ AGES', 38, RED), DW / 2, 1300, t, t0 + 0.45, None, slide=20)
    pop(c, chip('BULK ORDERS ONLY', 52, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1415, t, t0 + 0.6, None, slide=30)
    ca, cb_ = chip('192 PCS / CARTON', 34, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 34, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1530, t, t0 + 0.8, None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1530, t, t0 + 0.95, None, slide=20)
    pop(c, body('For Distributors  &  Wholesalers', 36, INK), DW / 2, 1630, t, t0 + 1.1, None, slide=20)
    pop(c, body('SPECIFICATIONS COLOURS AND CONTENTS MAY VARY FROM ILLUSTRATIONS', 17, WHITE), DW / 2, DH - 62, t, t0 + 1.2, None)
    return c

def render(t):
    if t < T.S_COUNTER: c = scene_street(t)
    elif t < T.S_DEMO: c = scene_counter(t, T.S_COUNTER, T.S_DEMO)
    elif t < T.S_RUSH: c = scene_demo(t, T.S_DEMO, T.S_RUSH)
    elif t < T.S_FACTS: c = scene_rush(t, T.S_RUSH, T.S_FACTS)
    elif t < T.S_CARTON: c = scene_facts(t, T.S_FACTS, T.S_CARTON)
    elif t < T.S_ROUTE: c = scene_carton(t, T.S_CARTON, T.S_ROUTE)
    elif t < T.S_END: c = scene_route(t, T.S_ROUTE, T.S_END)
    else: c = scene_end(t)
    if t < T.S_END:
        place(c, logo_sticker(200), 158, 1855 if t < T.S_COUNTER else 150, 1.0, 0, 0.94)   # Funhoods logo (bottom-left on the street shots)
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
