#!/usr/bin/env python3
"""Documentary-style reel renderer: talking-head A-roll (jump-cut punch-ins only, no graphics on it) with full-screen
B-roll collages built from REAL newspaper cuttings / article screenshots (Magnates-Media look: torn paper cut-outs on a
dark textured desk, highlighter strokes, red marker circles, camera pushes, grain), minimal Hindi subtitles.

  python3 docu.py projects/paimal/edl.json --out out.mp4 [--start 30 --end 45] [--stills 12,40 --stills-dir d]

EDL (all times are SOURCE seconds; the renderer maps them through the A-roll cuts):
  "segments": [[src0, src1, zoom], ...]     A-roll pieces in order (pauses removed between them)
  "brolls": [{"t0", "t1", "label": {"text"}, "pieces": [...], "cam": [[t, cx, cy, zoom], ...]}]
     piece: {"img", "crop": [x,y,w,h], "css": true (crop/quote rects in CSS px of a web shot, scaled by its .json),
             "pos": [x,y] scene centre, "w": scene width, "rot": deg, "at": src time it lands, "fx": "drop|slide",
             "hl": [{"rect": [x,y,w,h]} | {"quote": i, "lines": [..]}, "at": t, "d": seconds per line],
             "circle": [{"rect": [x,y,w,h], "at": t}]}
     cam keys use broll-relative seconds unless given as {"at": src}.
"""
import argparse, json, math, os, subprocess, sys
import numpy as np
import skia
import uharfbuzz as hb
from PIL import Image, ImageFilter

W, H, FPS = 1080, 1920, 30
BASE = os.path.dirname(os.path.abspath(__file__))
SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear)                      # A-roll frames (1440 proxy, mild downscale)
SAMPLING_B = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNearest)  # mipmapped B-roll assets


def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def ease_io(u): u = clamp(u); return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2
def out_cubic(u): u = clamp(u); return 1 - (1 - u) ** 3
def out_expo(u): u = clamp(u); return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)
def out_back(u, s=1.25): u = clamp(u) - 1; return 1 + (s + 1) * u ** 3 + s * u ** 2
def path(p): return p if os.path.isabs(p) else os.path.join(BASE, p)


# ---------------------------------------------------------------- timeline
class Timeline:
    def __init__(self, segs):
        self.segs, acc = [], 0.0
        for s in segs:
            s0, s1, z = s[0], s[1], (s[2] if len(s) > 2 else 1.0)
            self.segs.append({'src0': s0, 'src1': s1, 'zoom': z, 't0': acc, 't1': acc + s1 - s0}); acc += s1 - s0
        self.dur = acc

    def at(self, t):
        for s in self.segs:
            if t < s['t1']: return s, s['src0'] + max(0.0, t - s['t0'])
        s = self.segs[-1]; return s, s['src1']

    def tl(self, src):
        """source time -> timeline time (a time inside a removed pause snaps to the next kept piece)"""
        for s in self.segs:
            if src < s['src0']: return s['t0']
            if src <= s['src1']: return s['t0'] + src - s['src0']
        return self.dur


# ---------------------------------------------------------------- A-roll reader (sequential, forward-only)
class Reader:
    def __init__(self, f, start_src=0.0):
        self.f = f
        out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                              '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.split(',')
        self.w, self.h = int(out[0]), int(out[1])
        self.start = max(0.0, start_src - 0.5)
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{self.start:.3f}', '-i', f, '-f', 'rawvideo',
                                   '-pix_fmt', 'rgba', '-r', str(FPS), '-'], stdout=subprocess.PIPE, bufsize=10 ** 8)
        self.idx = int(round(self.start * FPS)) - 1; self.frame = None

    def get(self, src):
        want = int(round(src * FPS))
        n = self.w * self.h * 4
        while self.idx < want:
            buf = self.p.stdout.read(n)
            if len(buf) < n: break
            self.frame = buf; self.idx += 1
        arr = np.frombuffer(self.frame, np.uint8).reshape(self.h, self.w, 4)
        return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType)


def grade_filter(g):
    c, s = g.get('contrast', 1.0), g.get('saturation', 1.0)
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    sat = np.array([[lr * (1 - s) + s, lg * (1 - s), lb * (1 - s)],
                    [lr * (1 - s), lg * (1 - s) + s, lb * (1 - s)],
                    [lr * (1 - s), lg * (1 - s), lb * (1 - s) + s]])
    m = sat * c; off = 0.5 * (1 - c) + g.get('lift', 0.0)
    warm = g.get('warmth', 0.0)
    rows = []
    for i in range(3):
        rows += list(m[i]) + [0.0, off + (warm if i == 0 else -warm if i == 2 else 0.0)]
    rows += [0, 0, 0, 1, 0]
    return skia.ColorFilters.Matrix(rows)


# ---------------------------------------------------------------- text (HarfBuzz-shaped Devanagari)
class Font:
    cache = {}

    def __init__(self, f, size):
        key = (f, size)
        if key not in Font.cache:
            face = hb.Face(hb.Blob.from_file_path(path(f)))
            Font.cache[key] = (hb.Font(face), face.upem, skia.Font(skia.Typeface.MakeFromFile(path(f)), size))
        self.hbf, self.upem, self.sk = Font.cache[key]; self.size = size

    def blob(self, text):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
        hb.shape(self.hbf, buf, {})
        sc = self.size / self.upem; x = 0.0; gl, pts = [], []
        for i, p in zip(buf.glyph_infos, buf.glyph_positions):
            gl.append(i.codepoint); pts.append(skia.Point(x + p.x_offset * sc, -p.y_offset * sc)); x += p.x_advance * sc
        b = skia.TextBlobBuilder(); b.allocRunPos(self.sk, gl, pts)
        return b.make(), x


# ---------------------------------------------------------------- procedural textures
def rng_noise(h, w, scale, seed):
    r = np.random.default_rng(seed)
    small = r.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255


def desk_texture(w=1400, h=2400, seed=3):
    n = (0.45 * rng_noise(h, w, 260, seed) + 0.3 * rng_noise(h, w, 60, seed + 1) + 0.15 * rng_noise(h, w, 12, seed + 2)
         + 0.1 * rng_noise(h, w, 3, seed + 3))
    fib = rng_noise(h, w // 6, 2, seed + 4); fib = np.asarray(Image.fromarray((fib * 255).astype(np.uint8)).resize((w, h)), np.float32) / 255
    v = 0.055 + 0.07 * n + 0.025 * fib
    rgb = np.stack([v * 1.05, v * 0.98, v * 0.92], -1)
    yy, xx = np.mgrid[0:h, 0:w]; d = np.sqrt(((xx - w / 2) / (w * 0.62)) ** 2 + ((yy - h / 2) / (h * 0.55)) ** 2)
    rgb *= np.clip(1.25 - 0.75 * d ** 1.6, 0.25, 1.2)[..., None]
    a = np.concatenate([np.clip(rgb * 255, 0, 255), np.full((h, w, 1), 255.0)], -1).astype(np.uint8)
    return skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType)


def grain_frames(n=6, seed=11, strength=0.07):
    """film grain as pre-baked translucent black/white specks (cheap src-over instead of an overlay blend)"""
    r = np.random.default_rng(seed); out = []
    for _ in range(n):
        g = r.normal(0, 1, (H // 2, W // 2)).astype(np.float32)
        g = np.asarray(Image.fromarray(((g * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR), np.float32) / 255 - 0.5
        a = np.abs(g) * 2 * strength
        v = (g > 0).astype(np.float32)
        rgba = np.stack([v * a, v * a, v * a, a], -1)  # premultiplied
        out.append(skia.Image.fromarray(np.ascontiguousarray((rgba * 255).astype(np.uint8)), colorType=skia.kRGBA_8888_ColorType,
                                        alphaType=skia.kPremul_AlphaType))
    return out


def vignette_image():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (H * 0.72)) ** 2 + ((yy - H / 2) / (H * 0.72)) ** 2)
    a = np.clip((d - 0.45) / 0.55, 0, 1) ** 1.2 * 0.62
    rgba = np.zeros((H, W, 4), np.uint8); rgba[..., 3] = (a * 255).astype(np.uint8)
    return skia.Image.fromarray(rgba, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)


def torn_mask(w, h, seed, depth=7):
    """alpha mask with ragged top/bottom edges and slightly uneven sides (torn paper)"""
    r = np.random.default_rng(seed)
    def edge(n, d):
        e = np.cumsum(r.normal(0, 1, n)); e -= np.linspace(e[0], e[-1], n)
        e = (e - e.min()) / (np.ptp(e) + 1e-6) * d
        return e + r.random(n) * d * 0.35
    m = np.ones((h, w), np.float32)
    top, bot = edge(w, depth), edge(w, depth); left, right = edge(h, depth * 0.4), edge(h, depth * 0.4)
    yy = np.arange(h)[:, None]; xx = np.arange(w)[None, :]
    m *= np.clip(yy - top[None, :], 0, 1) * np.clip((h - 1 - yy) - bot[None, :], 0, 1)
    m *= np.clip(xx - left[:, None], 0, 1) * np.clip((w - 1 - xx) - right[:, None], 0, 1)
    return m


# ---------------------------------------------------------------- B-roll pieces
class Piece:
    def __init__(self, spec, tl, b_t0):
        self.spec = spec
        im = Image.open(path(spec['img'])).convert('RGB')
        self.s = 1.0
        meta = None
        if spec.get('css'):
            meta = json.load(open(os.path.splitext(path(spec['img']))[0] + '.json')); self.s = meta['scale']
        cx, cy, cw, ch = [v * self.s for v in spec['crop']]
        content = im.crop((int(cx), int(cy), int(cx + cw), int(cy + ch)))
        up = spec.get('upscale', 1.0)
        if up != 1.0:
            content = content.resize((int(content.width * up), int(content.height * up)), Image.LANCZOS)
            content = content.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
        self.k_src = up  # content px per (scaled) source px
        pad = int(spec.get('pad', 22) * up)
        paper = tuple(spec.get('paper', [252, 251, 247]))
        cw2, ch2 = content.width + 2 * pad, content.height + 2 * pad
        canvas = Image.new('RGB', (cw2, ch2), paper); canvas.paste(content, (pad, pad))
        arr = np.asarray(canvas, np.float32)
        tex = 0.965 + 0.035 * rng_noise(ch2, cw2, 4, spec.get('seed', 5))  # faint paper tooth
        arr *= tex[..., None]
        mask = torn_mask(cw2, ch2, spec.get('seed', 5), depth=spec.get('tear', 9) * up) if spec.get('torn', True) else np.ones((ch2, cw2), np.float32)
        rgba = np.concatenate([arr * mask[..., None], (mask * 255)[..., None]], -1).clip(0, 255).astype(np.uint8)
        img = skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.kRGBA_8888_ColorType)
        self.pad, self.wpx, self.hpx = pad, cw2, ch2
        self.k = spec['w'] / cw2  # scene px per piece px
        # bake the drop shadow once (16 px blur, 16 px down in scene units) instead of filtering every frame
        sig, off = 16 / self.k, 16 / self.k
        self.m = m = int(3 * sig + off + 4)
        surf = skia.Surface(cw2 + 2 * m, ch2 + 2 * m); cv = surf.getCanvas(); cv.clear(skia.ColorTRANSPARENT)
        cv.drawImage(img, m, m, skia.SamplingOptions(),
                     skia.Paint(ImageFilter=skia.ImageFilters.DropShadow(0, off, sig, sig, skia.Color4f(0, 0, 0, 0.75))))
        self.img = surf.makeImageSnapshot().withDefaultMipmaps()
        self.pos, self.rot = spec['pos'], spec.get('rot', 0.0)
        self.t_in = tl.tl(spec['at']) - b_t0 if 'at' in spec else spec.get('t', 0.0)
        self.fx = spec.get('fx', 'drop')
        self.crop_px = (cx, cy)
        # marks -> piece px rects
        self.hls = []
        for h in spec.get('hl', []):
            if 'quote' in h:
                lines = meta['quotes'][h['quote']]['lines']
                if 'lines' in h: lines = [lines[i] for i in h['lines']]
                rects = [self.css_rect(l) for l in lines]
            else:
                rects = [self.src_rect(h['rect'])] if not isinstance(h['rect'][0], list) else [self.src_rect(r) for r in h['rect']]
            t = tl.tl(h['at']) - b_t0; d = h.get('d', 0.32)
            for i, r in enumerate(rects):
                self.hls.append({'r': r, 't': t + i * d * 0.92, 'd': d, 'color': h.get('color', 'yellow')})
        self.circles = [{'r': self.src_rect(c['rect']), 't': tl.tl(c['at']) - b_t0, 'd': c.get('d', 0.42),
                         'seed': i + 1} for i, c in enumerate(spec.get('circle', []))]

    def scene_point(self, px, py):
        """piece px -> scene coords at rest (after landing)"""
        x, y = (px - self.wpx / 2) * self.k, (py - self.hpx / 2) * self.k
        a = math.radians(self.rot)
        return self.pos[0] + x * math.cos(a) - y * math.sin(a), self.pos[1] + x * math.sin(a) + y * math.cos(a)

    def focus(self, mark=None, i=0):
        """scene point to frame and the widest zoom that still shows it whole"""
        if mark == 'hl': x, y, w, h = self.hls[i]['r']
        elif mark == 'circle': x, y, w, h = self.circles[i]['r']; w += 2 * h
        else: return tuple(self.pos), 1020 / self.spec['w']
        return self.scene_point(x + w / 2 - (h if mark == 'circle' else 0), y + h / 2), 1000 / max(1.0, w * self.k)

    def css_rect(self, r):
        x, y, w, h = [v * self.s for v in r]
        return [(x - self.crop_px[0]) * self.k_src + self.pad, (y - self.crop_px[1]) * self.k_src + self.pad,
                w * self.k_src, h * self.k_src]

    def src_rect(self, r):
        if self.spec.get('css'): return self.css_rect(r)
        x, y, w, h = r
        return [(x - self.crop_px[0]) * self.k_src + self.pad, (y - self.crop_px[1]) * self.k_src + self.pad,
                w * self.k_src, h * self.k_src]

    def state(self, t):
        """(visible, dx, dy, scale, rot, alpha) of the landing animation at broll time t"""
        u = (t - self.t_in) / 0.34
        if u < 0: return None
        if self.fx == 'slide':
            dx, dy = self.spec.get('from', [0, 900])
            e = out_expo(u); return (dx * (1 - e), dy * (1 - e), 1.0, self.rot, clamp(u * 4))
        e = out_back(u, 1.1)
        return (0.0, 0.0, 1.0 + 0.22 * (1 - e), self.rot + 5.0 * (1 - out_cubic(u)), clamp(u * 3.5))

    def moving(self, t): return self.t_in - 0.02 <= t <= self.t_in + 0.36

    def draw(self, c, t, shadow_paint):
        st = self.state(t)
        if st is None: return
        dx, dy, sc, rot, a = st
        c.save()
        c.translate(self.pos[0] + dx, self.pos[1] + dy); c.rotate(rot); c.scale(self.k * sc, self.k * sc)
        c.translate(-self.wpx / 2, -self.hpx / 2)
        c.drawImage(self.img, -self.m, -self.m, SAMPLING_B, skia.Paint(Alphaf=a))
        # highlighter strokes (multiply over the print so the ink stays dark)
        for h in self.hls:
            u = (t - h['t']) / h['d']
            if u <= 0: continue
            x, y, w, hh = h['r']; e = ease_io(u)
            col = {'yellow': skia.Color(255, 224, 55), 'red': skia.Color(255, 120, 110)}[h['color']]
            hp = skia.Paint(Color=col, BlendMode=skia.BlendMode.kMultiply, AntiAlias=True, Alphaf=a)
            ext = hh * 0.12
            rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - ext, y + hh * 0.02, (w + 2 * ext) * e, hh * 0.98), hh * 0.18, hh * 0.18)
            c.drawRRect(rr, hp)
        # red marker circles
        for ci in self.circles:
            u = (t - ci['t']) / ci['d']
            if u <= 0: continue
            x, y, w, hh = ci['r']; cxp, cyp = x + w / 2, y + hh / 2
            rx, ry = w / 2 + hh * 0.42, hh / 2 + hh * 0.38
            r = np.random.default_rng(ci['seed']); pth = skia.Path()
            turns = 1.12; n = 90; a0 = math.radians(-160)
            jit = r.normal(0, 1, 6)
            for i in range(n + 1):
                th = a0 + 2 * math.pi * turns * i / n
                k = 1 + 0.035 * math.sin(3 * th + jit[0]) + 0.025 * math.sin(5 * th + jit[1]) + 0.06 * i / n
                px, py = cxp + rx * k * math.cos(th), cyp + ry * k * math.sin(th) + 0.04 * hh * i / n
                pth.moveTo(px, py) if i == 0 else pth.lineTo(px, py)
            pm = skia.PathMeasure(pth, False); seg = skia.Path()
            pm.getSegment(0, pm.getLength() * ease_io(u), seg, True)
            sw = max(4.0, hh * 0.13)
            c.drawPath(seg, skia.Paint(Color=skia.Color(222, 30, 38), Style=skia.Paint.kStroke_Style, StrokeWidth=sw,
                                       StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join,
                                       AntiAlias=True, Alphaf=0.92 * a))
        c.restore()


class Broll:
    def __init__(self, spec, tl, fonts):
        self.spec = spec
        self.t0, self.t1 = tl.tl(spec['t0']), tl.tl(spec['t1'])
        self.pieces = [Piece(p, tl, self.t0) for p in spec['pieces']]
        byid = {p.spec.get('id', str(i)): p for i, p in enumerate(self.pieces)}
        self.cam = []
        for k in spec.get('cam', [[0, 540, 960, 1.0]]):
            if isinstance(k, dict):
                t = tl.tl(k['at']) - self.t0 if 'at' in k else k.get('t', 0.0)
                z = k.get('zoom', 1.0)
                if 'focus' in k:
                    (fx, fy), fit = byid[k['focus']].focus(k.get('mark'), k.get('i', 0))
                    z = min(z, max(fit, 1.0), spec.get('max_zoom', 9))
                    ys = k.get('screen_y', 900)  # where on screen the focus point should sit
                    self.cam.append((t, fx + k.get('dx', 0), fy - (ys - H / 2) / z, z, k.get('d', 0.5)))
                else:
                    self.cam.append((t, k.get('cx', 540), k.get('cy', 960), z, k.get('d', 0.5)))
            else:
                self.cam.append(tuple(k) + (0.5,))
        self.cam.sort(key=lambda c: c[0])
        self.fonts = fonts
        labels = spec.get('labels') or ([spec['label']] if spec.get('label') else [])
        self.labels = []
        for L in labels:
            t = tl.tl(L['at']) - self.t0 if 'at' in L else L.get('t', 0.12)
            blob, w = fonts['label'].blob(L['text']); self.labels.append((t, blob, w))
        self.labels.sort(key=lambda x: x[0])

    def camera(self, t):
        """hold, then a quick eased move to each key's target starting at the key time (Magnates-style whip)"""
        ks = self.cam; cur = ks[0][1:4]
        for k in ks[1:]:
            if t <= k[0]: break
            u = ease_io((t - k[0]) / k[4])
            cur = tuple(cur[i] + (k[1 + i] - cur[i]) * u for i in range(3))
        cx, cy, z = cur
        return cx, cy, z * (1 + 0.010 * t)  # constant slow push-in

    def moving(self, t):
        if any(p.moving(t) for p in self.pieces): return True
        c0, c1 = self.camera(t - 1 / FPS), self.camera(t + 1 / FPS)
        return math.hypot(c1[0] - c0[0], c1[1] - c0[1]) * c1[2] > 9 or abs(c1[2] - c0[2]) > 0.012

    def draw_scene(self, c, t, desk, shadow):
        cx, cy, z = self.camera(t)
        c.save()
        # desk with mild parallax
        dx = round(W / 2 - (cx - 540) * 0.25 * z - desk.width() / 2); dy = round(H / 2 - (cy - 960) * 0.25 * z - desk.height() / 2)
        c.drawImage(desk, dx, dy, skia.SamplingOptions())  # plain blit with mild parallax
        c.translate(W / 2, H / 2); c.scale(z, z); c.translate(-cx, -cy)
        for p in self.pieces: p.draw(c, t, shadow)
        c.restore()

    def draw_label(self, c, t):
        cur = [L for L in self.labels if L[0] <= t]
        if not cur: return
        lt, blob, lw = cur[-1]
        u = (t - lt) / 0.30
        e = out_expo(u); x, y = 60, 236
        padx, h = 22, 62
        c.save(); c.clipRect(skia.Rect.MakeXYWH(x, y - 4, (lw + 2 * padx + 14) * e, h + 30))
        c.drawRect(skia.Rect.MakeXYWH(x + 4, y + 8, lw + 2 * padx + 10, h),
                   skia.Paint(Color=skia.Color(0, 0, 0), Alphaf=0.5, MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
        c.drawRect(skia.Rect.MakeXYWH(x, y, 10, h), skia.Paint(Color=skia.Color(255, 214, 0)))
        c.drawRect(skia.Rect.MakeXYWH(x + 10, y, lw + 2 * padx, h), skia.Paint(Color=skia.Color(206, 22, 32)))
        c.drawTextBlob(blob, x + 10 + padx, y + h * 0.74, skia.Paint(Color=skia.ColorWHITE, AntiAlias=True))
        c.restore()


# ---------------------------------------------------------------- subtitles
class Subs:
    def __init__(self, words, tl, cfg):
        self.cfg = cfg; self.font = Font(cfg.get('font', 'fonts/Mukta-Bold.ttf'), cfg.get('size', 56))
        kw = set(cfg.get('keywords', []))
        maxc, maxw = cfg.get('max_chars', 20), cfg.get('max_words', 4)
        # clauses: split at punctuation / clause ends / pauses, then cut each clause into balanced chunks
        clauses, cur = [], []
        for i, wd in enumerate(words):
            cur.append(wd[:3])
            nxt = words[i + 1] if i + 1 < len(words) else None
            end = (len(wd) > 3 and wd[3]) or wd[0][-1] in '।,?!' or nxt is None or nxt[1] - wd[2] > 0.32
            if end: clauses.append(cur); cur = []
        if cur: clauses.append(cur)
        chunks = []
        for cl in clauses:
            chars = sum(len(w[0]) for w in cl) + len(cl) - 1
            k = max(math.ceil(len(cl) / maxw), math.ceil(chars / (maxc + 2)), 1)
            k = min(k, max(1, len(cl) // 2)) if len(cl) > 1 else 1
            # balanced split by character count, no single-word tails unless unavoidable
            target = chars / k; part, acc = [], 0
            for idx, w in enumerate(cl):
                left_words = len(cl) - idx
                if part and len(chunks) < 10 ** 9 and acc + len(w[0]) / 2 > target and left_words >= 2 and len(part) >= 2:
                    chunks.append(part); part, acc = [], 0
                part.append(w); acc += len(w[0]) + 1
            if part:
                if len(part) == 1 and chunks and chunks[-1] and len(chunks[-1]) >= 2 and chunks[-1][-1][2] >= cl[0][1]:
                    chunks[-1].append(part[0])
                else:
                    chunks.append(part)
        self.items = []
        for ch in chunks:
            t0 = tl.tl(ch[0][1]) - 0.05; t1 = tl.tl(ch[-1][2]) + 0.12
            parts = []
            for w, _, _ in ch:
                clean = w.strip('।,?!')
                parts.append((w.rstrip('।,') if cfg.get('strip_punct', True) else w, clean in kw))
            self.items.append({'t0': t0, 't1': t1, 'parts': parts})
        for a, b in zip(self.items, self.items[1:]):
            a['t1'] = min(a['t1'] if b['t0'] - a['t1'] > 0.25 else b['t0'], b['t0'])
        self.cache = {}

    def layout(self, i):
        if i in self.cache: return self.cache[i]
        it = self.items[i]; space = self.font.size * 0.28; x = 0; runs = []
        for w, k in it['parts']:
            blob, adv = self.font.blob(w); runs.append((blob, x, k)); x += adv + space
        self.cache[i] = (runs, x - space); return self.cache[i]

    def draw(self, c, t):
        for i, it in enumerate(self.items):
            if it['t0'] <= t < it['t1']:
                runs, width = self.layout(i)
                u = clamp((t - it['t0']) / 0.09)
                y = self.cfg.get('y', 1530) + 10 * (1 - out_cubic(u)); x0 = W / 2 - width / 2
                sc = min(1.0, self.cfg.get('max_width', 900) / max(1, width))
                c.save(); c.translate(W / 2, y); c.scale(sc, sc); c.translate(-W / 2, -y)
                sh = skia.Paint(Color=skia.Color(0, 0, 0), Alphaf=0.55 * u, AntiAlias=True,
                                MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 7))
                st = skia.Paint(Color=skia.Color(0, 0, 0), Alphaf=u, AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                StrokeWidth=self.font.size * 0.17, StrokeJoin=skia.Paint.kRound_Join)
                for blob, x, k in runs: c.drawTextBlob(blob, x0 + x, y + 5, sh)
                for blob, x, k in runs: c.drawTextBlob(blob, x0 + x, y, st)
                for blob, x, k in runs:
                    col = skia.Color(255, 210, 31) if k else skia.ColorWHITE
                    c.drawTextBlob(blob, x0 + x, y, skia.Paint(Color=col, Alphaf=u, AntiAlias=True))
                c.restore()


# ---------------------------------------------------------------- render
class Edit:
    def __init__(self, e):
        self.e = e
        self.tl = Timeline(e['segments'])
        self.fonts = {'label': Font(e.get('label_font', 'fonts/Khand-SemiBold.ttf'), 44)}
        self.brolls = [Broll(b, self.tl, self.fonts) for b in e.get('brolls', [])]
        words = json.load(open(path(e['words'])))
        self.subs = Subs(words, self.tl, e.get('subs', {})) if e.get('subs', {}).get('on', True) else None
        self.desk = desk_texture().withDefaultMipmaps(); self.grain = grain_frames()
        self.hsurf = skia.Surface(W // 2, H // 2)
        self.shadow = skia.ImageFilters.DropShadow(0, 16, 16, 16, skia.Color4f(0, 0, 0, 0.75))
        self.grade = skia.Paint(ColorFilter=grade_filter(e.get('grade', {})))
        self.face = e.get('face', [0.5, 0.36])
        self.vignette = vignette_image()

    def broll_at(self, t):
        for b in self.brolls:
            if b.t0 - 0.001 <= t < b.t1: return b
        return None

    def draw_aroll(self, c, img, zoom):
        s = W / img.width() * zoom; fx, fy = self.face[0] * W, self.face[1] * H
        c.save(); c.translate(fx, fy); c.scale(s, s); c.translate(-self.face[0] * img.width(), -self.face[1] * img.height())
        c.drawImage(img, 0, 0, SAMPLING, self.grade); c.restore()

    def broll_image(self, b, tb, surf):
        c = surf.getCanvas(); c.clear(skia.ColorBLACK)
        n = 4 if b.moving(tb) else 1
        if n == 1:
            b.draw_scene(c, tb, self.desk, self.shadow)
        else:  # motion blur: average sub-frames, rendered at half size (the result is blurred anyway)
            hc = self.hsurf.getCanvas(); hc.clear(skia.ColorBLACK)
            for k in range(n):
                ts = tb + (k / (n - 1) - 0.5) / FPS * 0.6
                hc.saveLayer(paint=skia.Paint(Alphaf=1.0 / n, BlendMode=skia.BlendMode.kPlus))
                hc.save(); hc.scale(0.5, 0.5); b.draw_scene(hc, ts, self.desk, self.shadow); hc.restore(); hc.restore()
            c.save(); c.scale(2, 2); c.drawImage(self.hsurf.makeImageSnapshot(), 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear)); c.restore()
        c.drawImage(self.vignette, 0, 0)
        c.drawImage(self.grain[int(tb * FPS) % len(self.grain)], 0, 0)
        b.draw_label(c, tb)
        return surf.makeImageSnapshot()

    def frame(self, t, reader, surf, bsurf):
        c = surf.getCanvas()
        if t >= self.tl.dur:
            c.clear(skia.ColorBLACK); return
        seg, src = self.tl.at(t)
        b = self.broll_at(t)
        need_a = b is None or (t - b.t0) < 0.2 or (b.t1 - t) < 0.16
        if need_a:
            self.draw_aroll(c, reader.get(src), seg['zoom'])
        else:
            reader.get(src)  # keep the decoder in step
        if b is not None:
            tb = t - b.t0
            img = self.broll_image(b, tb, bsurf)
            u_in, u_out = clamp(tb / 0.18), clamp((b.t1 - t) / 0.14)
            a = out_cubic(u_in) * out_cubic(u_out)
            sc = (1.10 - 0.10 * out_cubic(u_in)) * (1.06 - 0.06 * out_cubic(u_out))
            c.save(); c.translate(W / 2, H / 2); c.scale(sc, sc); c.translate(-W / 2, -H / 2)
            c.drawImage(img, 0, 0, SAMPLING, skia.Paint(Alphaf=a)); c.restore()
        if self.subs: self.subs.draw(c, t)
        fade = self.e.get('fade_out', 0.5)
        if self.e.get('tail') and t > self.tl.dur - fade:  # fade to black into the tail
            c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Color=skia.ColorBLACK, Alphaf=clamp((t - self.tl.dur + fade) / fade)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('edl'); ap.add_argument('--out', default='out.mp4')
    ap.add_argument('--start', type=float, default=0.0); ap.add_argument('--end', type=float, default=None)
    ap.add_argument('--stills', default=None); ap.add_argument('--stills-dir', default='stills')
    ap.add_argument('--audio', default=None, help='finished mix (timeline time) to mux')
    ap.add_argument('--crf', type=int, default=17); ap.add_argument('--preset', default='fast')
    a = ap.parse_args()
    e = json.load(open(a.edl))
    ed = Edit(e)
    print(f'timeline {ed.tl.dur:.2f}s, {len(ed.brolls)} B-rolls, {len(ed.subs.items) if ed.subs else 0} subtitle chunks')
    surf, bsurf = skia.Surface(W, H), skia.Surface(W, H)
    if a.stills:
        os.makedirs(a.stills_dir, exist_ok=True)
        for ts in [float(x) for x in a.stills.split(',')]:
            seg, src = ed.tl.at(ts); rd = Reader(path(e['source']), src)
            ed.frame(ts, rd, surf, bsurf); rd.p.kill()
            Image.fromarray(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)[..., :3]).save(
                os.path.join(a.stills_dir, f'still_{ts:07.2f}.jpg'), quality=90)
        return
    full = ed.tl.dur + e.get('tail', 0.0)
    end = min(a.end or full, full)
    n0, n1 = int(round(a.start * FPS)), int(round(end * FPS))
    rd = Reader(path(e['source']), ed.tl.at(a.start)[1])
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
    if a.audio: cmd += ['-ss', f'{a.start:.3f}', '-t', f'{end - a.start:.3f}', '-i', a.audio]
    cmd += ['-c:v', 'libx264', '-preset', a.preset, '-crf', str(a.crf), '-pix_fmt', 'yuv420p', '-colorspace', 'bt709',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart']
    if a.audio: cmd += ['-c:a', 'aac', '-b:a', '256k', '-shortest']
    cmd += [a.out]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import time; t_start = time.time()
    for i in range(n0, n1):
        t = i / FPS
        ed.frame(t, rd, surf, bsurf)
        enc.stdin.write(surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType).tobytes())
        if (i - n0) % 150 == 0:
            el = time.time() - t_start; print(f'  {t:6.1f}s  {(i - n0 + 1) / max(el, 1e-6):.1f} fps', flush=True)
    enc.stdin.close(); enc.wait(); rd.p.kill()
    print('wrote', a.out)


if __name__ == '__main__':
    main()
