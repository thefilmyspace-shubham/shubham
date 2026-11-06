# 360° product view + packaging view sheets for the Press & Go Scooter (PL-001); the pack front is the new transparent
# pouch from the client's infographic (tools/new_pack.py), in the style of the client's earlier
# Funhoods infographics (light grey, logo top-left, red "3+ Years" badge, bold black labels).
# Built from the graded cut-outs in assets/ (tools/prep_assets.py). Writes exports/*_360_*.png (3072x4096) + previews.
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_B, F_H = os.path.join(FONTS, 'Inter-ExtraBold.ttf'), os.path.join(FONTS, 'LilitaOne-Regular.ttf')
S = 2                                   # layout in 1536x2048 units, rendered at 2x
DW, DH = 1536, 2048
RED, INK, GREY = (210, 24, 31), (24, 24, 28), (92, 96, 104)

def f(path, size): return ImageFont.truetype(path, int(size * S))

def base():
    y = np.linspace(0, 1, DH * S)[:, None, None]
    top, bot = np.array([244, 245, 247]), np.array([232, 234, 238])
    arr = (top * (1 - y) + bot * y) * np.ones((1, DW * S, 1))
    im = Image.fromarray(arr.astype(np.uint8)).convert('RGBA'); d = ImageDraw.Draw(im)
    lg = Image.open(A('logo_rgba.png')).convert('RGBA'); w = 380 * S
    im.alpha_composite(lg.resize((w, int(lg.height * w / lg.width)), Image.LANCZOS), (56 * S, 48 * S))
    d.rounded_rectangle(((DW - 222) * S, -40 * S, (DW - 46) * S, 176 * S), 34 * S, fill=RED)
    d.text(((DW - 134) * S, 72 * S), '3+', font=f(F_B, 76), fill='white', anchor='mm')
    d.text(((DW - 134) * S, 134 * S), 'Years', font=f(F_B, 40), fill='white', anchor='mm')
    return im, d

def fit(im, w, h):
    s = min(w * S / im.width, h * S / im.height)
    return im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)

def put(canvas, name, cx, cy, w, h, shadow=True, card=False):
    im = fit(Image.open(A(name + '.png')).convert('RGBA'), w, h)
    x, y = int(cx * S - im.width / 2), int(cy * S - im.height / 2)
    if shadow:
        sh = Image.new('RGBA', canvas.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        if card:                                                   # flat panel: soft drop shadow under the card
            sd.rounded_rectangle((x + 10 * S, y + 16 * S, x + im.width + 10 * S, y + im.height + 16 * S), 10 * S, fill=(40, 40, 50, 70))
        else:                                                      # object: contact shadow on the floor
            sd.ellipse((x + im.width * 0.08, y + im.height - 18 * S, x + im.width * 0.92, y + im.height + 22 * S), fill=(40, 40, 50, 90))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * S)))
    canvas.alpha_composite(im, (x, y))

def label(d, txt, x, y, size=46, col=INK, anchor='la'): d.text((x * S, y * S), txt, font=f(F_B, size), fill=col, anchor=anchor)

def chips(d, items, cy, size=30, gap=18, row_w=DW - 120):
    fo = f(F_B, size); pad = 26
    widths = [d.textlength(t, font=fo) / S + 2 * pad for t in items]
    rows, cur = [[]], 0
    for t, w in zip(items, widths):
        if cur + w > row_w and rows[-1]: rows.append([]); cur = 0
        rows[-1].append((t, w)); cur += w + gap
    for r, row in enumerate(rows):
        tot = sum(w for _, w in row) + gap * (len(row) - 1); x = (DW - tot) / 2; y = cy + r * (size + 44)
        for t, w in row:
            d.rounded_rectangle((x * S, (y - size / 2 - 16) * S, (x + w) * S, (y + size / 2 + 16) * S), (size / 2 + 16) * S, fill='white', outline=RED, width=3 * S)
            d.text(((x + w / 2) * S, y * S), t, font=fo, fill=RED, anchor='mm'); x += w + gap

def save(im, name):
    out = os.path.join(ROOT, 'exports', name)
    im.convert('RGB').save(out + '.png'); im.convert('RGB').resize((DW, DH), Image.LANCZOS).save(out + '_preview.jpg', quality=92)
    print(out + '.png')

# ---------------------------------------------------------------- 360° product view
im, d = base()
label(d, '360° Product View', DW / 2, 262, 92, INK, 'mm')
label(d, 'PRESS & GO SCOOTER · PL-001', DW / 2, 350, 40, RED, 'mm')
cells = [('FRONT', 'mouse_blue_front'), ('SIDE', 'mouse_blue_side'), ('BACK', 'mouse_blue_back'), ('3/4 BACK', 'mouse_blue_back34')]
for i, (lbl, n) in enumerate(cells):                              # 4 sides (mouse on blue)
    x0 = 50 + i * 362; y0 = 410
    label(d, lbl, x0 + 170, y0, 36, INK, 'ma')
    put(im, n, x0 + 170, y0 + 280, 320, 440)
d.rectangle((0, 1020 * S, DW * S, 1032 * S), fill=(222, 225, 230))
label(d, '2 Models · 4 Colours', DW / 2, 1080, 58, INK, 'mm')
row = [('MOUSE · SKY BLUE', 'mouse_blue_front'), ('MOUSE · RED', 'mouse_red_front'), ('DUCK · BLUE', 'duck_blue_front'), ('DUCK · ORANGE', 'duck_orange_front')]
for i, (lbl, n) in enumerate(row):
    x0 = 50 + i * 362; y0 = 1140
    put(im, n, x0 + 170, y0 + 250, 320, 470)
    label(d, lbl, x0 + 170, y0 + 520, 30, RED, 'ma')
d.rectangle((0, 1740 * S, DW * S, DH * S), fill=(222, 225, 230))
chips(d, ['PRESS THE HEAD', 'GOES FORWARD', 'SIZE 4–5 INCH', '3+ YEARS', 'BIS · IS 9873'], 1830)
save(im, 'Press_Go_Scooter_360_Product_View')

# ---------------------------------------------------------------- packaging view
im, d = base()
label(d, 'Packaging View', DW / 2, 262, 92, INK, 'mm')
label(d, 'PRESS & GO SCOOTER · PL-001 · NEW TRANSPARENT POUCH WITH HEADER CARD', DW / 2, 350, 28, RED, 'mm')
label(d, 'FRONT', 230, 420, 44, INK, 'ma')
put(im, 'pack_new', 400, 820, 640, 700)
x0 = 760
d.rounded_rectangle(((x0 + 20) * S, 520 * S, (x0 + 720) * S, 1080 * S), 28 * S, fill='white', outline=RED, width=4 * S)
for k, t in enumerate(['Transparent pouch: the rider is on show', 'Item code PL-001', '"Press the Head" on the label',
                       'BIS: IS 9873 (Part-1), CM/L 8200185112', 'Made in India · Non-toxic', '3 Years+ · 240 pcs / carton']):
    label(d, ('• ' if k else '') + t, x0 + 52, 560 + k * 80, 30 if k else 31, RED if k == 0 else INK)
label(d, 'BACK LABEL (from the earlier pack photos)', DW / 2, 1210, 40, INK, 'ma')
put(im, 'pack_back', DW / 2, 1560, 1380, 560, card=True)
save(im, 'Press_Go_Scooter_Packaging_View')
