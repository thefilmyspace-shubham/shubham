# Catalogue crops + transparent logo + product cut-outs.
# Run from the project root after placing the inputs in src/ (catalog.webp, logo.png) and
# upscaling the crops: python3 tools/prep_assets.py crops && OUTW=0 python3 tools/sr.py models/realesr-general-x4v3.pth cat_in cat_sr && python3 tools/prep_assets.py cutouts
import sys, os
import numpy as np
from collections import deque
from PIL import Image, ImageFilter

# catalogue tiles (941x1672 source), label text trimmed off
CROPS = {'pack': (626, 1286, 924, 1630), 'side': (0, 0, 470, 318), 'nozzle': (0, 840, 232, 1036),
         'badge': (473, 840, 706, 1036), 'grip': (0, 1062, 232, 1246), 'darts': (0, 1284, 302, 1614),
         'withdarts': (305, 1284, 604, 1612)}

def label_components(mask):
    H, W = mask.shape; lab = np.zeros((H, W), np.int32); comps = []; cur = 0
    for y0 in range(H):
        for x0 in np.where(mask[y0] & (lab[y0] == 0))[0]:
            if lab[y0, x0]: continue
            cur += 1; q = deque([(y0, x0)]); lab[y0, x0] = cur; pts = []; border = False
            while q:
                y, x = q.popleft(); pts.append((y, x))
                if y in (0, H - 1) or x in (0, W - 1): border = True
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = cur; q.append((yy, xx))
            comps.append((pts, border))
    return comps

def logo():
    im = np.asarray(Image.open('src/logo.png').convert('RGB')).astype(np.float32) / 255
    white = im.min(2) > 0.86
    transp = np.zeros(white.shape, bool)
    for pts, border in label_components(white):
        ys, xs = zip(*pts)
        if border or np.mean(ys) > 880: transp[list(ys), list(xs)] = True   # outside + tagline counters
    near = np.asarray(Image.fromarray((transp * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5))) > 0
    a = np.ones(white.shape, np.float32); a[transp] = 0
    edge = near & ~transp; a[edge] = np.clip((1 - im.min(2)[edge]) / 0.45, 0, 1)
    rgb = np.where(a[..., None] > 0.01, (im - (1 - a[..., None])) / np.maximum(a[..., None], 1e-3), 0)
    out = np.dstack([np.clip(rgb, 0, 1), a])
    Image.fromarray((out * 255 + .5).astype(np.uint8), 'RGBA').crop((0, 460, 1080, 990)).save('assets/logo_rgba.png')

def cutout(src, dst, thr=0.30):
    p = np.asarray(Image.open(src).convert('RGB')).astype(np.float32) / 255
    mx, mn = p.max(2), p.min(2); s = (mx - mn) / np.maximum(mx, 1e-3)
    m = np.asarray(Image.fromarray((((s > thr) & (mx > 0.18)) * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(5))) > 127
    for pts, border in label_components(~m):        # fill small enclosed holes (badge lettering)
        if not border and len(pts) < 6000:
            ys, xs = zip(*pts); m[list(ys), list(xs)] = True
    a = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    o = Image.open(src).convert('RGBA'); o.putalpha(a); o.crop(a.getbbox()).save(dst)

if __name__ == '__main__':
    os.makedirs('assets', exist_ok=True)
    if sys.argv[1] == 'crops':
        os.makedirs('cat_in', exist_ok=True)
        im = Image.open('src/catalog.webp').convert('RGB')
        for k, bx in CROPS.items(): im.crop(bx).save(f'cat_in/{k}.png')
        # original Funhoods packet photo (1080x1440, 4 darts): used as-is (already sharp) + dart close-up to upscale
        os.makedirs('cat_sr', exist_ok=True)
        pk = Image.open('src/pack_original.png').convert('RGB')
        pk.crop((136, 256, 968, 1288)).save('cat_sr/pack4.png')       # blister card only
        pk.crop((0, 232, 1080, 1440)).save('cat_sr/pack_styled.png')   # styled shot below its own logo
        pk.crop((206, 922, 522, 1200)).save('cat_in/darts4.png')       # 4 darts close-up
    else:
        logo()
        cutout('cat_sr/side.png', 'assets/gun_side.png')
        cutout('cat_sr/withdarts.png', 'assets/gun_withdarts.png')
