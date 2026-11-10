# The 12-pc display box (../funhoods-dino-car/assets/box_real.png) with its tray emptied, for the "box is empty" beat:
# the tray area between the back wall and the printed front lip is repainted as an empty teal tray (back wall,
# floor, slot dividers, soft shadows). render.py reveals it one colour column at a time as the dinos are taken.
# -> assets/box_empty.png (same size as box_real.png)
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
box = Image.open(os.path.join(ROOT, '..', 'funhoods-dino-car', 'assets', 'box_real.png')).convert('RGBA')
W, H = box.size
TRAY = [(345, 1300), (1955, 1300), (2125, 2122), (125, 2122)]          # inside of the tray, above the front lip
m = Image.new('L', box.size, 0); ImageDraw.Draw(m).polygon(TRAY, fill=255)
yy = np.arange(H)[:, None] * np.ones((1, W))
back = np.clip((yy - 1300) / 330, 0, 1)                                   # back wall -> floor
top, mid, floor = np.array([0, 96, 108]), np.array([0, 134, 146]), np.array([60, 170, 178])
col = np.where(back[..., None] < 1, top * (1 - back[..., None]) + mid * back[..., None],
               mid + (floor - mid) * np.clip((yy - 1630) / 490, 0, 1)[..., None])
tray = Image.fromarray(col.astype(np.uint8)).convert('RGBA'); d = ImageDraw.Draw(tray)
d.line([(330, 1630), (1990, 1630)], fill=(0, 110, 120, 255), width=10)      # where the back wall meets the floor
for x0, x1 in ((740, 760), (1165, 1185), (1595, 1615)):                   # slot dividers, in perspective
    d.polygon([(x0 + (x0 - 1040) * 0.0, 1630), (x1, 1630), (x1 + (x1 - 1040) * 0.12, 2122), (x0 + (x0 - 1040) * 0.12, 2122)], fill=(120, 196, 202, 255))
sh = Image.new('L', box.size, 0); ImageDraw.Draw(sh).rectangle((0, 2040, W, 2122), fill=110)   # shadow under the front lip
tray = Image.composite(Image.new('RGBA', box.size, (0, 70, 80, 255)), tray, sh.filter(ImageFilter.GaussianBlur(30)))
out = box.copy(); out.paste(tray, (0, 0), m.filter(ImageFilter.GaussianBlur(2)))
os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
out.save(os.path.join(ROOT, 'assets', 'box_empty.png')); print('box_empty.png', out.size)
