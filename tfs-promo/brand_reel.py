"""TFS brand reel (kinetic typography + feed clips, VO-synced). Design space 1080x1920; --scale 2 => 4K.
python3 brand_reel.py --out part.mp4 --scale 2 --fps 60 --start 0 --end 43
python3 brand_reel.py --stills 1.5,3.5 --scale 1
"""
import argparse, math, os, subprocess, sys
import numpy as np
import skia
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as Rn
from render import (font, hexc, text, text_w, cap_center_y, P, SP, R, rrect, Tx, Layer, NAVY, RED, SAND, WHITE, NAVY_L,
                    clamp, prog, lerp, eo3, eo5, eio3, eback, ei3, trimmed)
for k, f in {'r': 'Inter-Regular.ttf', 'serif': 'PlayfairDisplay-XBoldItalic.ttf', 'marker': 'PermanentMarker.ttf',
             'bebas': 'BebasNeue.ttf'}.items():
    Rn.TF[k] = skia.Typeface.MakeFromFile(os.path.join(HERE, 'fonts', f))

W, H = 1080, 1920
PAPER, INK, DARK = '#F3EFE8', '#141416', '#0D0D10'
FEED = os.path.join(os.path.dirname(HERE), 'feed')
VO_OFF = 0.30
END = 43.0
def V(t): return t + VO_OFF

# scene boundaries (video time)
B = [0, 2.30, 4.62, 6.50, 8.90, 10.25, 13.25, 15.95, 17.90, 19.48, 20.80, 23.80, 28.00, 29.95, 32.75, 35.70, 40.05, END]

# ---------------- media ----------------
_clips = {}
def clipsrc(reel, start, dur=3.0, size=(540, 960)):
    key = (reel, start, dur, size)
    if key not in _clips:
        if dur > 0.1 and sum(1 for k in _clips if k[2] > 0.1) > 6:
            _clips.pop(next(k for k in _clips if k[2] > 0.1))
        _clips[key] = Rn.VideoClip(os.path.join(FEED, reel + '.mp4'), size=size, fps=30, start=start, dur=dur)
    return _clips[key]

GRAY = skia.ColorFilters.Matrix([0.30, 0.59, 0.11, 0, 0, 0.30, 0.59, 0.11, 0, 0, 0.30, 0.59, 0.11, 0, 0, 0, 0, 0, 1, 0])
def draw_media(c, reel, start, tl, x, y, w, h, r=0, gray=False, dur=3.0, size=(540, 960), still=False, path=None, alpha=1.0):
    src = clipsrc(reel, start, 0.05 if still else dur, size)
    img = src.image(0 if still else max(0.0, tl))
    sw, sh = src.w, src.h
    sc = max(w / sw, h / sh); cw, ch = w / sc, h / sc
    p = skia.Paint(AntiAlias=True)
    if gray: p.setColorFilter(GRAY)
    p.setAlphaf(alpha)
    c.save()
    if path is not None: c.clipPath(path, True)
    else: c.clipRRect(skia.RRect.MakeRectXY(R(x, y, w, h), r, r), True)
    c.drawImageRect(img, R((sw - cw) / 2, (sh - ch) / 2, cw, ch), R(x, y, w, h), skia.SamplingOptions(skia.FilterMode.kLinear), p)
    c.restore()

_paper = {}
def paper(c, scale):
    if scale not in _paper:
        s = skia.Surface(int(W * scale), int(H * scale)); cc = s.getCanvas(); cc.scale(scale, scale)
        cc.drawPaint(P(hexc(PAPER)))
        for y in range(0, H, 64): cc.drawLine(0, y, W, y, SP(hexc('#E3A79C', 0.32), 1.4, cap=skia.Paint.kButt_Cap))
        for x in range(0, W, 64): cc.drawLine(x, 0, x, H, SP(hexc('#E3A79C', 0.18), 1.2, cap=skia.Paint.kButt_Cap))
        rng = np.random.default_rng(1)
        n = rng.integers(0, 255, (int(H * scale) // 2, int(W * scale) // 2), dtype=np.uint8)
        g = skia.Image.fromarray(np.stack([n, n, n, np.full_like(n, 255)], -1), colorType=skia.kRGBA_8888_ColorType)
        pp = skia.Paint(BlendMode=skia.BlendMode.kOverlay); pp.setAlphaf(0.10)
        cc.drawImageRect(g, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), pp)
        _paper[scale] = s.makeImageSnapshot()
    c.drawImageRect(_paper[scale], R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), None)

def dark(c, grid=True):
    c.drawPaint(P(hexc(DARK)))
    if grid:
        for y in range(0, H, 96): c.drawLine(0, y, W, y, SP(hexc('#FFFFFF', 0.04), 1.5))
        for x in range(0, W, 96): c.drawLine(x, 0, x, H, SP(hexc('#FFFFFF', 0.04), 1.5))

def pop(t, t0, d=0.28): return eo5(prog(t, t0, t0 + d))

def word(c, s, x, y, f, col, t, t0, align='l', rise=40, d=0.3):
    u = pop(t, t0, d)
    if u <= 0: return
    with Layer(c, clamp(u * 1.5)):
        text(c, s, x, y + (1 - u) * rise, f, hexc(col), align)

def highlight(c, x, y, w, h, u, col):
    if u > 0: c.drawRect(R(x, y, w * u, h), P(hexc(col)))

def pill(c, cx, cy, label, f, fill, fg, s=1.0, stroke=None):
    tw = text_w(label, f); pw, ph = tw + 60, f.getSize() * 1.55
    with Tx(c, s=s, px=cx, py=cy):
        if fill: rrect(c, cx - pw / 2, cy - ph / 2, pw, ph, ph / 2, P(hexc(fill)))
        if stroke: c.drawRRect(skia.RRect.MakeRectXY(R(cx - pw / 2, cy - ph / 2, pw, ph), ph / 2, ph / 2), SP(hexc(stroke), 3))
        text(c, label, cx, cap_center_y(f, cy), f, hexc(fg), 'c')
    return pw, ph

# ======================================================================
GLOBE = [('r1', 16.5), ('r4', 9.0), ('r1', 31.4), ('r4', 22.9), ('r7', 35.0), ('r1', 32.2), ('r4', 1.0), ('r3', 9.0),
         ('r2', 26.0), ('r4', 18.0), ('r1', 29.5), ('r5', 9.8), ('r6', 26.8), ('r4', 6.0)]
def sc1(c, t, S):
    paper(c, S)
    f = font('r', 66)
    for s, x, y, tw in [('In', 110, 250, 0.0), ('a', 330, 250, 0.12), ('world', 640, 250, 0.24), ('full', 200, 350, 0.48), ('of', 520, 350, 0.88)]:
        word(c, s, x, y, f, INK, t, V(tw))
    cx, cy, r = 540, 1010, 400
    u = eback(prog(t, 0.05, 0.55), 1.3)
    with Tx(c, s=max(0.001, u), px=cx, py=cy):
        c.drawCircle(cx + 14, cy + 30, r, P(hexc('#000000', 0.25), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
        cp = skia.Path(); cp.addCircle(cx, cy, r)
        c.save(); c.clipPath(cp, True)
        c.drawCircle(cx, cy, r, P(hexc(NAVY)))
        tw_, th_ = 200, 300; off = (t * 140) % (tw_ + 12)
        for row in range(4):
            for col in range(-1, 6):
                k = (row * 5 + col + 20) % len(GLOBE)
                x = cx - r + col * (tw_ + 12) - off + (row % 2) * 90; y = cy - r - 60 + row * (th_ + 12)
                rl, st = GLOBE[k]
                draw_media(c, rl, st, 0, x, y, tw_, th_, 14, still=True, size=(270, 480))
        sh = skia.GradientShader.MakeRadial(skia.Point(cx - r * 0.35, cy - r * 0.4), r * 1.6,
                                            [hexc('#FFFFFF', 0.25), hexc('#000000', 0.0), hexc('#000000', 0.55)], [0, 0.45, 1])
        c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Shader=sh))
        c.restore()
    cu = eo5(prog(t, V(1.06), V(1.06) + 0.35))
    if cu > 0:
        fC = font('cond', 260)
        c.save(); c.clipRect(R(0, 1050, W * cu, 400))
        text(c, 'CONTENT', 540 + 8, 1330 + 8, fC, hexc('#000000', 0.25), 'c')
        text(c, 'CONTENT', 540, 1330, fC, hexc(RED), 'c')
        c.restore()

def sc2(c, t, S):
    paper(c, S)
    tw_, th_, g = 220, 320, 28
    for col in range(5):
        u = eo5(prog(t, B[1] + col * 0.04, B[1] + 0.4 + col * 0.04))
        for row in range(7):
            x = -120 + col * (tw_ + g); y = -200 + row * (th_ + g) - (1 - u) * 1900 + (col % 2) * 140
            if 1 <= col <= 3 and 1 <= row <= 4: continue
            rrect(c, x, y, tw_, th_, 26, P(hexc(SAND if (row + col) % 3 else NAVY)))
    pu = eo5(prog(t, B[1], B[1] + 0.3))
    with Tx(c, s=lerp(0.85, 1, pu), px=540, py=960):
        rrect(c, 160, 330, 760, 1220, 30, P(hexc(PAPER)))
        word(c, 'The brands that', 540, 560, font('r', 60), INK, t, V(2.04), 'c')
        u = eback(prog(t, V(2.64), V(2.64) + 0.3), 1.6)
        if u > 0:
            fW = font('cond', 380)
            with Tx(c, s=u, px=540, py=880):
                text(c, 'WIN', 540, cap_center_y(fW, 880), fW, hexc(RED), 'c')
        word(c, "aren't the", 540, 1160, font('r', 48), INK, t, V(2.90), 'c')
        u = eo5(prog(t, V(3.58), V(3.58) + 0.3))
        if u > 0:
            fL = font('bebas', 200)
            c.save(); c.clipRect(R(160, 1180, 760, 260))
            text(c, 'LOUDEST', 540, 1400 + (1 - u) * 220, fL, hexc(NAVY), 'c')
            c.restore()
    for k, (rl, st, x, y, rot) in enumerate([('r4', 22.9, 800, 1330, -6), ('r1', 31.4, 790, 300, 5)]):
        u = eback(prog(t, 3.95 + k * 0.15, 4.25 + k * 0.15), 1.5)
        if u > 0:
            with Tx(c, rot=rot, s=u, px=x + 125, py=y + 220):
                rrect(c, x - 8, y - 8, 266, 456, 22, P(hexc(WHITE)))
                draw_media(c, rl, st, t - 3.95, x, y, 250, 440, 16)

def sc3(c, t, S):
    paper(c, S)
    cards = [('r4', 1.0, 230, -9), ('r1', 17.0, 540, 0), ('r4', 9.0, 850, 9)]
    for k, (rl, st, x, rot) in enumerate(cards):
        u = eo5(prog(t, B[2] + k * 0.08, B[2] + 0.45 + k * 0.08))
        if u <= 0: continue
        y = 1180 + (1 - u) * 1100 + abs(k - 1) * 40
        with Tx(c, rot=rot * u, px=x, py=y):
            c.drawRRect(skia.RRect.MakeRectXY(R(x - 150 + 8, y - 266 + 20, 300, 533), 26, 26), P(hexc('#000000', 0.3), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)))
            rrect(c, x - 158, y - 274, 316, 549, 30, P(hexc(SAND if k == 1 else WHITE)))
            draw_media(c, rl, st, t - B[2], x - 150, y - 266, 300, 533, 24)
    word(c, 'the ones people', 540, 470, font('r', 56), INK, t, V(4.62), 'c')
    u = eo5(prog(t, V(4.92) + 0.05, V(4.92) + 0.4))
    fS = font('serif', 170); s = 'Remember'; tw = text_w(s, fS)
    highlight(c, 540 - tw / 2 - 20, 560, tw + 40, 150, u, SAND)
    word(c, s, 540, 690, fS, INK, t, V(4.92), 'c', rise=30)

def sc4(c, t, S):
    dark(c)
    bu = prog(t, B[3], B[3] + 0.35)
    fB = font('head', 86); s = 'THE BEST BRANDS'; tw = text_w(s, fB)
    bx = 540 - tw / 2 - 30
    box = skia.Path(); box.addRect(R(bx, 290, tw + 60, 140))
    trimmed(c, box, SP(hexc(WHITE), 3, cap=skia.Paint.kSquare_Cap), eo3(bu))
    word(c, s, 540, 395, fB, WHITE, t, B[3] + 0.05, 'c', rise=20)
    fade = 1 - prog(t, V(7.0), V(7.0) + 0.25)
    if fade > 0:
        with Layer(c, fade):
            for k, (lab, x, y, t0) in enumerate([('Reach', 260, 700, 6.6), ('Views', 760, 820, 6.75), ('Followers', 380, 1180, 6.9)]):
                u = eback(prog(t, t0, t0 + 0.3), 1.4)
                if u > 0: pill(c, x, y - (t - t0) * 30, lab, font('m', 44), None, WHITE, s=u, stroke='#BBBBBB')
            for k in range(4):
                u = eo5(prog(t, 6.6 + k * 0.1, 7.1 + k * 0.1))
                x = 120 + k * 230 + (1 - u) * -300; y = 1450 + k * 70
                rrect(c, x, y, 180, 70, 12, P(hexc(RED, u)))
    su = prog(t, V(7.0), V(7.0) + 0.3)
    if su > 0:
        for k, x in enumerate([300, 780]):
            pulse = 0.5 + 0.5 * math.sin((t - V(7.0)) * 7 + k)
            c.drawCircle(x, 760, 70, P(hexc(RED, 0.9 * su), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30 + 20 * pulse)))
            c.drawCircle(x, 760, 42, P(hexc('#FF6A5E', su)))
            rr = 80 + 120 * ((t - V(7.0)) * 1.2 % 1)
            c.drawCircle(x, 760, rr, SP(hexc(RED, su * (1 - ((t - V(7.0)) * 1.2 % 1))), 3))
        word(c, 'Spark', 540, 1060, font('serif', 210), WHITE, t, V(7.0), 'c')
        word(c, 'Emotion', 700, 1150, font('m', 60), '#DDDDDD', t, V(7.48), 'c', rise=20)

def sc5(c, t, S):
    c.drawPaint(P(hexc(PAPER)))
    paper(c, S)
    su = eio3(prog(t, V(9.45), V(9.45) + 0.4))
    w = lerp(W, 820, su); h = lerp(H, 820, su); r = lerp(0, 60, su)
    z = 1.08 - 0.08 * prog(t, B[4], B[5])
    with Tx(c, s=z if su == 0 else 1.0, px=540, py=960):
        draw_media(c, 'r4', 6.0, t - B[4], 540 - w / 2, 960 - h / 2, w, h, r, gray=True, size=(1080, 1920), dur=1.6)
    c.drawRRect(skia.RRect.MakeRectXY(R(540 - w / 2, 960 - h / 2, w, h), r, r), P(hexc('#000000', 0.25 + 0.35 * su)))
    word(c, 'Moments', 540, 1000, font('serif', 160), WHITE, t, V(8.66), 'c')

def sc6(c, t, S):
    paper(c, S)
    pan = -420 * eio3(prog(t, V(11.56), V(11.56) + 0.45))
    with Tx(c, 0, pan):
        node = (540, 820)
        paths = []
        for (sx, sy, c1x, c1y, c2x, c2y) in [(-50, 300, 200, 300, 300, 700), (1130, 250, 900, 400, 800, 760), (-50, 1300, 150, 1000, 380, 900),
                                             (1130, 1250, 950, 1050, 700, 900), (300, -50, 380, 300, 500, 600)]:
            p = skia.Path(); p.moveTo(sx, sy); p.cubicTo(c1x, c1y, c2x, c2y, node[0], node[1]); paths.append(p)
        du = eio3(prog(t, B[5], B[5] + 0.6))
        for k, p in enumerate(paths):
            trimmed(c, p, SP(hexc(INK), 5), du)
        ru = prog(t, B[5] + 0.3, B[5] + 1.6)
        if 0 < ru < 1:
            pe = skia.Paint(SP(hexc(RED), 9))
            a, b = max(0, ru - 0.25), ru
            pe.setPathEffect(skia.TrimPathEffect.Make(a, b))
            c.drawPath(paths[1], pe); c.drawPath(paths[2], pe)
        u = eback(prog(t, V(10.02), V(10.02) + 0.3), 1.6)
        if u > 0: pill(c, node[0], node[1], 'TRUST', font('head', 64), RED, WHITE, s=u)
        word(c, 'Build', 540, 700, font('r', 54), INK, t, V(9.72), 'c', rise=20)
        lu = eio3(prog(t, V(11.56), V(11.56) + 0.5))
        c.drawLine(540, 880, 540, 880 + 560 * lu, SP(hexc(INK), 5))
        bu_ = pop(t, V(10.76))
        if bu_ > 0:
            fb_ = font('r', 50); bw_ = text_w('before they chase', fb_)
            rrect(c, 540 - bw_ / 2 - 24, 1250, bw_ + 48, 76, 20, P(hexc(PAPER, bu_)))
        word(c, 'before they chase', 540, 1300, font('r', 50), INK, t, V(10.76), 'c', rise=20)
        fu = eback(prog(t, V(12.08), V(12.08) + 0.3), 1.6)
        if fu > 0:
            pw, ph = pill(c, 540, 1500, 'FOLLOWERS', font('head', 64), SAND, INK, s=fu)
            dp = skia.Paint(SP(hexc(NAVY_L), 3, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([14, 10], (t * 40) % 24))
            c.drawRect(R(540 - pw / 2 - 26, 1500 - ph / 2 - 22, pw + 52, ph + 44), dp)

PILLS = [(0.05 + 0.9 * ((k * 0.618) % 1), 0.4 + 0.6 * ((k * 0.37) % 1), (k * 0.29) % 1) for k in range(16)]
def sc7(c, t, S):
    paper(c, S)
    tt = t - B[6]
    for k, (fx, d, ph) in enumerate(sorted(PILLS, key=lambda p: p[1])):
        u = eo3(prog(t, V(13.40) + k * 0.03, V(13.40) + 0.3 + k * 0.03))
        if u <= 0: continue
        y = (ph * 2400 - tt * 260 * d) % 2400 - 240
        x = fx * W
        blur = (1 - d) * 16
        a_ = u * (0.45 + 0.55 * d)
        f_ = font('m', 54 * d); tw_ = text_w('Great Brands', f_); pw_, ph_ = tw_ + 60, f_.getSize() * 1.55
        mf = skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur) if blur > 0.5 else None
        pp = P(hexc(RED, a_)); tp = P(hexc(WHITE, a_))
        if mf: pp.setMaskFilter(mf); tp.setMaskFilter(mf)
        c.drawRRect(skia.RRect.MakeRectXY(R(x - pw_ / 2, y - ph_ / 2, pw_, ph_), ph_ / 2, ph_ / 2), pp)
        c.drawString('Great Brands', x - tw_ / 2, cap_center_y(f_, y), f_, tp)
    rrect(c, 140, 860, 800, 200, 30, P(hexc(PAPER, 0.85), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20)))
    f = font('m', 76); f2 = font('xb', 76)
    with Layer(c, 1 - prog(t, V(14.2), V(14.2) + 0.25)):
        word(c, 'But even', 540, 820, font('r', 54), INK, t, V(13.04), 'c', rise=16)
    x0 = 540 - text_w('lost in the scroll.', f) / 2
    for s, off, tw0, ff in [('lost', 0, 14.36, f), ('in', text_w('lost ', f), 14.64, f), ('the', text_w('lost in ', f), 14.84, f), ('scroll.', text_w('lost in the ', f), 14.98, f2)]:
        word(c, s, x0 + off, 990, ff, INK, t, V(tw0), rise=20)

def sc8(c, t, S):
    paper(c, S)
    punch = 1 + 0.06 * math.sin(math.pi * prog(t, B[7], B[7] + 0.25))
    with Tx(c, s=punch, px=540, py=960):
        word(c, 'The', 170, 830, font('r', 70), INK, t, V(15.72))
        u = eo5(prog(t, V(15.86), V(15.86) + 0.35))
        fS = font('serif', 190); tw = text_w('Answer?', fS)
        highlight(c, 140, 870, tw + 60, 170, u, RED)
        word(c, 'Answer?', 170, 1010, fS, INK, t, V(15.86), rise=30)
        word(c, "isn't", 180, 1130, font('r', 64), INK, t, V(16.12))
        word(c, 'more', 640, 1130, font('r', 64), INK, t, V(16.54))
        word(c, 'posts.', 640, 1215, font('xb', 64), INK, t, V(16.76))

def sc9(c, t, S):
    paper(c, S)
    for s, x, tw0 in [("it's", 230, 17.66), ('a', 420, 17.84), ('sharper', 560, 17.94)]:
        word(c, s, x, 760, font('r', 64), INK, t, V(tw0))
    fP = font('serif', 260); tw = text_w('Plan.', fP)
    word(c, 'Plan.', 540, 1020, fP, INK, t, V(18.24), 'c', rise=40)
    bu = eo5(prog(t, V(18.24) + 0.15, V(18.24) + 0.45))
    if bu > 0:
        x0, y0, bw, bh = 540 - tw / 2 - 40, 820, tw + 80, 270
        dp = skia.Paint(SP(hexc(NAVY_L), 3, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([16, 10], 0))
        with Layer(c, bu):
            c.drawRect(R(x0, y0, bw, bh), dp)
            for hx, hy in [(x0, y0), (x0 + bw, y0), (x0, y0 + bh), (x0 + bw, y0 + bh)]:
                c.drawRect(R(hx - 10, hy - 10, 20, 20), P(hexc(WHITE))); c.drawRect(R(hx - 10, hy - 10, 20, 20), SP(hexc(NAVY_L), 3))
        au = eo5(prog(t, V(18.24) + 0.2, V(18.24) + 0.6))
        ax, ay = lerp(980, x0 + bw - 10, au), lerp(1500, y0 + bh - 10, au)
        ar = skia.Path(); ar.moveTo(ax, ay); ar.lineTo(ax + 18, ay + 52); ar.lineTo(ax + 28, ay + 32); ar.lineTo(ax + 50, ay + 30); ar.close()
        c.drawPath(ar, P(hexc(RED)))

TILES10 = [('r1', 17.0), ('r4', 9.0), ('r1', 32.2), ('r7', 35.0), ('r4', 24.0), ('r1', 31.4)]
def sc10(c, t, S):
    paper(c, S)
    for k, (rl, st) in enumerate(TILES10):
        u = eback(prog(t, B[9] + k * 0.05, B[9] + 0.3 + k * 0.05), 1.4)
        if u <= 0: continue
        r_, cc = divmod(k, 2)
        x = 40 + cc * 300; y = 250 + r_ * 480
        with Tx(c, s=u, px=x + 135, py=y + 215):
            draw_media(c, rl, st, t - B[9], x, y, 270, 430, 22, size=(360, 640))
    for s, x, col, tw0 in [('BOLDER', 875, RED, 19.24), ('CONTENT', 680, INK, 19.56)]:
        u = eo5(prog(t, V(tw0), V(tw0) + 0.35))
        if u <= 0: continue
        f = font('cond', 210)
        with Tx(c, x, 960, rot=90):
            c.save(); c.clipRect(R(-900, -200, 1800, 240))
            text(c, s, 0, 0 + (1 - u) * 230, f, hexc(col), 'c', track=4)
            c.restore()

def sc11(c, t, S):
    paper(c, S)
    word(c, 'Stories', 540, 400, font('cond', 240), RED, t, V(20.54), 'c')
    f = font('r', 54); line = 'that make people stop'
    x0 = 540 - text_w(line, f) / 2
    for s, tw0 in [('that', 20.90), ('make', 21.22), ('people', 21.40), ('stop', 21.64)]:
        idx = line.index(s if s != 'that' else 'that')
        word(c, s, x0 + text_w(line[:idx], f), 500, font('xb' if s == 'stop' else 'r', 54), INK, t, V(tw0), rise=16)
    u = eo5(prog(t, V(20.54) + 0.15, V(20.54) + 0.55))
    if u > 0:
        with Tx(c, 0, (1 - u) * 300):
            with Layer(c, clamp(u * 2)):
                draw_media(c, 'r4', 12.0, t - B[10], 60, 600, 960, 640, 30, size=(720, 1280))
    word(c, 'and', 540, 1350, font('r', 54), INK, t, V(22.25), 'c', rise=14)
    u = eback(prog(t, V(22.61), V(22.61) + 0.3), 1.5)
    if u > 0:
        fS = font('cond', 420)
        with Tx(c, s=lerp(1.4, 1.0, u), px=540, py=1650):
            with Layer(c, clamp(u * 2)):
                text(c, 'STAY', 540, cap_center_y(fS, 1650), fS, hexc(NAVY), 'c')

Q12 = [('Every', 23.59), ('brand', 23.82), ('needs', 24.12), ('a', 24.38), ('creative', 24.52), ('partner', 24.82), ('that', 25.24),
       ('knows', 25.48), ('exactly', 25.72), ('how', 26.44), ('to', 26.72), ('make', 26.82), ('it', 26.98), ('seen.', 27.12)]
def sc12(c, t, S):
    paper(c, S)
    u = eo5(prog(t, B[11], B[11] + 0.4))
    bw = lerp(200, 980, u); bh = 150; x0 = 540 - bw / 2; y0 = 960 - bh / 2
    c.drawRRect(skia.RRect.MakeRectXY(R(x0 + 4, y0 + 18, bw, bh), 75, 75), P(hexc('#000000', 0.18), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 26)))
    rrect(c, x0, y0, bw, bh, 75, P(hexc('#FFFFFF')))
    if u < 0.9: return
    ix = x0 + bw - 70
    lens = skia.Path(); c.drawCircle(ix, 960 - 4, 20, SP(hexc(NAVY_L), 6)); c.drawLine(ix + 14, 960 + 10, ix + 28, 960 + 24, SP(hexc(NAVY_L), 6))
    mx = ix - 70
    rrect(c, mx - 10, 960 - 26, 20, 36, 10, P(hexc(RED))); c.drawLine(mx, 960 + 18, mx, 960 + 30, SP(hexc(RED), 4))
    f = font('r', 46)
    s = ' '.join(wd for wd, tw0 in Q12 if t >= V(tw0))
    tw = text_w(s, f) if s else 0
    avail = bw - 230
    c.save(); c.clipRect(R(x0 + 50, y0, avail + 10, bh))
    tx = x0 + 60 - max(0, tw - avail)
    if s: text(c, s, tx, cap_center_y(f, 960), f, hexc(INK))
    if int(t * 3) % 2 == 0: c.drawRect(R(tx + tw + 6, 960 - 30, 3, 60), P(hexc(INK)))
    c.restore()

def sc13(c, t, S):
    paper(c, S)
    f = font('r', 66); line = "A partner that doesn't"
    x0 = 540 - text_w(line, f) / 2
    for s, tw0 in [('A', 27.78), ('partner', 27.92), ('that', 28.18), ("doesn't", 28.40)]:
        word(c, s, x0 + text_w(line[:line.index(s)], f), 880, f, INK, t, V(tw0), rise=20)
    word(c, 'just', 300, 1020, f, INK, t, V(28.72), rise=20)
    u = eback(prog(t, V(28.90), V(28.90) + 0.3), 1.6)
    if u > 0:
        fS = font('cond', 170)
        with Tx(c, s=u, px=620, py=990):
            text(c, 'SHOOT', 460, 1050, fS, hexc(RED))

CUT = [('PLANS', 'r1', 2.0, NAVY, 29.74 + 0.26), ('CREATES', 'r1', 32.2, RED, 30.28 + 0.22), ('DELIVERS', 'r1', 31.4, SAND, 31.20 + 0.15)]
def torn(cx, cy, w, h, seed):
    rng = np.random.default_rng(seed); p = skia.Path()
    pts = []
    n = 26
    for i in range(n):
        a = i / n * 2 * math.pi
        rr = 1 + rng.uniform(-0.12, 0.12)
        pts.append((cx + math.cos(a) * w / 2 * rr, cy + math.sin(a) * h / 2 * rr))
    p.moveTo(*pts[0]); [p.lineTo(*q) for q in pts[1:]]; p.close(); return p
def sc14(c, t, S):
    paper(c, S)
    k = 0
    for i, cc in enumerate(CUT):
        if t >= V(cc[4]) - 0.05: k = i
    lab, rl, st, col, tw0 = CUT[k]
    t0 = B[13] if k == 0 else V(tw0) - 0.05
    u = eo5(prog(t, t0, t0 + 0.3))
    with Tx(c, s=lerp(1.12, 1.0, u), rot=lerp(4, 0, u), px=540, py=1000):
        c.drawPath(torn(330, 1350, 700, 520, 3 + k), P(hexc(col)))
        c.drawPath(torn(800, 760, 520, 420, 9 + k), P(hexc([RED, SAND, NAVY][k])))
        rp = skia.Path(); rng = np.random.default_rng(20 + k)
        x0, y0, w, h = 190, 560, 700, 980
        pts = [(x0 + rng.uniform(-14, 14), y0 + rng.uniform(-14, 14)), (x0 + w + rng.uniform(-14, 14), y0 + rng.uniform(-14, 14)),
               (x0 + w + rng.uniform(-14, 14), y0 + h + rng.uniform(-14, 14)), (x0 + rng.uniform(-14, 14), y0 + h + rng.uniform(-14, 14))]
        rp.moveTo(*pts[0]); [rp.lineTo(*q) for q in pts[1:]]; rp.close()
        c.drawPath(rp, P(hexc('#FFFFFF')))
        sp = skia.Path(); sp.moveTo(pts[0][0] + 14, pts[0][1] + 14); [sp.lineTo(q[0] + (14 if i in (0, 3) else -14), q[1] + (14 if i < 2 else -14)) for i, q in enumerate(pts[1:], 1)]; sp.close()
        draw_media(c, rl, st, t - t0, x0, y0, w, h, gray=True, path=sp, size=(720, 1280))
        fM = font('marker', 150)
        with Tx(c, rot=-8, px=420, py=420):
            text(c, lab, 140, 470, fM, hexc(INK))
            bu = eo5(prog(t, t0 + 0.12, t0 + 0.4))
            bp = skia.Path(); bp.moveTo(150, 510); bp.cubicTo(350, 490, 600, 520, 150 + text_w(lab, fM), 500)
            trimmed(c, bp, SP(hexc(RED), 16), bu)
        for j in range(5):
            a = -1.2 + j * 0.3
            c.drawLine(930 + math.cos(a) * 50, 330 + math.sin(a) * 50, 930 + math.cos(a) * 95, 330 + math.sin(a) * 95, SP(hexc(INK), 6))

FLASH = [('SCRIPT', 'r4', 22.9, NAVY, 31.88 + 0.33), ('SHOOT', 'r7', 35.0, RED, 32.76 + 0.48), ('EDIT', 'r1', 17.0, SAND, 33.54 + 0.5), ('POST', 'r4', 1.0, NAVY, 34.20 + 0.46)]
def sc15(c, t, S):
    k = 0
    for i, f in enumerate(FLASH):
        if t >= V(f[4]) - 0.03: k = i
    lab, rl, st, col, tw0 = FLASH[k]
    t0 = B[14] if k == 0 else V(tw0) - 0.03
    if k > 0:
        pl = FLASH[k - 1]
        draw_media(c, pl[1], pl[2], t - t0 + 0.7, 0, 0, W, H, size=(1080, 1920), dur=1.6)
    wu = 1 - (1 - prog(t, t0, t0 + 0.2)) ** 4 if k > 0 else 1
    top = H * (1 - wu)
    c.save(); c.clipRect(R(0, top, W, H - top))
    with Tx(c, 0, top * 0.3, s=lerp(1.1, 1.0, eo5(prog(t, t0, t0 + 0.5))), px=540, py=960):
        draw_media(c, rl, st, t - t0, 0, 0, W, H, size=(1080, 1920), dur=1.6)
    c.restore()
    c.drawPaint(P(hexc('#000000', 0.28)))
    u = eback(prog(t, t0 + 0.02, t0 + 0.28), 1.6)
    f = font('head', 150); tw = text_w(lab, f)
    with Tx(c, s=u, px=540, py=960):
        rrect(c, 540 - tw / 2 - 50, 960 - 120, tw + 100, 240, 20, P(hexc(col)))
        text(c, lab, 540, cap_center_y(f, 960), f, hexc(INK if col == SAND else WHITE), 'c')

CLIENTS = [('THE FIVE ELEMENTS', 'head'), ('Phulwari', 'serif'), ('FUNHOODS', 'cond'), ('HOUSE OF STRENGTH', 'bebas'), ('Swad Exotica', 'serif'),
           ('R.O.W', 'head'), ('SCIENCE ACADEMY', 'xb'), ('Ghunghat Ghar', 'serif'), ('JALSARA', 'cond'), ('TEQUILA', 'bebas'),
           ('BATTLE & BOUNCE', 'head'), ('Eminence', 'serif'), ('IBRAHIM FOOTWEARS', 'xb'), ('COLSEE PAINTS', 'cond'), ('SAI SHREE ACADEMY', 'bebas'), ('HALLBERD', 'head')]
def sc16(c, t, S):
    paper(c, S)
    tt = t - B[15]
    for i, (nm, fk) in enumerate(CLIENTS):
        r_, k = divmod(i, 2)
        x = 290 if k == 0 else 790; y = 200 + r_ * 205 + (k * 90) - tt * 22
        u = eo3(prog(t, B[15] + i * 0.035, B[15] + 0.4 + i * 0.035))
        sz = {'head': 44, 'serif': 58, 'cond': 64, 'bebas': 66, 'xb': 40}[fk]
        f = font(fk, sz)
        if text_w(nm, f) > 440: f = font(fk, sz * 440 / text_w(nm, f))
        with Layer(c, u * 0.55):
            text(c, nm, x, y, f, hexc('#7E7E86'), 'c')
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 980), 520, [hexc(PAPER, 1.0), hexc(PAPER, 0.9), hexc(PAPER, 0.0)], [0, 0.55, 1])
    c.drawPaint(skia.Paint(Shader=rs))
    fT = font('head', 104)
    line = 'The Filmy Space'; x0 = 540 - text_w(line, fT) / 2
    for s, tw0, col in [('The', 35.51, INK), ('Filmy', 35.80, RED), ('Space', 36.10, INK)]:
        u = eback(prog(t, V(tw0), V(tw0) + 0.3), 1.5)
        if u > 0:
            x = x0 + text_w(line[:line.index(s)], fT)
            with Tx(c, s=u, px=x + text_w(s, fT) / 2, py=930):
                text(c, s, x, cap_center_y(fT, 930), fT, hexc(col))
    word(c, 'Born from belief.', 540, 1060, font('m', 54), INK, t, V(36.81), 'c', rise=16)
    f2 = font('m', 54); l2 = 'Built to grow brands.'; x2 = 540 - text_w(l2, f2) / 2
    u = pop(t, V(38.12))
    if u > 0:
        with Layer(c, u):
            yy = 1140 + (1 - u) * 16
            text(c, 'Built to ', x2, yy, f2, hexc(INK))
            text(c, 'grow', x2 + text_w('Built to ', f2), yy, font('xb', 54), hexc(RED))
            text(c, ' brands.', x2 + text_w('Built to grow', f2) + 0 * 0, yy, f2, hexc(INK))

_logo = None
BLOCKS = [(189, 369), (417, 597), (646, 826)]; BY0, BY1 = 175, 462
def sc17(c, t, S):
    global _logo
    if _logo is None: _logo = skia.Image.open(os.path.join(HERE, 'logo.png'))
    c.drawPaint(P(hexc('#050507')))
    gu = eo3(prog(t, B[16], B[16] + 1.0))
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 960), 900, [hexc(NAVY, 0.45 * gu), hexc('#050507', 0.0)])
    c.drawPaint(skia.Paint(Shader=rs))
    sc = 0.9 * (1 + 0.04 * eo3(prog(t, B[16], END)))
    lw = BLOCKS[-1][1] - BLOCKS[0][0] + 1; bh = (BY1 - BY0 + 1) * sc
    x0 = 540 - lw * sc / 2; ytop = 960 - bh / 2
    for i, (a, b) in enumerate(BLOCKS):
        u = eo5(prog(t, B[16] + 0.1 + i * 0.1, B[16] + 0.7 + i * 0.1))
        if u <= 0: continue
        dx = x0 + (a - BLOCKS[0][0]) * sc; bw = (b - a + 1) * sc
        src = R(a, BY0, b - a + 1, BY1 - BY0 + 1)
        gp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(40, 40)); gp.setAlphaf(0.55 * u * (0.8 + 0.2 * math.sin(t * 3 + i)))
        c.drawImageRect(_logo, src, R(dx, ytop, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), gp)
        c.save(); c.clipRect(R(dx, ytop, bw, bh))
        c.drawImageRect(_logo, src, R(dx, ytop + (1 - u) * bh, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), None)
        c.restore()

SCENES = [sc1, sc2, sc3, sc4, sc5, sc6, sc7, sc8, sc9, sc10, sc11, sc12, sc13, sc14, sc15, sc16, sc17]
def frame(c, t, S):
    for i in range(len(SCENES)):
        if B[i] <= t < B[i + 1] or (i == len(SCENES) - 1 and t >= B[i]):
            SCENES[i](c, t, S); return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='brand.mp4'); ap.add_argument('--fps', type=int, default=60); ap.add_argument('--scale', type=float, default=2)
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=END)
    ap.add_argument('--stills', default=''); ap.add_argument('--crf', type=int, default=18)
    a = ap.parse_args()
    S = a.scale; OW, OH = int(W * S), int(H * S)
    surf = skia.Surface(OW, OH); c = surf.getCanvas()
    def render(t):
        c.clear(hexc('#000000')); c.save(); c.scale(S, S); frame(c, t, S); c.restore()
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'brand_stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s)
            skia.Image.fromarray(render(t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'brand_stills', f'{t:06.2f}.png'))
        return
    n0, n1 = int(round(a.start * a.fps)), int(round(a.end * a.fps))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{OW}x{OH}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', str(a.crf), '-maxrate', '16M', '-bufsize', '32M', '-pix_fmt', 'yuv420p',
           '-x264-params', 'threads=2', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        pr.stdin.write(render(n / a.fps).tobytes())
        if n % (a.fps * 2) == 0: print(f'{n / a.fps:.1f}', flush=True)
    pr.stdin.close(); pr.wait(); print('done')

if __name__ == '__main__':
    main()
