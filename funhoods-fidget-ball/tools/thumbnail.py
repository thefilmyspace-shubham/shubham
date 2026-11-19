# Reel cover / thumbnail for the FIDGET BALL video, in the format of the earlier Funhoods reels (Press & Go, Dino Car, ...):
# light sunburst + halftone background, Funhoods logo sticker top-left, a small red chip, the big yellow title with a red
# outline, a red subtitle, the product on a soft burst, and chips at the bottom. The drawing helpers are the Press & Go
# reel's own (funhoods-press-go-scooter/render.py), so the look matches exactly.
# The 4 balls are cut out of the client's video (line-up at 31.3 s, no hands) with rembg (isnet-general-use): assets/ball_*.png.
# Everything that matters sits inside the 3:4 centre crop (y 240-1680 of 1920) that Instagram shows on the profile grid.
# usage: python3 tools/thumbnail.py      -> exports/Funhoods_Fidget_Ball_Thumbnail.jpg (1080x1920) + _grid_preview.jpg
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
    rgb = im.convert('RGB').filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2)); rgb.putalpha(im.getchannel('A'))
    return R.drop_shadow(rgb, blur=16, dy=22, alpha=120)

def make():
    c = R.sunburst_light(0).convert('RGBA')
    R.place(c, R.soft_burst(1120), 540, 1060, 1.0, 8, 0.34)
    # 2 x 2, as in the video's line-up: back row a little smaller and higher, front row overlapping it
    for name, x, y, sz, rot, g in [('batman', 315, 905, 330, -8, 1.0), ('super', 765, 905, 330, 8, 0.6),
                                   ('spider', 345, 1240, 380, -5, 1.0), ('captain', 735, 1240, 380, 5, 1.0)]:
        R.place(c, ball(name, sz, g), x, y, 1.0, rot)
    R.place(c, R.logo_sticker(120), 110, 302)            # inside the grid crop, so the brand shows on the profile grid too
    R.place(c, R.chip('NEW LAUNCH', 38, R.RED, R.WHITE, R.F_HEAD, 30, 12), 540, 302)
    R.place(c, R.impact_txt('FIDGET BALL', 190, R.YEL), 540, 468, 1.0, 3)
    R.place(c, R.head('AVENGERS SERIES SPINNER', 70), 540, 622)
    R.place(c, R.chip('4 DESIGNS  •  288 PCS / CARTON', 46, R.RED, R.WHITE, R.F_HEAD, 38, 16), 540, 1520)
    R.place(c, R.chip('FOR DISTRIBUTORS & WHOLESALERS', 36, R.YEL, R.DRED, R.F_BODY, 30, 14), 540, 1612)
    return c.convert('RGB').resize((1080, 1920), Image.LANCZOS)

if __name__ == '__main__':
    out = os.path.join(ROOT, 'exports'); os.makedirs(out, exist_ok=True)
    im = make(); im.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail.jpg'), quality=95)
    g = im.crop((0, 240, 1080, 1680)); g.save(os.path.join(out, 'Funhoods_Fidget_Ball_Thumbnail_grid_preview.jpg'), quality=92)
    print('saved', im.size, g.size)
