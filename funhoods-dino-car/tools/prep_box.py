# The real 12 pcs display box, cut out of one 4K frame of the client's reference video (t = 5.62 s,
# assets/src/box_frame_5.62.png) -- used as a still only. The blue car in the foreground hides the lip's left end:
# that strip is patched, cut back to the lip's real bottom edge and inpainted from the surrounding lip.
# usage: python3 tools/prep_box.py <rembg models dir (has birefnet-general)> [out.png]
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.environ['U2NET_HOME'] = sys.argv[1]
from rembg import remove, new_session
out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'assets', 'box_real.png')

im = Image.open(os.path.join(ROOT, 'assets', 'src', 'box_frame_5.62.png')).convert('RGB')
# 1 rough patch behind the car (frame coords): lip left end in lip white, tray wall strip in its pink
fix = im.copy(); d = ImageDraw.Draw(fix)
d.polygon([(150, 1690), (205, 1692), (205, 1845), (395, 1848), (398, 1966), (150, 1912)], fill=(247, 239, 220))
d.polygon([(150, 1688), (150, 1600), (215, 1560), (215, 1690)], fill=(212, 140, 118))
PATCH = [(150, 1600), (215, 1560), (215, 1690), (205, 1692), (205, 1845), (395, 1848), (398, 1966), (150, 1912)]
m = Image.new('L', im.size, 0); ImageDraw.Draw(m).polygon(PATCH, fill=255)
im = Image.composite(fix, im, m.filter(ImageFilter.GaussianBlur(3)))
OX, OY = 120, 40
crop = im.crop((OX, OY, 2160, 2330))
# 2 BiRefNet cut-out
cut = np.asarray(remove(crop, session=new_session('birefnet-general'), post_process_mask=True)).copy()
rgb, A = cut[..., :3].copy(), cut[..., 3].astype(np.float32)
H, W = A.shape; yy, xx = np.mgrid[0:H, 0:W]
# 3 left of the patch the mask follows the car: cut it back to the lip's bottom edge, fitted on the visible lip
xs = list(range(330, 730, 20)); ys = [int(np.nonzero(A[1700:, x] > 128)[0].max()) + 1700 for x in xs]
k, b = np.polyfit(xs, ys, 1); line = k * xx + b
A = np.where(xx < 350, np.minimum(A, np.clip((line + 1.5 - yy) / 3, 0, 1) * 255), A)
# 4 inpaint the patch from the lip around it (outside pixels near it set to lip white first so the sofa can't bleed in)
pm = Image.new('L', (W, H), 0); ImageDraw.Draw(pm).polygon([(x - OX, y - OY) for x, y in PATCH], fill=255)
mk = np.asarray(pm.filter(ImageFilter.MaxFilter(9))) > 0
lip = rgb[1674:1704, 128:228].reshape(-1, 3).mean(0).astype(np.uint8)
rgb2 = rgb.copy(); rgb2[(A < 128) & (xx < 450)] = lip
inp = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(rgb2, cv2.COLOR_RGB2BGR), mk.astype(np.uint8) * 255, 21, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
soft = cv2.GaussianBlur(mk.astype(np.float32), (0, 0), 3)[..., None]
rgb = (inp * soft + rgb * (1 - soft)).astype(np.uint8)
out = Image.fromarray(np.dstack([rgb, A.astype(np.uint8)]))
out = out.crop(out.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())
out.save(out_path); print(out_path, out.size)
