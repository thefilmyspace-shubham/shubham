# Product + packaging assets for the Racing Inertia Car, from the client's phone photos (Drive, 1 Nov, 4000x2252).
# assets/src/<photo>.png = BiRefNet cut-outs (largest part kept). This script:
#   - grades every cut-out (photos were shot indoors, a little dim and warm): per-channel levels on the object's own
#     pixels (0.5 / 99.5 %), +6 % contrast, +12 % saturation, light unsharp mask
#   - straightens the flat box panels (4-corner perspective warp) so they read as clean packaging art
import os, sys
import numpy as np, cv2
from PIL import Image, ImageEnhance, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)

def grade(im):
    a = np.asarray(im.getchannel('A')); rgb = np.asarray(im.convert('RGB')).astype(np.float32)
    m = a > 200
    for c in range(3):
        lo, hi = np.percentile(rgb[..., c][m], [0.5, 99.5])
        rgb[..., c] = np.clip((rgb[..., c] - lo) / max(1, hi - lo) * 255, 0, 255) * 0.85 + rgb[..., c] * 0.15
    out = Image.fromarray(rgb.astype(np.uint8))
    out = ImageEnhance.Contrast(out).enhance(1.06); out = ImageEnhance.Color(out).enhance(1.12)
    out = out.filter(ImageFilter.UnsharpMask(radius=3, percent=45, threshold=2)).convert('RGBA'); out.putalpha(Image.fromarray(a))
    return out

def flatten(im, rotate=0):
    """perspective-correct a near-frontal box face: largest contour -> 4 corners -> rectangle"""
    a = np.asarray(im.getchannel('A'))
    cs, _ = cv2.findContours((a > 128).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    c = max(cs, key=cv2.contourArea); peri = cv2.arcLength(c, True)
    for eps in np.linspace(0.01, 0.08, 30):
        q = cv2.approxPolyDP(c, eps * peri, True)
        if len(q) == 4: break
    if len(q) != 4: q = cv2.boxPoints(cv2.minAreaRect(c))
    q = q.reshape(4, 2).astype(np.float32)
    s, d = q.sum(1), np.diff(q, axis=1).ravel()
    tl, br, tr, bl = q[np.argmin(s)], q[np.argmax(s)], q[np.argmin(d)], q[np.argmax(d)]
    w = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl))); h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
    M = cv2.getPerspectiveTransform(np.float32([tl, tr, br, bl]), np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
    rgba = cv2.warpPerspective(np.asarray(im), M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    out = Image.fromarray(rgba); out.putalpha(255)
    out = out.crop((6, 6, w - 6, h - 6))                       # trim the soft cut-out edge
    return out.rotate(rotate, expand=True) if rotate else out

PRODUCT = {'120711': 'car_front', '120757': 'car_side', '120750': 'car_side_r', '120801': 'car_back', '120725': 'car_back34',
           '120720': 'car_q34', '120737': 'car_top', '120804': 'car_wheel_r', '120806': 'car_wheel_f'}
BOX = {'120421': ('box_q34', None), '120433': ('box_back', 0), '120428': ('box_end_l', 0), '120438': ('box_end_r', 0),
       '120446': ('box_top', 0), '120459': ('box_bottom', 270)}
for k, n in PRODUCT.items():
    grade(Image.open(A('src', k + '.png')).convert('RGBA')).save(A(n + '.png')); print(n)
for k, (n, rot) in BOX.items():
    im = grade(Image.open(A('src', k + '.png')).convert('RGBA'))
    im = im if rot is None else flatten(im, rot)
    if n in ('box_end_l', 'box_end_r'): im = im.crop((0, 0, im.width, int(im.height * 0.95)))   # drop the bottom flap edge
    im.save(A(n + '.png')); print(n, im.size)
