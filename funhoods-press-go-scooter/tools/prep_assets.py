# Product + pack assets for the Press & Go Scooter (PL-001), from the client's phone photos (Drive, 5 Nov, 2252x4000).
# assets/src/<photo>.png = BiRefNet cut-outs (largest part kept). Light grade on every cut-out (levels on the object's own
# pixels, +6 % contrast, +12 % saturation, light clarity). On the pack's back label the MRP line and the customer-care
# phone number are painted out (B2B reel: no price, no phone number).
import os
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

NAMES = {'130515': 'mouse_blue_front', '130531': 'mouse_blue_side', '130537': 'mouse_blue_back34', '130543': 'mouse_blue_back',
         '130607': 'mouse_red_front', '130653': 'duck_blue_front', '130701': 'duck_blue_front2',
         '130733': 'duck_orange_front', '130742': 'duck_orange_front2', '130337': 'pack_front', '130341': 'pack_front2',
         '130353': 'pack_back'}
for k, n in NAMES.items():
    im = grade(Image.open(A('src', k + '.png')).convert('RGBA'))
    if n == 'pack_back':                                          # hide MRP + phone number on the label (inpainted)
        rgb = np.asarray(im.convert('RGB')).copy(); mk = np.zeros(rgb.shape[:2], np.uint8)
        for y0, y1, x0, x1 in [(388, 452, 235, 1080), (870, 942, 310, 1440)]: mk[y0:y1, x0:x1] = 255
        rgb = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mk, 9, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
        out = Image.fromarray(rgb).convert('RGBA'); out.putalpha(im.getchannel('A')); im = out
    im.save(A(n + '.png')); print(n, im.size)
