# Assets from the client's new infographic (assets/src_infographic/funhoods_press_go_infographic.webp, 1199x1312, sent in
# chat 6 Nov): the NEW transparent packaging and the mouse in its 4 colours (blue, red, sky blue, orange).
# Each view was cropped, upscaled 4x (Real-ESRGAN general x4v3) and cut out with BiRefNet (assets/src_infographic/*_cut.png).
# The cut-out keeps the header card and the toy but drops the clear bag, so the bag is rebuilt here as a clear film:
# its outline (traced on the upscaled photo), a faint tint, a thin edge, and the plastic's own glare and crease lines
# taken from the photo (bright / dark detail against the smoothed backdrop seen through it).
# -> assets/pack_new.png, assets/c4_blue.png, c4_red.png, c4_skyblue.png, c4_orange.png, mouse_orange_hero.png
import os
import numpy as np, cv2
from PIL import Image, ImageDraw
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
SRC = lambda n: A('src_infographic', n)

sr = Image.open(SRC('ig_pack_sr.png')).convert('RGB'); W, H = sr.size                    # 1640 x 1980
cut = Image.open(SRC('ig_pack_cut.png')).convert('RGBA')
# the cut-out was cropped to its bbox: find its offset in the upscaled photo
res = cv2.matchTemplate(np.asarray(sr), np.asarray(cut.convert('RGB')), cv2.TM_SQDIFF, mask=np.repeat(np.asarray(cut.getchannel('A'))[..., None] > 128, 3, -1).astype(np.uint8))
oy, ox = np.unravel_index(np.argmin(res), res.shape)
solid = np.zeros((H, W), np.float32); solid[oy:oy + cut.height, ox:ox + cut.width] = np.asarray(cut.getchannel('A')) / 255
bag = Image.new('L', (W, H), 0)                                                         # pouch outline, below the header card
ImageDraw.Draw(bag).polygon([(95, 590), (1525, 590), (1518, 1100), (1502, 1870), (1450, 1902), (165, 1902), (112, 1870), (100, 1100)], fill=255)
bag = np.asarray(bag).astype(np.float32) / 255
bag = cv2.GaussianBlur(bag, (0, 0), 2)
rgb = np.asarray(sr).astype(np.float32); L = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
Lb = cv2.GaussianBlur(L, (0, 0), 40)
hi = np.clip((L - Lb - 3) / 22, 0, 1); lo = np.clip((Lb - L - 3) / 22, 0, 1)
dist = cv2.distanceTransform((bag > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
edge = np.clip(1 - dist / 12, 0, 1) * (bag > 0.05)
film_a = np.clip(0.10 + 0.70 * hi + 0.40 * lo + 0.45 * edge, 0, 0.9) * bag
tint = np.array([226, 232, 240], np.float32); grey = np.array([150, 160, 172], np.float32)
film = tint * (1 - hi[..., None]) + 255 * hi[..., None]
film = film * (1 - (0.6 * lo + 0.35 * edge)[..., None]) + grey * (0.6 * lo + 0.35 * edge)[..., None]
out_rgb = rgb * solid[..., None] + film * (1 - solid[..., None])
out_a = np.clip(solid + (1 - solid) * film_a, 0, 1)
out = Image.fromarray(np.concatenate([np.clip(out_rgb, 0, 255), out_a[..., None] * 255], -1).astype(np.uint8), 'RGBA')
out = out.crop(out.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox()); out.save(A('pack_new.png')); print('pack_new.png', out.size, 'offset', ox, oy)

for k in ('blue', 'red', 'skyblue', 'orange'):
    Image.open(SRC('ig_%s_cut.png' % k)).save(A('c4_%s.png' % k))
Image.open(SRC('ig_hero_cut.png')).save(A('mouse_orange_hero.png')); print('c4_*.png, mouse_orange_hero.png')
