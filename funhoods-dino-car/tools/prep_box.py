# The 12 pcs display box: the FRONT VIEW of the client's "360° packaging mockup" (assets/src/box_front_up.png =
# crop (115, 343)-(768, 960) of that image, Real-ESRGAN x4). The mockup is AI-made and its small print is garbled, so
# every garbled line is painted out and re-set with the client's packaging text; both logo tags get the real logo.
# usage: python3 tools/prep_box.py <rembg models dir (has birefnet-general)> [out.png]
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_BODY, F_HEAD = os.path.join(FONTS, 'Inter-ExtraBold.ttf'), os.path.join(FONTS, 'LilitaOne-Regular.ttf')
os.environ['U2NET_HOME'] = sys.argv[1]
from rembg import remove, new_session
out_path = sys.argv[2] if len(sys.argv) > 2 else A('box_real.png')

im = Image.open(A('src', 'box_front_up.png')).convert('RGB')
W, H = im.size
# 1 cut-out; keep the box (largest part) -- drops the mockup's rotation arrows
m = np.asarray(remove(im, session=new_session('birefnet-general'), only_mask=True, post_process_mask=True)).astype(np.float32)
lab, n = ndi.label(m > 128); sizes = ndi.sum(m > 128, lab, range(1, n + 1))
keep = ndi.binary_dilation(lab == (np.argmax(sizes) + 1), iterations=3)
alpha = (m * keep).astype(np.uint8)

# 2 retouch
rgb = np.asarray(im).copy()
def ring_colour(box, w=8):
    x0, y0, x1, y1 = box
    r = np.concatenate([rgb[max(0, y0 - w):y0, x0:x1].reshape(-1, 3), rgb[y1:y1 + w, x0:x1].reshape(-1, 3),
                        rgb[y0:y1, max(0, x0 - w):x0].reshape(-1, 3), rgb[y0:y1, x1:x1 + w].reshape(-1, 3)])
    return np.median(r, 0)
def patch(box, col=None):
    """paint a garbled area out with the colour around it (soft 2 px edge)"""
    col = ring_colour(box) if col is None else np.array(col, np.float32)
    mk = Image.new('L', (W, H), 0); ImageDraw.Draw(mk).rectangle(box, fill=255)
    mk = np.asarray(mk.filter(ImageFilter.GaussianBlur(2))).astype(np.float32)[..., None] / 255
    rgb[:] = (rgb * (1 - mk) + col * mk).astype(np.uint8)
canvas = None
def text(txt, path, size, x, y, fill, maxw=None, anchor='mm'):
    f = ImageFont.truetype(path, size)
    while maxw and f.getlength(txt) > maxw and size > 6:
        size -= 1; f = ImageFont.truetype(path, size)
    canvas.text((x, y), txt, font=f, fill=fill, anchor=anchor)
def logo(name, cx, cy, wd):
    lg = Image.open(A(name)).convert('RGBA'); lg = lg.resize((wd, round(lg.height * wd / lg.width)), Image.LANCZOS)
    base.alpha_composite(lg, (int(cx - lg.width / 2), int(cy - lg.height / 2)))

TEAL_TXT, INK, GREY = (0, 104, 114), (40, 30, 30), (95, 95, 95)
# back panel (teal)
for b in [(1390, 214, 1592, 238), (1212, 362, 1768, 401), (1678, 410, 1786, 482), (720, 846, 992, 884), (720, 1100, 992, 1144)]: patch(b)
# left flap (white): icon print, labels, "360 DEGREE TUMBLING STUNT CAR" and the disclaimer line
flap = np.median(rgb[1150:1170, 420:480].reshape(-1, 3), 0)
for b in [(414, 908, 471, 930), (400, 945, 488, 963), (503, 945, 597, 963), (408, 1080, 487, 1110),
          (508, 1080, 592, 1110), (404, 1196, 712, 1280), (404, 1278, 836, 1302), (1328, 1256, 1850, 1302)]: patch(b)
patch((530, 880, 566, 912), flap)                    # inside the 360 icon's ring
# lip (white)
for b in [(1100, 2196, 1292, 2217), (902, 2322, 1498, 2356), (1966, 2248, 2192, 2302), (1966, 2322, 2164, 2370),
          (152, 2312, 218, 2340), (150, 2343, 222, 2370), (294, 2343, 380, 2370), (426, 2343, 500, 2370)]: patch(b)
# a garbled sticker on the tray's back wall, between the blue and green columns: paint its dark plate (and letters) teal
reg = (1098, 1494, 1278, 1604); x0, y0, x1, y1 = reg
hsv = np.asarray(Image.fromarray(rgb[y0:y1, x0:x1]).convert('HSV')).astype(np.float32)
dark = ndi.binary_dilation(hsv[..., 2] < 90, iterations=14) & ndi.binary_closing(hsv[..., 2] < 90, iterations=20)
wall = np.median(rgb[1474:1494, 1130:1240].reshape(-1, 3), 0)
mk = ndi.gaussian_filter(dark.astype(np.float32), 2)[..., None]
rgb[y0:y1, x0:x1] = (rgb[y0:y1, x0:x1] * (1 - mk) + wall * mk).astype(np.uint8)

base = Image.fromarray(rgb).convert('RGBA'); canvas = ImageDraw.Draw(base)
# the packaging text (client's wording)
text('Childhood full of fun', F_BODY, 22, 1476, 229, 'white', 200)
text('DINOSAUR 4WD OFF-ROAD ROLLOVER VEHICLE', F_BODY, 30, 1490, 381, 'white', 540)
text('3+', F_HEAD, 42, 1740, 430, 'white'); text('AGES', F_BODY, 20, 1740, 465, 'white')
text('360 DEGREE FLIP, COOL STUNTS,', F_BODY, 15, 865, 856, 'white', 240); text('MORE ADDICTIVE', F_BODY, 15, 865, 875, 'white', 240)
text('DINOSAUR MOUTH CAN BE', F_BODY, 15, 865, 1112, 'white', 240); text('OPENED UP AND DOWN', F_BODY, 15, 865, 1132, 'white', 240)
text('CLIMB', F_BODY, 15, 442, 919, INK, 54); text('360°', F_HEAD, 17, 548, 896, INK, 34)
text('MULTIPLE VENUES', F_BODY, 11, 443, 954, INK, 84); text('TUMBLING STUNT CAR', F_BODY, 11, 549, 954, INK, 90)
text('INTELLECTUAL', F_BODY, 11, 447, 1086, INK, 76); text('DEVELOPMENT', F_BODY, 11, 447, 1098, INK, 76)
text('HANDS-ON', F_BODY, 11, 550, 1086, INK, 80); text('ABILITY', F_BODY, 11, 550, 1098, INK, 80)
text('360 DEGREE', F_HEAD, 40, 418, 1226, INK, 290, 'lm'); text('TUMBLING STUNT CAR', F_HEAD, 40, 418, 1270, INK, 290, 'lm')
text('SPECIFICATIONS COLOURS AND CONTENTS MAY VARY FROM ILLUSTRATIONS', F_BODY, 13, 1598, 1280, GREY, 490)
text('Childhood full of fun', F_BODY, 17, 1196, 2208, INK, 190)
text('DINOSAUR 4WD OFF-ROAD ROLLOVER VEHICLE', F_BODY, 26, 1200, 2339, TEAL_TXT, 590)
for i, ln in enumerate(['THIS PRODUCT IS', 'AVAILABLE IN 4 COLORS']): text(ln, F_BODY, 17, 1972, 2263 + i * 24, INK, 215, 'lm')
for i, ln in enumerate(['360° TUMBLING', 'STUNT CAR']): text(ln, F_BODY, 17, 1972, 2335 + i * 24, INK, 190, 'lm')
text('CLIMB', F_BODY, 13, 185, 2326, INK, 62)
text('MULTIPLE VENUES', F_BODY, 10, 186, 2357, INK, 70); text('INTELLECTUAL DEVELOPMENT', F_BODY, 10, 337, 2357, INK, 84)
text('HANDS-ON ABILITY', F_BODY, 10, 463, 2357, INK, 72)
# the real logo on both tags (banner without the tagline; the tagline is set above / below it)
logo('logo_banner.png', 1476, 160, 284)
logo('logo_banner.png', 1194, 2148, 272)

out = base.copy(); out.putalpha(Image.fromarray(alpha))
bb = out.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox(); out = out.crop(bb)
out.save(out_path); print(out_path, out.size, 'crop', bb)
