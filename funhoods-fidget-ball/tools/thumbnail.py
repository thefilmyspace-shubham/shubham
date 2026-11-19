# Reel cover / thumbnail for the FIDGET BALL video, in the format of the earlier Funhoods reels (Press & Go, Dino Car, ...):
# light sunburst + halftone background, Funhoods logo sticker top-left, a small red chip, the big yellow title with a red
# outline, a red subtitle, the product on a soft burst, and chips at the bottom. The drawing helpers are the Press & Go
# reel's own (funhoods-press-go-scooter/render.py), so the look matches exactly.
# The 4 balls come from the client's video (line-up at 31.75 s, the last clean frame before the white flash, no hands):
# each crop upscaled 4x with Real-ESRGAN (general x4v3), then cut out with rembg (isnet-general-use); the white ball's
# lower edge, lost against the white cloth, is filled with its convex hull. -> assets/ball_*.png (1200 px wide).
# usage: python3 tools/thumbnail.py      -> exports/Funhoods_Fidget_Ball_Thumbnail_4K.png/.jpg (2160x3840) + _1080x1920.jpg
import os, sys
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, '..', 'funhoods-press-go-scooter'))
import render as R                                    # K = 2: design space 1080x1920, drawn at 2160x3840

def ball(name, size, gamma=1.0):
    """cut-out, levels on the ball's own pixels (the white one reads grey in the shade), +10 % saturation, sized in design px"""
    im = Image.open(os.path.join(ROOT, 'assets', 'ball_%s.png' % name)).convert('RGBA')
    a = np.asarray(im).astype(np.float32); m = a[..., 3] > 200
    hi = np.percentile(a[..., :3][m].max(1), 99.0); lo = np.percentile(a[..., :3][m].min(1), 0.5)
    rgb = np.clip((a[..., :3] - lo) / max(1.0, hi - lo), 0, 1) ** gamma * 245.0          # gamma < 1 lifts the shaded white ball
    im = Image.fromarray(np.dstack([rgb, a[..., 3]]).astype(np.uint8), 'RGBA')
    im = ImageEnhance.Color(im).enhance(1.10)
    s = size * R.K / im.width
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=2, percent=35, threshold=2)); rgb.putalpha(im.getchannel('A'))
    return R.drop_shadow(rgb, blur=16, dy=22, alpha=120)

def make():
    """9:16 cover at 2160x3840: no logo sticker / watermark (client), the content spread over the full height"""
    c = R.sunburst_light(0).convert('RGBA')
    R.place(c, R.soft_burst(1180), 540, 1090, 1.0, 8, 0.34)
    # 2 x 2, as in the video's line-up: back row a little smaller and higher, front row overlapping it
    for name, x, y, sz, rot, g in [('batman', 305, 915, 370, -8, 1.0), ('super', 775, 915, 370, 8, 0.7),
                                   ('spider', 335, 1290, 430, -5, 1.0), ('captain', 745, 1290, 430, 5, 1.0)]:
        R.place(c, ball(name, sz, g), x, y, 1.0, rot)
    R.place(c, R.chip('NEW LAUNCH', 42, R.RED, R.WHITE, R.F_HEAD, 32, 13), 540, 290)
    R.place(c, R.impact_txt('FIDGET BALL', 200, R.YEL), 540, 450, 1.0, 3)
    R.place(c, R.head('AVENGERS SERIES SPINNER', 74), 540, 615)
    R.place(c, R.chip('4 DESIGNS  •  288 PCS / CARTON', 50, R.RED, R.WHITE, R.F_HEAD, 40, 17), 540, 1615)
    R.place(c, R.chip('FOR DISTRIBUTORS & WHOLESALERS', 40, R.YEL, R.DRED, R.F_BODY, 32, 15), 540, 1715)
    return c.convert('RGB')

if __name__ == '__main__':
    out = os.path.join(ROOT, 'exports'); os.makedirs(out, exist_ok=True)
    im = make()                                                         # 2160x3840 (9:16)
    im.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_4K.png'), optimize=True)
    im.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_4K.jpg'), quality=97, subsampling=0)
    im.resize((1080, 1920), Image.LANCZOS).save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_1080x1920.jpg'), quality=97, subsampling=0)
    print('saved', im.size)
