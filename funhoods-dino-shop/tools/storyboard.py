# Storyboard board for the Dino Car "shop story" reel: 9 key frames rendered by render.py (the real art, on the
# provisional VO timing in timeline.py), each with its scene number, time, VO line and what happens.
# -> exports/Dino_Shop_Story_Storyboard.png (+ _preview.jpg)
import os, sys
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, ROOT)
import render as R, timeline as T
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_B, F_H = os.path.join(FONTS, 'Inter-ExtraBold.ttf'), os.path.join(FONTS, 'LilitaOne-Regular.ttf')
RED, INK, GREY = (210, 24, 31), (30, 24, 24), (90, 90, 96)
PW, PH, CAP = 540, 960, 300                 # panel size and caption height
def f(p, s): return ImageFont.truetype(p, s)
PANELS = [
    (2.2, 'Morning at the toy shop. Full shelves... but nobody stops.', 'Shutter rolls up, dull shelves, the dealer yawns. Kids walk past without looking in.'),
    (T.CARTON_LAND + 0.15, 'Then the Funhoods Dino Car arrives!', 'The Funhoods truck pulls up; a carton hops to the shop door. The dealer is surprised.'),
    (T.BOX_LAND + 0.6, 'Twelve dinos in a bright display box, right on the counter.', 'The real 12-pc box lands on the counter, the lamp turns into a spotlight, the shop lights up.'),
    (T.LAUNCH + 0.3, 'One push, and off it goes! A full 360 flip... and that dino mouth opens wide!', 'A kid pushes the dino: it rolls up a book ramp, flips 360, lands and chomps (real friction whirr).'),
    (T.REORDER + 0.3, 'Kids crowd in... and by evening, the box is empty. Time to reorder!', 'Dinos hop out to the kids, the clock runs to evening, SOLD OUT stamp, the dealer gives a thumbs-up with a reorder slip.'),
    (T.FACT_POPS[3] + 0.4, 'Four colours, BIS approved, safe for little hands.', 'The 4 colours on the shelf; badges: BIS APPROVED, SAFE FOR LITTLE HANDS, 3+ AGES.'),
    (T.TRUCK + 0.7, '192 pieces per carton, pan India delivery.', 'Cartons stack (192 PCS), the Funhoods truck drives in.'),
    (T.ROUTE_LIT[2] + 0.4, 'Distributors and wholesalers, put the Dino Car in every shop on your route!', 'A row of shops; the truck drives past and each window lights up with the Dino display.'),
    (T.DUR - 0.9, 'Funhoods... Childhood Full of Fun!', 'End card: logo, display box, colours, BULK ORDERS ONLY, 192 PCS / CARTON, PAN INDIA DELIVERY.'),
]
def wrap(d, s, fo, w):
    out, cur = [], ''
    for wd in s.split():
        tr = (cur + ' ' + wd).strip()
        if d.textlength(tr, font=fo) <= w: cur = tr
        else: out.append(cur); cur = wd
    return out + [cur]
cols, rows, gap, top = 3, 3, 36, 260
board = Image.new('RGB', (cols * PW + (cols + 1) * gap, top + rows * (PH + CAP + gap) + gap), (244, 241, 236)); d = ImageDraw.Draw(board)
d.text((gap, 60), 'Funhoods Dino Car — "The Shop Story" · storyboard', font=f(F_H, 72), fill=RED)
d.text((gap, 150), 'About 34 s · 9:16 · 4K60 · animated in code · B2B (distributors & wholesalers)', font=f(F_B, 30), fill=GREY)
d.text((gap, 196), 'Times are estimates until the VO is recorded.', font=f(F_B, 26), fill=GREY)
for i, (t, vo, act) in enumerate(PANELS):
    x0 = gap + (i % cols) * (PW + gap); y0 = top + (i // cols) * (PH + CAP + gap)
    fr = R.render(t).resize((PW, PH), Image.LANCZOS); board.paste(fr, (x0, y0))
    d.rounded_rectangle((x0 + PW - 80, y0 + 14, x0 + PW - 14, y0 + 70), 14, fill=RED); d.text((x0 + PW - 47, y0 + 42), str(i + 1), font=f(F_H, 40), fill=(255, 255, 255), anchor='mm')
    d.rectangle((x0, y0 + PH, x0 + PW, y0 + PH + CAP), fill=(255, 255, 255))
    yy = y0 + PH + 16
    d.text((x0 + 18, yy), '%.1f s' % t, font=f(F_B, 26), fill=RED); yy += 40
    for ln in wrap(d, '“' + vo + '”', f(F_H, 30), PW - 36): d.text((x0 + 18, yy), ln, font=f(F_H, 30), fill=INK); yy += 38
    yy += 6
    for ln in wrap(d, act, f(F_B, 23), PW - 36): d.text((x0 + 18, yy), ln, font=f(F_B, 23), fill=GREY); yy += 30
out = os.path.join(ROOT, 'exports', 'Dino_Shop_Story_Storyboard')
board.save(out + '.png'); board.resize((board.width // 2, board.height // 2), Image.LANCZOS).save(out + '_preview.jpg', quality=90)
print(out + '.png', board.size)
