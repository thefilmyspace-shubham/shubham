# Back-of-head pose for the press-and-turn rig. The client's photos have no shot of the head from behind, so it is made from
# the front head's silhouette: the yellow of the head (eyes, lashes, inner ears and muzzle left out) is spread over the whole
# shape (normalised convolution: blur(img*keep) / blur(keep)), then shaded like moulded plastic -- darker towards the rim
# and under the head, a soft highlight top-left -- so it reads as the plain back of the head with its two ears.
# -> assets/rig_head_back.png (same size and anchor as rig_head_front.png)
import os
import numpy as np, cv2
from PIL import Image
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
im = Image.open(A('rig_head_front.png')).convert('RGBA')
v = np.asarray(im).astype(np.float32); a = v[..., 3]; rgb = v[..., :3]
hsv = np.asarray(im.convert('RGB').convert('HSV')).astype(np.float32)
hue, sat, val = hsv[..., 0] * 360 / 255, hsv[..., 1], hsv[..., 2]
feat = (a > 10) & ((val < 150) | (hue < 40) | (hue > 70) | (sat < 90))       # eyes, lashes, inner ears, glints
feat = cv2.dilate(feat.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
yy, xx = np.mgrid[0:im.height, 0:im.width]
muzzle = ((xx - 685) / 290) ** 2 + ((yy - 700) / 175) ** 2 < 1
keep = ((a > 250) & ~feat & ~muzzle & (val > 200)).astype(np.float32)          # clean, lit yellow only
base = np.zeros_like(rgb) + rgb[keep > 0].mean(0); wsum = np.zeros(a.shape, np.float32)
for sig in (70, 160, 360):                                      # finest scale with enough clean yellow around it wins
    den = cv2.GaussianBlur(keep, (0, 0), sig); est = cv2.GaussianBlur(rgb * keep[..., None], (0, 0), sig) / np.maximum(den, 1e-6)[..., None]
    w = np.clip((den - 0.05) / 0.15, 0, 1) * (1 - wsum); base = base * (1 - w[..., None]) + est * w[..., None] if sig == 70 else base + (est - base) * w[..., None]
    wsum = wsum + w
inside = (a > 128).astype(np.uint8)
dist = cv2.distanceTransform(inside, cv2.DIST_L2, 5)
shade = 0.80 + 0.20 * np.clip(dist / 90, 0, 1)                                  # rounder: darker towards the outline
shade *= 1 - 0.16 * np.clip((yy - 740) / 120, 0, 1)                             # shadow under the head, on the neck
hl = np.exp(-(((xx - 560) / 230) ** 2 + ((yy - 250) / 150) ** 2))               # soft highlight, top-left of the dome
for cx, cy in ((240, 190), (1140, 190)): hl += 0.6 * np.exp(-(((xx - cx) / 90) ** 2 + ((yy - cy) / 70) ** 2))   # on the ears
res = base * shade[..., None]
res = res + (255 - res) * (0.35 * np.clip(hl, 0, 1))[..., None]
res = np.concatenate([np.clip(res, 0, 255), a[..., None]], -1).astype(np.uint8)
Image.fromarray(res, 'RGBA').save(A('rig_head_back.png')); print('rig_head_back.png', im.size)
