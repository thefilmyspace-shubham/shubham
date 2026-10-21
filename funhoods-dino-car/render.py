# Funhoods "Dino Car (MT-03)" B2B reel -- 2160x3840 @ 60 fps. All motion graphics on the white backdrop of the
# Musical Stick reel (white sunburst, red type, yellow lines with a red outline). How the toy works (push & go, 360°
# flip, climb, mouth opens) is animated from cut-outs of the client's product mockup -- no footage is used.
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
GEO = json.load(open(P('assets', 'geom.json')))

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

# ---------------------------------------------------------------- scenes
def scene_hero(t):
    """The Dino Monster Truck! -- the truck drops in, then roars"""
    c = bg(t); t_land = 0.32; Hc = 760; cx, gy = DW / 2, 1490
    place(c, soft_burst(1050), cx, 1060, 0.9 + 0.03 * math.sin(t * 2.5) + 0.12 * prog(t, T.ROAR, 0.2), (t * 10) % 360, 0.30 * clamp(t / 0.3))
    roar = prog(t, T.ROAR, 0.10) * (1 - prog(t, T.ROAR + 0.55, 0.2))
    sq = 1.0 if t < t_land else 1 - 0.07 * math.exp(-(t - t_land) * 9) * math.cos((t - t_land) * 34)
    sc = 1.0 + 0.06 * e_out(roar) + 0.010 * max(0, t - t_land)
    cyc = gy - Hc / 2 * sc * sq - (1500 * (1 - e_in(t / t_land)) if t < t_land else 0)
    ground_shadow(c, cx, gy + 8, 640, clamp(t / t_land))
    sx, sy = shake_xy(t, T.ROAR, 16 * roar + 0.01, 3)
    place(c, with_shadow('front.png', Hc, 14, 18, 80), cx + sx, cyc + sy, sc, 2.5 * math.sin(t * 2.1) * (t > t_land), 1.0, sy=sc * sq)
    dust(c, t, t_land, cx - 280, gy, 6, 2, 160, dirx=-1); dust(c, t, t_land, cx + 280, gy, 6, 3, 160, dirx=1)
    if roar > 0:                                                   # roar arcs from the mouth
        sd = SD(c); my = gy - Hc * 0.42
        for k_ in range(3):
            q = ((t - T.ROAR) * 2.4 + k_ / 3) % 1; rr = 330 + 160 * q; a = int(230 * (1 - q) * roar)
            for a0, a1 in ((150, 210), (-30, 30)):
                sd.arc((cx - rr, my - rr, cx + rr, my + rr), a0, a1, width=14, fill=RED + (a,))
    pop(c, chip('NEW DESIGN', 40, RED, WHITE, F_HEAD, 34, 14), cx, 300, t, 0.12, None, rot=-3)
    pop(c, impact_txt('DINO', 190, YEL), cx, 440, t, T.w(0, 1) - 0.06, None, d=0.36, from_scale=1.6)
    pop(c, head('MONSTER TRUCK', 118), cx, 592, t, T.w(0, 2) - 0.04, None, slide=30)
    pop(c, impact_txt('RAWR!', 210, YEL), cx + sx * 0.5, 1640 + sy * 0.5, t, T.ROAR, None, d=0.3, rot=-6, from_scale=1.9)
    pop(c, body('DINOSAUR 4WD OFF-ROAD ROLLOVER VEHICLE', 34, RED), cx, 1820, t, 1.05, None, slide=20)
    return c

def scene_push(t, t0, t1):
    """No batteries needed -- just push and go: a glove pushes the truck, lets go, it zooms off (friction motor)"""
    c = bg(t); gy, Hc = 1340, 560
    ground(c, gy)
    # car position: rolls in, pushed forward by the hand, then zooms off
    x_in = lerp(-420, 390, e_out(prog(t, t0, 0.5)))
    push = e_inout(prog(t, T.PUSH0, T.RELEASE - T.PUSH0))
    x = x_in + 170 * push
    z = prog(t, T.RELEASE + 0.02, 0.48); x += 1300 * z ** 2.2
    dist = (x - (-420))
    jit = 1.6 * math.sin(t * 140) if 0 < push < 1 else 0.0
    if z < 1:
        ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
        draw_car(c, x, gy + jit, Hc, dist, ghost=260 * clamp(z * 3) if z > 0 else 0)
    if z > 0: speed_lines(c, t, gy - 520, gy - 30, 14, 5, 1 - prog(t, t1 - 0.25, 0.25))
    dust(c, t, T.RELEASE + 0.03, x_in + 170 - car_w(Hc) * 0.30, gy - 10, 8, 4, 180, 0.7, 40)
    # glove: in from the top-left, presses on the back of the shell, pushes, lifts away
    gin = e_out(prog(t, T.HAND_IN, 0.30)); gout = e_inout(prog(t, T.RELEASE, 0.35))
    if gin > 0 and gout < 1:
        hx = x_in + 170 * push - car_w(Hc) * 0.24 - 30; hy = gy - Hc - 2
        hx += -420 * (1 - gin) - 260 * gout; hy += -560 * (1 - gin) - 380 * gout
        press = 6 * math.sin(t * 40) if 0 < push < 1 else 0
        place(c, glove(330), hx, hy + press, 1.0, -14 + 10 * gout, 1 - gout)
    # copy
    pop(c, head('NO BATTERIES', 118), DW / 2, 330, t, T.w(1, 0) - 0.04, T.HAND_IN + 0.1, slide=30)
    pop(c, head('NEEDED!', 124, YEL), DW / 2, 470, t, T.w(1, 2) - 0.06, T.HAND_IN + 0.1, slide=30)
    pop(c, no_battery(210), DW / 2, 630, t, T.w(1, 1), T.HAND_IN + 0.1, rot=-6)
    pop(c, head('JUST PUSH', 126), DW / 2, 360, t, T.PUSH0, T.RELEASE + 0.05, slide=30)
    pop(c, impact_txt('& GO!', 190, YEL), DW / 2, 540, t, T.w(1, 6) - 0.05, T.RELEASE + 0.05, d=0.32, rot=-4, from_scale=1.7)
    if t >= T.RELEASE:
        place(c, burst(700), DW / 2, 520, 0.3 + 0.7 * e_back(prog(t, T.RELEASE, 0.3), 1.6), (t * 40) % 360, 0.9 * (1 - prog(t, t1 - 0.2, 0.2)))
    pop(c, impact_txt('ZOOM!', 230, YEL), DW / 2, 520, t, T.RELEASE + 0.02, None, d=0.3, rot=-6, from_scale=1.9)
    pop(c, chip('PUSH & GO', 44, YEL, DRED), DW / 2, 1560, t, T.PUSH0 + 0.1, None, slide=30)
    pop(c, chip('INERTIAL POWER', 40, RED, WHITE), DW / 2, 1680, t, T.RELEASE + 0.1, None, slide=30)
    return c

def scene_stunt(t, t0, t1):
    """360° TUMBLING STUNT CAR -- the truck climbs a ramp, flips 360 in the air and lands"""
    c = bg(t); gy, Hc = 1420, 400
    ground(c, gy)
    rx0, rx1, rh = 300, 560, 210                                   # ramp: foot, lip, height
    sd = SD(c)
    sd.polygon([(rx0 - 10, gy + 3), (rx1, gy - rh), (rx1 + 14, gy - rh), (rx1 + 14, gy + 3)], fill=DRED + (255,))
    sd.polygon([(rx0, gy), (rx1, gy - rh + 10), (rx1, gy)], fill=YEL + (255,))
    for k in range(4):
        xa = rx0 + 40 + k * 55; ya = gy - (xa - rx0) / (rx1 - rx0) * (rh - 10)
        sd.line([(xa, ya + 12), (xa + 26, gy - 6)], width=10, fill=(255, 170, 0, 255))
    slope = math.degrees(math.atan2(rh - 10, rx1 - rx0))
    ta = t0 + 0.44                                                 # reaches the ramp foot
    if t < ta:                                                     # drive in
        u = prog(t, t0, ta - t0); x = lerp(-300, rx0 - car_w(Hc) * 0.25, u); rot, lift = 0.0, 0.0; dist = x + 300
        draw_car(c, x, gy, Hc, dist, ghost=90); ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
    elif t < T.LAUNCH:                                             # climb the ramp, nose up
        u = prog(t, ta, T.LAUNCH - ta); xc = lerp(rx0, rx1, u); yc = gy - (xc - rx0) / (rx1 - rx0) * (rh - 10)
        sl = slope * e_out(clamp(u * 3)); th = math.radians(sl); x = xc - math.sin(th) * Hc / 2; y = yc - math.cos(th) * Hc / 2
        place(c, car_side(Hc, wq(wheel_deg(600 + u * 340, Hc))), x, y, 1.0, sl)
        ground_shadow(c, xc, gy + 6, car_w(Hc) * 0.7, 0.7)
    elif t < T.LAND:                                               # airborne: 360° flip
        u = prog(t, T.LAUNCH, T.LAND - T.LAUNCH)
        x0, y0 = rx1 - math.sin(math.radians(slope)) * Hc / 2, gy - rh - Hc / 2 * math.cos(math.radians(slope))
        x1, y1 = 760, gy - Hc / 2
        x = lerp(x0, x1, u); y = lerp(y0, y1, u) - 300 * 4 * u * (1 - u)
        rot = slope - (slope + 360) * e_inout(u)
        ground_shadow(c, x, gy + 6, car_w(Hc) * (0.4 + 0.4 * u), 0.6)
        place(c, car_side(Hc, wq(wheel_deg(940 + u * 900, Hc))), x, y, 1.0, rot)
        # spinning arrows round the flip
        ring = 1 - abs(2 * u - 1) ** 3; ra = 250
        for k_ in range(2):
            a0 = (-u * 540 + k_ * 180) % 360
            sd.arc((x - ra, y - ra, x + ra, y + ra), a0, a0 + 120, width=16, fill=RED + (int(230 * ring),))
            ang = math.radians(a0 + 120); ax, ay = x + ra * math.cos(ang), y + ra * math.sin(ang)
            tang = ang + math.pi / 2; nx, ny = math.cos(ang), math.sin(ang); tx_, ty_ = math.cos(tang), math.sin(tang)
            sd.polygon([(ax + tx_ * 34, ay + ty_ * 34), (ax + nx * 26, ay + ny * 26), (ax - nx * 26, ay - ny * 26)], fill=RED + (int(230 * ring),))
    else:                                                          # land, bounce, roll on
        u = t - T.LAND; x = 760 + 80 * e_out(prog(t, T.LAND, 0.6))
        sq = 1 - 0.10 * math.exp(-u * 10) * math.cos(u * 30)
        ground_shadow(c, x, gy + 6, car_w(Hc) * 0.9)
        draw_car(c, x, gy, Hc, 1840 + (x - 760), squash=sq)
        dust(c, t, T.LAND, x - 120, gy, 7, 6, 150); dust(c, t, T.LAND, x + 120, gy, 7, 7, 150, dirx=1)
    pop(c, impact_txt('360°', 250, YEL), DW / 2, 340, t, T.w(2, 2) - 0.08, None, d=0.34, from_scale=1.7, rot=-4)
    pop(c, head('TUMBLING STUNT CAR', 96), DW / 2, 510, t, T.w(2, 3) - 0.10, None, slide=30)
    pop(c, chip('CLIMB - MULTIPLE VENUES', 36, YEL, DRED), DW / 2, 1590, t, ta, None, slide=30)
    pop(c, body('360 DEGREE FLIP, COOL STUNTS, MORE ADDICTIVE', 30, RED), DW / 2, 1700, t, T.LAND - 0.05, None, slide=20)
    return c

def jaw_angle(t):
    """head lift: quick open, short hold, snap shut -- the chomp of the real toy"""
    a = 0.0
    for t0, amp, hold in T.CHOMPS:
        up = e_back(prog(t, t0, 0.16), 1.2); down = e_in(prog(t, t0 + 0.16 + hold, 0.10))
        a = max(a, amp * up * (1 - down))
    return a

def scene_mouth(t, t0, t1):
    """DINOSAUR MOUTH CAN BE OPENED UP AND DOWN -- close-up, the shell lifts and the mouth opens wide"""
    c = bg(t); Hc = 760; gy = 1500
    p = prog(t, t0, 0.42)
    place(c, soft_burst(1100), 640, 1050, 0.95 + 0.02 * math.sin(t * 2), (t * 9) % 360, 0.26 * clamp(p * 3))
    ja = jaw_angle(t)
    im = car_side(Hc, 0, round(ja * 4) / 4, True)
    ground_shadow(c, DW / 2 + 10, gy + 8, car_w(Hc) * 0.9, clamp(p * 3))
    s = (0.82 + 0.18 * e_back(p, 1.4)) * (1 + 0.02 * (t - t0))
    cy = gy - (Hc + PAD * Hc / GEO['size'][1]) / 2 * s
    place(c, im, DW / 2 + 10 + 140 * (1 - e_out(p)), cy, s, 0, clamp(p * 3))
    if t > T.CHOMPS[0][0]:                                         # up / down arrows at the snout
        ax, ay = DW / 2 + 10 + car_w(Hc) * 0.43 * s + 40, gy - Hc * 0.62 * s
        sd = SD(c); a = int(255 * clamp((t - T.CHOMPS[0][0]) / 0.2)); bob = 10 * ja / 16
        sd.line([(ax, ay - 120 - bob), (ax, ay + 120 + bob)], width=14, fill=RED + (a,))
        sd.polygon([(ax - 34, ay - 110 - bob), (ax + 34, ay - 110 - bob), (ax, ay - 170 - bob)], fill=RED + (a,))
        sd.polygon([(ax - 34, ay + 110 + bob), (ax + 34, ay + 110 + bob), (ax, ay + 170 + bob)], fill=RED + (a,))
    pop(c, head('DINOSAUR MOUTH', 116), DW / 2, 330, t, t0 + 0.05, None, slide=30)
    pop(c, head('CAN BE OPENED UP AND DOWN', 72, YEL), DW / 2, 466, t, t0 + 0.30, None, slide=30)
    return c

def scene_colors(t, t0, t1):
    """AVAILABLE IN 4 COLORS -- blue, pink, green, yellow pop in on the words"""
    c = bg(t)
    pop(c, head('AVAILABLE IN', 92), DW / 2, 300, t, t0 + 0.10, None, slide=30)
    pop(c, impact_txt('4 COLORS', 170, YEL), DW / 2, 440, t, T.w(3, 1) - 0.06, None, d=0.34, from_scale=1.6, rot=-3)
    spots = [(290, 850, 'c_blue.png', 'BLUE', SKY), (790, 850, 'c_pink.png', 'PINK', PINK),
             (290, 1350, 'c_green.png', 'GREEN', LIME), (790, 1350, 'c_yellow.png', 'YELLOW', (255, 176, 0))]
    sd = SD(c)
    for i, (x, y, a, lbl, col) in enumerate(spots):
        q = e_back(prog(t, t0 + 0.30 + i * 0.08, 0.4), 1.5)          # colour blob behind each slot
        if q > 0:
            r = 215 * q; sd.ellipse((x - r, y - r * 0.92, x + r, y + r * 0.92), fill=col + (60,))
        tp = T.COL_POPS[i]
        if t >= tp:
            pp = prog(t, tp, 0.42)
            place(c, with_shadow(a, 380, 12, 16, 80), x, y - 10 + 6 * math.sin(t * 2.4 + i) + 160 * (1 - e_back(pp, 1.3)),
                  0.6 + 0.4 * e_back(pp, 1.5), -4 + 3 * math.sin(t * 1.7 + i), clamp(pp * 3))
            pop(c, chip(lbl, 40, col, WHITE, F_HEAD, 30, 12), x, y + 225, t, tp + 0.08, None, slide=20)
    return c

def scene_safe(t, t0, t1):
    """BIS approved, virgin polymer, safe for little hands, 3+ ages"""
    c = bg(t); p = prog(t, t0, 0.5)
    place(c, soft_burst(980), DW / 2, 700, 0.9 + 0.03 * math.sin(t * 2.5), (t * 10) % 360, 0.28 * clamp(p * 3))
    place(c, with_shadow('front.png', 640, 14, 18, 80), DW / 2, 720 + 10 * math.sin((t - t0) * 2.2) + 200 * (1 - e_back(p, 1.3)),
          (0.8 + 0.2 * e_back(p, 1.4)) * (1 + 0.01 * (t - t0)), -3 + 3 * math.sin((t - t0) * 1.6), clamp(p * 3))
    sparkles(c, t, 11, DW / 2, 720, 430, 380, n=10)
    rows = [('shield', 'BIS APPROVED'), ('drop', 'VIRGIN POLYMER'), ('hand', 'SAFE FOR LITTLE HANDS'), ('age', '3+ AGES')]
    for i, ((k, txt), tp) in enumerate(zip(rows, T.SAFE_POPS)):
        im = badge_row(k, txt, 66)
        pop(c, im, 110 + im.width / K / 2, 1190 + i * 132, t, tp - 0.04, None, slide=30)
    return c

BOX_H = 860
def scene_box(t, t0, t1):
    """12 PCS DISPLAY BOX -- the real display box drops in and lands on a shop counter"""
    c = bg(t); cx, cy = DW / 2, 1060
    pop(c, impact_txt('12 PCS', 200, YEL), DW / 2, 320, t, T.w(6, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('DISPLAY BOX', 110), DW / 2, 490, t, T.w(6, 2) - 0.08, None, slide=30)
    cp = e_out(prog(t, T.COUNTER - 0.05, 0.45))
    if cp > 0: place(c, counter_top(), DW / 2 - DW * (1 - cp), cy + BOX_H / 2 + 55)
    q = prog(t, T.BOX_LAND - 0.34, 0.34)
    if q > 0:
        if t < T.BOX_LAND: y, rot = cy - 1300 * (1 - e_in(q)), -4 * (1 - q)
        else:
            u = t - T.BOX_LAND; y = cy - 30 * math.exp(-u * 9) * abs(math.sin(u * 22)); rot = 0.8 * math.sin(u * 1.6)
        sh = shake_xy(t, T.BOX_LAND, 10, 10) if t >= T.BOX_LAND else (0, 0)
        place(c, with_shadow('box_real.png', BOX_H, 16, 20, 90), cx + sh[0], y + sh[1], 1.0 + 0.012 * max(0, t - T.BOX_LAND), rot)
    if t > T.COUNTER: sparkles(c, t, 17, cx, cy - 60, 470, 420, n=12, size=40)
    pop(c, chip('COUNTER-READY DISPLAY', 46, RED, WHITE), DW / 2, 1745, t, T.COUNTER + 0.12, None, slide=30)
    return c

def scene_carton(t, t0, t1):
    """192 PCS PER CARTON -- cartons drop and stack; a Funhoods truck delivers: PAN INDIA DELIVERY"""
    c = bg(t); shake = [0.0, 0.0]
    pop(c, impact_txt('192 PCS', 200, YEL), DW / 2, 320, t, T.w(7, 0) - 0.06, None, d=0.34, from_scale=1.7, rot=-3)
    pop(c, head('PER CARTON', 104), DW / 2, 490, t, T.w(7, 1) - 0.06, None, slide=30)
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
    pop(c, head('PAN INDIA DELIVERY', 92), DW / 2, 1735, t, T.w(7, 6) - 0.08, None, slide=30)
    return shift(c, shake[0], shake[1])

def scene_bulk(t, t0, t1):
    """FOR DISTRIBUTORS & WHOLESALERS -- BULK ORDERS ONLY -- ORDER TODAY!"""
    c = bg(t)
    pop(c, body('FOR', 46, RED), DW / 2, 290, t, t0 + 0.06, None, slide=20)
    pop(c, head('DISTRIBUTORS', 124), DW / 2, 392, t, T.w(8, 0) - 0.06, None, slide=30)
    pop(c, head('& WHOLESALERS', 112, YEL), DW / 2, 528, t, T.w(8, 2) - 0.06, None, slide=30)
    gy = 1090; ground(c, gy, 60, 1020)
    for i, a in enumerate(BOX_COLS[::-1]):
        tp = t0 + 0.30 + i * 0.12; pp = prog(t, tp, 0.42)
        if pp <= 0: continue
        x = 168 + i * 248
        ground_shadow(c, x, gy + 4, 240, clamp(pp * 3))
        place(c, with_shadow(a, 270, 10, 12, 70), x, gy - 130 + 6 * math.sin(t * 2.6 + i) - 220 * (1 - e_back(pp, 1.3)),
              1.0, -3 + 3 * math.sin(t * 2 + i), clamp(pp * 3))
    pop(c, chip('BULK ORDERS ONLY', 60, YEL, DRED, F_HEAD, 44, 20), DW / 2, 1250, t, T.w(8, 5) - 0.06, None, slide=30)
    to = T.w(8, 7) - 0.10
    if t >= to:
        place(c, burst(760), DW / 2, 1580, 0.25 + 0.55 * e_back(prog(t, to, 0.3), 1.6), (t * 40) % 360, 0.95 * (1 - prog(t, t1 - 0.25, 0.25)))
    pop(c, impact_txt('ORDER TODAY!', 150, YEL), DW / 2, 1580, t, to, None, d=0.3, rot=-5, from_scale=1.9)
    return c

def scene_end(t):
    t0 = T.S_END
    c = cream_bg().copy(); sd = SD(c)
    p = e_out(prog(t, t0, 0.5))
    sd.polygon([(0, 0), (DW, 0), (DW, 250 * p + 60), (DW / 2, 330 * p + 60), (0, 250 * p + 60)], fill=RED + (255,))
    sd.polygon([(0, 250 * p + 60), (DW / 2, 330 * p + 60), (DW, 250 * p + 60), (DW, 250 * p + 76), (DW / 2, 346 * p + 60), (0, 250 * p + 76)], fill=ORANGE + (255,))
    sd.polygon([(0, DH), (DW, DH), (DW, DH - 200 * p), (0, DH - 260 * p)], fill=RED + (255,))
    lg = asset('logo_rgba.png')
    tl = T.w(9, 0) - 0.22
    place(c, lg, DW / 2, 520, (800 * K / lg.width) * (0.4 + 0.6 * e_back(prog(t, tl, 0.42), 1.6)), 0, clamp((t - tl) / 0.1))
    for i, (a, x, h_, dl, rot) in enumerate([('c_blue.png', 205, 300, 0.25, 6), ('c_pink.png', 875, 300, 0.35, -6)]):
        pb = prog(t, t0 + dl, 0.5); side = -1 if x < DW / 2 else 1
        place(c, with_shadow(a, h_, 10, 12, 70), x + side * 500 * (1 - e_out(pb)), 1035 + 5 * math.sin(t * 2.2 + i), 1.0, rot, clamp(pb * 3))
    pf = prog(t, t0 + 0.15, 0.5)
    place(c, with_shadow('front.png', 460, 12, 16, 80), DW / 2, 1000 + 260 * (1 - e_back(pf, 1.3)) + 5 * math.sin(t * 2), 1.0, 0, clamp(pf * 3))
    pop(c, body('DINO CAR  •  MT-03  •  3+ AGES', 38, RED), DW / 2, 1300, t, t0 + 0.45, None, slide=20)
    pop(c, chip('BULK ORDERS ONLY', 52, RED, WHITE, F_HEAD, 40, 18), DW / 2, 1415, t, t0 + 0.6, None, slide=30)
    ca, cb_ = chip('192 PCS / CARTON', 34, YEL, DRED, F_BODY, 24, 14), chip('PAN INDIA DELIVERY', 34, YEL, DRED, F_BODY, 24, 14)
    pop(c, ca, DW / 2 - 6 - ca.width / K / 2, 1530, t, t0 + 0.8, None, slide=20)
    pop(c, cb_, DW / 2 + 6 + cb_.width / K / 2, 1530, t, t0 + 0.95, None, slide=20)
    pop(c, body('For Distributors  &  Wholesalers', 36, INK), DW / 2, 1630, t, t0 + 1.1, None, slide=20)
    pop(c, body('SPECIFICATIONS COLOURS AND CONTENTS MAY VARY FROM ILLUSTRATIONS', 17, WHITE), DW / 2, DH - 62, t, t0 + 1.2, None)
    return c

def render(t):
    if t < T.S_PUSH: c = scene_hero(t)
    elif t < T.S_STUNT: c = scene_push(t, T.S_PUSH, T.S_STUNT)
    elif t < T.S_MOUTH: c = scene_stunt(t, T.S_STUNT, T.S_MOUTH)
    elif t < T.S_COLORS: c = scene_mouth(t, T.S_MOUTH, T.S_COLORS)
    elif t < T.S_SAFE: c = scene_colors(t, T.S_COLORS, T.S_SAFE)
    elif t < T.S_BOX: c = scene_safe(t, T.S_SAFE, T.S_BOX)
    elif t < T.S_CARTON: c = scene_box(t, T.S_BOX, T.S_CARTON)
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
