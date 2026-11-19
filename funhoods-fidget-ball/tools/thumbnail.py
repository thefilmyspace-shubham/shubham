# Reel cover / thumbnail for the FIDGET BALL video, in the format of the earlier Funhoods reels (Press & Go, Dino Car,
# Musical Stick ...): a sunburst + halftone background, a small chip, the big yellow title with an outline, a subtitle,
# the product on a burst, and chips at the bottom. The drawing helpers are the Press & Go reel's own
# (funhoods-press-go-scooter/render.py), so the type and chips match.
# v2 (client: "still dull"): Funhoods red background (as the Musical Stick opener), a bright yellow burst + glow behind
# the balls (no soft glow: it went muddy), punchier balls with a white sticker outline, white spin arcs. No logo sticker (client: no watermark).
# The 4 balls come from the client's video (line-up at 31.75 s, the last clean frame before the white flash, no hands):
# each crop upscaled 4x with Real-ESRGAN (general x4v3), then cut out with rembg (isnet-general-use); the white ball's
# lower edge, lost against the white cloth, is filled with its convex hull. -> assets/ball_*.png (1200 px wide).
# usage: python3 tools/thumbnail.py      -> exports/Funhoods_Fidget_Ball_Thumbnail_4K.png/.jpg (2160x3840) + _1080x1920.jpg
import os, sys, math
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, '..', 'funhoods-press-go-scooter'))
import render as R                                    # K = 2: design space 1080x1920, drawn at 2160x3840
K = R.K
YEL, DRED, DEEP, WHITE = (255, 212, 0), R.DRED, (90, 0, 8), (255, 255, 255)
CY = 1100                                              # centre of the ball cluster (design px)

def ball(name, size, gamma=1.0):
    """cut-out with levels on its own pixels, punchy colour (+30 % saturation, +12 % contrast, clarity), a white sticker
    outline and a strong drop shadow, so it pops off the background; size in design px"""
    im = Image.open(os.path.join(ROOT, 'assets', 'ball_%s.png' % name)).convert('RGBA')
    a = np.asarray(im).astype(np.float32); m = a[..., 3] > 200
    hi = np.percentile(a[..., :3][m].max(1), 99.0); lo = np.percentile(a[..., :3][m].min(1), 0.5)
    rgb = np.clip((a[..., :3] - lo) / max(1.0, hi - lo), 0, 1) ** gamma * 250.0          # gamma < 1 lifts the shaded white ball
    im = Image.fromarray(np.dstack([rgb, a[..., 3]]).astype(np.uint8), 'RGBA')
    s = size * K / im.width
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    al = im.getchannel('A'); rgb = im.convert('RGB')
    rgb = ImageEnhance.Color(rgb).enhance(1.30); rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=24, percent=35, threshold=0))       # clarity
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=2, percent=45, threshold=2)); rgb.putalpha(al)
    o = 9 * K                                                                           # white sticker outline
    out = Image.new('RGBA', (rgb.width + 2 * o, rgb.height + 2 * o), (0, 0, 0, 0))
    ring = Image.new('L', out.size, 0); ring.paste(al, (o, o))
    ring = ring.filter(ImageFilter.MaxFilter(2 * o + 1)).filter(ImageFilter.GaussianBlur(1.5))
    out.paste(Image.new('RGBA', out.size, WHITE + (255,)), (0, 0), ring); out.alpha_composite(rgb, (o, o))
    return R.drop_shadow(out, blur=22, dy=30, alpha=170)

def red_bg():
    """Funhoods red with darker-red sunburst rays, a bright middle, deep edges and faint halftone"""
    S = 4600; n = 28; im = Image.new('RGB', (S, S), (230, 32, 40)); d = ImageDraw.Draw(im); c = S // 2
    for i in range(0, n, 2):
        a0, a1 = math.radians(i * 360 / n), math.radians((i + 1) * 360 / n)
        d.polygon([(c, c), (c + 2 * S * math.cos(a0), c + 2 * S * math.sin(a0)), (c + 2 * S * math.cos(a1), c + 2 * S * math.sin(a1))], fill=(206, 18, 28))
    cy = CY * K; im = im.crop((c - R.W // 2, c - cy, c + R.W // 2, c - cy + R.H))
    arr = np.asarray(im).astype(np.float32)
    yy, xx = np.mgrid[0:R.H, 0:R.W]; r = np.sqrt(((xx - R.W / 2) / R.W) ** 2 + ((yy - cy) / R.H) ** 2)
    arr *= np.clip(1.06 - 0.55 * r, 0.78, 1.06)[..., None]                               # gentle vignette, stays bright red
    ht = np.asarray(R.halftone()).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.10 * ht) + np.array((255, 90, 60), np.float32) * 0.10 * ht
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')

def glow(c, cx, cy, r, col, alpha):
    g = Image.new('L', (int(2 * r * K), int(2 * r * K)), 0)
    ImageDraw.Draw(g).ellipse((0, 0, g.width, g.height), fill=int(255 * alpha)); g = g.filter(ImageFilter.GaussianBlur(r * K / 3))
    lay = Image.new('RGBA', g.size, col + (255,)); lay.putalpha(g); R.place(c, lay, cx, cy)

def spin_arcs(c, cx, cy, rx, ry):
    """white motion arcs round the cluster: the balls spin"""
    lay = Image.new('RGBA', (R.W, R.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for a0, a1, w, k in [(198, 252, 16, 1.00), (208, 242, 9, 1.09), (18, 72, 16, 1.00), (28, 62, 9, 1.09)]:
        d.arc(((cx - rx * k) * K, (cy - ry * k) * K, (cx + rx * k) * K, (cy + ry * k) * K), a0, a1, fill=WHITE + (235,), width=int(w * K))
    c.alpha_composite(lay)

def sparkle(c, x, y, s):
    """4-point white sparkle"""
    S = int(s * K); im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); h = S / 2; t = S * 0.11
    d.polygon([(h, 0), (h + t, h - t), (S, h), (h + t, h + t), (h, S), (h - t, h + t), (0, h), (h - t, h - t)], fill=WHITE + (255,))
    R.place(c, im, x, y)

def make():
    """9:16 cover at 2160x3840"""
    c = red_bg()
    R.place(c, R.burst(1420, 26, (255, 150, 0), (255, 150, 0), (255, 110, 0)), 540, CY, 1.0, 0)      # orange outer burst
    R.place(c, R.burst(1260, 22, YEL, (255, 250, 214), (255, 196, 0)), 540, CY, 1.0, 6)               # yellow burst, pale centre
    spin_arcs(c, 540, CY, 520, 470)
    # 2 x 2, as in the video's line-up: back row a little smaller and higher, front row overlapping it
    for name, x, y, sz, rot, g in [('batman', 310, CY - 180, 380, -8, 1.0), ('super', 770, CY - 180, 380, 8, 0.55),
                                   ('spider', 335, CY + 195, 440, -5, 1.0), ('captain', 745, CY + 195, 440, 5, 1.0)]:
        R.place(c, ball(name, sz, g), x, y, 1.0, rot)
    for x, y, s in [(120, 760, 64), (960, 1470, 72), (950, 690, 44), (150, 1480, 44)]:
        sparkle(c, x, y, s)
    R.place(c, R.chip('NEW LAUNCH', 44, YEL, DRED, R.F_HEAD, 34, 14), 540, 285)
    R.place(c, R.text_img('FIDGET BALL', R.F_IMPACT, 205, YEL, 7, DRED, 16, DEEP), 540, 448, 1.0, 3)
    R.place(c, R.text_img('AVENGERS SERIES SPINNER', R.F_HEAD, 76, WHITE, 0, DRED, 5, DEEP), 540, 618)
    R.place(c, R.chip('4 DESIGNS  •  288 PCS / CARTON', 52, WHITE, R.RED, R.F_HEAD, 42, 18), 540, 1625)
    R.place(c, R.chip('FOR DISTRIBUTORS & WHOLESALERS', 41, YEL, DRED, R.F_BODY, 34, 16), 540, 1728)
    return c.convert('RGB')

if __name__ == '__main__':
    out = os.path.join(ROOT, 'exports'); os.makedirs(out, exist_ok=True)
    im = make()                                                         # 2160x3840 (9:16)
    im.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_4K.png'), optimize=True)
    im.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_4K.jpg'), quality=97, subsampling=0)
    im.resize((1080, 1920), Image.LANCZOS).save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_1080x1920.jpg'), quality=97, subsampling=0)
    print('saved', im.size)
