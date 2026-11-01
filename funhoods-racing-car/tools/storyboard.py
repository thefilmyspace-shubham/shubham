# Storyboard board for the 32 s Racing Inertia Car reel: 10 key frames (9:16) with time, VO line and action notes.
# Rough layout frames built from the graded cut-outs; the final reel is rendered by render.py in the reels' house style.
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_B, F_H, F_I = (os.path.join(FONTS, n) for n in ('Inter-ExtraBold.ttf', 'LilitaOne-Regular.ttf', 'LuckiestGuy-Regular.ttf'))
RED, DRED, YEL, INK, WHITE, GOLD = (210, 24, 31), (120, 6, 14), (255, 212, 0), (30, 22, 22), (255, 255, 255), (255, 186, 0)
PW, PH = 432, 768
def f(p, s): return ImageFont.truetype(p, int(s))

def bg():
    im = Image.new('RGB', (PW, PH), WHITE); d = ImageDraw.Draw(im); c = (PW / 2, PH * 0.42)
    for i in range(0, 24, 2):
        a0, a1 = math.radians(i * 15), math.radians((i + 1) * 15)
        d.polygon([c, (c[0] + 900 * math.cos(a0), c[1] + 900 * math.sin(a0)), (c[0] + 900 * math.cos(a1), c[1] + 900 * math.sin(a1))], fill=(255, 244, 240))
    return im.convert('RGBA')

def put(c, name, cx, cy, w, rot=0, flip=False):
    im = Image.open(A(name + '.png')).convert('RGBA')
    if flip: im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im = im.resize((int(w), int(im.height * w / im.width)), Image.LANCZOS)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    sh = Image.new('RGBA', c.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((cx - w * 0.42, cy + im.height * 0.42, cx + w * 0.42, cy + im.height * 0.42 + 18), fill=(90, 30, 30, 90))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8))); c.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def txt(d, s, x, y, size, col=RED, font=F_H, stroke=0, sc=DRED, anchor='mm'):
    fo = f(font, size)
    while d.textlength(s, font=fo) > PW - 30 and size > 10: size -= 1; fo = f(font, size)
    d.text((x + max(1, size // 18), y + max(1, size // 18)), s, font=fo, fill=DRED, anchor=anchor, stroke_width=stroke, stroke_fill=DRED)
    d.text((x, y), s, font=fo, fill=col, anchor=anchor, stroke_width=stroke, stroke_fill=sc)

def chip(d, s, x, y, size=17, bg=YEL, fg=DRED):
    fo = f(F_B, size); w = d.textlength(s, font=fo) + 28
    d.rounded_rectangle((x - w / 2, y - size / 2 - 9, x + w / 2, y + size / 2 + 9), size, fill=bg); d.text((x, y), s, font=fo, fill=fg, anchor='mm')

def logo(c):
    lg = Image.open(A('logo_rgba.png')).convert('RGBA'); w = 92; lg = lg.resize((w, int(lg.height * w / lg.width)), Image.LANCZOS)
    card = Image.new('RGBA', (w + 18, lg.height + 18), (0, 0, 0, 0)); ImageDraw.Draw(card).rounded_rectangle((0, 0, w + 17, lg.height + 17), 10, fill=WHITE)
    card.alpha_composite(lg, (9, 9)); c.alpha_composite(card, (14, 14))

def speed(d, y0, y1, n=7, x1=PW):
    rng = np.random.default_rng(int(y0))
    for k in range(n):
        y = rng.uniform(y0, y1); x = rng.uniform(0, x1 - 120); d.line([(x, y), (x + rng.uniform(60, 130), y)], fill=[RED, GOLD, (250, 190, 180)][k % 3], width=4)

def burst(d, cx, cy, r, n=14):
    pts = [(cx + (r if i % 2 == 0 else r * 0.62) * math.cos(math.pi * i / n), cy + (r if i % 2 == 0 else r * 0.62) * math.sin(math.pi * i / n)) for i in range(2 * n)]
    d.polygon(pts, fill=DRED); d.polygon([(cx + (x - cx) * 0.9, cy + (y - cy) * 0.9) for x, y in pts], fill=YEL)

def note(d, x, y, col):
    d.ellipse((x - 14, y + 6, x + 6, y + 22), fill=col); d.rectangle((x + 2, y - 26, x + 7, y + 14), fill=col)
    d.polygon([(x + 7, y - 26), (x + 24, y - 14), (x + 22, y - 6), (x + 7, y - 16)], fill=col)

def glove(d, x, y):
    """cartoon glove, palm down, fingers pointing left, pressing on the car's back"""
    for k in range(4): d.rounded_rectangle((x - 52, y - 20 + k * 11, x + 4, y - 8 + k * 11), 6, fill=WHITE, outline=DRED, width=2)
    d.rounded_rectangle((x - 8, y - 26, x + 40, y + 26), 14, fill=WHITE, outline=DRED, width=3)
    d.rounded_rectangle((x + 34, y - 20, x + 62, y + 22), 6, fill=WHITE, outline=DRED, width=3)
    d.line([(x - 60, y + 40), (x - 110, y + 40)], fill=RED, width=5); d.polygon([(x - 110, y + 30), (x - 128, y + 40), (x - 110, y + 50)], fill=RED)

def panel(i):
    c = bg(); d = ImageDraw.Draw(c)
    if i == 0:
        d.rounded_rectangle((96, 120, 336, 210), 26, fill=INK)
        for k, col in enumerate([(230, 40, 40), (230, 40, 40), (40, 200, 70)]): d.ellipse((116 + k * 72, 132, 172 + k * 72, 188), fill=col)
        txt(d, 'ON YOUR MARKS · GET SET', PW / 2, 250, 24); txt(d, 'VROOM!', PW / 2, 318, 76, YEL, F_I, 3, RED)
        speed(d, 430, 560); put(c, 'car_side', 250, 500, 330)
    elif i == 1:
        put(c, 'car_q34', PW / 2, 470, 380)
        d.arc((40, 330, 392, 620), 200, 340, fill=RED, width=6); d.polygon([(380, 410), (396, 446), (360, 440)], fill=RED)
        txt(d, 'SAY HELLO TO THE', PW / 2, 200, 22); txt(d, 'RACING', PW / 2, 252, 64, YEL, F_I, 3, RED); txt(d, 'INERTIA CAR', PW / 2, 312, 44)
    elif i == 2:
        d.line([(30, 560), (402, 560)], fill=(242, 214, 208), width=4); put(c, 'car_side', 190, 490, 300)
        glove(d, 318, 392)
        for k in range(3): d.polygon([(250 + k * 40, 600), (272 + k * 40, 612), (250 + k * 40, 624)], fill=RED)
        txt(d, 'HOW IT WORKS', PW / 2, 180, 24); txt(d, 'PUSH...', PW / 2, 240, 58, RED, F_H); txt(d, 'LET GO!', PW / 2, 302, 60, YEL, F_I, 3, RED)
        chip(d, 'FRICTION', 110, 690); chip(d, 'HAND PUSH', 216, 690); chip(d, 'INERTIA', 322, 690)
    elif i == 3:
        put(c, 'car_front', PW / 2, 470, 220)
        glow = Image.new('RGBA', c.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        for x in (180, 252): gd.ellipse((x - 46, 478 - 46, x + 46, 478 + 46), fill=(255, 230, 120, 210))
        c.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14))); d = ImageDraw.Draw(c)
        for k, (x, y) in enumerate([(70, 360), (360, 380), (90, 560), (350, 590)]): note(d, x, y, [RED, GOLD, (40, 160, 226), RED][k])
        txt(d, 'PRESS THE ROOF', PW / 2, 190, 34); txt(d, 'LIGHTS & MUSIC!', PW / 2, 250, 44, YEL, F_I, 2, RED)
        chip(d, 'LOUD MUSIC', 140, 690, bg=RED, fg=WHITE); chip(d, 'BRIGHT LIGHT', 292, 690, bg=RED, fg=WHITE)
    elif i == 4:
        put(c, 'car_side_r', PW / 2, 470, 360)
        for (x0, y0, x1, y1, s) in [(120, 540, 70, 640, 'CHUNKY TYRES'), (230, 420, 300, 330, 'STURDY BODY')]:
            d.line([(x0, y0), (x1, y1)], fill=RED, width=3); d.ellipse((x0 - 6, y0 - 6, x0 + 6, y0 + 6), fill=RED); chip(d, s, x1 + (40 if x1 < 200 else 0), y1 + (16 if y1 > 500 else -14), 15)
        txt(d, 'FOUR-WHEEL', PW / 2, 190, 54, YEL, F_I, 3, RED); txt(d, 'DRIVE', PW / 2, 246, 44)
    elif i == 5:
        for k, (n, x, y, w) in enumerate([('box_end_l', 118, 400, 190), ('box_end_r', 316, 400, 190), ('box_back', 118, 560, 190), ('car_q34', 316, 560, 200)]): put(c, n, x, y, w)
        txt(d, 'COOL STYLE', PW / 2, 190, 40); txt(d, 'MULTIPLE MODELS', PW / 2, 242, 34, YEL, F_I, 2, RED); txt(d, '& COLOURS', PW / 2, 290, 34)
    elif i == 6:
        d.rectangle((0, 610, PW, 680), fill=(214, 168, 116)); d.rectangle((0, 600, PW, 614), fill=(238, 206, 160))
        put(c, 'box_q34', PW / 2, 520, 380)
        for (x, y) in [(70, 420), (370, 400), (360, 590)]: d.polygon([(x, y - 14), (x + 4, y - 4), (x + 14, y), (x + 4, y + 4), (x, y + 14), (x - 4, y + 4), (x - 14, y), (x - 4, y - 4)], fill=GOLD)
        txt(d, 'EYE-CATCHING', PW / 2, 200, 50, YEL, F_I, 3, RED); txt(d, 'WINDOW BOX', PW / 2, 256, 44)
    elif i == 7:
        for (x, y) in [(130, 430), (302, 430), (216, 330)]:
            d.polygon([(x - 70, y - 40), (x + 70, y - 40), (x + 84, y - 54), (x - 56, y - 54)], fill=(226, 186, 136)); d.rectangle((x - 70, y - 40, x + 70, y + 46), fill=(206, 160, 108))
            d.polygon([(x + 70, y - 40), (x + 84, y - 54), (x + 84, y + 32), (x + 70, y + 46)], fill=(176, 128, 80)); d.text((x, y + 8), '[N] PCS', font=f(F_H, 24), fill=RED, anchor='mm')
        d.rounded_rectangle((90, 560, 260, 640), 10, fill=YEL); d.polygon([(262, 584), (312, 584), (336, 612), (336, 640), (262, 640)], fill=RED)
        for x in (124, 222, 312): d.ellipse((x - 18, 630, x + 18, 666), fill=INK)
        txt(d, '[N] PCS', PW / 2, 180, 62, YEL, F_I, 3, RED); txt(d, 'PER CARTON', PW / 2, 236, 38); txt(d, 'PAN INDIA DELIVERY', PW / 2, 700, 30)
    elif i == 8:
        txt(d, 'FOR', PW / 2, 160, 18, RED, F_B); txt(d, 'DISTRIBUTORS', PW / 2, 206, 46); txt(d, '& WHOLESALERS', PW / 2, 256, 40, YEL, F_H, 2, RED)
        for k, x in enumerate((90, 216, 342)): put(c, 'box_q34', x, 420 + (k % 2) * 6, 150)
        chip(d, 'BULK ORDERS ONLY', PW / 2, 540, 24); burst(d, PW / 2, 640, 92); txt(d, 'STOCK UP NOW!', PW / 2, 640, 40, YEL, F_I, 2, RED)
    elif i == 9:
        c = Image.new('RGBA', (PW, PH), (255, 248, 236, 255)); d = ImageDraw.Draw(c)
        d.polygon([(0, 0), (PW, 0), (PW, 110), (PW / 2, 140), (0, 110)], fill=RED); d.polygon([(0, PH), (PW, PH), (PW, PH - 80), (0, PH - 104)], fill=RED)
        lg = Image.open(A('logo_rgba.png')).convert('RGBA'); w = 320; lg = lg.resize((w, int(lg.height * w / lg.width)), Image.LANCZOS); c.alpha_composite(lg, (int(PW / 2 - w / 2), 180))
        put(c, 'car_q34', 150, 440, 230); put(c, 'box_q34', 318, 446, 190)
        d.text((PW / 2, 548), 'RACING INERTIA CAR • 3+ AGES', font=f(F_B, 17), fill=RED, anchor='mm'); chip(d, 'BULK ORDERS ONLY', PW / 2, 594, 20, RED, WHITE)
        chip(d, '[N] PCS / CARTON', 140, 640, 15); chip(d, 'PAN INDIA DELIVERY', 300, 640, 15)
        return c
    logo(c); return c

ROWS = [('0.0–3.0', 'On your marks... get set... VROOM!', 'Start lights count down, the car shoots in. Rev + zoom SFX'),
        ('3.0–5.5', 'Say hello to the Funhoods Racing Inertia Car!', '360° turntable: front → side → back'),
        ('5.5–9.0', 'Give it a push... let go... and watch it race!', 'Glove pushes, lets go, the car races off. Friction + zoom SFX'),
        ('9.0–12.0', 'Press the roof... bright lights and loud music!', 'Finger press, headlights glow, notes burst. Music jingle'),
        ('12.0–15.0', 'Four-wheel drive, a sturdy body and chunky tyres.', 'Callouts draw on, wheels spin'),
        ('15.0–18.0', 'Cool style, multiple models, multiple colours!', "The box's car artworks pop in a row"),
        ('18.0–21.5', 'A bold window box that grabs every eye in the store.', 'Box turns front → side → back, lands on a counter'),
        ('21.5–25.0', '[N] pieces per carton, shipped anywhere in India.', 'Cartons stack, the Funhoods truck drives in'),
        ('25.0–28.8', 'Distributors and wholesalers, stock up for the season!', 'Boxes line up · BULK ORDERS ONLY · STOCK UP NOW!'),
        ('28.8–32.0', 'Funhoods, Childhood Full of Fun!', 'End card · final hit, fade')]
COLS, CAP = 5, 150
board = Image.new('RGB', (COLS * (PW + 24) + 24, 2 * (PH + CAP + 24) + 120), (246, 246, 248)); bd = ImageDraw.Draw(board)
bd.text((24, 30), 'Funhoods · Racing Inertia Car · 32 s reel · Storyboard v1', font=f(F_B, 38), fill=INK)
bd.text((24, 78), 'White-background motion graphics · B2B (distributors & wholesalers) · Funhoods logo top-left · [N] = carton count (to confirm)', font=f(F_B, 20), fill=(110, 110, 120))
for i in range(10):
    x, y = 24 + (i % COLS) * (PW + 24), 120 + (i // COLS) * (PH + CAP + 24)
    p = panel(i).convert('RGB'); board.paste(p, (x, y)); bd.rectangle((x, y, x + PW - 1, y + PH - 1), outline=(200, 200, 205), width=2)
    bd.rounded_rectangle((x + PW - 150, y + PH - 44, x + PW - 10, y + PH - 10), 14, fill=INK); bd.text((x + PW - 80, y + PH - 27), ROWS[i][0] + ' s', font=f(F_B, 17), fill=WHITE, anchor='mm')
    words, line, yy = f'{i + 1}. VO: "{ROWS[i][1]}"'.split(), '', y + PH + 12
    for w_ in words:
        t = (line + ' ' + w_).strip()
        if bd.textlength(t, font=f(F_B, 17)) > PW: bd.text((x, yy), line, font=f(F_B, 17), fill=INK); yy += 24; line = w_
        else: line = t
    bd.text((x, yy), line, font=f(F_B, 17), fill=INK)
    words, line, yy = ROWS[i][2].split(), '', yy + 32
    for w_ in words:
        t = (line + ' ' + w_).strip()
        if bd.textlength(t, font=f(F_B, 16)) > PW: bd.text((x, yy), line, font=f(F_B, 16), fill=(110, 110, 120)); yy += 24; line = w_
        else: line = t
    bd.text((x, yy), line, font=f(F_B, 16), fill=(110, 110, 120))
out = os.path.join(ROOT, 'exports', 'Racing_Inertia_Car_Storyboard.png'); board.save(out); print(out, board.size)
