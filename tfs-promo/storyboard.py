"""Storyboard style-frames for the TFS vertical intro reel (1080x1920)."""
import math, os, sys
import numpy as np
import skia
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import font, hexc, text, text_w, cap_center_y, P, SP, R, rrect, Tx, Layer, NAVY, RED, SAND, WHITE, NAVY_L, draw_logo

W, H = 1080, 1920
OFF = '#F2EEE6'; INK = '#111114'

def dots(c, col, a=0.35, step=54):
    for y in range(40, H, step):
        for x in range(30, W, step):
            c.drawCircle(x, y, 2.2, P(hexc(col, a)))

def caret(c, x, y, h, col=WHITE):
    c.drawRect(R(x + 6, y - h, 4, h * 1.15), P(hexc(col)))

def starburst(c, cx, cy, r0, r1, n, col):
    for k in range(n):
        a = k * 2 * math.pi / n
        rr = r1 * (0.75 + 0.25 * ((k * 7) % 5) / 4)
        c.drawLine(cx + math.cos(a) * r0, cy + math.sin(a) * r0, cx + math.cos(a) * rr, cy + math.sin(a) * rr, SP(hexc(col), 7))

def f1(c):  # typing intro
    c.drawPaint(P(hexc('#000000')))
    f = font('m', 54); s = 'Hi there.'
    w = text(c, s, W / 2, 975, f, hexc(WHITE), 'c')
    caret(c, W / 2 + w / 2, 975, 44)

def f2(c):  # collage "We're a CONTENT STUDIO."
    c.drawPaint(P(hexc(OFF)))
    starburst(c, W / 2, 900, 60, 430, 44, RED)
    c.drawCircle(W / 2, 900, 120, P(hexc(OFF)))
    fw = font('m', 54); ww = text_w("We're a", fw)
    rrect(c, W / 2 - ww / 2 - 24, 640, ww + 48, 80, 40, P(hexc(OFF)))
    text(c, "We're a", W / 2, 697, fw, hexc(INK), 'c')
    word = 'CONTENT'; fonts = ['head', 'cond', 'head', 'cond', 'head', 'head', 'cond']
    cols = [NAVY, INK, RED, SAND, NAVY, RED, INK]
    fs = [font(fn, 118 if fn == 'head' else 140) for fn in fonts]
    cws = [f.measureText(ch) + 26 for f, ch in zip(fs, word)]
    total = sum(cws) + 6 * (len(word) - 1)
    x = W / 2 - total / 2; y = 900
    for i, ch in enumerate(word):
        f = fs[i]; cw = cws[i]
        with Tx(c, rot=[-6, 4, -3, 7, -5, 3, -4][i], px=x + cw / 2, py=y):
            c.drawRect(R(x, y - 85, cw, 170), P(hexc(cols[i])))
            text(c, ch, x + cw / 2, cap_center_y(f, y), f, hexc(WHITE if cols[i] != SAND else INK), 'c')
        x += cw + 6
    f = font('head', 130)
    text(c, 'STUDIO.', W / 2, 1180, f, hexc(INK), 'c')

def f3(c):  # growing brands
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, 1500), 1500, [hexc(NAVY), hexc('#0B1622'), hexc('#05080C')], [0, 0.55, 1])
    c.drawPaint(skia.Paint(Shader=sh))
    dots(c, SAND, 0.25)
    # film reel object
    cx, cy, r = W / 2, 760, 210
    c.drawCircle(cx, cy, r + 60, P(hexc(SAND, 0.25), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 60)))
    g = skia.GradientShader.MakeLinear([skia.Point(cx - r, cy - r), skia.Point(cx + r, cy + r)], [hexc('#F7E3B0'), hexc('#8C6B2E')])
    c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Shader=g))
    for k in range(5):
        a = k * 2 * math.pi / 5 - math.pi / 2
        c.drawCircle(cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.55, r * 0.22, P(hexc('#0B1622')))
    c.drawCircle(cx, cy, r * 0.12, P(hexc('#0B1622')))
    f = font('head', 150)
    with Tx(c):
        c.skew(-0.2, 0)
        text(c, 'growing', W / 2 + 225, 1180, f, hexc(SAND), 'c')
    text(c, 'brands', W / 2, 1260, font('b', 44), hexc(WHITE), 'c')

def f4(c):  # red ring + through stories that stop the scroll
    c.drawPaint(P(hexc('#FAF8F4')))
    dots(c, '#999999', 0.35)
    with Tx(c, rot=-18, px=W / 2, py=930):
        for k, (w_, a) in enumerate([(120, 1.0)]):
            ov = R(W / 2 - 360, 930 - 230, 720, 460)
            p = SP(hexc(RED), 120)
            g = skia.GradientShader.MakeLinear([skia.Point(0, 700), skia.Point(0, 1160)], [hexc('#E8574F'), hexc('#8E1C18')])
            p.setShader(g)
            c.drawOval(ov, p)
            c.drawOval(R(W / 2 - 330, 930 - 205, 660, 410), SP(hexc('#FFFFFF', 0.35), 10))
    f = font('m', 66)
    text(c, 'through', 230, 760, f, hexc(INK))
    text(c, 'stories that', W / 2, 930, f, hexc(INK), 'c')
    text(c, 'stop the scroll.', W - 150, 1100, f, hexc(INK), 'r')

def f5(c):  # conversational
    c.drawPaint(P(hexc('#000000')))
    f = font('m', 40)
    text(c, 'Ok.', W / 2, 820, f, hexc('#666666'), 'c')
    text(c, "Ok, that's cool.", W / 2, 900, f, hexc('#888888'), 'c')
    s1, s2, s3 = 'But ', 'what', ' do you actually do?'
    tw = text_w(s1 + s2 + s3, f); x = W / 2 - tw / 2
    text(c, s1, x, 990, f, hexc(WHITE)); x2 = x + text_w(s1, f)
    text(c, s2, x2, 990, f, hexc(RED)); c.drawRect(R(x2, 1002, text_w(s2, f), 4), P(hexc(RED)))
    text(c, s3, x2 + text_w(s2, f), 990, f, hexc(WHITE))

def f6(c):  # services rapid cycle on gradient
    c.drawPaint(P(hexc(NAVY)))
    for (x, y, r, col) in [(250, 500, 650, RED), (900, 1500, 700, SAND), (700, 300, 500, NAVY_L)]:
        c.drawCircle(x, y, r, P(hexc(col, 0.85), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 220)))
    c.drawCircle(W / 2, 960, 300, SP(hexc(WHITE, 0.8), 3))
    c.drawCircle(W / 2 + 300 * math.cos(0.6), 960 + 300 * math.sin(0.6), 9, P(hexc(WHITE)))
    # tiny feed clip inside ring (optional)
    rrect(c, W / 2 - 90, 960 - 330 - 180, 180, 320, 18, P(hexc('#000000', 0.25)))
    text(c, 'feed clip', W / 2, 960 - 330 - 10, font('b', 22), hexc(WHITE, 0.7), 'c')
    f = font('head', 96)
    text(c, 'Concept', W / 2, 950, f, hexc(WHITE), 'c')
    text(c, 'Videos', W / 2, 1060, f, hexc(WHITE), 'c')

def f7(c):  # story line
    c.drawPaint(P(hexc('#FFFFFF')))
    p = skia.Path(); p.moveTo(820, -20)
    p.cubicTo(1150, 300, 650, 520, 760, 820); p.cubicTo(860, 1100, 1200, 1050, 980, 1400); p.cubicTo(800, 1700, 1050, 1800, 900, 1960)
    c.drawPath(p, SP(hexc(NAVY), 3))
    f = font('m', 64); fb = font('xb', 66)
    for k, s in enumerate(['Every brand', 'has a story.']):
        text(c, s, 110, 780 + k * 82, f, hexc(INK))
    for k, s in enumerate(['We bring it', 'to the screen.']):
        text(c, s, 110, 1010 + k * 82, fb, hexc(INK))

def f8(c):  # logo
    c.drawPaint(P(hexc('#000000')))
    draw_logo(c, W / 2, 940, 0.85)
    text(c, '@thefilmyspace', W / 2, 1230, font('b', 38), hexc('#9A9AA2'), 'c', track=2)

FRAMES = [
    ('0.0-1.8s', 'TYPING HOOK', f1),
    ('1.8-3.4s', 'MUSIC HIT: COLLAGE', f2),
    ('3.4-5.4s', 'GROWING BRANDS', f3),
    ('5.4-7.7s', 'RED RING', f4),
    ('7.7-10.6s', 'CONVERSATION', f5),
    ('10.6-13.0s', 'SERVICES FAST CYCLE', f6),
    ('13.0-16.3s', 'STORY LINE', f7),
    ('16.3-19.5s', 'LOGO', f8),
]

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storyboard')
    os.makedirs(out, exist_ok=True)
    s = skia.Surface(W, H); c = s.getCanvas()
    for i, (tm, name, fn) in enumerate(FRAMES):
        c.clear(hexc('#000000')); c.save(); fn(c); c.restore()
        s.makeImageSnapshot().save(os.path.join(out, f'f{i + 1}.png'))
    # sheet
    pw, ph = 360, 640; pad = 30; head = 70
    SW = 4 * pw + 5 * pad; SH = 2 * (ph + head) + 3 * pad + 90
    ss = skia.Surface(SW, SH); cc = ss.getCanvas(); cc.clear(hexc('#141417'))
    text(cc, 'TFS INTRO REEL  ·  STORYBOARD  ·  9:16  ·  ~19.5s', pad, 62, font('xb', 34), hexc(WHITE), track=2)
    for i, (tm, name, fn) in enumerate(FRAMES):
        r_, k = divmod(i, 4)
        x = pad + k * (pw + pad); y = 90 + pad + r_ * (ph + head + pad)
        text(cc, f'{i + 1}', x, y + 34, font('cond', 40), hexc(SAND))
        text(cc, name, x + 40, y + 30, font('xb', 22), hexc(WHITE), track=1)
        text(cc, tm, x + 40, y + 56, font('m', 20), hexc('#9A9AA2'))
        img = skia.Image.open(os.path.join(out, f'f{i + 1}.png'))
        cc.drawImageRect(img, R(x, y + head, pw, ph), skia.SamplingOptions(skia.FilterMode.kLinear), None)
        cc.drawRect(R(x, y + head, pw, ph), SP(hexc('#333338'), 2, cap=skia.Paint.kSquare_Cap))
    ss.makeImageSnapshot().save(os.path.join(out, 'TFS_reel_storyboard.png'))
    print('ok')

if __name__ == '__main__':
    main()
