"""TFS brand reel v2 — re-timed to the reference's music (35.44s), camera motion, motion-blur transitions,
no repeated clips. Design space 1080x1920; --scale 2 => 4K.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import skia
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as Rn
from render import (font, hexc, text, text_w, cap_center_y, P, SP, R, rrect, Tx, Layer, NAVY, RED, SAND, WHITE, NAVY_L,
                    clamp, prog, lerp, eo3, eo5, eio3, eback, ei3, trimmed)
import brand_reel as BR
from brand_reel import paper, dark, draw_media, pill, highlight, torn, PAPER, INK, W, H

END = 35.44
# VO segments: (vo_start, vo_end, video_start, tempo) — each sentence sits where the reference's line sits
SEG = [(0.00, 4.15, 0.00, 1.065), (4.40, 6.00, 3.95, 1.0), (6.25, 8.36, 5.85, 1.0), (8.66, 9.75, 8.65, 1.0),
       (9.97, 12.75, 10.00, 1.06), (13.00, 15.52, 12.60, 1.0), (15.72, 17.42, 15.15, 1.0), (17.62, 18.90, 17.00, 1.0),
       (19.15, 20.35, 18.25, 1.0), (20.45, 23.24, 19.45, 1.08), (23.50, 27.60, 22.05, 1.10), (27.65, 29.40, 25.80, 1.0),
       (29.70, 32.15, 27.60, 1.0), (35.45, 36.50, 30.10, 1.0), (36.75, 37.87, 31.85, 1.0), (38.05, 39.70, 33.20, 1.0)]
def T(vo):
    """VO time -> video time"""
    for a, b, v, tp in SEG:
        if a - 0.05 <= vo <= b + 0.05:
            return v + max(0.0, vo - a) / tp
    best = min(SEG, key=lambda s: abs(s[0] - vo)); return best[2]

WORDS = json.load(open(os.path.join(os.path.dirname(HERE), 'tfs2', 'vo_words.json')))

B = [0, 1.83, 4.33, 5.85, 6.55, 8.60, 10.00, 12.60, 15.15, 17.00, 18.25, 19.45, 22.05, 25.75, 27.55, 30.00, 31.60, END]
TRANS = {4.33: ('whip_up', .30), 5.85: ('zoom_in', .30), 6.55: ('whip_up', .30), 8.60: ('whip_left', .30),
         10.00: ('zoom_out', .30), 12.60: ('whip_up', .30), 15.15: ('blur_cross', .40), 17.00: ('whip_left', .26),
         18.25: ('zoom_in', .26), 19.45: ('whip_up', .30), 22.05: ('zoom_out', .30), 25.75: ('blur_cross', .30),
         27.55: ('zoom_in', .30), 30.00: ('whip_up', .30)}
ONSETS = [0.75, 1.64, 2.62, 3.54, 4.92, 5.76, 6.78, 7.34, 8.17, 9.54, 10.38, 11.92, 13.13, 14.02, 15.09, 16.00, 16.93,
          17.86, 18.32, 19.53, 20.45, 21.99, 22.89, 24.32, 25.22, 25.91, 26.64, 27.62, 28.42, 29.06, 31.15, 31.71, 32.64]
CAM = {1: (1.28, 1.0), 11: (1.0, 1.06), 12: (1.0, 1.14), 16: (1.0, 1.05)}

def word(c, s, x, y, f, col, t, t0, align='l', rise=46, d=0.32):
    """word entrance with directional motion blur"""
    u = eo5(prog(t, t0, t0 + d))
    if u <= 0: return
    tw = text_w(s, f); sz = f.getSize()
    x0 = x - tw / 2 if align == 'c' else (x - tw if align == 'r' else x)
    if u >= 0.98:
        text(c, s, x, y, f, hexc(col), align); return
    bp = skia.Paint(); bp.setAlphaf(clamp(u * 1.6))
    sig = (1 - u) * 14
    if sig > 0.4: bp.setImageFilter(skia.ImageFilters.Blur(0.01, sig))
    c.saveLayer(R(x0 - 60, y - sz * 1.3, tw + 120, sz * 2.2 + rise), bp)
    text(c, s, x, y + (1 - u) * rise, f, hexc(col), align)
    c.restore()

def wt(i):  # video time of the i-th whisper word
    return T(WORDS[i][0])
def find(wd, after=0.0):
    for a, b, w_ in WORDS:
        if w_.strip('.,?').lower() == wd.strip('.,?').lower() and a >= after - 1e-6: return T(a)
    return None

# ---------------- scenes ----------------
GLOBE = [('r8', 3.4), ('r8', 18.8), ('r9', 0.5), ('r9', 18.0), ('r10', 8.6), ('r10', 27.9), ('r11', 2.3), ('r11', 5.7), ('r5', 2.5),
         ('r6', 30.9), ('r7', 22.8), ('r2', 18.5), ('r3', 9.4), ('r1', 27.2), ('r4', 15.8), ('r6', 33.0), ('r11', 16.0), ('r8', 25.6)]
def s_globe(c, t, S):
    paper(c, S)
    f = font('r', 66)
    for s, x, y, key in [('In', 110, 250, 0.0), ('a', 330, 250, 0.12), ('world', 640, 250, 0.24), ('full', 180, 350, 0.48), ('of', 470, 350, 0.88)]:
        word(c, s, x, y, f, INK, t, T(key))
    cx, cy, r = 540, 1010, 400
    u = eback(prog(t, 0.0, 0.5), 1.3)
    with Tx(c, s=max(0.001, u), px=cx, py=cy):
        c.drawCircle(cx + 14, cy + 30, r, P(hexc('#000000', 0.28), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30)))
        cp = skia.Path(); cp.addCircle(cx, cy, r)
        c.save(); c.clipPath(cp, True)
        c.drawCircle(cx, cy, r, P(hexc('#10202F')))
        rot = t * 0.9
        rows = [-0.95, -0.48, 0.0, 0.48, 0.95]
        k = 0
        for ri, phi in enumerate(rows):
            cphi = math.cos(phi); y = cy + r * math.sin(phi)
            for ci in range(10):
                th = rot + ci * (2 * math.pi / 10) + ri * 0.3
                th = (th + math.pi) % (2 * math.pi) - math.pi
                cth = math.cos(th)
                if cth <= 0.05: continue
                x = cx + r * math.sin(th) * cphi
                tw_, th_ = 150 * cth * cphi, 230 * cphi
                rl, st = GLOBE[(ri * 10 + ci) % len(GLOBE)]
                with Layer(c, 0.35 + 0.65 * cth):
                    draw_media(c, rl, st, 0, x - tw_ / 2, y - th_ / 2, tw_, th_, 10, still=True, size=(270, 480))
        sh = skia.GradientShader.MakeRadial(skia.Point(cx - r * 0.35, cy - r * 0.4), r * 1.6,
                                            [hexc('#FFFFFF', 0.28), hexc('#000000', 0.0), hexc('#000000', 0.6)], [0, 0.45, 1])
        c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Shader=sh))
        c.restore()
    cu = eo5(prog(t, T(1.06), T(1.06) + 0.3))
    if cu > 0:
        fC = font('cond', 270)
        c.save(); c.clipRect(R(0, 1040, W * cu, 420))
        text(c, 'CONTENT', 548, 1340, fC, hexc('#000000', 0.22), 'c')
        text(c, 'CONTENT', 540, 1332, fC, hexc(RED), 'c')
        c.restore()

def s_tiles(c, t, S):
    paper(c, S)
    tw_, th_, g = 220, 320, 28
    for col in range(5):
        u = eo5(prog(t, B[1] + col * 0.04, B[1] + 0.38 + col * 0.04))
        drift = (t - B[1]) * (40 if col % 2 else -40)
        for row in range(-1, 8):
            x = -120 + col * (tw_ + g); y = -200 + row * (th_ + g) - (1 - u) * 1900 + (col % 2) * 140 + drift
            if 1 <= col <= 3 and 1 <= row <= 4: continue
            rrect(c, x, y, tw_, th_, 26, P(hexc(SAND if (row + col) % 3 else NAVY)))
    rrect(c, 160, 330, 760, 1220, 30, P(hexc(PAPER)))
    word(c, 'The brands that', 540, 560, font('r', 60), INK, t, find('the', 1.9), 'c')
    u = eback(prog(t, find('win'), find('win') + 0.3), 1.6)
    if u > 0:
        fW = font('cond', 380)
        with Tx(c, s=u, px=540, py=880):
            text(c, 'WIN', 540, cap_center_y(fW, 880), fW, hexc(RED), 'c')
    word(c, "aren't the", 540, 1160, font('r', 48), INK, t, find("aren't"), 'c')
    lu = eo5(prog(t, find('loudest.'), find('loudest.') + 0.3))
    if lu > 0:
        fL = font('bebas', 200)
        c.save(); c.clipRect(R(160, 1180, 760, 260))
        text(c, 'LOUDEST', 540, 1400 + (1 - lu) * 220, fL, hexc(NAVY), 'c')
        c.restore()
    for k, (rl, st, x, y, rot) in enumerate([('r9', 25.9, 800, 1330, -6), ('r10', 22.0, 790, 290, 5)]):
        u = eback(prog(t, 3.55 + k * 0.15, 3.85 + k * 0.15), 1.5)
        if u > 0:
            with Tx(c, rot=rot, s=u, px=x + 125, py=y + 220):
                rrect(c, x - 8, y - 8, 266, 456, 22, P(hexc(WHITE)))
                draw_media(c, rl, st, t - 3.55, x, y, 250, 440, 16)

STRIP = [('r8', 5.1), ('r11', 9.2), ('r9', 30.0), ('r10', 30.0), ('r5', 29.5), ('r3', 9.2), ('r6', 9.0)]
STACK = [('r9', 22.4), ('r4', 18.0), ('r1', 31.4)]
def s_remember(c, t, S):
    paper(c, S)
    tl = t - B[2]
    if t < 4.95:
        off = -tl * 1150
        for k, (rl, st) in enumerate(STRIP):
            x = 120 + k * 230 + off + 400
            y = 960 + (k % 2) * 30 - 160
            draw_media(c, rl, st, tl, x, y, 200, 356, 18, size=(360, 640))
    else:
        for k, (rl, st) in enumerate(STACK):
            u = eo5(prog(t, 4.95 + k * 0.06, 5.35 + k * 0.06))
            x = 540 + (k - 1) * lerp(420, 190, u); rot = (k - 1) * 8 * u
            y = 1180
            with Tx(c, rot=rot, px=x, py=y):
                c.drawRRect(skia.RRect.MakeRectXY(R(x - 150 + 8, y - 266 + 22, 300, 533), 26, 26),
                            P(hexc('#000000', 0.3), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22)))
                rrect(c, x - 158, y - 274, 316, 549, 30, P(hexc(SAND if k == 1 else WHITE)))
                draw_media(c, rl, st, t - 4.95, x - 150, y - 266, 300, 533, 24)
    word(c, 'the ones people', 540, 470, font('r', 56), INK, t, find('ones'), 'c')
    tr = find('remember.')
    u = eo5(prog(t, tr + 0.05, tr + 0.35))
    fS = font('serif', 170); tw = text_w('Remember', fS)
    highlight(c, 540 - tw / 2 - 20, 560, tw + 40, 150, u, SAND)
    word(c, 'Remember', 540, 690, fS, INK, t, tr, 'c', rise=34)

def s_best(c, t, S):
    dark(c)
    bu = prog(t, B[3], B[3] + 0.3)
    fB = font('head', 86); s = 'THE BEST BRANDS'; tw = text_w(s, fB)
    box = skia.Path(); box.addRect(R(540 - tw / 2 - 30, 290, tw + 60, 140))
    trimmed(c, box, SP(hexc(WHITE), 3, cap=skia.Paint.kSquare_Cap), eo3(bu))
    word(c, s, 540, 395, fB, WHITE, t, B[3] + 0.02, 'c', rise=24)
    for k, (lab, x, y, t0) in enumerate([('Reach', 260, 820, 5.95), ('Views', 760, 980, 6.08), ('Followers', 400, 1250, 6.2)]):
        u = eback(prog(t, t0, t0 + 0.25), 1.4)
        if u > 0: pill(c, x, y - (t - t0) * 60, lab, font('m', 44), None, WHITE, s=u, stroke='#BBBBBB')
    for k in range(4):
        u = eo5(prog(t, 5.88 + k * 0.07, 6.3 + k * 0.07))
        x = 120 + k * 230 + (1 - u) * -400 + (t - B[3]) * 120; y = 1450 + k * 80
        rrect(c, x, y, 180, 70, 12, P(hexc(RED, u)))

def s_spark(c, t, S):
    dark(c)
    ts = find('spark')
    for k, x in enumerate([300, 780]):
        tt = t - B[4]
        pulse = 0.5 + 0.5 * math.sin(tt * 7 + k)
        c.drawCircle(x, 760, 70, P(hexc(RED, 0.9), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 30 + 20 * pulse)))
        c.drawCircle(x, 760, 42, P(hexc('#FF6A5E')))
        ph = (tt * 1.2 + k * 0.5) % 1
        c.drawCircle(x, 760, 80 + 140 * ph, SP(hexc(RED, 1 - ph), 3))
    for k in range(7):
        a = k * 0.9 + (t - B[4]) * 0.6
        c.drawCircle(540 + math.cos(a) * 420, 1150 + math.sin(a * 1.3) * 380, 26 + 10 * (k % 3), SP(hexc(RED, 0.6), 3))
    u = eback(prog(t, max(B[4], ts - 0.05), ts + 0.3), 1.5)
    if u > 0:
        f = font('serif', 230)
        with Tx(c, s=u, px=540, py=1000):
            text(c, 'Spark', 540, 1060, f, hexc(WHITE), 'c')
    word(c, 'Emotion', 720, 1160, font('m', 64), '#DDDDDD', t, find('emotion,'), 'c', rise=24)

def s_moments(c, t, S):
    paper(c, S)
    su = eio3(prog(t, 9.25, 9.65))
    w = lerp(W, 820, su); h = lerp(H, 820, su); r = lerp(0, 60, su)
    draw_media(c, 'r9', 40.0, t - B[5], 540 - w / 2, 960 - h / 2, w, h, r, gray=True, size=(1080, 1920), dur=1.6)
    c.drawRRect(skia.RRect.MakeRectXY(R(540 - w / 2, 960 - h / 2, w, h), r, r), P(hexc('#000000', 0.25 + 0.35 * su)))
    word(c, 'Moments', 540, 1000, font('serif', 170), WHITE, t, find('moments,'), 'c')

def s_trust(c, t, S):
    paper(c, S)
    tb = find('before')
    pan = -420 * eio3(prog(t, 11.0, 11.4))
    with Tx(c, 0, pan):
        node = (540, 820); paths = []
        for (sx, sy, c1x, c1y, c2x, c2y) in [(-50, 300, 200, 300, 300, 700), (1130, 250, 900, 400, 800, 760), (-50, 1300, 150, 1000, 380, 900),
                                             (1130, 1250, 950, 1050, 700, 900), (300, -50, 380, 300, 500, 600)]:
            p = skia.Path(); p.moveTo(sx, sy); p.cubicTo(c1x, c1y, c2x, c2y, node[0], node[1]); paths.append(p)
        du = eio3(prog(t, B[6], B[6] + 0.5))
        for p in paths: trimmed(c, p, SP(hexc(INK), 5), du)
        ru = prog(t, B[6] + 0.2, B[6] + 1.2)
        if 0 < ru < 1:
            pe = skia.Paint(SP(hexc(RED), 10)); pe.setPathEffect(skia.TrimPathEffect.Make(max(0, ru - 0.3), ru))
            for p in paths[:4]: c.drawPath(p, pe)
        u = eback(prog(t, find('trust'), find('trust') + 0.3), 1.6)
        if u > 0: pill(c, node[0], node[1], 'TRUST', font('head', 64), RED, WHITE, s=u)
        word(c, 'Build', 540, 700, font('r', 54), INK, t, find('build'), 'c', rise=20)
        lu = eio3(prog(t, 11.0, 11.5))
        c.drawLine(540, 880, 540, 880 + 560 * lu, SP(hexc(INK), 5))
        bu_ = eo5(prog(t, tb, tb + 0.3))
        if bu_ > 0:
            fb_ = font('r', 50); bw_ = text_w('before they chase', fb_)
            rrect(c, 540 - bw_ / 2 - 24, 1250, bw_ + 48, 76, 20, P(hexc(PAPER, bu_)))
        word(c, 'before they chase', 540, 1300, font('r', 50), INK, t, tb, 'c', rise=20)
        tf = find('followers.')
        fu = eback(prog(t, tf, tf + 0.3), 1.6)
        if fu > 0:
            pw, ph = pill(c, 540, 1500, 'FOLLOWERS', font('head', 64), SAND, INK, s=fu)
            dp = skia.Paint(SP(hexc(NAVY_L), 3, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([14, 10], (t * 40) % 24))
            c.drawRect(R(540 - pw / 2 - 26, 1500 - ph / 2 - 22, pw + 52, ph + 44), dp)

PILLS = [(0.05 + 0.9 * ((k * 0.618) % 1), 0.35 + 0.65 * ((k * 0.37) % 1), (k * 0.29) % 1) for k in range(18)]
def s_pills(c, t, S):
    paper(c, S)
    tt = t - B[7]
    tg = find('great')
    for k, (fx, d, ph) in enumerate(sorted(PILLS, key=lambda p: p[1])):
        u = eo3(prog(t, tg - 0.1 + k * 0.025, tg + 0.2 + k * 0.025))
        if u <= 0: continue
        y = (ph * 2400 - tt * 320 * d) % 2400 - 240
        x = fx * W + math.sin(tt * 1.5 + k) * 20
        blur = (1 - d) * 18 + (2 if d > 0.95 else 0)
        a_ = u * (0.45 + 0.55 * d)
        f_ = font('m', 58 * d); tw_ = text_w('Great Brands', f_); pw_, ph_ = tw_ + 60, f_.getSize() * 1.55
        mf = skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur) if blur > 0.5 else None
        pp = P(hexc(RED, a_)); tp = P(hexc(WHITE, a_))
        if mf: pp.setMaskFilter(mf); tp.setMaskFilter(mf)
        c.drawRRect(skia.RRect.MakeRectXY(R(x - pw_ / 2, y - ph_ / 2, pw_, ph_), ph_ / 2, ph_ / 2), pp)
        c.drawString('Great Brands', x - tw_ / 2, cap_center_y(f_, y), f_, tp)
    rrect(c, 140, 860, 800, 200, 30, P(hexc(PAPER, 0.85), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 20)))
    with Layer(c, 1 - prog(t, tg, tg + 0.2)):
        word(c, 'But even', 540, 960, font('r', 60), INK, t, find('but'), 'c', rise=16)
    f = font('m', 76); f2 = font('xb', 76)
    line = 'lost in the scroll.'; x0 = 540 - text_w(line, f) / 2
    for s, off, key, ff in [('lost', 0, 'lost', f), ('in', text_w('lost ', f), 'in', f), ('the', text_w('lost in ', f), 'the', f),
                            ('scroll.', text_w('lost in the ', f), 'scroll.', f2)]:
        word(c, s, x0 + off, 990, ff, INK, t, find(key, 14.0), rise=24)

def s_answer(c, t, S):
    paper(c, S)
    word(c, 'The', 170, 830, font('r', 70), INK, t, B[8] + 0.02)
    ta = find('answer')
    u = eo5(prog(t, ta, ta + 0.3))
    fS = font('serif', 190); tw = text_w('Answer?', fS)
    highlight(c, 140, 870, tw + 60, 170, u, RED)
    word(c, 'Answer?', 170, 1010, fS, INK, t, ta, rise=34)
    word(c, "isn't", 180, 1130, font('r', 64), INK, t, find("isn't"))
    word(c, 'more', 640, 1130, font('r', 64), INK, t, find('more'))
    tp = find('posts.')
    pu = eback(prog(t, tp, tp + 0.25), 1.6) * (1 - eio3(prog(t, tp + 0.7, tp + 1.0)))
    if pu > 0.01:
        pill(c, 540, 1290, 'posts', font('head', 60), SAND, INK, s=pu)

def s_plan(c, t, S):
    paper(c, S)
    for s, x, key in [("it's", 230, "it's"), ('a', 420, 'a'), ('sharper', 560, 'sharper')]:
        word(c, s, x, 1180, font('r', 64), INK, t, find(key, 17.5))
    fP = font('serif', 260); tw = text_w('Plan.', fP); tpl = find('plan,')
    word(c, 'Plan.', 540, 1020, fP, INK, t, tpl, 'c', rise=40)
    bu = eo5(prog(t, tpl + 0.15, tpl + 0.4))
    if bu > 0:
        x0, y0, bw, bh = 540 - tw / 2 - 40, 820, tw + 80, 270
        dp = skia.Paint(SP(hexc(NAVY_L), 3, cap=skia.Paint.kButt_Cap)); dp.setPathEffect(skia.DashPathEffect.Make([16, 10], 0))
        with Layer(c, bu):
            c.drawRect(R(x0, y0, bw, bh), dp)
            for hx, hy in [(x0, y0), (x0 + bw, y0), (x0, y0 + bh), (x0 + bw, y0 + bh)]:
                c.drawRect(R(hx - 10, hy - 10, 20, 20), P(hexc(WHITE))); c.drawRect(R(hx - 10, hy - 10, 20, 20), SP(hexc(NAVY_L), 3))
        au = eo5(prog(t, tpl + 0.2, tpl + 0.55))
        ax, ay = lerp(980, x0 + bw - 10, au), lerp(1500, y0 + bh - 10, au)
        ar = skia.Path(); ar.moveTo(ax, ay); ar.lineTo(ax + 18, ay + 52); ar.lineTo(ax + 28, ay + 32); ar.lineTo(ax + 50, ay + 30); ar.close()
        c.drawPath(ar, P(hexc(RED)))

TILES = [('r7', 35.4), ('r11', 20.6), ('r1', 17.0), ('r10', 2.6), ('r4', 24.0), ('r5', 32.4)]
def s_bolder(c, t, S):
    paper(c, S)
    for k, (rl, st) in enumerate(TILES):
        u = eback(prog(t, B[10] + k * 0.04, B[10] + 0.26 + k * 0.04), 1.4)
        if u <= 0: continue
        r_, cc = divmod(k, 2)
        x = 40 + cc * 300; y = 250 + r_ * 480
        with Tx(c, s=u, px=x + 135, py=y + 215):
            draw_media(c, rl, st, t - B[10], x, y, 270, 430, 22, size=(360, 640))
    for s, x, col, key in [('BOLDER', 875, RED, 'bolder'), ('CONTENT', 680, INK, 'content,')]:
        tk = find(key, 18.0)
        u = eo5(prog(t, tk, tk + 0.3))
        if u <= 0: continue
        f = font('cond', 210)
        with Tx(c, x, 960, rot=90):
            c.save(); c.clipRect(R(-900, -200, 1800, 240))
            text(c, s, 0, (1 - u) * 230, f, hexc(col), 'c', track=4)
            c.restore()

def s_stories(c, t, S):
    paper(c, S)
    word(c, 'Stories', 540, 400, font('cond', 240), RED, t, find('stories'), 'c')
    f = font('r', 54); line = 'that make people stop'
    x0 = 540 - text_w(line, f) / 2
    for s, key in [('that', 'that'), ('make', 'make'), ('people', 'people'), ('stop', 'stop')]:
        word(c, s, x0 + text_w(line[:line.index(s)], f), 500, font('xb' if s == 'stop' else 'r', 54), INK, t, find(key, 20.5), rise=18)
    u = eo5(prog(t, find('stories') + 0.12, find('stories') + 0.5))
    tand = find('and', 22.0)
    if u > 0:
        rl, st = ('r8', 11.9) if t < tand else ('r9', 34.0)
        with Tx(c, 0, (1 - u) * 300):
            with Layer(c, clamp(u * 2)):
                draw_media(c, rl, st, t - (B[11] if t < tand else tand), 60, 600, 960, 640, 30, size=(720, 1280))
    word(c, 'and', 540, 1350, font('r', 54), INK, t, tand, 'c', rise=14)
    ts = find('stay.')
    u = eback(prog(t, ts, ts + 0.28), 1.5)
    if u > 0:
        fS = font('cond', 420)
        with Tx(c, s=lerp(1.4, 1.0, u), px=540, py=1650):
            with Layer(c, clamp(u * 2)):
                text(c, 'STAY', 540, cap_center_y(fS, 1650), fS, hexc(NAVY), 'c')

def s_search(c, t, S):
    paper(c, S)
    u = eo5(prog(t, B[12], B[12] + 0.35))
    bw = lerp(200, 980, u); bh = 150; x0 = 540 - bw / 2; y0 = 960 - bh / 2
    c.drawRRect(skia.RRect.MakeRectXY(R(x0 + 4, y0 + 18, bw, bh), 75, 75), P(hexc('#000000', 0.18), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 26)))
    rrect(c, x0, y0, bw, bh, 75, P(hexc('#FFFFFF')))
    if u < 0.9: return
    ix = x0 + bw - 70
    c.drawCircle(ix, 956, 20, SP(hexc(NAVY_L), 6)); c.drawLine(ix + 14, 970, ix + 28, 984, SP(hexc(NAVY_L), 6))
    mx = ix - 70
    rrect(c, mx - 10, 934, 20, 36, 10, P(hexc(RED))); c.drawLine(mx, 978, mx, 990, SP(hexc(RED), 4))
    f = font('r', 46)
    ws = [(w_, T(a)) for a, b, w_ in WORDS if 23.4 <= a <= 27.5]
    s = ''
    for w_, tw0 in ws:
        if t >= tw0:
            n = int(clamp((t - tw0) / 0.035, 0, len(w_)))
            s += (' ' if s else '') + w_[:n]
    tw = text_w(s, f) if s else 0
    avail = bw - 230
    c.save(); c.clipRect(R(x0 + 50, y0, avail + 10, bh))
    tx = x0 + 60 - max(0, tw - avail)
    if s: text(c, s, tx, cap_center_y(f, 960), f, hexc(INK))
    if int(t * 3) % 2 == 0: c.drawRect(R(tx + tw + 6, 930, 3, 60), P(hexc(INK)))
    c.restore()

def s_partner(c, t, S):
    paper(c, S)
    f = font('r', 66); line = "A partner that doesn't"
    x0 = 540 - text_w(line, f) / 2
    for s, key in [('A', 'A'), ('partner', 'partner'), ('that', 'that'), ("doesn't", "doesn't")]:
        word(c, s, x0 + text_w(line[:line.index(s)], f), 880, f, INK, t, find(key, 27.5), rise=22)
    word(c, 'just', 300, 1020, f, INK, t, find('just', 27.5), rise=22)
    tsh = find('shoot,', 27.5)
    u = eback(prog(t, tsh, tsh + 0.28), 1.6)
    if u > 0:
        fS = font('cond', 170)
        with Tx(c, s=u, px=620, py=990):
            text(c, 'SHOOT', 460, 1050, fS, hexc(RED))

CUT = [('PLANS', 'r10', 12.9, NAVY, 'plans'), ('CREATES', 'r5', 8.0, RED, 'creates'), ('DELIVERS', 'r9', 18.0, SAND, 'delivers')]
def s_cutouts(c, t, S):
    paper(c, S)
    times = [B[14]] + [find(cc[4], 29.0) - 0.06 for cc in CUT[1:]]
    k = max(i for i in range(3) if t >= times[i])
    lab, rl, st, col, key = CUT[k]
    t0 = times[k]
    u = eo5(prog(t, t0, t0 + 0.28))
    bl = (1 - u) * 26
    p_ = skia.Paint(); p_.setAlphaf(clamp(u * 2))
    if bl > 0.5 and k > 0: p_.setImageFilter(skia.ImageFilters.Blur(bl, bl * 0.4))
    c.saveLayer(None, p_)
    with Tx(c, (1 - u) * (300 if k % 2 else -300), 0, s=lerp(1.15, 1.0, u), rot=lerp(5, 0, u), px=540, py=1000):
        c.drawPath(torn(330, 1350, 700, 520, 3 + k), P(hexc(col)))
        c.drawPath(torn(800, 760, 520, 420, 9 + k), P(hexc([RED, SAND, NAVY][k])))
        rng = np.random.default_rng(20 + k)
        x0, y0, w, h = 190, 560, 700, 980
        pts = [(x0 + rng.uniform(-14, 14), y0 + rng.uniform(-14, 14)), (x0 + w + rng.uniform(-14, 14), y0 + rng.uniform(-14, 14)),
               (x0 + w + rng.uniform(-14, 14), y0 + h + rng.uniform(-14, 14)), (x0 + rng.uniform(-14, 14), y0 + h + rng.uniform(-14, 14))]
        rp = skia.Path(); rp.moveTo(*pts[0]); [rp.lineTo(*q) for q in pts[1:]]; rp.close()
        c.drawPath(rp, P(hexc('#FFFFFF')))
        sp = skia.Path(); sp.moveTo(pts[0][0] + 14, pts[0][1] + 14)
        for i, q in enumerate(pts[1:], 1): sp.lineTo(q[0] + (14 if i in (0, 3) else -14), q[1] + (14 if i < 2 else -14))
        sp.close()
        draw_media(c, rl, st, t - t0, x0, y0, w, h, gray=True, path=sp, size=(720, 1280))
        fM = font('marker', 150)
        with Tx(c, rot=-8, px=420, py=420):
            text(c, lab, 140, 470, fM, hexc(INK))
            bu = eo5(prog(t, t0 + 0.1, t0 + 0.35))
            bp = skia.Path(); bp.moveTo(150, 510); bp.cubicTo(350, 490, 600, 520, 150 + text_w(lab, fM), 500)
            trimmed(c, bp, SP(hexc(RED), 16), bu)
        for j in range(5):
            a = -1.2 + j * 0.3
            c.drawLine(930 + math.cos(a) * 50, 330 + math.sin(a) * 50, 930 + math.cos(a) * 95, 330 + math.sin(a) * 95, SP(hexc(INK), 6))
    c.restore()

CLIENTS = BR.CLIENTS
def s_wall(c, t, S):
    paper(c, S)
    tt = t - B[15]
    cols = [NAVY, RED, '#B58A3A', INK]
    for i, (nm, fk) in enumerate(CLIENTS):
        r_, k = divmod(i, 2)
        x = 290 if k == 0 else 790; y = 200 + r_ * 205 + (k * 90) - tt * 30
        u = eo3(prog(t, B[15] + i * 0.03, B[15] + 0.35 + i * 0.03))
        sz = {'head': 44, 'serif': 58, 'cond': 64, 'bebas': 66, 'xb': 40}[fk]
        f = font(fk, sz)
        if text_w(nm, f) > 440: f = font(fk, sz * 440 / text_w(nm, f))
        with Layer(c, u * 0.45):
            text(c, nm, x, y, f, hexc(cols[i % 4]), 'c')
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 960), 500, [hexc(PAPER, 1.0), hexc(PAPER, 0.9), hexc(PAPER, 0.0)], [0, 0.55, 1])
    c.drawPaint(skia.Paint(Shader=rs))
    fT = font('head', 104)
    line = 'The Filmy Space'; x0 = 540 - text_w(line, fT) / 2
    for s, key, col in [('The', 'the', INK), ('Filmy', 'filmy', RED), ('Space', 'space', INK)]:
        tk = find(key, 34.5)
        u = eback(prog(t, tk, tk + 0.28), 1.5)
        if u > 0:
            x = x0 + text_w(line[:line.index(s)], fT)
            with Tx(c, s=u, px=x + text_w(s, fT) / 2, py=950):
                text(c, s, x, cap_center_y(fT, 950), fT, hexc(col))

_logo = None
LB = [(189, 369), (417, 597), (646, 826)]; BY0, BY1 = 175, 462
def s_logo(c, t, S):
    global _logo
    if _logo is None: _logo = skia.Image.open(os.path.join(HERE, 'logo.png'))
    c.drawPaint(P(hexc('#050507')))
    tt = t - B[16]
    gu = eo3(prog(t, B[16], B[16] + 1.0))
    rs = skia.GradientShader.MakeRadial(skia.Point(540, 900), 900, [hexc(NAVY, 0.5 * gu), hexc('#050507', 0.0)])
    c.drawPaint(skia.Paint(Shader=rs))
    sc = 0.9 * (1 + 0.04 * eo3(prog(t, B[16], END)))
    lw = LB[-1][1] - LB[0][0] + 1; bh = (BY1 - BY0 + 1) * sc
    x0 = 540 - lw * sc / 2; ytop = 880 - bh / 2
    rects = []
    for i, (a, b) in enumerate(LB):
        u = eo5(prog(t, B[16] + 0.06 + i * 0.09, B[16] + 0.6 + i * 0.09))
        if u <= 0: continue
        dx = x0 + (a - LB[0][0]) * sc; bw = (b - a + 1) * sc
        src = R(a, BY0, b - a + 1, BY1 - BY0 + 1)
        gp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(46, 46)); gp.setAlphaf(0.6 * u * (0.8 + 0.2 * math.sin(t * 3 + i)))
        c.drawImageRect(_logo, src, R(dx, ytop, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), gp)
        c.save(); c.clipRect(R(dx, ytop, bw, bh))
        c.drawImageRect(_logo, src, R(dx, ytop + (1 - u) * bh, bw, bh), skia.SamplingOptions(skia.FilterMode.kLinear), None)
        c.restore()
        rects.append(R(dx, ytop, bw, bh))
    # light sweep across the blocks
    su = prog(t, B[16] + 0.75, B[16] + 1.55)
    if 0 < su < 1 and rects:
        c.save()
        clipp = skia.Path()
        for rr in rects: clipp.addRect(rr)
        c.clipPath(clipp, True)
        sx = lerp(x0 - 300, x0 + lw * sc + 300, su)
        g = skia.GradientShader.MakeLinear([skia.Point(sx - 120, 0), skia.Point(sx + 120, 0)],
                                           [hexc('#FFFFFF', 0.0), hexc('#FFFFFF', 0.55), hexc('#FFFFFF', 0.0)])
        with Tx(c, rot=18, px=540, py=880):
            c.drawRect(R(-500, 0, 2100, 1920), skia.Paint(Shader=g, BlendMode=skia.BlendMode.kPlus))
        c.restore()
    f = font('b', 40)
    for s, tk, y in [('BORN FROM BELIEF.', T(36.81), 1120), ('BUILT TO GROW BRANDS.', T(38.12), 1185)]:
        u = eo5(prog(t, tk, tk + 0.35))
        if u <= 0: continue
        with Layer(c, u):
            if 'GROW' in s:
                tw = text_w(s, f, 6); xx = 540 - tw / 2
                xx += text(c, 'BUILT TO ', xx, y + (1 - u) * 14, f, hexc('#DADADA'), track=6) + 6
                xx += text(c, 'GROW', xx, y + (1 - u) * 14, f, hexc(RED), track=6) + 6
                text(c, ' BRANDS.', xx, y + (1 - u) * 14, f, hexc('#DADADA'), track=6)
            else:
                text(c, s, 540, y + (1 - u) * 14, f, hexc(SAND), 'c', track=6)

SCENES = [s_globe, s_tiles, s_remember, s_best, s_spark, s_moments, s_trust, s_pills, s_answer, s_plan, s_bolder,
          s_stories, s_search, s_partner, s_cutouts, s_wall, s_logo]

def scene_index(t):
    for i in range(len(SCENES)):
        if B[i] <= t < B[i + 1]: return i
    return len(SCENES) - 1

def draw_scene(c, i, t, S):
    a, b = B[i], B[i + 1]
    z0, z1 = CAM.get(i, (1.0, 1.05))
    u = clamp((t - a) / (b - a))
    z = lerp(z0, z1, eio3(u) if z0 > z1 else u)
    punch = 0.0
    for o in ONSETS:
        if 0 <= t - o < 0.2: punch = max(punch, 0.022 * (1 - (t - o) / 0.2) ** 2)
    dx = math.sin(t * 0.7 + i) * 8; dy = math.cos(t * 0.5 + i) * 8
    c.save(); c.translate(540 + dx, 960 + dy); c.scale(z + punch, z + punch); c.translate(-540, -960)
    SCENES[i](c, t, S)
    c.restore()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='b2.mp4'); ap.add_argument('--fps', type=int, default=60); ap.add_argument('--scale', type=float, default=2)
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=END)
    ap.add_argument('--stills', default=''); ap.add_argument('--crf', type=int, default=17)
    a = ap.parse_args()
    S = a.scale; OW, OH = int(W * S), int(H * S)
    surf = skia.Surface(OW, OH); c = surf.getCanvas()
    sA = skia.Surface(OW, OH); sB = skia.Surface(OW, OH)
    def offscreen(sf, i, t):
        cc = sf.getCanvas(); cc.clear(hexc('#000000')); cc.save(); cc.scale(S, S); draw_scene(cc, i, t, S); cc.restore()
        return sf.makeImageSnapshot()
    def blit(img, dx=0.0, dy=0.0, sc=1.0, bx=0.0, by=0.0, alpha=1.0):
        p = skia.Paint(); p.setAlphaf(clamp(alpha))
        if bx > 0.5 or by > 0.5: p.setImageFilter(skia.ImageFilters.Blur(max(bx, 0.01), max(by, 0.01)))
        c.save(); c.translate(OW / 2 + dx, OH / 2 + dy); c.scale(sc, sc); c.translate(-OW / 2, -OH / 2)
        c.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), p)
        c.restore()
    def render(t):
        c.clear(hexc('#000000'))
        tr = None
        for b, (kind, d) in TRANS.items():
            if b - d / 2 <= t < b + d / 2: tr = (b, kind, d)
        if tr is None:
            c.save(); c.scale(S, S); draw_scene(c, scene_index(t), t, S); c.restore()
            if 31.60 <= t < 31.78: c.drawPaint(P(hexc('#FFFFFF', 0.7 * (1 - (t - 31.60) / 0.18))))
            return surf.makeImageSnapshot().toarray()
        b, kind, d = tr
        p = (t - (b - d / 2)) / d
        i_new = B.index(b); i_old = i_new - 1
        A_ = offscreen(sA, i_old, t) if p < 0.5 else None
        B_ = offscreen(sB, i_new, t) if p >= 0.5 else None
        q = p * 2 if p < 0.5 else p * 2 - 1
        blur = 70 * S
        if kind == 'whip_up':
            if A_: blit(A_, dy=-OH * 0.55 * ei3(q), by=blur * q)
            else: blit(B_, dy=OH * 0.55 * (1 - eo3(q)), by=blur * (1 - q))
        elif kind == 'whip_left':
            if A_: blit(A_, dx=-OW * 0.6 * ei3(q), bx=blur * q)
            else: blit(B_, dx=OW * 0.6 * (1 - eo3(q)), bx=blur * (1 - q))
        elif kind == 'zoom_in':
            if A_: blit(A_, sc=1 + 0.7 * ei3(q), bx=blur * 0.5 * q, by=blur * 0.5 * q)
            else: blit(B_, sc=1 + 0.5 * (1 - eo3(q)), bx=blur * 0.5 * (1 - q), by=blur * 0.5 * (1 - q))
        elif kind == 'zoom_out':
            if A_: blit(A_, sc=1 - 0.3 * ei3(q), bx=blur * 0.4 * q, by=blur * 0.4 * q)
            else: blit(B_, sc=1 + 0.35 * (1 - eo3(q)), bx=blur * 0.4 * (1 - q), by=blur * 0.4 * (1 - q))
        elif kind == 'blur_cross':
            A2 = offscreen(sA, i_old, t); B2 = offscreen(sB, i_new, t)
            blit(A2, bx=40 * S * p, by=40 * S * p)
            blit(B2, bx=40 * S * (1 - p), by=40 * S * (1 - p), alpha=eio3(p))
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'b2_stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s)
            skia.Image.fromarray(render(t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'b2_stills', f'{t:06.2f}.png'))
        return
    n0, n1 = int(round(a.start * a.fps)), int(round(a.end * a.fps))
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{OW}x{OH}', '-r', str(a.fps), '-i', '-',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', str(a.crf), '-maxrate', '20M', '-bufsize', '40M', '-pix_fmt', 'yuv420p',
           '-x264-params', 'threads=2', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(n0, n1):
        pr.stdin.write(render(n / a.fps).tobytes())
        if n % (a.fps * 2) == 0: print(f'{n / a.fps:.1f}', flush=True)
    pr.stdin.close(); pr.wait(); print('done')

if __name__ == '__main__':
    main()
