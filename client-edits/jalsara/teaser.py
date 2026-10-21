"""Jalsara 'Project B' teaser (15s, 9:16, 4K60) cut from the interview.
Stage 1 (--base): ffmpeg builds base.mp4 (segments cropped above the burned-in captions, graded, concatenated).
Stage 2 (default): skia reads base.mp4 frame by frame and adds punches, transitions, kinetic captions, end card.
"""
import argparse, json, math, os, random, subprocess, sys
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'film'))
import film as F                      # fonts / easing / text helpers from the TFS film renderer
from film import font, hexc, P, SP, R, rrect, text, text_w, capc, Layer, Tx, clamp, prog, lerp, eo3, eo5, ei3, eio3, eback, rad, lin

SRC = os.path.join(os.path.dirname(HERE), 'jalsara_dl', 'jalsara.mp4')
W, H = 1080, 1920
FPS = 60
AMBER = '#FFB23E'

# ---------------- music grid (Mixkit 'Epical Drums 01') ----------------
_bj = np.array(json.load(open(os.path.join(HERE, 'beats676.json')))['beats'])
HIT = 34.80                                   # strong hit in the track -> lands on the end-card slam
E = 12.45                                     # end-card slam (video time)
M0 = HIT - E                                  # track time at video t=0
BEATS = [b - M0 for b in _bj if 0 <= b - M0 <= 16]
END = 15.0

# ---------------- edit decision list ----------------
# bites: (name, src_in, src_out, crop_top_frac)
B1 = ('b1', 50.00, 52.70, 0.0)
TAIL = [('b2', 57.78, 59.90, 0.0), ('b3', 60.02, 62.15, 0.0), ('b4', 63.93, 65.80, 0.0), ('b5', 67.50, 69.15, 0.0)]
GAP = 0.06
MONT = [(2.36, True, 0.0), (0.05, True, 0.0), (20.10, False, 0.0), (13.20, False, 0.0)]
VO_1990 = (18.50, 19.56)          # "1990 mein shuru hui thi" under the montage

def build_edl():
    segs = []                       # (out_start, out_end, src_in, bw, crop_top, kind)
    t = 0.0
    segs.append((0.0, B1[2] - B1[1], B1[1], False, 0.0, 'b1')); t = B1[2] - B1[1]
    # tail bites placed backwards from the slam
    tail = []; te = E - 0.04
    for nm, a, b, ct in reversed(TAIL):
        d = b - a; ts = te - d; tail.append((ts, te, a, False, ct, nm)); te = ts - GAP
    tail.reverse(); m_end = tail[0][0]
    # video stays contiguous: each tail shot runs until the next one starts (the gap is audio-only)
    tail = [(ts, tail[i + 1][0] if i + 1 < len(tail) else te_, src, bw, ct, nm)
            for i, (ts, te_, src, bw, ct, nm) in enumerate(tail)]
    # montage: cut on beats between b1 end and first tail bite
    cuts = [t] + [b for b in BEATS if t + 0.25 < b < m_end - 0.25] + [m_end]
    for i in range(len(cuts) - 1):
        src, bw, ct = MONT[i % len(MONT)]
        segs.append((cuts[i], cuts[i + 1], src, bw, ct, f'm{i}'))
    # last bite: cut away to a reaction shot before the source's own 'till then' title appears (audio continues)
    ts5, te5, src5, bw5, ct5, nm5 = tail[-1]; cut5 = ts5 + (68.05 - src5)
    tail[-1] = (ts5, cut5, src5, bw5, ct5, nm5); tail.append((cut5, te5, 62.70, False, 0.0, 'b5x'))
    segs += tail
    last = tail[-2]
    segs.append((E - 0.04, END, last[2] + (last[1] - last[0]) - 0.02, False, 0.0, 'end'))   # freeze source for end card
    return segs
SEGS = build_edl()
CUTS = [s[0] for s in SEGS[1:]]

def base_cmd(out):
    ins, fl = [], []
    for k, (a, b, src, bw, ct, kind) in enumerate(SEGS):
        d = b - a
        if kind == 'end':
            ins += ['-ss', f'{src:.3f}', '-t', '0.05', '-i', SRC]
        else:
            ins += ['-ss', f'{src:.3f}', '-t', f'{d + 0.05:.3f}', '-i', SRC]
        g = 'hue=s=0,eq=contrast=1.12:brightness=-0.02' if bw else 'eq=contrast=1.07:saturation=1.10:brightness=-0.01,colorbalance=rs=0.03:bs=-0.03'
        f = f'[{k}:v]setpts=PTS-STARTPTS,fps={FPS},{g}'
        if kind == 'end':
            f += f',tpad=stop_mode=clone:stop_duration={d:.3f}'
        f += f',trim=duration={d:.4f},setpts=PTS-STARTPTS,format=yuv420p[v{k}]'
        fl.append(f)
    fl.append(''.join(f'[v{k}]' for k in range(len(SEGS))) + f'concat=n={len(SEGS)}:v=1:a=0[out]')
    return ['ffmpeg', '-y', '-v', 'error'] + ins + ['-filter_complex', ';'.join(fl), '-map', '[out]', '-r', str(FPS),
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '12', '-pix_fmt', 'yuv420p', out]

# ---------------- captions ----------------
def src2out(seg_name, s):
    for (a, b, src, bw, ct, kind) in SEGS:
        if kind == seg_name: return a + (s - src)
    raise KeyError(seg_name)
CAPS = [  # (segment, src_start, src_end, [(word, accent)])
    ('b1', 50.55, 51.80, [('abhi', 0), ('toh', 0), ('main', 0)]),
    ('b1', 51.80, 52.70, [('REVEAL', 1), ('NAHI', 1), ('KARUNGA', 1)]),
    ('b2', 57.80, 58.40, [('toh', 0), ('woh', 0), ('sab', 0)]),
    ('b2', 58.40, 59.90, [('PROJECT B', 1), ('laane', 0), ('wala', 0), ('hai', 0)]),
    ('b3', 60.02, 60.83, [('aur', 0), ('RATLAM', 1), ('walon', 0), ('ko', 0)]),
    ('b3', 60.83, 62.15, [('bahut', 0), ('hi', 0), ('MAZA', 1), ('AAYEGA', 1)]),
    ('b4', 63.93, 64.98, [('pura', 0), ('NAYA', 1), ('EXPERIENCE', 1)]),
    ('b4', 64.98, 65.80, [('rahega', 0), ('unke', 0), ('liye', 0)]),
    ('b5', 67.50, 68.30, [('ki', 0), ('JALSARA', 1), ('mein', 0), ('naya', 0)]),
    ('b5', 68.30, 69.15, [('KYA', 1), ('HONE', 1), ('WALA', 1), ('HAI?', 1)]),
]
CAP_T = [(src2out(sg, a), src2out(sg, b), ws) for sg, a, b, ws in CAPS]
VO_AT = SEGS[1][0] + 0.10                         # where the '1990' line sits in the montage
CAP_T.insert(2, (VO_AT, VO_AT + (VO_1990[1] - VO_1990[0]) + 0.25, [('1990', 1), ('mein…', 0)]))
CARD = (50, 1400, 980, 155)

def draw_caption(c, t):
    cx_, cy_ = W / 2, CARD[1] + CARD[3] / 2
    for (a, b, ws) in CAP_T:
        if not (a - 0.02 <= t < b + 0.02): continue
        f = font('tx', 70)
        sp = text_w(' ', f)
        tot = sum(text_w(w_, f) for w_, _ in ws) + sp * (len(ws) - 1) + 20 * sum(acc for _, acc in ws)
        if tot > 900: f = font('tx', 70 * 900 / tot); sp = text_w(' ', f)
        tot = sum(text_w(w_, f) for w_, _ in ws) + sp * (len(ws) - 1)
        n = len(ws); dur = (b - a) * 0.7
        x = cx_ - tot / 2; y = capc(f, cy_)
        for k, (w_, acc) in enumerate(ws):
            ww = text_w(w_, f)
            tw = a + dur * k / max(1, n)
            u = clamp((t - tw) / 0.14)
            if u > 0:
                s = eback(u, 2.4) if u < 1 else 1.0
                with Tx(c, s=0.55 + 0.45 * s, px=x + ww / 2, py=cy_):
                    with Layer(c, clamp(u * 2)):
                        if acc:
                            ch = f.getMetrics().fCapHeight
                            rrect(c, x - 9, cy_ - ch / 2 - 14, ww + 18, ch + 28, 10, P(hexc(AMBER)))
                            text(c, w_, x, y, f, hexc('#1A1006'))
                        else:
                            text(c, w_, x, y, f, hexc('#FFFFFF'))
            x += ww + sp

# ---------------- hero texts ----------------
def glitch_text(c, s, x, y, f, col, amt, t, align='c', track=0):
    """RGB-split glitch: amt 0..1"""
    if amt > 0.01:
        rnd = random.Random(int(t * 30))
        for dx, cc in [(-1, '#FF2A4F'), (1, '#2AE0FF')]:
            p = skia.Paint(AntiAlias=True, Color=hexc(cc, 0.85)); p.setBlendMode(skia.BlendMode.kScreen)
            text(c, s, x + dx * 16 * amt + rnd.uniform(-6, 6) * amt, y + rnd.uniform(-4, 4) * amt, f, None, align, track, paint=p)
        # slice offsets
        w = text_w(s, f, track); h = f.getSize()
        for k in range(3):
            yy = y - h * rnd.uniform(0.1, 0.8); hh = h * rnd.uniform(0.05, 0.14); off = rnd.uniform(-40, 40) * amt
            c.save(); c.clipRect(R(0, yy, W, hh)); text(c, s, x + off, y, f, col, align, track); c.restore()
    text(c, s, x, y, f, col, align, track)

def hero_projectb(c, t):
    t0 = 0.08; t1 = SEGS[0][1]
    if not (t0 <= t < t1 + 0.12): return
    u = prog(t, t0, t0 + 0.22); out = prog(t, t1 - 0.05, t1 + 0.12)
    fP = font('anton', 210)
    s = 1.0 + 0.6 * (1 - eo5(u))
    with Layer(c, clamp(u * 2) * (1 - out)):
        with Tx(c, s=s, px=W / 2, py=360):
            sub = font('tm', 34)
            text(c, 'JALSARA PRESENTS', W / 2, 205, sub, hexc('#FFFFFF', 0.85), 'c', 10)
            glitch_text(c, 'PROJECT B', W / 2, capc(fP, 360), fP, hexc('#FFFFFF'), max(1 - prog(t, t0, t0 + 0.45), 0.25 * (math.sin(t * 40) > 0.85)), t, 'c', 4)

def hero_1990(c, t):
    segm = [s for s in SEGS if s[5].startswith('m')]
    if not segm: return
    a, b = segm[0][0], segm[-1][1]
    if not (a <= t < b): return
    u = prog(t, a + 0.05, a + 0.35)
    f1 = font('tm', 40); f2 = font('anton', 260)
    with Layer(c, clamp(u * 1.6) * (1 - prog(t, b - 0.12, b))):
        text(c, 'S I N C E', W / 2, 330, f1, hexc(AMBER), 'c', 4)
        yr = 1990
        sh = skia.Paint(AntiAlias=True, Color=hexc('#000000', 0.5)); sh.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 14))
        c.drawString(str(yr), W / 2 - text_w(str(yr), f2) / 2 + 4, capc(f2, 520) + 8, f2, sh)
        with Tx(c, s=1 + 0.25 * (1 - eo5(u)), px=W / 2, py=520):
            text(c, str(yr), W / 2, capc(f2, 520), f2, hexc('#FFFFFF'), 'c')

# ---------------- end card ----------------
def end_card(c, t, base_img_draw):
    u = prog(t, E, E + 0.25)
    # background: frozen frame, blurred + darkened
    with Layer(c, 1.0, (40 * eo3(u), 40 * eo3(u))):
        base_img_draw(1.0 + 0.08 * eo3(prog(t, E, END)))
    c.drawPaint(P(hexc('#0B0704', 0.55 + 0.25 * eo3(u))))
    c.drawPaint(skia.Paint(Shader=rad(W / 2, 880, 900, [hexc(AMBER, 0.18), hexc(AMBER, 0)])))
    fP = font('anton', 250)
    up = prog(t, E, E + 0.2)
    s = 1 + 0.9 * (1 - eo5(up))
    with Tx(c, s=s, px=W / 2, py=860):
        with Layer(c, clamp(up * 3)):
            glitch_text(c, 'PROJECT B', W / 2, capc(fP, 860), fP, hexc('#FFFFFF'),
                        max(1 - prog(t, E, E + 0.5), 0.3 * (math.sin(t * 37) > 0.9)), t, 'c', 4)
    fJ = font('cin', 64)
    uj = eo3(prog(t, E + 0.35, E + 0.75))
    with Layer(c, uj, (10 * (1 - uj), 10 * (1 - uj))):
        text(c, 'JALSARA', W / 2, 640, fJ, hexc(AMBER), 'c', 22)
    fr = font('tm', 36)
    ur = eo3(prog(t, E + 0.7, E + 1.1))
    with Layer(c, ur):
        text(c, 'RATLAM  ·  REVEAL THIS MONTH', W / 2, 1010, fr, hexc('#FFFFFF', 0.9), 'c', 6)
    us = eback(prog(t, E + 1.05, E + 1.4), 2.0)
    if us > 0:
        fs = font('tx', 44); tw = text_w('STAY TUNED', fs, 8)
        with Tx(c, s=us, px=W / 2, py=1160):
            rrect(c, W / 2 - tw / 2 - 40, 1120, tw + 80, 84, 42, P(hexc(AMBER)))
            text(c, 'STAY TUNED', W / 2, 1180, fs, hexc('#1A1006'), 'c', 8)

# ---------------- frame compositor ----------------
def beat_pulse(t):
    """zoom pulse on every beat (decays in 0.25s)"""
    prev = [b for b in BEATS if b <= t]
    if not prev: return 0.0
    d = t - prev[-1]
    return max(0.0, 1 - d / 0.25) ** 2

def shake(t):
    a = 0.0
    for tk, amp in [(0.10, 22), (E, 30)]:
        if tk <= t < tk + 0.35: a = max(a, amp * (1 - (t - tk) / 0.35))
    if a <= 0: return 0, 0
    rnd = random.Random(int(t * 60))
    return rnd.uniform(-a, a), rnd.uniform(-a, a)

def transition_state(t):
    """zoom-blur around each cut: (scale_extra, blur)"""
    for ct in CUTS:
        if ct == SEGS[-1][0]: continue
        d = t - ct
        if -0.10 <= d < 0: q = (d + 0.10) / 0.10; return 0.22 * ei3(q), 34 * q
        if 0 <= d < 0.14: q = 1 - d / 0.14; return 0.16 * eo3(q), 30 * q
    return 0.0, 0.0

def render_frame(c, img, t, S):
    c.clear(hexc('#000000'))
    seg = [s for s in SEGS if s[0] <= t < s[1]] or [SEGS[-1]]
    kind = seg[0][5]
    def draw_base(sc=1.0, blur=0.0, dx=0.0, dy=0.0):
        p = skia.Paint()
        if blur > 0.5: p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
        c.save(); c.translate(W / 2 + dx, H / 2 + dy); c.scale(sc, sc); c.translate(-W / 2, -H / 2)
        c.drawImageRect(img, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        c.restore()
    if kind == 'end':
        end_card(c, t, lambda sc: draw_base(sc))
    else:
        se, bl = transition_state(t)
        sp = 0.035 * beat_pulse(t) if kind.startswith('b') else 0.05 * beat_pulse(t)
        drift = 0.04 * prog(t, seg[0][0], seg[0][1])
        dx, dy = shake(t)
        draw_base(1.0 + drift + sp + se, bl, dx, dy)
        # light leak on montage cuts
        if kind.startswith('m'):
            ul = prog(t, seg[0][0], seg[0][0] + 0.3)
            if ul < 1:
                p = skia.Paint(Shader=rad(W * 0.85, H * 0.25, 900, [hexc('#FF9A3C', 0.55 * (1 - ul)), hexc('#FF9A3C', 0)]))
                p.setBlendMode(skia.BlendMode.kScreen); c.drawPaint(p)
        # top + bottom gradient for text legibility
        c.drawRect(R(0, 1150, W, 770), skia.Paint(Shader=lin(0, 1150, 0, 1920, [hexc('#000000', 0), hexc('#000000', 0.55)])))
        c.drawRect(R(0, 0, W, 620), skia.Paint(Shader=lin(0, 0, 0, 620, [hexc('#000000', 0.45), hexc('#000000', 0)])))
        hero_projectb(c, t)
        hero_1990(c, t)
        # frosted caption card (also hides the interview's burned-in subtitles)
        x, y, w, h = CARD
        uc = eo3(prog(t, 0.0, 0.2))
        rr = skia.RRect.MakeRectXY(R(x, y, w, h), 34, 34)
        c.save(); c.clipRRect(rr, True)
        draw_base(1.0 + drift + sp + se, 34 + bl, dx, dy)
        c.drawRect(R(x, y, w, h), P(hexc('#0B0806', 0.62)))
        c.restore()
        c.drawRRect(rr, SP(hexc('#FFFFFF', 0.14), 2))
        draw_caption(c, t)
    # flashes on the big cuts
    for ft in (0.08, SEGS[1][0], [s for s in SEGS if s[5] == 'b2'][0][0], E):
        if ft <= t < ft + 0.07: c.drawPaint(P(hexc('#FFFFFF', 0.75 * (1 - (t - ft) / 0.07))))
    F.grain(c, t, 0.05)
    F.vignette(c, 0.35)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', action='store_true'); ap.add_argument('--out', default='teaser.mp4')
    ap.add_argument('--scale', type=float, default=2); ap.add_argument('--stills', default='')
    ap.add_argument('--start', type=float, default=0); ap.add_argument('--end', type=float, default=END)
    a = ap.parse_args()
    basef = os.path.join(HERE, 'base.mp4')
    if a.base:
        subprocess.run(base_cmd(basef), check=True); return
    S = a.scale; OW, OH = int(W * S), int(H * S)
    surf = skia.Surface(OW, OH); c = surf.getCanvas()
    def frames(t0, t1):
        cmd = ['ffmpeg', '-v', 'error', '-ss', f'{t0:.4f}', '-i', basef, '-t', f'{t1 - t0:.4f}', '-vf', f'scale={OW}:{OH}',
               '-pix_fmt', 'rgba', '-f', 'rawvideo', '-']
        pr = subprocess.Popen(cmd, stdout=subprocess.PIPE); n = OW * OH * 4
        while True:
            buf = pr.stdout.read(n)
            if len(buf) < n: break
            yield np.frombuffer(buf, np.uint8).reshape(OH, OW, 4)
    def one(arr, t):
        img = skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)
        c.save(); c.scale(S, S)
        render_frame(c, img, t, S)
        c.restore()
        return surf.makeImageSnapshot().toarray()
    if a.stills:
        os.makedirs(os.path.join(HERE, 'stills'), exist_ok=True)
        for s in a.stills.split(','):
            t = float(s); arr = next(frames(t, t + 0.05))
            skia.Image.fromarray(one(arr, t), colorType=skia.kBGRA_8888_ColorType).save(os.path.join(HERE, 'stills', f'{t:05.2f}.png'))
        return
    n0, n1 = int(round(a.start * FPS)), int(round(a.end * FPS))
    enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{OW}x{OH}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-x264-params', 'threads=2', a.out],
                           stdin=subprocess.PIPE)
    k = n0
    for arr in frames(n0 / FPS, n1 / FPS + 0.5):
        if k >= n1: break
        enc.stdin.write(one(arr, k / FPS).tobytes()); k += 1
    enc.stdin.close(); enc.wait()

if __name__ == '__main__':
    main()
