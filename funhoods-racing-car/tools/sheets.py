# 360° product view + 360° packaging view sheets for the Racing Inertia Car, in the style of the client's earlier
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
label(d, 'RACING INERTIA CAR', DW / 2, 350, 40, RED, 'mm')
cells = [('FRONT', 'car_front'), ('SIDE', 'car_side'), ('BACK', 'car_back'), ('OTHER SIDE', 'car_side_r'),
         ('3/4 FRONT', 'car_q34'), ('3/4 REAR', 'car_back34')]
for i, (lbl, n) in enumerate(cells):
    col, row = i % 2, i // 2; x0, y0 = 70 + col * 718, 420 + row * 420
    label(d, lbl, x0 + 10, y0, 44)
    put(im, n, x0 + 334, y0 + 230, 600 if 'side' in n or 'q34' in n else 470, 300)
d.rectangle((0, 1700 * S, DW * S, DH * S), fill=(222, 225, 230))
label(d, 'Push & Go · Lights & Music', 70, 1745, 54)
chips(d, ['FRICTION', 'HAND PUSH', 'INERTIA', 'STURDY', 'FOUR-WHEEL DRIVE', 'LOUD MUSIC', 'BRIGHT LIGHT'], 1880)
save(im, 'Racing_Inertia_Car_360_Product_View')

# ---------------------------------------------------------------- 360° packaging view
im, d = base()
label(d, '360° Packaging View', DW / 2, 262, 88, INK, 'mm')
label(d, 'RACING INERTIA CAR · WINDOW BOX', DW / 2, 350, 40, RED, 'mm')
label(d, 'FRONT', 80, 400, 44)
put(im, 'box_q34', DW / 2, 690, 1180, 520)
grid = [('BACK', 'box_back'), ('TOP', 'box_top'), ('LEFT SIDE', 'box_end_l'), ('RIGHT SIDE', 'box_end_r'), ('BOTTOM', 'box_bottom')]
for i, (lbl, n) in enumerate(grid):
    col, row = i % 2, i // 2; x0, y0 = 70 + col * 718, 990 + row * 350
    label(d, lbl, x0 + 10, y0, 40)
    put(im, n, x0 + 334, y0 + 190, 600, 250, card=True)
x0, y0 = 70 + 718, 990 + 2 * 350                                  # info card next to BOTTOM
d.rounded_rectangle(((x0 + 20) * S, (y0 + 30) * S, (x0 + 650) * S, (y0 + 320) * S), 28 * S, fill='white', outline=RED, width=4 * S)
for k, t in enumerate(['Window box: product on show', 'Functional version NO.3301', 'Loud music & bright light',
                       '3 x 1.5V Ag13 button batteries', 'Ages 3+']):
    label(d, ('• ' if k else '') + t, x0 + 52, y0 + 66 + k * 52, 30 if k else 34, RED if k == 0 else INK)
save(im, 'Racing_Inertia_Car_360_Packaging_View')
