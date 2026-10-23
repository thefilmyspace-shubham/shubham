"""Kinetic text matched to the two reference reels (DXanI5ECvq-, DXeU5dDkeXe).

Measured from the references (30 fps, frame by frame):
- Type: Helvetica Neue mixed weights in one stack — thin/light connector words, medium or bold key words,
  tight negative tracking, tight leading (baseline gap ~0.85 x the next line's size), stepped indents.
  Here: Aileron (CC0 neo-grotesque). Drop licensed Helvetica Neue files in fonts/ and map them via EDL "fonts".
- Entry ("rise"): each word on its own spoken time, comes up from 1.35 em below with ease-out-expo over 0.33 s
  (offset halves every frame: 288 -> 144 -> 72 -> 39 -> 18 -> 6 -> 1 -> 0 px for a 210 px word), opacity in by ~0.12 s,
  real motion blur (10 sub-frame samples over a centred 360 deg shutter, which gives the reference's echo streaks).
- Exit: words leave upward half a frame apart in reading order, ease-in-cubic over 0.1 s (gone in 3 frames), same motion blur.
- Key words: gradient fills (cyan / blue / azure / navy / chrome) with a slow sheen, often behind the speaker.
- Caps: one centred upper-case word at a time (medium, soft drop shadow), quick blur fades between words.

Block format (times in source seconds, sizes in px at 1080 wide):
  {"style": "stack", "anchor": [0.185, 0.536], "end": 14.2, "align": "left",
   "lines": [{"dx": 0,   "words": [{"w": "Look", "t": 12.30, "weight": "medium", "size": 210}]},
             {"dx": 88,  "words": [{"w": "at", "t": 12.45, "weight": "thin", "size": 120}, {"w": "your", "t": 12.52, "weight": "thin", "size": 120}]},
             {"dx": 125, "words": [{"w": "standards", "t": 12.60, "weight": "bold", "size": 142, "fill": "cyan", "layer": "behind"}]}]}
  {"style": "caps", "y": 0.64, "size": 77, "end": 13.1, "words": [["BASEMENT", 12.0], ["WHERE", 12.5]]}
"""
import math, os
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')

FACES = {   # weight -> (file, faux-bold stroke in em)
    'thin': ('Aileron-Thin.ttf', 0.0), 'thin_i': ('Aileron-ThinItalic.ttf', 0.0),
    'light': ('Aileron-Light.ttf', 0.0), 'light_i': ('Aileron-LightItalic.ttf', 0.0),
    'regular': ('Aileron-Regular.ttf', 0.0), 'regular_i': ('Aileron-Italic.ttf', 0.0),
    'medium': ('Aileron-Regular.ttf', 0.012), 'medium_i': ('Aileron-Italic.ttf', 0.012),
    'semibold': ('Aileron-SemiBold.ttf', 0.0), 'semibold_i': ('Aileron-SemiBoldItalic.ttf', 0.0),
    'bold': ('Aileron-Bold.ttf', 0.0), 'bold_i': ('Aileron-BoldItalic.ttf', 0.0),
    'heavy': ('Aileron-Heavy.ttf', 0.0),
}
TRACK = {'thin': -0.02, 'light': -0.025, 'regular': -0.045, 'medium': -0.059, 'semibold': -0.03,
         'bold': 0.0, 'heavy': -0.02}           # em; calibrated against the reference frames
SPACE = 0.22                                       # word gap in em

FILLS = {   # sampled from the reference frames
    'white': None,
    'cyan': {'stops': [(0, '#2FA9BB'), (0.16, '#A6E4EA'), (0.30, '#BDF0F7'), (0.48, '#3EAFC2'), (0.74, '#1F9AAC'), (1, '#23A0B3')]},
    'blue': {'stops': [(0, '#2B7BB4'), (0.35, '#33A0CB'), (0.60, '#9CEEF8'), (0.72, '#44A9CC'), (1, '#2E74B1')],
             'vshade': ('#C6D2E4', '#FFFFFF')},
    'azure': {'stops': [(0, '#2A9ECC'), (0.45, '#2A99C7'), (0.62, '#5CC0E2'), (0.75, '#2A95CA'), (1, '#2580A5')],
              'vshade': ('#C9D9E6', '#FFFFFF')},
    'navy': {'stops': [(0, '#0E2F7B'), (0.40, '#0F3685'), (0.66, '#1993C2'), (0.80, '#144592'), (1, '#145395')]},
    'chrome': {'stops': [(0, '#FFFFFF'), (0.35, '#F4F3F7'), (0.52, '#CFCED8'), (0.60, '#BDBCC8'), (0.72, '#F2F2F6'), (1, '#DCDBE4')], 'axis': 'y'},
}

ENTRY_D, ENTRY_DY, ENTRY_FADE = 0.33, 1.35, 0.025
EXIT_D, EXIT_DY, EXIT_STAGGER = 0.10, 1.35, 1 / 60
SUBSAMPLES = 10
SHUTTER = 1 / 30          # blur length in seconds = one reference frame, independent of the output fps

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def hexc(h, a=1.0):
    h = h.lstrip('#'); return skia.ColorSetARGB(int(clamp(a) * 255), int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
def out_expo(u): return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def in_expo(u): return 0.0 if u <= 0 else 2 ** (10 * (u - 1)) - 2 ** -10 * (1 - u)

class Kinetic:
    def __init__(self, W, H, fps=30, fonts=None, scale=None):
        self.W, self.H, self.fps = W, H, fps
        self.S = scale or (W / 1080.0)
        self.over = fonts or {}
        self._tf, self._f = {}, {}

    # ------------------------------------------------------------ fonts
    def font(self, weight, size):
        key = (weight, round(size, 2))
        if key not in self._f:
            fn = self.over.get(weight) or FACES[weight][0]
            if fn not in self._tf:
                self._tf[fn] = skia.Typeface.MakeFromFile(fn if os.path.isabs(fn) else os.path.join(FONTS, fn))
            f = skia.Font(self._tf[fn], size); f.setSubpixel(True); f.setEdging(skia.Font.Edging.kAntiAlias)
            f.setHinting(skia.FontHinting.kNone)
            self._f[key] = f
        return self._f[key]

    def stroke(self, weight):
        return 0.0 if weight in self.over else FACES[weight][1]

    def advances(self, s, f, track):
        return [f.measureText(ch) + track for ch in s]

    # ------------------------------------------------------------ layout
    def layout(self, blk):
        """words with absolute x/baseline and resolved style; cached on the block"""
        if '_lay' in blk: return blk['_lay']
        S, W, H = self.S, self.W, self.H
        ax, ay = blk.get('anchor', [0.5, 0.5])
        x0, y = ax * W, ay * H
        out, k = [], 0
        for li, line in enumerate(blk['lines']):
            words = line['words']
            lsz = max(w.get('size', 120) for w in words) * S
            if li > 0: y += line.get('gap', 0.86) * lsz
            items, x = [], 0.0
            for w in words:
                wt = w.get('weight', 'regular'); base = wt.replace('_i', '')
                sz = w.get('size', 120) * S
                f = self.font(wt, sz)
                tr = w.get('track', TRACK.get(base, -0.03)) * sz
                adv = self.advances(w['w'], f, tr)
                wd = sum(adv) - tr
                items.append(dict(w, _f=f, _tr=tr, _wd=wd, _x=x, _sz=sz, _k=k, _wt=wt))
                x += wd + SPACE * sz; k += 1
            lw = x - SPACE * items[-1]['_sz']
            align = line.get('align', blk.get('align', 'left'))
            lx = x0 + line.get('dx', 0) * S - (lw / 2 if align == 'center' else lw if align == 'right' else 0)
            for it in items:
                it['_x'] += lx; it['_y'] = y + line.get('dy', 0) * S
                out.append(it)
        blk['_lay'] = out
        return out

    # ------------------------------------------------------------ motion
    def state(self, w, t, blk):
        """(dy, alpha) of a word at source time t"""
        t_in = w['t'] - w.get('lead', 0.0)
        if t < t_in: return None
        sz = w['_sz']
        u = (t - t_in) / w.get('entry_d', ENTRY_D)
        dy = ENTRY_DY * sz * (1 - out_expo(clamp(u)))
        a = clamp((t - t_in) / ENTRY_FADE)
        end = blk.get('end')
        if end is not None:
            te = w.get('exit_at', end + w['_k'] * blk.get('exit_stagger', EXIT_STAGGER))
            if t >= te:
                v = clamp((t - te) / EXIT_D)
                if v >= 1: return None
                dy -= EXIT_DY * sz * v ** 3
                a *= 1 - clamp((v - 0.2) / 0.8)
        return dy, a

    # ------------------------------------------------------------ paint
    def paint_for(self, w, t, x, y):
        fill = FILLS.get(w.get('fill', 'white'))
        p = skia.Paint(AntiAlias=True)
        if fill is None:
            p.setColor(hexc(w.get('color', '#FFFFFF')))
        else:
            sz, wd = w['_sz'], w['_wd']
            pos = [s for s, _ in fill['stops']]; cols = [hexc(c) for _, c in fill['stops']]
            sheen = (t * 0.06 * wd) % (wd * 0.3) if w.get('sheen', True) else 0.0
            if fill.get('axis') == 'y':
                g = skia.GradientShader.MakeLinear([skia.Point(x, y - sz * 0.75), skia.Point(x + wd * 0.12, y + sz * 0.05)], cols, pos)
            else:
                g = skia.GradientShader.MakeLinear([skia.Point(x - wd * 0.08 + sheen, y - sz * 0.8),
                                                    skia.Point(x + wd * 1.02 + sheen, y + sz * 0.1)], cols, pos,
                                                   skia.TileMode.kMirror)
            if fill.get('vshade'):
                v = skia.GradientShader.MakeLinear([skia.Point(x, y - sz * 0.75), skia.Point(x, y)],
                                                   [hexc(fill['vshade'][0]), hexc(fill['vshade'][1])])
                g = skia.Shaders.Blend(skia.BlendMode.kMultiply, g, v)
            p.setShader(g)
        st = self.stroke(w['_wt']) * w['_sz']
        if st > 0:
            p.setStyle(skia.Paint.kStrokeAndFill_Style); p.setStrokeWidth(st); p.setStrokeJoin(skia.Paint.kRound_Join)
        return p

    def glyphs(self, c, w, x, y, paint):
        f, tr = w['_f'], w['_tr']
        for ch in w['w']:
            c.drawString(ch, x, y, f, paint); x += f.measureText(ch) + tr

    def draw_word(self, c, w, t, blk):
        x, y = w['_x'], w['_y']
        dt = SHUTTER
        samples = [t + dt * (k / (SUBSAMPLES - 1) - 0.5) for k in range(SUBSAMPLES)]   # centred 360 deg shutter
        st = [self.state(w, ts, blk) for ts in samples]
        st = [s for s in st if s is not None]
        cur = self.state(w, t, blk)
        if not st or cur is None and not st: return
        moving = max(s[0] for s in st) - min(s[0] for s in st) > 0.6
        shadow = w.get('shadow', 0.22 if w.get('fill', 'white') == 'white' else 0.0)
        if shadow and cur is not None:
            sp = skia.Paint(AntiAlias=True, Color=hexc('#000000', shadow * cur[1]),
                            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, max(2.0, w['_sz'] * 0.05)))
            self.glyphs(c, w, x, y + cur[0] + w['_sz'] * 0.03, sp)
        if not moving:
            dy, a = cur if cur is not None else st[0]
            p = self.paint_for(w, t, x, y + dy); p.setAlphaf(a * p.getAlphaf())
            self.glyphs(c, w, x, y + dy, p)
            return
        c.saveLayer(None, skia.Paint())        # accumulation buffer: samples add up (kPlus)
        for dy, a in st:
            p = self.paint_for(w, t, x, y + dy); p.setAlphaf(a / len(samples) * p.getAlphaf())
            p.setBlendMode(skia.BlendMode.kPlus)
            self.glyphs(c, w, x, y + dy, p)
        c.restore()

    def draw_caps(self, c, blk, t):
        words = blk['words']
        S = self.S
        sz = blk.get('size', 77) * S
        f = self.font(blk.get('weight', 'medium'), sz)
        tr = blk.get('track', 0.0) * sz
        cy = blk.get('y', 0.64) * self.H
        for i, (s, t0) in enumerate(words):
            t1 = words[i + 1][1] if i + 1 < len(words) else blk['end']
            if not (t0 - 0.01 <= t <= t1 + 0.14): continue
            a_in = clamp((t - t0) / 0.08); a_out = 1 - clamp((t - t1) / 0.13)
            a = a_in * a_out
            if a <= 0: continue
            blur = (1 - a_in) * 6 + (1 - a_out) * 9
            s = s.upper()
            wd = sum(f.measureText(ch) + tr for ch in s) - tr
            x = self.W / 2 - wd / 2
            w = {'w': s, '_f': f, '_tr': tr, '_sz': sz, '_wd': wd, '_wt': blk.get('weight', 'medium'),
                 'fill': blk.get('fill', 'white'), 'color': blk.get('color', '#FFFFFF'), 'sheen': False}
            sh = blk.get('shadow', 0.5)
            if sh > 0:
                sp = skia.Paint(AntiAlias=True, Color=hexc('#000000', sh * a),
                                MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 9 * S + blur))
                self.glyphs(c, w, x, cy + 4 * S, sp)
            p = self.paint_for(w, t, x, cy); p.setAlphaf(a)
            if blur > 0.3: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
            self.glyphs(c, w, x, cy, p)

    # ------------------------------------------------------------ public
    def needs_matte(self, blocks):
        return any(w.get('layer') == 'behind' for b in blocks if b.get('style', 'stack') == 'stack'
                   for l in b['lines'] for w in l['words'])

    def draw(self, c, blocks, t, layer='front'):
        for blk in blocks:
            style = blk.get('style', 'stack')
            if style == 'caps':
                if layer == blk.get('layer', 'front'): self.draw_caps(c, blk, t)
                continue
            first = min(w['t'] - w.get('lead', 0.0) for l in blk['lines'] for w in l['words'])
            if t < first - 0.05: continue
            if blk.get('end') is not None and t > blk['end'] + 2.0: continue
            for w in self.layout(blk):
                if w.get('layer', blk.get('layer', 'front')) == layer:
                    self.draw_word(c, w, t, blk)
