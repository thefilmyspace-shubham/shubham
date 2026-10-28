# The blister pack (front card) from the client's "What's in the box" infographic: crop (215, 479)-(858, 1643) of the
# 1529x2048 image, Real-ESRGAN x4 (assets/src/pack_up.png). The card is a rounded rectangle, so it is masked as one
# (BiRefNet picks the jets instead of the card); the infographic's callout line and dot on its left side are inpainted.
import os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
im = Image.open(A('src', 'pack_up.png')).convert('RGB'); W, H = im.size
rgb = np.asarray(im).copy()
# callout: a dark line from the left edge to a ring at (250, 1585)
m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
d.rectangle((0, 1568, 205, 1602), fill=255); d.ellipse((182, 1517, 318, 1653), fill=255)
mk = np.asarray(m.filter(ImageFilter.MaxFilter(9)))
rgb = cv2.cvtColor(cv2.inpaint(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mk, 15, cv2.INPAINT_TELEA), cv2.COLOR_BGR2RGB)
BOX, R = (34, 18, 2541, 4639), 95
am = Image.new('L', (W * 2, H * 2), 0); ImageDraw.Draw(am).rounded_rectangle([v * 2 for v in BOX], R * 2, fill=255)
out = Image.fromarray(rgb).convert('RGBA'); out.putalpha(am.resize((W, H), Image.LANCZOS))
out = out.crop(out.getchannel('A').getbbox()); out.save(A('src', 'pack.png')); print(out.size)
