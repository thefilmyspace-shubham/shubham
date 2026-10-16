#!/usr/bin/env python3
"""Jalsra interview edit renderer.

Hook montage -> title reveal (on the music drop) -> interview with smooth word-by-word text -> outro.
Everything is driven by an EDL json (see style_test.json):

  python3 edit.py style_test.json --out test.mp4            # full render with audio
  python3 edit.py edl.json --stills 2.0,9.5 --stills-dir st  # check frames
  python3 edit.py edl.json --start 0 --end 20 --no-audio --out p0.mp4   # render a chunk

Caption / hook word times are in SOURCE time (seconds in the source file), as they come out of transcribe.py.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
SR = 48000

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def lerp(a, b, u): return a + (b - a) * u
def eo3(u): return 1 - (1 - u) ** 3
def eo5(u): return 1 - (1 - u) ** 5
def ei3(u): return u ** 3
def eio3(u): return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def eback(u, s=1.4):
    u -= 1; return u * u * ((s + 1) * u + s) + 1

# ---------------------------------------------------------------- skia helpers
_tf, _fonts = {}, {}
FACE = {'xb': 'Inter-ExtraBold.ttf', 'b': 'Inter-Bold.ttf', 'm': 'Inter-Medium.ttf',
        'serif': 'InstrumentSerif-Italic.ttf', 'serif_r': 'InstrumentSerif-Regular.ttf',
        'dev': 'NotoSansDevanagari-ExtraBold.ttf', 'dev_b': 'NotoSansDevanagari-Bold.ttf'}

def font(k, size):
    key = (k, round(size, 1))
    if key not in _fonts:
        if k not in _tf:
            _tf[k] = skia.Typeface.MakeFromFile(os.path.join(FONTS, FACE[k]))
        f = skia.Font(_tf[k], size); f.setEdging(skia.Font.Edging.kAntiAlias); f.setSubpixel(True)
        _fonts[key] = f
    return _fonts[key]

def is_dev(s): return any('ऀ' <= ch <= 'ॿ' for ch in s)
def fk(k, s):
    """swap to the Devanagari face when the word is in Devanagari script"""
    if is_dev(s): return 'dev' if k in ('xb', 'b') else 'dev_b'
    return k

def hexc(h, a=1.0):
    h = h.lstrip('#'); return skia.ColorSetARGB(int(clamp(a) * 255), int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def P(color, **kw): return skia.Paint(AntiAlias=True, Color=color, **kw)
def R(x, y, w, h): return skia.Rect.MakeXYWH(x, y, w, h)

def text_w(s, f, track=0.0):
    if not track: return f.measureText(s)
    return sum(f.measureText(ch) for ch in s) + track * (len(s) - 1)

def draw_text(c, s, x, y, f, color, alpha=1.0, blur=0.0, track=0.0, shadow=0.45):
    """x = left edge, y = baseline"""
    if alpha <= 0.003: return
    items = [(s, x)] if not track else []
    if track:
        cx = x
        for ch in s:
            items.append((ch, cx)); cx += f.measureText(ch) + track
    if shadow > 0:
        sp = P(hexc('#000000', shadow * alpha), MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10 + blur))
        for ch, cx in items: c.drawString(ch, cx, y + f.getSize() * 0.04, f, sp)
    p = P(color); p.setAlphaf(clamp(alpha) * (color >> 24 & 255) / 255)
    if blur > 0.3: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    for ch, cx in items: c.drawString(ch, cx, y, f, p)

class Tx:
    def __init__(self, c, s=1.0, px=0, py=0, dx=0, dy=0, rot=0.0):
        self.c, self.s, self.px, self.py, self.dx, self.dy, self.rot = c, s, px, py, dx, dy, rot
    def __enter__(self):
        c = self.c; c.save(); c.translate(self.dx + self.px, self.dy + self.py)
        if self.rot: c.rotate(self.rot)
        c.scale(self.s, self.s); c.translate(-self.px, -self.py); return c
    def __exit__(self, *a): self.c.restore()

def to_img(arr): return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)

# ---------------------------------------------------------------- media
_probe = {}
def probe(src):
    if src not in _probe:
        out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                              'stream=width,height:stream_side_data=rotation', '-of', 'json', src],
                             capture_output=True, text=True).stdout
        st = json.loads(out)['streams'][0]
        w, h = st['width'], st['height']
        rot = 0
        for sd in st.get('side_data_list', []) or []:
            rot = int(sd.get('rotation', 0) or 0)
        if abs(rot) in (90, 270): w, h = h, w
        _probe[src] = (w, h)
    return _probe[src]

def vfilter(src, W, H, fps, item, grade):
    """crop to the output aspect (crop_x/crop_y pick the window), scale, grade"""
    sw, sh = probe(src)
    ar = W / H
    if sw / sh > ar:   # source wider -> crop width
        cw, ch = int(sh * ar) // 2 * 2, sh
    else:
        cw, ch = sw, int(sw / ar) // 2 * 2
    cw = int(cw / item.get('crop_zoom', 1.0)) // 2 * 2; ch = int(ch / item.get('crop_zoom', 1.0)) // 2 * 2
    x = int((sw - cw) * item.get('crop_x', 0.5)); y = int((sh - ch) * item.get('crop_y', 0.5))
    g = {**grade, **item.get('grade', {})}
    f = [f'crop={cw}:{ch}:{x}:{y}', f'scale={W}:{H}:flags=lanczos', f'fps={fps}',
         f"eq=contrast={g.get('contrast', 1.06)}:saturation={g.get('saturation', 1.08)}:brightness={g.get('brightness', 0.0)}:gamma={g.get('gamma', 1.0)}",
         f"colorbalance=rs={g.get('warm', 0.04)}:bs={-g.get('warm', 0.04)}:rm={g.get('warm', 0.04) / 2}:bm={-g.get('warm', 0.04) / 2}"]
    return ','.join(f)

class Reader:
    """sequential RGBA frame reader for one clip item"""
    def __init__(self, item, W, H, fps, grade, t_off=0.0):
        self.W, self.H = W, H
        dur = item['out'] - item['in'] - t_off
        cmd = ['ffmpeg', '-v', 'error', '-ss', f"{item['in'] + t_off:.4f}", '-t', f'{dur + 0.5:.4f}', '-i', item['src'],
               '-vf', vfilter(item['src'], W, H, fps, item, grade), '-an', '-pix_fmt', 'rgba', '-f', 'rawvideo', '-']
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.last = None
    def next(self):
        n = self.W * self.H * 4
        buf = self.p.stdout.read(n)
        if len(buf) == n:
            self.last = to_img(np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 4))
        return self.last
    def close(self):
        try: self.p.stdout.close(); self.p.kill()
        except Exception: pass

_still = {}
def still(src, t, W, H, grade, blur=0.0, dim=1.0, item=None):
    key = (src, round(t, 3), W, H, blur, dim)
    if key not in _still:
        it = dict(item or {}); it.setdefault('in', t)
        vf = vfilter(src, W, H, 30, it, grade)
        if blur: vf += f',gblur=sigma={blur}'
        if dim != 1.0: vf += f',eq=brightness={-(1 - dim) * 0.5}:saturation=0.8'
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', src, '-frames:v', '1', '-vf', vf,
                              '-pix_fmt', 'rgba', '-f', 'rawvideo', '-'], capture_output=True).stdout
        _still[key] = to_img(np.frombuffer(raw[:W * H * 4], np.uint8).reshape(H, W, 4))
    return _still[key]

# ---------------------------------------------------------------- timeline
class Edit:
    def __init__(self, edl, base):
        self.e = edl
        self.W, self.H = edl.get('size', [1080, 1920])
        self.fps = edl.get('fps', 30)
        self.S = self.W / 1080.0 if self.H > self.W else self.H / 1080.0   # type scale
        self.vertical = self.H > self.W
        self.accent = edl.get('accent', '#FFD27A')
        self.grade = edl.get('grade', {})
        self.items = []
        t = 0.0
        for it in edl['timeline']:
            it = dict(it)
            if 'src' in it: it['src'] = os.path.join(base, it['src']) if not os.path.isabs(it['src']) else it['src']
            if 'bg' in it and not os.path.isabs(it['bg'][0]): it['bg'] = [os.path.join(base, it['bg'][0]), it['bg'][1]]
            dur = it['out'] - it['in'] if it['type'] == 'clip' else it['dur']
            it['start'], it['end'] = t, t + dur
            t += dur
            self.items.append(it)
        self.total = t
        self.title_start = next((i['start'] for i in self.items if i['type'] == 'title'), 0.0)
        self.grain = self._grain()

    def _grain(self):
        rng = np.random.default_rng(7); w, h = self.W // 2, self.H // 2; out = []
        for _ in range(4):
            n = rng.normal(0, 1, (h, w)).astype(np.float32)
            g = np.clip(128 + n * 60, 0, 255).astype(np.uint8)
            a = np.full((h, w), int(255 * self.e.get('grain', 0.05)), np.uint8)
            out.append(to_img(np.dstack([g, g, g, a])))
        return out

    def item_at(self, t):
        for i, it in enumerate(self.items):
            if it['start'] <= t < it['end']: return i, it
        return len(self.items) - 1, self.items[-1]

    # ------------------------------------------------------------ text styles
    def layout(self, words, em, style):
        """-> list of (word, font_key, size, x, baseline, is_em)"""
        S, W = self.S, self.W
        maxw = W * (0.84 if self.vertical else 0.7)
        ei = None
        if em:
            for k, w in enumerate(words):
                if w[0].strip('.,!?"\'').lower() == em.lower(): ei = k; break
        if style == 'hook':
            small_k, small_sz, big_k, big_sz = 'xb', 74 * S, 'xb', 132 * S
            up = True
        else:
            small_k, small_sz, big_k, big_sz = 'serif', 66 * S, 'xb', 112 * S
            up = False
        def disp(w, big):
            s = w[0]
            return s.upper() if (up or (big and style == 'hook')) and not is_dev(s) else s
        rows = []   # each row: list of (idx, text, fkey, size)
        def add_rows(idxs, k, sz, big):
            cells = []
            for i in idxs:
                s = disp(words[i], big); f = font(fk(k, s), sz)
                cells.append(((i, s, fk(k, s), sz), f.measureText(s), f.measureText(' ')))
            if not cells: return
            def width(cs): return sum(w for _, w, _ in cs) + sum(sp for _, _, sp in cs[1:])
            if width(cells) <= maxw:
                rows.append([c[0] for c in cells]); return
            # two balanced lines when that fits, else greedy
            best = min(range(1, len(cells)), key=lambda j: max(width(cells[:j]), width(cells[j:])))
            if max(width(cells[:best]), width(cells[best:])) <= maxw:
                rows.append([c[0] for c in cells[:best]]); rows.append([c[0] for c in cells[best:]]); return
            row, rw = [], 0.0
            for cell, ww, sp in cells:
                if row and rw + sp + ww > maxw:
                    rows.append(row); row, rw = [], 0.0
                row.append(cell); rw += (sp if len(row) > 1 else 0) + ww
            if row: rows.append(row)
        if ei is not None:
            add_rows(range(0, ei), small_k, small_sz, False)
            bs = disp(words[ei], True); bsz = big_sz
            while font(fk(big_k, bs), bsz).measureText(bs) > maxw and bsz > 40: bsz *= 0.92
            rows.append([(ei, bs, fk(big_k, bs), bsz)])
            add_rows(range(ei + 1, len(words)), small_k, small_sz, False)
        else:
            k, sz = ('xb', 88 * S) if style == 'hook' else ('b', 66 * S)
            add_rows(range(len(words)), k, sz, False)
        # vertical stacking
        heights = [max(sz for _, _, _, sz in row) * (0.98 if any(i == ei for i, *_ in row) else 1.12) for row in rows]
        total = sum(heights)
        cy = self.H * (0.74 if self.vertical else 0.80) if style != 'hook' else self.H * (0.72 if self.vertical else 0.76)
        y = cy - total / 2
        out = []
        for row, hgt in zip(rows, heights):
            fsz = max(sz for _, _, _, sz in row)
            base = y + hgt * 0.80
            widths = [font(k, sz).measureText(s) for _, s, k, sz in row]
            sp = font(row[0][2], row[0][3]).measureText(' ')
            rw = sum(widths) + sp * (len(row) - 1)
            x = self.W / 2 - rw / 2
            for (i, s, k, sz), ww in zip(row, widths):
                out.append((i, s, k, sz, x, base, i == ei))
                x += ww + sp
            y += hgt
        return out

    def draw_caption(self, c, grp, lt_src, style):
        """grp: {'words': [[text, t_src], ...], 'end': t_src, 'em': word}"""
        words = grp['words']
        t0, t1 = words[0][1], grp['end']
        lead = 0.07
        if lt_src < t0 - lead - 0.01 or lt_src > t1 + 0.01: return
        out_u = prog(lt_src, t1 - 0.2, 0.2)                    # group exit
        ex_a, ex_dy, ex_blur = 1 - eio3(out_u), -14 * self.S * eio3(out_u), 8 * out_u
        for i, s, k, sz, x, base, is_em in self.layout(words, grp.get('em'), style):
            wt = words[i][1] - lead
            d = 0.22 if style == 'hook' else 0.34
            u = prog(lt_src, wt, d)
            if u <= 0: continue
            e = eo5(u)
            f = font(k, sz)
            col = hexc(self.accent) if (is_em and (style == 'hook' or grp.get('accent', True))) else hexc('#FFFFFF')
            if is_em:
                sc = lerp(1.22 if style == 'hook' else 1.12, 1.0, e)
                track = lerp(0.12 * sz, 0.0, e) if style != 'hook' else 0.0
                blur = (1 - e) * 16
                w0 = text_w(s, f, track); cx = x + f.measureText(s) / 2
                with Tx(c, s=sc, px=cx, py=base - sz * 0.35, dy=ex_dy):
                    draw_text(c, s, cx - w0 / 2, base, f, col, alpha=e * ex_a, blur=blur + ex_blur, track=track)
            else:
                dy = (1 - e) * 26 * self.S + ex_dy
                sc = lerp(0.94, 1.0, e)
                cx = x + f.measureText(s) / 2
                a = e * ex_a * (0.92 if k.startswith('serif') else 1.0)
                with Tx(c, s=sc, px=cx, py=base, dy=dy):
                    draw_text(c, s, x, base, f, col, alpha=a, blur=(1 - e) * 9 + ex_blur)

    # ------------------------------------------------------------ frames
    def draw_video(self, c, img, it, lt):
        W, H = self.W, self.H
        dur = it['end'] - it['start']
        z0, z1 = it.get('zoom', [1.0, 1.05])
        z = lerp(z0, z1, eio3(clamp(lt / dur)))
        for pt, amt in it.get('punch', []):        # hard punch-ins on emphasis
            if lt >= pt: z *= amt
        dx = dy = 0.0
        if it.get('section') == 'hook' or it.get('impact'):
            u = prog(lt, 0, 0.32)
            z *= lerp(1.16, 1.0, eo3(u))
            sh = (1 - u) * 14 * self.S
            dx, dy = math.sin(lt * 90) * sh, math.cos(lt * 77) * sh
        fx, fy = it.get('focus', [0.5, 0.42])
        with Tx(c, s=z, px=W * fx, py=H * fy, dx=dx, dy=dy):
            c.drawImageRect(img, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone))

    def overlays(self, c, t, section):
        W, H = self.W, self.H
        # readability gradient under the captions + vignette
        g = skia.GradientShader.MakeLinear([skia.Point(0, H * 0.45), skia.Point(0, H)],
                                           [hexc('#000000', 0.0), hexc('#000000', 0.55 if section != 'title' else 0)])
        c.drawRect(R(0, 0, W, H), skia.Paint(Shader=g))
        v = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.45), max(W, H) * 0.75,
                                           [hexc('#000000', 0.0), hexc('#000000', 0.0), hexc('#000000', 0.42)], [0.0, 0.55, 1.0])
        c.drawRect(R(0, 0, W, H), skia.Paint(Shader=v))

    def draw_title(self, c, it, lt):
        W, H, S = self.W, self.H, self.S
        dur = it['end'] - it['start']
        c.drawPaint(P(hexc('#07080A')))
        if it.get('bg'):
            img = still(it['bg'][0], it['bg'][1], W, H, self.grade, blur=14, dim=0.55)
            z = lerp(1.08, 1.0, eo3(clamp(lt / dur)))
            p = skia.Paint(); p.setAlphaf(0.9 * eo3(prog(lt, 0, 0.4)))
            with Tx(c, s=z, px=W / 2, py=H / 2):
                c.drawImageRect(img, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        out = eio3(prog(lt, dur - 0.35, 0.35))
        title = it.get('title', '')
        f = font('xb', it.get('size', 150) * S)
        n = max(1, len(title))
        track = lerp(0.55, 0.10, eo5(prog(lt, 0.0, 1.1))) * f.getSize()
        widths = [f.measureText(ch) for ch in title]
        tw = sum(widths) + track * (n - 1)
        x = W / 2 - tw / 2; base = H * 0.5 + f.getSize() * 0.33
        with Tx(c, s=lerp(1.0, 1.05, out), px=W / 2, py=H / 2):
            for k, (ch, cw) in enumerate(zip(title, widths)):
                u = eo5(prog(lt, 0.05 + abs(k - (n - 1) / 2) * 0.05, 0.5))
                draw_text(c, ch, x, base + (1 - u) * 30 * S, f, hexc('#FFFFFF'), alpha=u * (1 - out), blur=(1 - u) * 14 + out * 10)
                x += cw + track
            # accent rule
            lu = eo5(prog(lt, 0.45, 0.6))
            lw = tw * 0.42 * lu
            c.drawRRect(skia.RRect.MakeRectXY(R(W / 2 - lw / 2, base + 34 * S, lw, 5 * S), 3 * S, 3 * S),
                        P(hexc(self.accent, 1 - out)))
            sub = it.get('sub')
            if sub:
                fs = font('serif', 64 * S)
                su = eo5(prog(lt, 0.6, 0.6))
                draw_text(c, sub, W / 2 - fs.measureText(sub) / 2, base + 120 * S + (1 - su) * 20 * S, fs,
                          hexc('#FFFFFF'), alpha=su * (1 - out) * 0.92, blur=(1 - su) * 8)
        # flash in on the drop
        fl = 1 - prog(lt, 0, 0.18)
        if fl > 0: c.drawPaint(P(hexc('#FFFFFF', 0.85 * eo3(fl))))

    def draw_outro(self, c, it, lt, last_img):
        W, H, S = self.W, self.H, self.S
        dur = it['end'] - it['start']
        c.drawPaint(P(hexc('#07080A')))
        bgimg = still(it['bg'][0], it['bg'][1], W, H, self.grade, blur=16, dim=0.5) if it.get('bg') else None
        if bgimg is not None:
            p = skia.Paint(); p.setAlphaf(0.85)
            with Tx(c, s=lerp(1.0, 1.06, clamp(lt / dur)), px=W / 2, py=H / 2):
                c.drawImageRect(bgimg, R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)
        out = eio3(prog(lt, dur - 0.6, 0.6))
        y = H * 0.40
        for k, (txt, key, sz, col, gap) in enumerate([(it.get('kicker', ''), 'serif', 70, '#FFFFFF', 1.0),
                                                     (it.get('title', ''), 'xb', 150, self.accent, 1.0),
                                                     (it.get('sub', ''), 'm', 44, '#FFFFFF', 2.2)]):
            if not txt: continue
            f = font(key, sz * S)
            u = eo5(prog(lt, 0.15 + k * 0.18, 0.55))
            y += sz * S * gap
            draw_text(c, txt, W / 2 - f.measureText(txt) / 2, y + (1 - u) * 24 * S, f, hexc(col),
                      alpha=u * (1 - out) * (0.9 if key != 'xb' else 1.0), blur=(1 - u) * 10)
        if out > 0: c.drawPaint(P(hexc('#000000', out)))

    def draw_lower_third(self, c, t):
        lt3 = self.e.get('lower_third')
        if not lt3: return
        W, H, S = self.W, self.H, self.S
        a0, d = lt3['at'], lt3.get('dur', 4.0)
        if not (a0 <= t <= a0 + d): return
        u_in = eo5(prog(t, a0, 0.7)); u_out = eio3(prog(t, a0 + d - 0.45, 0.45))
        x = 70 * S; y = (260 if self.vertical else 120) * S
        fn, fr = font('b', 50 * S), font('serif', 44 * S)
        name, role = lt3['name'], lt3.get('role', '')
        wmax = max(fn.measureText(name), fr.measureText(role)) + 30 * S
        # accent bar grows down, then text wipes in from the bar
        bh = 120 * S * u_in * (1 - u_out)
        c.drawRRect(skia.RRect.MakeRectXY(R(x, y, 6 * S, bh), 3 * S, 3 * S), P(hexc(self.accent)))
        c.save(); c.clipRect(R(x + 6 * S, y - 20 * S, wmax * u_in * (1 - u_out) + 30 * S, 200 * S))
        tx = x + 28 * S - (1 - u_in) * 40 * S
        draw_text(c, name, tx, y + 50 * S, fn, hexc('#FFFFFF'), alpha=u_in * (1 - u_out))
        draw_text(c, role, tx, y + 104 * S, fr, hexc('#FFFFFF'), alpha=0.9 * u_in * (1 - u_out))
        c.restore()

    def render_frames(self, t0, t1, sink, stills=None):
        W, H, fps = self.W, self.H, self.fps
        surf = skia.Surface(W, H); c = surf.getCanvas()
        reader, rid, last_img = None, None, None
        times = stills if stills else [n / fps for n in range(int(round(t0 * fps)), int(round(t1 * fps)))]
        for t in times:
            i, it = self.item_at(t)
            lt = t - it['start']
            c.clear(hexc('#000000'))
            if it['type'] == 'clip':
                if rid != i or stills:
                    if reader: reader.close()
                    reader = Reader(it, W, H, fps, self.grade, t_off=lt); rid = i
                img = reader.next() or last_img
                last_img = img
                if img is not None: self.draw_video(c, img, it, lt)
                self.overlays(c, t, it.get('section'))
                lt_src = it['in'] + lt
                style = 'hook' if it.get('section') == 'hook' else 'main'
                for grp in it.get('captions', []):
                    self.draw_caption(c, grp, lt_src, style)
                if it.get('section') == 'hook':
                    fl = 1 - prog(lt, 0, 0.12)
                    if fl > 0: c.drawPaint(P(hexc('#FFFFFF', 0.55 * fl)))
                elif it.get('fade_in'):
                    fl = 1 - prog(lt, 0, it['fade_in'])
                    if fl > 0: c.drawPaint(P(hexc('#000000', eo3(fl))))
            elif it['type'] == 'title':
                self.draw_title(c, it, lt)
            elif it['type'] == 'outro':
                self.draw_outro(c, it, lt, last_img)
            self.draw_lower_third(c, t)
            # grain
            gp = skia.Paint(); gp.setBlendMode(skia.BlendMode.kOverlay)
            c.drawImageRect(self.grain[int(t * fps) % 4], R(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), gp)
            wm = self.e.get('watermark')
            if wm:
                f = font('m', 26 * self.S)
                draw_text(c, wm, W - f.measureText(wm) - 40 * self.S, (H - 60 * self.S) if not self.vertical else 120 * self.S,
                          f, hexc('#FFFFFF'), alpha=0.6, shadow=0.3)
            sink(t, surf.makeImageSnapshot())
        if reader: reader.close()

# ---------------------------------------------------------------- audio
def load_audio(src, t0=0.0, dur=None):
    cmd = ['ffmpeg', '-v', 'error', '-ss', f'{t0:.4f}']
    if dur is not None: cmd += ['-t', f'{dur:.4f}']
    cmd += ['-i', src, '-vn', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()

def db(x): return 10 ** (x / 20)

def sfx_impact(gain=0.5):
    n = int(SR * 0.9); t = np.arange(n) / SR
    f = 110 * np.exp(-t * 5) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.2)
    rng = np.random.default_rng(3)
    click = rng.normal(0, 1, n) * np.exp(-t * 60) * 0.5
    x = np.tanh((body + click) * 1.6) * gain
    return np.stack([x, x], 1).astype(np.float32)

def sfx_whoosh(d=0.6, gain=0.35, rise=True):
    from scipy.signal import butter, sosfilt
    n = int(SR * d); t = np.linspace(0, 1, n)
    rng = np.random.default_rng(5)
    nz = rng.normal(0, 1, (n, 2))
    lo = sosfilt(butter(2, 900, 'low', fs=SR, output='sos'), nz, axis=0)
    hi = sosfilt(butter(2, 2500, 'high', fs=SR, output='sos'), nz, axis=0)
    mix = (t if rise else 1 - t)[:, None]
    env = (np.sin(np.pi * t) ** 2 if not rise else t ** 2.2 * (1 - np.clip((t - 0.92) / 0.08, 0, 1)))[:, None]
    x = (lo * (1 - mix) + hi * mix) * env
    x = x / (np.abs(x).max() + 1e-9) * gain
    return x.astype(np.float32)

def place(buf, clip, t):
    i = int(round(t * SR))
    if i >= len(buf): return
    if i < 0: clip = clip[-i:]; i = 0
    n = min(len(clip), len(buf) - i)
    buf[i:i + n] += clip[:n]

def render_audio(ed, out_wav, base):
    e = ed.e
    n = int(math.ceil(ed.total * SR)) + SR
    dia = np.zeros((n, 2), np.float32)
    speech = np.zeros(n, np.float32)              # 1 where dialogue plays (for ducking)
    target = db(e.get('dialogue_rms_db', -20))
    for it in ed.items:
        if it['type'] != 'clip' or it.get('mute'): continue
        a = load_audio(it['src'], it['in'], it['out'] - it['in'])
        if not len(a): continue
        mono = a.mean(1)
        rms = np.sqrt(np.mean(mono[np.abs(mono) > 0.01] ** 2)) if np.any(np.abs(mono) > 0.01) else 0
        g = clamp(target / rms, 0.25, 6.0) if rms > 0 else 1.0
        a *= g * db(it.get('gain_db', 0))
        fd = int(SR * 0.012)                           # click-free cut edges
        ramp = np.linspace(0, 1, fd)[:, None]
        a[:fd] *= ramp; a[-fd:] *= ramp[::-1]
        place(dia, a, it['start'])
        i0 = int(it['start'] * SR); speech[i0:i0 + len(a)] = 1.0
    # music, aligned so its drop hits the title
    m = e['music']
    mus_all = load_audio(os.path.join(base, m['file']))
    off = m.get('drop', 0.0) - ed.title_start + m.get('nudge', 0.0)
    if off >= 0: mus = mus_all[int(off * SR):]
    else: mus = np.concatenate([np.zeros((int(-off * SR), 2), np.float32), mus_all])
    mus = mus[:n] if len(mus) >= n else np.concatenate([mus, np.zeros((n - len(mus), 2), np.float32)])
    # level automation per section (dB), smoothed
    lev = np.full(n, m.get('main_db', -21.0), np.float32)
    for it in ed.items:
        i0, i1 = int(it['start'] * SR), int(it['end'] * SR)
        if it['type'] == 'title': lev[i0:i1] = m.get('title_db', -3.0)
        elif it['type'] == 'outro': lev[i0:i1] = m.get('outro_db', -6.0)
        elif it.get('section') == 'hook': lev[i0:i1] = m.get('hook_db', -15.0)
    # extra duck under live speech in the main section
    from scipy.ndimage import uniform_filter1d
    sp = uniform_filter1d(speech, int(SR * 0.25))
    lev = lev - sp * m.get('speech_duck_db', 2.0)
    lev = uniform_filter1d(lev, int(SR * 0.18))
    gain = db(lev)
    # fade out tail
    end_i = int(ed.total * SR); fo = int(SR * m.get('fade_out', 2.0))
    gain[end_i - fo:end_i] *= np.linspace(1, 0, fo) ** 1.5
    gain[end_i:] = 0
    mus *= gain[:, None] * db(m.get('gain_db', 0))
    # sfx
    fx = np.zeros_like(dia)
    if e.get('sfx', True):
        for it in ed.items:
            if it.get('section') == 'hook' and it['start'] > 0.05:
                place(fx, sfx_whoosh(0.35, 0.12, rise=False), it['start'] - 0.17)
        place(fx, sfx_whoosh(1.4, 0.22, rise=True), ed.title_start - 1.4)
        place(fx, sfx_impact(0.42), ed.title_start)
        for it in ed.items:
            if it['type'] == 'outro': place(fx, sfx_whoosh(0.6, 0.14, rise=False), it['start'] - 0.2)
    mix = dia + mus + fx
    peak = np.abs(mix).max()
    if peak > 0.98: mix = np.tanh(mix / peak * 1.2) / np.tanh(1.2) * 0.98
    import wave
    pcm = (np.clip(mix[:end_i], -1, 1) * 32767).astype('<i2')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl'); ap.add_argument('--out', default='out.mp4')
    ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--end', type=float, default=None)
    ap.add_argument('--no-audio', action='store_true'); ap.add_argument('--crf', type=int, default=16)
    ap.add_argument('--stills'); ap.add_argument('--stills-dir', default='stills')
    ap.add_argument('--preset', default='medium')
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(a.edl))
    ed = Edit(json.load(open(a.edl)), base)
    W, H, fps = ed.W, ed.H, ed.fps
    print(f'timeline {ed.total:.2f}s  title @ {ed.title_start:.2f}s  {W}x{H}@{fps}', flush=True)
    if a.stills:
        os.makedirs(a.stills_dir, exist_ok=True)
        ts = [float(s) for s in a.stills.split(',')]
        ed.render_frames(0, 0, lambda t, img: img.save(os.path.join(a.stills_dir, f'{t:06.2f}.png')), stills=ts)
        return
    t1 = ed.total if a.end is None else min(a.end, ed.total)
    wav = os.path.splitext(a.out)[0] + '_mix.wav'
    if not a.no_audio:
        render_audio(ed, wav, base)
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-']
    if not a.no_audio:
        cmd += ['-ss', f'{a.start:.4f}', '-t', f'{t1 - a.start:.4f}', '-i', wav,
                '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000']
    cmd += ['-c:v', 'libx264', '-preset', a.preset, '-crf', str(a.crf), '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', a.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    state = {'n': 0}
    def sink(t, img):
        pr.stdin.write(img.toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
        state['n'] += 1
        if state['n'] % (fps * 5) == 0: print(f'  {t:6.2f}s', flush=True)
    ed.render_frames(a.start, t1, sink)
    pr.stdin.close(); pr.wait()
    print('wrote', a.out)

if __name__ == '__main__':
    main()
