"""TFS brand reel v3 — reference music/timing (from brand2) + 3D assets, real paper, graded footage, bigger framing,
earlier word sync, depth/shadows, neon logo. Uses brand2's renderer/transitions; replaces scenes.
python3 brand3.py --scale 2 --fps 60 --start 0 --end 9 --out p0.mp4
"""
import math, os, subprocess, sys
import numpy as np
import skia
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as Rn
from render import (font, hexc, text, text_w, cap_center_y, P, SP, R, rrect, Tx, Layer, NAVY, RED, SAND, WHITE, NAVY_L,
                    clamp, prog, lerp, eo3, eo5, eio3, eback, ei3, trimmed)
import brand_reel as BR
import brand2 as B2
from brand2 import T, find, WORDS, B, END
W, H = 1080, 1920
INK = '#141416'
A3 = os.path.join(HERE, 'assets3d')
FEED = os.path.join(os.path.dirname(HERE), 'feed')

# ---------------------------------------------------------------- assets
_img = {}
def img(name):
    if name not in _img:
        _img[name] = skia.Image.open(os.path.join(A3, name))
    return _img[name]

def sprite(c, name, cx, cy, h, rot=0.0, alpha=1.0, shadow=True):
    im = img(name); w = h * im.width() / im.height()
    with Tx(c, rot=rot, px=cx, py=cy):
        if shadow:
            sp = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, h * 0.05, h * 0.05, h * 0.05, skia.ColorSetARGB(int(110 * alpha), 0, 0, 0)))
            c.drawImageRect(im, R(cx - w / 2, cy - h / 2, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), sp)
        p = skia.Paint(); p.setAlphaf(clamp(alpha))
        c.drawImageRect(im, R(cx - w / 2, cy - h / 2, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)

_paper = {}
def paper(c, S, tint='#F5F0E6'):
    key = (S, tint)
    if key not in _paper:
        from PIL import Image
        src = Image.open(os.path.join(A3, 'paper', 'Paper001_2K-JPG_Color.jpg')).convert('RGB')
        cw = int(src.height * 9 / 16); src = src.crop(((src.width - cw) // 2, 0, (src.width - cw) // 2 + cw, src.height))
        src = src.resize((int(W * S), int(H * S)))
        a = np.asarray(src).astype(np.float32) / 255.0
        lum = a.mean(2, keepdims=True); lum = (lum - lum.mean()) * 0.9
        t = np.array([int(tint[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255.0
        out = np.clip(t + lum, 0, 1)
        # faint ruled grid like the reference
        step = int(64 * S)
        out[::step, :, :] *= np.array([1.0, 0.86, 0.84], np.float32)
        out[:, ::step, :] *= np.array([1.0, 0.93, 0.92], np.float32)
        rgba = np.concatenate([(out * 255).astype(np.uint8), np.full(out.shape[:2] + (1,), 255, np.uint8)], 2)
        _paper[key] = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)
    c.drawImageRect(_paper[key], R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), None)

def dark(c, S):
    c.drawPaint(P(hexc('#0C0C0F')))
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 820), 1100, [hexc('#1D1F27', 1.0), hexc('#0C0C0F', 1.0)])
    c.drawPaint(skia.Paint(Shader=rs))
    for y in range(0, H, 96): c.drawLine(0, y, W, y, SP(hexc('#FFFFFF', 0.035), 1.5))
    for x in range(0, W, 96): c.drawLine(x, 0, x, H, SP(hexc('#FFFFFF', 0.035), 1.5))

# graded, caption-safe footage
CROP = {'r9': (0.0, 0.66), 'r10': (0.0, 0.74), 'r5': (0.08, 0.74), 'r3': (0.10, 1.0), 'r2': (0.10, 1.0), 'r6': (0.08, 1.0), 'r8': (0.0, 0.60)}
class Graded(Rn.VideoClip):
    def __init__(self, reel, start, dur, size):
        w, h = size; y0, y1 = CROP.get(reel, (0.0, 1.0))
        vf = (f'crop=iw:ih*{y1 - y0}:0:ih*{y0},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},'
              'eq=contrast=1.08:saturation=1.12:gamma=0.97,colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.03:bm=-0.03,fps=30')
        cmd = ['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(dur), '-i', os.path.join(FEED, reel + '.mp4'), '-vf', vf,
               '-pix_fmt', 'rgba', '-f', 'rawvideo', '-']
        raw = subprocess.run(cmd, capture_output=True).stdout
        n = len(raw) // (w * h * 4)
        self.frames = np.frombuffer(raw[:n * w * h * 4], np.uint8).reshape(n, h, w, 4) if n else np.zeros((1, h, w, 4), np.uint8)
        self.fps, self.w, self.h, self.cache = 30, w, h, {}

_clips = {}
def clipsrc(reel, start, dur=3.0, size=(540, 960)):
    key = (reel, start, dur, size)
    if key not in _clips:
        if dur > 0.1 and sum(1 for k in _clips if k[2] > 0.1) > 6:
            _clips.pop(next(k for k in _clips if k[2] > 0.1))
        _clips[key] = Graded(reel, start, dur, size)
    return _clips[key]
BR.clipsrc = clipsrc
from brand_reel import draw_media, torn

def shadow_text(c, s, x, y, f, col, align='l', sh=0.22, off=8, blur=10, track=0.0):
    p = P(hexc('#000000', sh), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    tw = text_w(s, f, track)
    x0 = x - tw / 2 if align == 'c' else (x - tw if align == 'r' else x)
    if track:
        xx = x0
        for ch in s:
            c.drawString(ch, xx + off * 0.4, y + off, f, p); xx += f.measureText(ch) + track
    else:
        c.drawString(s, x0 + off * 0.4, y + off, f, p)
    text(c, s, x, y, f, hexc(col), align, track=track)

LEAD = 0.06
def word(c, s, x, y, f, col, t, t0, align='l', rise=56, d=0.2, shadow=True):
    t0 -= LEAD
    u = eo5(prog(t, t0, t0 + d))
    if u <= 0: return
    tw = text_w(s, f); sz = f.getSize()
    x0 = x - tw / 2 if align == 'c' else (x - tw if align == 'r' else x)
    def draw(yy):
        if shadow: shadow_text(c, s, x, yy, f, col, align, sh=0.16, off=6, blur=8)
        else: text(c, s, x, yy, f, hexc(col), align)
    if u >= 0.98: draw(y); return
    bp = skia.Paint(); bp.setAlphaf(clamp(u * 1.8))
    sig = (1 - u) * 18
    if sig > 0.4: bp.setImageFilter(skia.ImageFilters.Blur(0.01, sig))
    c.saveLayer(R(x0 - 80, y - sz * 1.4, tw + 160, sz * 2.4 + rise), bp)
    draw(y + (1 - u) * rise)
    c.restore()

def glossy_pill(c, cx, cy, label, f, fill, fg, s=1.0):
    tw = text_w(label, f); pw, ph = tw + 80, f.getSize() * 1.7
    with Tx(c, s=s, px=cx, py=cy):
        rr = skia.RRect.MakeRectXY(R(cx - pw / 2, cy - ph / 2, pw, ph), ph * 0.32, ph * 0.32)
        c.drawRRect(skia.RRect.MakeRectXY(R(cx - pw / 2 + 6, cy - ph / 2 + 18, pw, ph), ph * 0.32, ph * 0.32),
                    P(hexc('#000000', 0.3), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16)))
        g = skia.GradientShader.MakeLinear([skia.Point(0, cy - ph / 2), skia.Point(0, cy + ph / 2)], [hexc(fill), hexc(fill)])
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Shader=g))
        hl = skia.GradientShader.MakeLinear([skia.Point(0, cy - ph / 2), skia.Point(0, cy)], [hexc('#FFFFFF', 0.35), hexc('#FFFFFF', 0.0)])
        c.drawRRect(rr, skia.Paint(AntiAlias=True, Shader=hl))
        c.drawRRect(rr, SP(hexc('#000000', 0.25), 3))
        text(c, label, cx, cap_center_y(f, cy), f, hexc(fg), 'c')
    return pw, ph

def card_shadow(c, x, y, w, h, r=24, a=0.35):
    c.drawRRect(skia.RRect.MakeRectXY(R(x + 6, y + 22, w, h), r, r), P(hexc('#000000', a), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 24)))

# ---------------------------------------------------------------- 3D earth
_tex = None
def earth_frame(size, angle):
    global _tex
    if _tex is None:
        from PIL import Image
        e = np.asarray(Image.open(os.path.join(A3, 'earth_atmos_2048.jpg')).convert('RGB')).astype(np.float32) / 255
        cl = np.asarray(Image.open(os.path.join(A3, 'earth_clouds_1024.png')).convert('RGBA').resize((e.shape[1], e.shape[0]))).astype(np.float32) / 255
        _tex = (e, cl[..., 3] if cl[..., 3].std() > 0.01 else cl[..., :3].mean(2))
    e, cl = _tex
    n = size
    ys, xs = np.mgrid[0:n, 0:n].astype(np.float32)
    x = (xs + 0.5) / n * 2 - 1; y = (ys + 0.5) / n * 2 - 1
    r2 = x * x + y * y; m = r2 <= 1.0
    z = np.sqrt(np.clip(1 - r2, 0, 1))
    tilt = 0.35
    y2 = y * math.cos(tilt) - z * math.sin(tilt); z2 = y * math.sin(tilt) + z * math.cos(tilt)
    lon = np.arctan2(x, z2) + angle; lat = -np.arcsin(np.clip(y2, -1, 1))
    u = ((lon / (2 * math.pi) + 0.5) % 1.0) * (e.shape[1] - 1); v = (0.5 - lat / math.pi) * (e.shape[0] - 1)
    ui = u.astype(np.int32); vi = np.clip(v.astype(np.int32), 0, e.shape[0] - 1)
    col = e[vi, ui]
    cv = cl[vi, (ui + int(angle * 40)) % e.shape[1]][..., None]
    col = col * (1 - cv * 0.85) + cv * 0.95
    L = np.array([-0.55, -0.45, 0.70]); L /= np.linalg.norm(L)
    nd = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1)[..., None]
    col = col * (0.18 + 0.95 * nd)
    spec = (nd ** 30) * 0.35
    col = col + spec
    rim = ((1 - z) ** 3)[..., None]
    col = col * (1 - rim * 0.5) + np.array([0.35, 0.6, 1.0]) * rim * 0.6
    alpha = np.clip((1 - np.sqrt(r2)) * n * 0.5, 0, 1) * m
    rgba = np.concatenate([np.clip(col, 0, 1) * 255, (alpha * 255)[..., None]], 2).astype(np.uint8)
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)

# ---------------------------------------------------------------- scenes
def s_globe(c, t, S):
    paper(c, S)
    f = font('r', 76)
    for s, x, y, key in [('In', 90, 300, 0.0), ('a', 330, 300, 0.12), ('world', 990, 300, 0.24), ('full', 90, 410, 0.48), ('of', 990, 410, 0.88)]:
        word(c, s, x, y, f, INK, t, T(key), 'r' if x > 900 else 'l')
    cx, cy, r = 540, 1060, 430
    u = eback(prog(t, 0.0, 0.45), 1.3)
    gap = 70 * eo5(prog(t, 0.55, 0.85))
    with Tx(c, s=max(0.001, u), px=cx, py=cy):
        c.drawCircle(cx + 16, cy + 40, r, P(hexc('#000000', 0.25), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 40)))
        n = int(2 * r * S)
        ei = earth_frame(min(n, 1400), t * 0.9)
        for half, dy in ((0, -gap / 2), (1, gap / 2)):
            c.save(); c.clipRect(R(cx - r - 10, cy - r - 10 + half * (r + 10) + dy, 2 * r + 20, r + 10))
            c.drawImageRect(ei, R(cx - r, cy - r + dy, 2 * r, 2 * r), skia.SamplingOptions(skia.FilterMode.kLinear), None)
            c.restore()
        # phones bursting out of the slit
        for k, (dx, h, rot, d) in enumerate([(-270, 210, -24, 0.0), (-120, 260, -8, 0.05), (40, 300, 6, 0.1), (190, 250, 18, 0.07), (320, 200, 30, 0.12)]):
            pu = eback(prog(t, 0.62 + d, 0.92 + d), 1.6)
            if pu > 0:
                sprite(c, 'phone.png', cx + dx, cy - 20 - pu * (h * 0.45), h * pu, rot=rot)
    cu = eo5(prog(t, T(1.06) - LEAD, T(1.06) + 0.2))
    if cu > 0:
        fC = font('cond', 300)
        c.save(); c.clipRect(R(0, 1160, W * cu, 460))
        shadow_text(c, 'CONTENT', 540, 1460, fC, RED, 'c', sh=0.35, off=12, blur=14)
        c.restore()
    for k, (x, y) in enumerate([(160, 620), (940, 1500)]):
        su = eback(prog(t, 1.1 + k * 0.1, 1.4 + k * 0.1), 1.6)
        if su > 0: sprite(c, 'sparkles.png', x, y, 130 * su, rot=k * 20)

def s_tiles(c, t, S):
    paper(c, S)
    tw_, th_, g = 230, 340, 30
    for col in range(5):
        u = eo5(prog(t, B[1] + col * 0.04, B[1] + 0.36 + col * 0.04))
        drift = (t - B[1]) * (50 if col % 2 else -50)
        for row in range(-1, 8):
            x = -150 + col * (tw_ + g); y = -230 + row * (th_ + g) - (1 - u) * 2000 + (col % 2) * 150 + drift
            if 1 <= col <= 3 and 1 <= row <= 4: continue
            card_shadow(c, x, y, tw_, th_, 28, 0.18)
            rrect(c, x, y, tw_, th_, 28, P(hexc(SAND if (row + col) % 3 else NAVY)))
            if (row * 3 + col) % 4 == 0:
                sprite(c, ['camera.png', 'clapper.png', 'megaphone.png', 'chart.png'][(row + col) % 4], x + tw_ / 2, y + th_ / 2, 120, alpha=0.35, shadow=False)
    card_shadow(c, 120, 300, 840, 1280, 34, 0.2)
    rrect(c, 120, 300, 840, 1280, 34, P(hexc('#FBF8F2')))
    word(c, 'The brands that', 540, 560, font('r', 72), INK, t, find('the', 1.9), 'c')
    tw0 = find('win')
    u = eback(prog(t, tw0 - LEAD, tw0 + 0.22), 1.6)
    if u > 0:
        fW = font('cond', 520)
        with Tx(c, s=u, px=540, py=900):
            shadow_text(c, 'WIN', 540, cap_center_y(fW, 900), fW, RED, 'c', sh=0.3, off=14, blur=16)
    word(c, "aren't the", 540, 1200, font('r', 60), INK, t, find("aren't"), 'c')
    tl = find('loudest.')
    lu = eo5(prog(t, tl - LEAD, tl + 0.2))
    if lu > 0:
        fL = font('bebas', 250)
        c.save(); c.clipRect(R(120, 1220, 840, 300))
        shadow_text(c, 'LOUDEST', 540, 1470 + (1 - lu) * 260, fL, NAVY, 'c', sh=0.2)
        c.restore()
    for k, (rl, st, x, y, rot) in enumerate([('r9', 25.9, 760, 1360, -7), ('r10', 22.0, 30, 160, 6)]):
        u = eback(prog(t, 3.5 + k * 0.12, 3.78 + k * 0.12), 1.5)
        if u > 0:
            with Tx(c, rot=rot, s=u, px=x + 150, py=y + 265):
                card_shadow(c, x, y, 300, 530, 24)
                rrect(c, x - 10, y - 10, 320, 550, 26, P(hexc(WHITE)))
                draw_media(c, rl, st, t - 3.5, x, y, 300, 530, 18)

STRIP = [('r8', 5.1), ('r11', 9.2), ('r9', 30.0), ('r10', 30.0), ('r5', 29.5), ('r3', 9.2), ('r6', 9.0)]
STACK = [('r9', 22.4), ('r4', 18.0), ('r1', 31.4)]
def s_remember(c, t, S):
    paper(c, S)
    tl = t - B[2]
    if t < 4.95:
        off = -tl * 1500
        for k, (rl, st) in enumerate(STRIP):
            x = 420 + k * 330 + off; y = 980 - 280 + (k % 2) * 40
            card_shadow(c, x, y, 300, 533, 22)
            draw_media(c, rl, st, tl, x, y, 300, 533, 22, size=(360, 640))
    else:
        for k, (rl, st) in enumerate(STACK):
            u = eo5(prog(t, 4.95 + k * 0.05, 5.3 + k * 0.05))
            x = 540 + (k - 1) * lerp(460, 230, u); rot = (k - 1) * 9 * u; y = 1250
            with Tx(c, rot=rot, px=x, py=y):
                card_shadow(c, x - 190, y - 338, 380, 676, 30)
                rrect(c, x - 200, y - 348, 400, 696, 34, P(hexc(SAND if k == 1 else WHITE)))
                draw_media(c, rl, st, t - 4.95, x - 190, y - 338, 380, 676, 28)
        hu = eback(prog(t, 5.2, 5.45), 1.8)
        if hu > 0: sprite(c, 'heart.png', 900, 820, 170 * hu, rot=14)
    word(c, 'the ones people', 540, 420, font('r', 68), INK, t, find('ones'), 'c')
    tr = find('remember.')
    u = eo5(prog(t, tr - LEAD, tr + 0.25))
    fS = font('serif', 172); tw = text_w('Remember', fS)
    if u > 0:
        card_shadow(c, 540 - tw / 2 - 26, 490, (tw + 52) * u, 190, 6, 0.18)
        c.drawRect(R(540 - tw / 2 - 26, 490, (tw + 52) * u, 190), P(hexc(SAND)))
    word(c, 'Remember', 540, 650, fS, INK, t, tr, 'c', rise=40)

def s_best(c, t, S):
    dark(c, S)
    for i, (nm, fk) in enumerate(BR.CLIENTS):
        r_, k = divmod(i, 3)
        f = font(fk, 40); x = 180 + k * 360; y = 260 + r_ * 300 + (k % 2) * 120
        text(c, nm[:14], x, y, f, hexc('#FFFFFF', 0.06), 'c')
    bu = prog(t, B[3] - LEAD, B[3] + 0.22)
    fB = font('head', 84); s = 'THE BEST BRANDS'; tw = text_w(s, fB)
    box = skia.Path(); box.addRect(R(540 - tw / 2 - 34, 270, tw + 68, 170))
    trimmed(c, box, SP(hexc(WHITE), 4, cap=skia.Paint.kSquare_Cap), eo3(bu))
    word(c, s, 540, 398, fB, WHITE, t, B[3] + 0.04, 'c', rise=28, shadow=False)
    for k, (lab, icon, x, y, t0) in enumerate([('Reach', 'chart.png', 300, 830, 5.92), ('Views', 'eyes.png', 760, 1010, 6.04), ('Followers', 'thumbsup.png', 420, 1260, 6.16)]):
        u = eback(prog(t, t0, t0 + 0.22), 1.4)
        if u > 0:
            yy = y - (t - t0) * 70
            pw, ph = glossy_pill(c, x, yy, lab, font('m', 58), '#2A2C34', WHITE, s=u)
            sprite(c, icon, x - pw / 2 * u - 60, yy - 10, 120 * u, rot=-10)
    for k in range(4):
        u = eo5(prog(t, 5.86 + k * 0.06, 6.25 + k * 0.06))
        x = 80 + k * 250 + (1 - u) * -420 + (t - B[3]) * 160; y = 1480 + k * 90
        rrect(c, x, y, 210, 82, 14, P(hexc(RED, u)))

def s_spark(c, t, S):
    dark(c, S)
    ts = find('spark')
    tt = t - B[4]
    for k, x in enumerate([290, 790]):
        pulse = 0.5 + 0.5 * math.sin(tt * 7 + k)
        c.drawCircle(x, 640, 150, P(hexc('#FF7A2E', 0.55), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 70 + 30 * pulse)))
        happy = t >= ts - LEAD
        pu = eback(prog(t, ts - LEAD, ts + 0.25), 2.0) if happy else 1.0
        name = ('starstruck.png' if k == 0 else 'hearteyes.png') if happy else 'pensive.png'
        sprite(c, name, x, 640 + math.sin(tt * 3 + k) * 12, 230 * (0.85 + 0.15 * pu), rot=math.sin(tt * 2 + k) * 6)
        ph = (tt * 1.1 + k * 0.5) % 1
        c.drawCircle(x, 640, 150 + 160 * ph, SP(hexc('#FF7A2E', 0.8 * (1 - ph)), 4))
    for k in range(8):
        a = k * 0.9 + tt * 0.6
        c.drawCircle(540 + math.cos(a) * 440, 1250 + math.sin(a * 1.3) * 420, 28 + 10 * (k % 3), SP(hexc('#FF7A2E', 0.5), 4))
    u = eback(prog(t, max(B[4], ts - LEAD), ts + 0.24), 1.5)
    if u > 0:
        f = font('serif', 300)
        with Tx(c, s=u, px=540, py=1080):
            shadow_text(c, 'Spark', 540, 1150, f, WHITE, 'c', sh=0.5, off=10, blur=18)
    word(c, 'Emotion', 760, 1270, font('m', 76), '#E8E8E8', t, find('emotion,'), 'c', rise=26)
    fu = eback(prog(t, ts + 0.1, ts + 0.35), 1.8)
    if fu > 0: sprite(c, 'fire.png', 230, 1110, 150 * fu, rot=-12)

def s_moments(c, t, S):
    paper(c, S)
    su = eio3(prog(t, 9.25, 9.62))
    w = lerp(W + 40, 900, su); h = lerp(H + 40, 900, su); r = lerp(0, 70, su)
    z = 1.12 - 0.12 * prog(t, B[5], 9.25)
    if su > 0: card_shadow(c, 540 - w / 2, 960 - h / 2, w, h, r, 0.4)
    with Tx(c, s=z, px=540, py=960):
        draw_media(c, 'r4', 6.0, t - B[5], 540 - w / 2, 960 - h / 2, w, h, r, gray=True, size=(1080, 1920), dur=1.6)
    c.drawRRect(skia.RRect.MakeRectXY(R(540 - w / 2, 960 - h / 2, w, h), r, r), P(hexc('#000000', 0.25 + 0.35 * su)))
    word(c, 'Moments', 540, 1020, font('serif', 200), WHITE, t, find('moments,'), 'c')

def s_trust(c, t, S):
    paper(c, S)
    tb = find('before')
    pan = -520 * eio3(prog(t, 11.0, 11.35))
    with Tx(c, 0, pan):
        node = (540, 860); paths = []
        for (sx, sy, c1x, c1y, c2x, c2y) in [(-60, 300, 220, 300, 300, 740), (1140, 230, 900, 400, 820, 800), (-60, 1360, 150, 1040, 380, 940),
                                             (1140, 1300, 950, 1080, 700, 940), (280, -60, 380, 300, 500, 640), (820, -60, 760, 300, 600, 640)]:
            p = skia.Path(); p.moveTo(sx, sy); p.cubicTo(c1x, c1y, c2x, c2y, node[0], node[1]); paths.append(p)
        du = eio3(prog(t, B[6], B[6] + 0.45))
        for p in paths: trimmed(c, p, SP(hexc(INK), 7), du)
        ru = prog(t, B[6] + 0.15, B[6] + 1.1)
        if 0 < ru < 1:
            pe = skia.Paint(SP(hexc(RED), 14)); pe.setPathEffect(skia.TrimPathEffect.Make(max(0, ru - 0.3), ru))
            for p in paths: c.drawPath(p, pe)
        tt_ = find('trust')
        u = eback(prog(t, tt_ - LEAD, tt_ + 0.22), 1.6)
        if u > 0:
            glossy_pill(c, node[0], node[1], 'TRUST', font('head', 84), RED, WHITE, s=u)
            sprite(c, 'bullseye.png', node[0] + 250 * u, node[1] - 90, 140 * u, rot=12)
        word(c, 'Build', 540, 720, font('r', 70), INK, t, find('build'), 'c', rise=24)
        lu = eio3(prog(t, 11.0, 11.35))
        c.drawLine(540, 930, 540, 930 + 640 * lu, SP(hexc(INK), 7))
        bu_ = eo5(prog(t, tb - LEAD, tb + 0.2))
        if bu_ > 0:
            fb_ = font('r', 64); bw_ = text_w('before they chase', fb_)
            rrect(c, 540 - bw_ / 2 - 30, 1305, bw_ + 60, 96, 24, P(hexc('#F5F0E6', bu_)))
        word(c, 'before they chase', 540, 1375, font('r', 64), INK, t, tb, 'c', rise=22)
        tf = find('followers.')
        fu = eback(prog(t, tf - LEAD, tf + 0.22), 1.6)
        if fu > 0:
            pw, ph = glossy_pill(c, 540, 1600, 'FOLLOWERS', font('head', 84), SAND, INK, s=fu)
            dp = skia.Paint(SP(hexc(NAVY_L), 4, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([16, 12], (t * 40) % 28))
            c.drawRect(R(540 - pw / 2 - 30, 1600 - ph / 2 - 26, pw + 60, ph + 52), dp)

PILLS = [(0.05 + 0.9 * ((k * 0.618) % 1), 0.35 + 0.65 * ((k * 0.37) % 1), (k * 0.29) % 1) for k in range(12)]
def s_pills(c, t, S):
    paper(c, S)
    tt = t - B[7]
    tg = find('great')
    for k, (fx, d, ph) in enumerate(sorted(PILLS, key=lambda p: p[1])):
        u = eo3(prog(t, tg - 0.15 + k * 0.03, tg + 0.15 + k * 0.03))
        if u <= 0: continue
        y = (ph * 2600 - tt * 360 * d) % 2600 - 300
        x = fx * W + math.sin(tt * 1.5 + k) * 24
        blur = (1 - d) * 22
        a_ = u * (0.5 + 0.5 * d)
        f_ = font('m', 92 * d); tw_ = text_w('Great Brands', f_); pw_, ph_ = tw_ + 80, f_.getSize() * 1.6
        mf = skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur) if blur > 0.5 else None
        pp = P(hexc(RED, a_)); tp = P(hexc(WHITE, a_))
        if mf: pp.setMaskFilter(mf); tp.setMaskFilter(mf)
        c.drawRRect(skia.RRect.MakeRectXY(R(x - pw_ / 2, y - ph_ / 2, pw_, ph_), ph_ * 0.32, ph_ * 0.32), pp)
        c.drawString('Great Brands', x - tw_ / 2, cap_center_y(f_, y), f_, tp)
    # hero pill + caption
    hu = eback(prog(t, tg - LEAD, tg + 0.22), 1.5)
    if hu > 0:
        glossy_pill(c, 540, 860, 'Great Brands', font('m', 96), RED, WHITE, s=hu)
    with Layer(c, 1 - prog(t, tg - 0.1, tg + 0.1)):
        word(c, 'But even', 540, 900, font('r', 76), INK, t, find('but'), 'c', rise=20)
    f = font('m', 92); f2 = font('xb', 92)
    line = 'lost in the scroll.'; x0 = 540 - text_w(line, f) / 2
    rrect(c, x0 - 40, 1010, text_w(line, f) + 80, 140, 30, P(hexc('#F5F0E6', 0.85 * clamp((t - find('lost', 14.0)) * 5)),
                                                                   MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
    for s, off, key, ff in [('lost', 0, 'lost', f), ('in', text_w('lost ', f), 'in', f), ('the', text_w('lost in ', f), 'the', f),
                            ('scroll.', text_w('lost in the ', f), 'scroll.', f2)]:
        word(c, s, x0 + off, 1110, ff, INK, t, find(key, 14.0), rise=28)

def s_answer(c, t, S):
    paper(c, S)
    word(c, 'The', 120, 760, font('r', 90), INK, t, B[8] + 0.08)
    ta = find('answer')
    u = eo5(prog(t, ta - LEAD, ta + 0.22))
    fS = font('serif', 205); tw = text_w('Answer?', fS)
    if u > 0:
        card_shadow(c, 90, 800, (tw + 80) * u, 230, 6, 0.2)
        c.drawRect(R(90, 800, (tw + 80) * u, 230), P(hexc(RED)))
    word(c, 'Answer?', 130, 985, fS, INK, t, ta, rise=40)
    word(c, "isn't", 130, 1150, font('r', 84), INK, t, find("isn't"))
    word(c, 'more', 950, 1150, font('r', 84), INK, t, find('more'), 'r')
    tp = find('posts.')
    pu = eback(prog(t, tp - LEAD, tp + 0.22), 1.6)
    crumble = eio3(prog(t, tp + 0.55, tp + 0.9))
    if pu > 0 and crumble < 1:
        with Tx(c, 0, crumble * 120, rot=crumble * 25, px=540, py=1340):
            with Layer(c, 1 - crumble):
                glossy_pill(c, 540, 1340, 'posts', font('head', 84), SAND, INK, s=pu * (1 - 0.4 * crumble))

def s_plan(c, t, S):
    paper(c, S)
    for s, x, key in [("it's", 170, "it's"), ('a', 430, 'a'), ('sharper', 600, 'sharper')]:
        word(c, s, x, 1290, font('r', 84), INK, t, find(key, 17.5))
    fP = font('serif', 340); tw = text_w('Plan.', fP); tpl = find('plan,')
    word(c, 'Plan.', 540, 1080, fP, INK, t, tpl, 'c', rise=50)
    bu = eo5(prog(t, tpl + 0.08, tpl + 0.3))
    if bu > 0:
        x0, y0, bw, bh = 540 - tw / 2 - 50, 820, tw + 100, 340
        dp = skia.Paint(SP(hexc(NAVY_L), 4, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([18, 12], 0))
        with Layer(c, bu):
            c.drawRect(R(x0, y0, bw, bh), dp)
            for hx, hy in [(x0, y0), (x0 + bw, y0), (x0, y0 + bh), (x0 + bw, y0 + bh)]:
                c.drawRect(R(hx - 13, hy - 13, 26, 26), P(hexc(WHITE))); c.drawRect(R(hx - 13, hy - 13, 26, 26), SP(hexc(NAVY_L), 4))
        au = eo5(prog(t, tpl + 0.12, tpl + 0.45))
        ax, ay = lerp(1000, x0 + bw - 14, au), lerp(1600, y0 + bh - 14, au)
        click = 1 + 0.25 * math.sin(math.pi * prog(t, tpl + 0.45, tpl + 0.6))
        with Tx(c, s=click, px=ax, py=ay):
            ar = skia.Path(); ar.moveTo(ax, ay); ar.lineTo(ax + 24, ay + 70); ar.lineTo(ax + 37, ay + 43); ar.lineTo(ax + 66, ay + 40); ar.close()
            c.drawPath(ar, P(hexc('#000000', 0.25), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6)))
            c.drawPath(ar, P(hexc(RED)))

def s_bolder(c, t, S):
    paper(c, S)
    tiles = [('r7', 35.4, 40, 230, 600, 470), ('r11', 20.6, 40, 730, 295, 380), ('r1', 17.0, 345, 730, 295, 380),
             ('r10', 2.6, 40, 1140, 295, 380), ('r4', 24.0, 345, 1140, 295, 380), ('r5', 32.4, 40, 1550, 600, 300)]
    for k, (rl, st, x, y, w, h) in enumerate(tiles):
        u = eback(prog(t, B[10] + k * 0.035, B[10] + 0.24 + k * 0.035), 1.4)
        if u <= 0: continue
        with Tx(c, s=u, px=x + w / 2, py=y + h / 2):
            card_shadow(c, x, y, w, h, 22, 0.3)
            draw_media(c, rl, st, t - B[10], x, y, w, h, 22, size=(540, 540) if w > 400 else (360, 460))
    for s, x, col, key in [('BOLDER', 880, RED, 'bolder'), ('CONTENT', 680, INK, 'content,')]:
        tk = find(key, 18.0)
        u = eo5(prog(t, tk - LEAD, tk + 0.22))
        if u <= 0: continue
        f = font('cond', 228)
        with Tx(c, x, 960, rot=90):
            c.save(); c.clipRect(R(-1000, -220, 2000, 260))
            shadow_text(c, s, 0, (1 - u) * 250, f, col, 'c', sh=0.2, track=4)
            c.restore()

def s_stories(c, t, S):
    paper(c, S)
    word(c, 'Stories', 540, 470, font('cond', 380), RED, t, find('stories'), 'c', rise=70)
    f = font('r', 66)
    for s, key, x in [('that', 'that', 70), ('make', 'make', 330), ('people', 'people', 600), ('stop', 'stop', 900)]:
        word(c, s, x, 580, font('xb' if s == 'stop' else 'r', 66), INK, t, find(key, 20.5), rise=20)
    st0 = find('stories')
    u = eo5(prog(t, st0 + 0.05, st0 + 0.4))
    tand = find('and', 22.0)
    if u > 0:
        rl, st = ('r8', 11.9) if t < tand else ('r9', 34.0)
        with Tx(c, 0, (1 - u) * 340):
            card_shadow(c, 30, 640, 1020, 680, 34)
            draw_media(c, rl, st, t - (B[11] if t < tand else tand), 30, 640, 1020, 680, 34, size=(1020, 680))
    word(c, 'and', 1000, 1410, font('r', 64), INK, t, tand, 'r', rise=18)
    ts = find('stay.')
    u = eback(prog(t, ts - LEAD, ts + 0.24), 1.5)
    if u > 0:
        fS = font('cond', 560)
        with Tx(c, s=lerp(1.45, 1.0, u), px=540, py=1650):
            with Layer(c, clamp(u * 2)):
                shadow_text(c, 'STAY', 540, cap_center_y(fS, 1650), fS, NAVY, 'c', sh=0.28, off=14, blur=16)

def s_search(c, t, S):
    paper(c, S)
    u = eo5(prog(t, B[12], B[12] + 0.3))
    bw = lerp(260, 1240, u); bh = 210; x0 = 540 - bw / 2; y0 = 960 - bh / 2
    c.drawRRect(skia.RRect.MakeRectXY(R(x0 + 6, y0 + 26, bw, bh), 105, 105), P(hexc('#000000', 0.2), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
    rrect(c, x0, y0, bw, bh, 105, P(hexc('#FFFFFF')))
    if u < 0.9: return
    ix = min(x0 + bw - 90, 1000)
    c.drawCircle(ix, 954, 26, SP(hexc(NAVY_L), 8)); c.drawLine(ix + 18, 972, ix + 36, 990, SP(hexc(NAVY_L), 8))
    mx = ix - 90
    rrect(c, mx - 13, 924, 26, 48, 13, P(hexc(RED))); c.drawLine(mx, 984, mx, 1000, SP(hexc(RED), 5))
    f = font('r', 66)
    ws = [(w_, T(a)) for a, b, w_ in WORDS if 23.4 <= a <= 27.5]
    s = ''
    for w_, tw0 in ws:
        if t >= tw0 - LEAD:
            n = int(clamp((t - tw0 + LEAD) / 0.03, 0, len(w_)))
            s += (' ' if s else '') + w_[:n]
    tw = text_w(s, f) if s else 0
    left = max(x0 + 70, 40); avail = (mx - 50) - left
    c.save(); c.clipRect(R(left - 10, y0, avail + 20, bh))
    tx = left - max(0, tw - avail)
    if s: text(c, s, tx, cap_center_y(f, 960), f, hexc(INK))
    if int(t * 3) % 2 == 0: c.drawRect(R(tx + tw + 8, 918, 4, 84), P(hexc(INK)))
    c.restore()
    mu = eback(prog(t, 22.4, 22.7), 1.6)
    if mu > 0: sprite(c, 'magnifier.png', 900, 700, 190 * mu, rot=-12)

def s_partner(c, t, S):
    paper(c, S)
    f = font('r', 84); line = "A partner that doesn't"
    x0 = 540 - text_w(line, f) / 2
    for s, key in [('A', 'A'), ('partner', 'partner'), ('that', 'that'), ("doesn't", "doesn't")]:
        word(c, s, x0 + text_w(line[:line.index(s)], f), 820, f, INK, t, find(key, 27.5), rise=26)
    word(c, 'just', x0, 1100, f, INK, t, find('just', 27.5), rise=26)
    tsh = find('shoot,', 27.5)
    u = eback(prog(t, tsh - LEAD, tsh + 0.22), 1.6)
    if u > 0:
        fS = font('cond', 260)
        jx = x0 + text_w('just ', f)
        with Tx(c, s=u, px=jx + 290, py=1030):
            shadow_text(c, 'SHOOT', jx, 1140, fS, RED, sh=0.28, off=12, blur=14)
        sprite(c, 'moviecam.png', 880, 1380, 220 * u, rot=10)

CUTS = [('PLANS', 'cut_plans.png', NAVY, 'plans', 'bulb.png'), ('CREATES', 'cut_creates.png', RED, 'creates', 'pencil.png'),
        ('DELIVERS', 'cut_delivers.png', SAND, 'delivers', 'package.png')]
def s_cutouts(c, t, S):
    paper(c, S)
    times = [B[14]] + [find(cc[3], 29.0) - 0.1 for cc in CUTS[1:]]
    k = max(i for i in range(3) if t >= times[i])
    lab, cut, col, key, icon = CUTS[k]
    t0 = times[k]
    u = eo5(prog(t, t0, t0 + 0.24))
    bl = (1 - u) * 30
    p_ = skia.Paint(); p_.setAlphaf(clamp(u * 2))
    if bl > 0.5 and k > 0: p_.setImageFilter(skia.ImageFilters.Blur(bl, bl * 0.3))
    c.saveLayer(None, p_)
    drift = (t - t0) * 30
    with Tx(c, (1 - u) * (340 if k % 2 else -340), 0, s=lerp(1.15, 1.0, u) + (t - t0) * 0.03, rot=lerp(5, 0, u), px=540, py=1050):
        for (cx_, cy_, w_, h_, cc_, sd) in [(300, 1460, 820, 640, col, 3 + k), (820, 820, 560, 480, [RED, SAND, NAVY][k], 9 + k)]:
            pth = torn(cx_, cy_, w_, h_, sd)
            c.drawPath(pth, P(hexc('#000000', 0.18), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14)))
            c.drawPath(pth, P(hexc(cc_)))
            for j in range(40):
                rng = np.random.default_rng(sd * 100 + j)
                c.drawLine(cx_ + rng.uniform(-w_ / 2.6, w_ / 2.6), cy_ + rng.uniform(-h_ / 2.6, h_ / 2.6),
                           cx_ + rng.uniform(-w_ / 2.6, w_ / 2.6), cy_ + rng.uniform(-h_ / 2.6, h_ / 2.6), SP(hexc('#FFFFFF', 0.06), 3))
        im = img(cut); hh = 1150; ww = hh * im.width() / im.height()
        if ww > 980: ww = 980; hh = ww * im.height() / im.width()
        cx_, cy_ = 560, 1220 - drift * 0.3
        gp = skia.Paint(ColorFilter=B2.BR.GRAY if hasattr(B2.BR, 'GRAY') else BR.GRAY)
        sp = skia.Paint(ImageFilter=skia.ImageFilters.DropShadowOnly(0, 18, 18, 18, skia.ColorSetARGB(110, 0, 0, 0)))
        c.drawImageRect(im, R(cx_ - ww / 2, cy_ - hh / 2, ww, hh), skia.SamplingOptions(skia.FilterMode.kLinear), sp)
        c.drawImageRect(im, R(cx_ - ww / 2, cy_ - hh / 2, ww, hh), skia.SamplingOptions(skia.FilterMode.kLinear), gp)
        fM = font('marker', 190)
        if text_w(lab, fM) > 760: fM = font('marker', 190 * 760 / text_w(lab, fM))
        with Tx(c, rot=-8, px=420, py=380):
            shadow_text(c, lab, 90, 440, fM, INK, sh=0.18, off=6, blur=6)
            bu = eo5(prog(t, t0 + 0.08, t0 + 0.3))
            bp = skia.Path(); bp.moveTo(100, 490); bp.cubicTo(380, 465, 650, 500, 100 + text_w(lab, fM), 478)
            trimmed(c, bp, SP(hexc(RED), 20), bu)
        iu = eback(prog(t, t0 + 0.1, t0 + 0.35), 1.8)
        if iu > 0: sprite(c, icon, 940, 640, 210 * iu, rot=12)
        for j in range(5):
            a = -1.2 + j * 0.3
            c.drawLine(760 + math.cos(a) * 60, 240 + math.sin(a) * 60, 760 + math.cos(a) * 110, 240 + math.sin(a) * 110, SP(hexc(INK), 7))
    c.restore()

def s_wall(c, t, S):
    paper(c, S)
    tt = t - B[15]
    cols = [NAVY, RED, '#B58A3A', INK]
    for i, (nm, fk) in enumerate(BR.CLIENTS):
        r_, k = divmod(i, 2)
        x = 280 if k == 0 else 800; y = 150 + r_ * 230 + (k * 110) - tt * 40
        u = eo3(prog(t, B[15] + i * 0.02, B[15] + 0.3 + i * 0.02))
        sz = {'head': 52, 'serif': 68, 'cond': 76, 'bebas': 80, 'xb': 48}[fk]
        f = font(fk, sz)
        if text_w(nm, f) > 470: f = font(fk, sz * 470 / text_w(nm, f))
        with Layer(c, u * 0.5):
            text(c, nm, x, y, f, hexc(cols[i % 4]), 'c')
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 980), 560, [hexc('#F5F0E6', 1.0), hexc('#F5F0E6', 0.92), hexc('#F5F0E6', 0.0)], [0, 0.55, 1])
    c.drawPaint(skia.Paint(Shader=rs))
    fT = font('head', 100)
    line = 'The Filmy Space'; x0 = 540 - text_w(line, fT) / 2
    for s, key, col in [('The', 'the', INK), ('Filmy', 'filmy', RED), ('Space', 'space', INK)]:
        tk = find(key, 34.5)
        u = eback(prog(t, tk - LEAD, tk + 0.22), 1.5)
        if u > 0:
            x = x0 + text_w(line[:line.index(s)], fT)
            with Tx(c, s=u, px=x + text_w(s, fT) / 2, py=1020):
                shadow_text(c, s, x, cap_center_y(fT, 1020), fT, col, sh=0.2)
    lu = eback(prog(t, find('filmy', 34.5), find('filmy', 34.5) + 0.25), 1.6)
    if lu > 0:
        logo_blocks(c, 540, 830, 0.42 * lu, 1.0)

LB = [(189, 369), (417, 597), (646, 826)]; BY0, BY1 = 175, 462
def logo_blocks(c, cx, cy, sc, alpha=1.0, gray=False, rise=None):
    lg = img('../logo.png')
    lw = LB[-1][1] - LB[0][0] + 1; bh = (BY1 - BY0 + 1) * sc
    x0 = cx - lw * sc / 2; ytop = cy - bh / 2
    p = skia.Paint(); p.setAlphaf(clamp(alpha))
    if gray: p.setColorFilter(BR.GRAY)
    rects = []
    for i, (a, b) in enumerate(LB):
        dx = x0 + (a - LB[0][0]) * sc; bw = (b - a + 1) * sc
        c.drawImageRect(lg, R(a, BY0, b - a + 1, BY1 - BY0 + 1), R(dx, ytop, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        rects.append(R(dx, ytop, bw, bh))
    return rects

def s_logo(c, t, S):
    c.drawPaint(P(hexc('#050507')))
    tt = t - B[16]
    on = 0.75  # power-on moment
    zoom = lerp(2.6, 1.0, eio3(prog(t, B[16], B[16] + on)))
    flick = [0.25, 1.0, 0.45, 1.0, 0.7, 1.0]
    fi = int(clamp((tt - on) / 0.05, 0, len(flick) - 1)) if tt >= on else -1
    lit = 0.0 if fi < 0 else flick[fi]
    gu = eo3(prog(t, B[16] + on, B[16] + on + 0.8))
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 900), 1000, [hexc(NAVY, 0.55 * gu * lit), hexc('#050507', 0.0)])
    c.drawPaint(skia.Paint(Shader=rs))
    sc = 0.95 * zoom * (1 + 0.04 * eo3(prog(t, B[16] + on, END)))
    if lit > 0:
        gl = skia.Paint(ImageFilter=skia.ImageFilters.Blur(60, 60))
        c.saveLayer(None, gl); logo_blocks(c, 540, 900, sc, 0.9 * lit); c.restore()
    rects = logo_blocks(c, 540, 900, sc, 0.35 if lit == 0 else lit, gray=(lit == 0))
    # lens flare streak
    su = prog(t, B[16] + on + 0.05, B[16] + on + 0.7)
    if 0 < su < 1:
        fx = lerp(-200, 1280, eio3(su))
        g = skia.GradientShader.MakeLinear([skia.Point(fx - 500, 0), skia.Point(fx + 500, 0)], [hexc('#FFFFFF', 0.0), hexc('#FFE7B8', 0.85), hexc('#FFFFFF', 0.0)])
        c.drawRect(R(0, 893, W, 14), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kPlus,
                                                  MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6)))
        c.drawCircle(fx, 900, 90, P(hexc('#FFE7B8', 0.35 * math.sin(math.pi * su)), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 50)))
        c.save(); clipp = skia.Path()
        for rr in rects: clipp.addRect(rr)
        c.clipPath(clipp, True)
        g2 = skia.GradientShader.MakeLinear([skia.Point(fx - 140, 0), skia.Point(fx + 140, 0)], [hexc('#FFFFFF', 0.0), hexc('#FFFFFF', 0.6), hexc('#FFFFFF', 0.0)])
        with Tx(c, rot=18, px=540, py=900):
            c.drawRect(R(-600, -200, 2300, 2300), skia.Paint(Shader=g2, BlendMode=skia.BlendMode.kPlus))
        c.restore()
    f = font('b', 46)
    for s, tk, y in [('BORN FROM BELIEF.', T(36.81), 1160), ('BUILT TO GROW BRANDS.', T(38.12), 1235)]:
        u = eo5(prog(t, tk - LEAD, tk + 0.3))
        if u <= 0: continue
        with Layer(c, u):
            yy = y + (1 - u) * 16
            if 'GROW' in s:
                tw = text_w(s, f, 7); xx = 540 - tw / 2
                xx += text(c, 'BUILT TO ', xx, yy, f, hexc('#E2E2E2'), track=7) + 7
                xx += text(c, 'GROW', xx, yy, f, hexc(RED), track=7) + 7
                text(c, ' BRANDS.', xx, yy, f, hexc('#E2E2E2'), track=7)
            else:
                text(c, s, 540, yy, f, hexc(SAND), 'c', track=7)

SCENES = [s_globe, s_tiles, s_remember, s_best, s_spark, s_moments, s_trust, s_pills, s_answer, s_plan, s_bolder,
          s_stories, s_search, s_partner, s_cutouts, s_wall, s_logo]

# ---------------------------------------------------------------- finishing: grain + vignette on every scene
_grain = {}
def grain(c, t, S):
    if S not in _grain:
        rng = np.random.default_rng(11); lst = []
        for k in range(6):
            n = rng.integers(0, 255, (int(H * S) // 2, int(W * S) // 2), dtype=np.uint8)
            lst.append(skia.Image.fromarray(np.stack([n, n, n, np.full_like(n, 255)], -1), colorType=skia.kRGBA_8888_ColorType))
        _grain[S] = lst
    g = _grain[S][int(t * 24) % 6]
    p = skia.Paint(BlendMode=skia.BlendMode.kOverlay); p.setAlphaf(0.08)
    c.drawImageRect(g, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    rs = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), H * 0.62, [hexc('#000000', 0.0), hexc('#000000', 0.0), hexc('#000000', 0.32)], [0, 0.6, 1])
    c.drawPaint(skia.Paint(Shader=rs))

_orig_draw_scene = B2.draw_scene
def draw_scene(c, i, t, S):
    _orig_draw_scene(c, i, t, S)
    grain(c, t, S)

B2.SCENES = SCENES
B2.draw_scene = draw_scene
B2.CAM = {1: (1.45, 1.0), 2: (1.0, 1.06), 11: (1.0, 1.06), 12: (1.0, 1.16), 16: (1.0, 1.0)}

if __name__ == '__main__':
    if '--stills' in sys.argv:
        i = sys.argv.index('--stills'); sys.argv[i + 1]
    sys.argv = [a.replace('b2_stills', 'b3_stills') for a in sys.argv]
    B2.main()
