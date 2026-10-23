#!/usr/bin/env python3
"""Jalsra interview edit renderer.

Hook montage -> title reveal (on the music drop) -> interview -> outro, with the reference-reel kinetic text
(kinetic.py: Helvetica-style mixed weights, rise-in with real motion blur, gradient key words, text behind the
speaker via a person matte). Driven by an EDL json (see style_test.json):

  python3 edit.py style_test.json --out test.mp4            # full render with audio
  python3 edit.py edl.json --stills 2.0,9.5 --stills-dir st  # check frames
  python3 edit.py edl.json --start 0 --end 20 --no-audio --out p0.mp4   # render a chunk

Text word times inside clips are in SOURCE time (seconds in the source file), as they come out of transcribe.py.
Title / outro text times are relative to the start of that card; lower_third and top-level "text" blocks use
timeline time (top-level blocks are drawn over every shot, so a sentence can run across cuts).
"""
import argparse, json, math, os, subprocess
import numpy as np
import skia
from kinetic import Kinetic, clamp, hexc

HERE = os.path.dirname(os.path.abspath(__file__))
RVM = os.path.join(HERE, 'models', 'rvm_mobilenetv3_fp32.onnx')
RVM_URL = 'https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx'
SR = 48000

def prog(t, t0, d): return clamp((t - t0) / d) if d > 0 else float(t >= t0)
def lerp(a, b, u): return a + (b - a) * u
def eo3(u): return 1 - (1 - u) ** 3
def eio3(u): return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2
def P(color, **kw): return skia.Paint(AntiAlias=True, Color=color, **kw)
def R(x, y, w, h): return skia.Rect.MakeXYWH(x, y, w, h)
LINEAR = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)

def to_img(arr, unpremul=False):
    kw = {'alphaType': skia.kUnpremul_AlphaType} if unpremul else {}
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType, **kw)

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
    if sw / sh > ar: cw, ch = int(sh * ar) // 2 * 2, sh
    else: cw, ch = sw, int(sw / ar) // 2 * 2
    cz = item.get('crop_zoom', 1.0)
    cw, ch = int(cw / cz) // 2 * 2, int(ch / cz) // 2 * 2
    x = int((sw - cw) * item.get('crop_x', 0.5)); y = int((sh - ch) * item.get('crop_y', 0.5))
    g = {**grade, **item.get('grade', {})}
    warm = g.get('warm', 0.03)
    return ','.join([f'crop={cw}:{ch}:{x}:{y}', f'scale={W}:{H}:flags=lanczos', f'fps={fps}',
                     f"eq=contrast={g.get('contrast', 1.05)}:saturation={g.get('saturation', 1.06)}:brightness={g.get('brightness', 0.0)}:gamma={g.get('gamma', 1.0)}",
                     f'colorbalance=rs={warm}:bs={-warm}:rm={warm / 2}:bm={-warm / 2}'])

class Matter:
    """person alpha matte, Robust Video Matting (recurrent, so it stays stable frame to frame)"""
    _sess = None
    def __init__(self, ratio=0.25):
        if Matter._sess is None:
            if not os.path.exists(RVM):
                os.makedirs(os.path.dirname(RVM), exist_ok=True)
                subprocess.run(['curl', '-sSL', '-o', RVM, RVM_URL], check=True)
            import onnxruntime as ort
            Matter._sess = ort.InferenceSession(RVM, providers=['CPUExecutionProvider'])
        self.ratio = np.array([ratio], np.float32)
        self.rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    def __call__(self, rgba):
        src = (rgba[:, :, :3].astype(np.float32) / 255).transpose(2, 0, 1)[None]
        _, pha, *self.rec = Matter._sess.run(None, {'src': src, 'r1i': self.rec[0], 'r2i': self.rec[1], 'r3i': self.rec[2],
                                                    'r4i': self.rec[3], 'downsample_ratio': self.ratio})
        return (pha[0, 0] * 255).astype(np.uint8)

class Reader:
    """sequential RGBA frame reader for one clip item; optional person matte"""
    def __init__(self, item, W, H, fps, grade, t_off=0.0, matte=False):
        self.W, self.H = W, H
        dur = item['out'] - item['in'] - t_off
        cmd = ['ffmpeg', '-v', 'error', '-ss', f"{item['in'] + t_off:.4f}", '-t', f'{dur + 0.5:.4f}', '-i', item['src'],
               '-vf', vfilter(item['src'], W, H, fps, item, grade), '-an', '-pix_fmt', 'rgba', '-f', 'rawvideo', '-']
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.matter = Matter() if matte else None
        self.last = (None, None)
    def next(self):
        n = self.W * self.H * 4
        buf = self.p.stdout.read(n)
        if len(buf) == n:
            arr = np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 4)
            person = None
            if self.matter:
                pa = arr.copy(); pa[:, :, 3] = self.matter(arr)
                person = to_img(pa, unpremul=True)
            self.last = (to_img(arr), person)
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
        if dim != 1.0: vf += f',eq=brightness={-(1 - dim) * 0.5}:saturation=0.85'
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
        self.S = self.W / 1080.0
        self.grade = edl.get('grade', {})
        fonts = {k: (v if os.path.isabs(v) else os.path.join(base, v)) for k, v in edl.get('fonts', {}).items()}
        self.K = Kinetic(self.W, self.H, self.fps, fonts=fonts)
        self.items = []
        t = 0.0
        for it in edl['timeline']:
            it = dict(it)
            if 'src' in it and not os.path.isabs(it['src']): it['src'] = os.path.join(base, it['src'])
            if 'bg' in it and not os.path.isabs(it['bg'][0]): it['bg'] = [os.path.join(base, it['bg'][0]), it['bg'][1]]
            dur = it['out'] - it['in'] if it['type'] == 'clip' else it['dur']
            it['start'], it['end'] = t, t + dur
            if it['type'] in ('title', 'outro') and 'text' not in it: it['text'] = self.card_text(it)
            it['_matte'] = it['type'] == 'clip' and (it.get('matte') or self.K.needs_matte(it.get('text', [])))
            t += dur
            self.items.append(it)
        self.total = t
        self.title_start = next((i['start'] for i in self.items if i['type'] == 'title'), 0.0)
        self.lt_block = self.lower_third_block(edl.get('lower_third'))
        self.gtext = edl.get('text', [])          # timeline-time blocks, drawn over every shot (can span cuts)
        self.grain = self._grain()

    def card_text(self, it):
        """default title / outro typography in the reference style"""
        dur = it['dur']
        lines = []
        if it.get('kicker'): lines.append({'words': [{'w': w, 't': 0.10 + 0.06 * k, 'weight': 'light_i', 'size': 78}
                                                     for k, w in enumerate(it['kicker'].split())]})
        if it.get('title'): lines.append({'gap': 0.92, 'words': [{'w': it['title'], 't': 0.28 if lines else 0.05, 'weight': 'bold',
                                                                  'size': it.get('size', 210), 'fill': it.get('fill', 'chrome'),
                                                                  'track': -0.03}]})
        if it.get('sub'): lines.append({'gap': 0.95, 'words': [{'w': w, 't': 0.5 + 0.07 * k, 'weight': 'thin', 'size': 84}
                                                               for k, w in enumerate(it['sub'].split())]})
        return [{'style': 'stack', 'anchor': [0.5, 0.45], 'align': 'center', 'end': dur - 0.3, 'lines': lines}]

    def lower_third_block(self, lt3):
        if not lt3: return None
        a0 = lt3['at']
        return {'style': 'stack', 'anchor': lt3.get('anchor', [0.075, 0.145]), 'end': a0 + lt3.get('dur', 3.5),
                'lines': [{'words': [{'w': w, 't': a0 + 0.06 * k, 'weight': 'medium', 'size': 64}
                                     for k, w in enumerate(lt3['name'].split())]},
                          {'gap': 0.95, 'words': [{'w': w, 't': a0 + 0.2 + 0.06 * k, 'weight': 'light_i', 'size': 46}
                                                  for k, w in enumerate(lt3.get('role', '').split())]}]}

    def _grain(self):
        rng = np.random.default_rng(7); w, h = self.W // 2, self.H // 2; out = []
        for _ in range(4):
            g = np.clip(128 + rng.normal(0, 1, (h, w)) * 60, 0, 255).astype(np.uint8)
            a = np.full((h, w), int(255 * self.e.get('grain', 0.04)), np.uint8)
            out.append(to_img(np.dstack([g, g, g, a])))
        return out

    def item_at(self, t):
        for i, it in enumerate(self.items):
            if it['start'] <= t < it['end']: return i, it
        return len(self.items) - 1, self.items[-1]

    # ------------------------------------------------------------ frames
    def video_tf(self, it, lt):
        W, H = self.W, self.H
        dur = it['end'] - it['start']
        z0, z1 = it.get('zoom', [1.0, 1.04])
        z = lerp(z0, z1, eio3(clamp(lt / dur)))
        for pt, amt in it.get('punch', []):
            if lt >= pt: z *= amt
        dx = dy = 0.0
        if it.get('section') == 'hook' or it.get('impact'):
            u = prog(lt, 0, 0.32)
            z *= lerp(1.16, 1.0, eo3(u))
            sh = (1 - u) * 14 * self.S
            dx, dy = math.sin(lt * 90) * sh, math.cos(lt * 77) * sh
        fx, fy = it.get('focus', [0.5, 0.42])
        return z, W * fx, H * fy, dx, dy

    def draw_img(self, c, img, tf, alpha=1.0):
        z, px, py, dx, dy = tf
        c.save(); c.translate(dx + px, dy + py); c.scale(z, z); c.translate(-px, -py)
        p = None
        if alpha < 1: p = skia.Paint(); p.setAlphaf(alpha)
        c.drawImageRect(img, R(0, 0, self.W, self.H), LINEAR, p)
        c.restore()

    def vignette(self, c):
        v = self.e.get('vignette', 0.18)
        if v <= 0: return
        W, H = self.W, self.H
        sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H * 0.45), max(W, H) * 0.75,
                                            [hexc('#000000', 0.0), hexc('#000000', 0.0), hexc('#000000', v)], [0.0, 0.6, 1.0])
        c.drawRect(R(0, 0, W, H), skia.Paint(Shader=sh))

    def draw_card(self, c, it, lt):
        W, H = self.W, self.H
        dur = it['end'] - it['start']
        c.drawPaint(P(hexc('#07080A')))
        if it.get('bg'):
            img = still(it['bg'][0], it['bg'][1], W, H, self.grade, blur=14, dim=0.55)
            z = lerp(1.08, 1.0, eo3(clamp(lt / dur))) if it['type'] == 'title' else lerp(1.0, 1.06, clamp(lt / dur))
            self.draw_img(c, img, (z, W / 2, H / 2, 0, 0), alpha=0.9 * eo3(prog(lt, 0, 0.4)))
        self.K.draw(c, it['text'], lt, 'behind'); self.K.draw(c, it['text'], lt, 'front')
        if it['type'] == 'title':
            fl = 1 - prog(lt, 0, 0.18)
            if fl > 0: c.drawPaint(P(hexc('#FFFFFF', 0.85 * eo3(fl))))
        else:
            out = eio3(prog(lt, dur - 0.6, 0.6))
            if out > 0: c.drawPaint(P(hexc('#000000', out)))

    def render_frames(self, t0, t1, sink, stills=None):
        W, H, fps = self.W, self.H, self.fps
        surf = skia.Surface(W, H); c = surf.getCanvas()
        reader, rid = None, None
        times = stills if stills else [n / fps for n in range(int(round(t0 * fps)), int(round(t1 * fps)))]
        for t in times:
            i, it = self.item_at(t)
            lt = t - it['start']
            c.clear(hexc('#000000'))
            if it['type'] == 'clip':
                if rid != i or stills:
                    if reader: reader.close()
                    reader = Reader(it, W, H, fps, self.grade, t_off=lt, matte=it['_matte']); rid = i
                img, person = reader.next()
                tf = self.video_tf(it, lt)
                if img is not None: self.draw_img(c, img, tf)
                lt_src = it['in'] + lt
                blocks = it.get('text', [])
                self.K.draw(c, blocks, lt_src, 'behind'); self.K.draw(c, self.gtext, t, 'behind')
                if person is not None: self.draw_img(c, person, tf)
                self.vignette(c)
                self.K.draw(c, blocks, lt_src, 'front'); self.K.draw(c, self.gtext, t, 'front')
                if it.get('section') == 'hook':
                    fl = 1 - prog(lt, 0, 0.12)
                    if fl > 0: c.drawPaint(P(hexc('#FFFFFF', 0.55 * fl)))
                elif it.get('fade_in'):
                    fl = 1 - prog(lt, 0, it['fade_in'])
                    if fl > 0: c.drawPaint(P(hexc('#000000', eo3(fl))))
            else:
                self.draw_card(c, it, lt)
                self.K.draw(c, self.gtext, t, 'behind'); self.K.draw(c, self.gtext, t, 'front')
            if self.lt_block: self.K.draw(c, [self.lt_block], t, 'front')
            gp = skia.Paint(); gp.setBlendMode(skia.BlendMode.kOverlay)
            c.drawImageRect(self.grain[int(t * fps) % 4], R(0, 0, W, H), LINEAR, gp)
            wm = self.e.get('watermark')
            if wm:
                f = self.K.font('medium', 26 * self.S)
                p = P(hexc('#FFFFFF', 0.6))
                c.drawString(wm, W - f.measureText(wm) - 40 * self.S, 120 * self.S, f, p)
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
    click = np.random.default_rng(3).normal(0, 1, n) * np.exp(-t * 60) * 0.5
    x = np.tanh((body + click) * 1.6) * gain
    return np.stack([x, x], 1).astype(np.float32)

def sfx_whoosh(d=0.6, gain=0.35, rise=True):
    from scipy.signal import butter, sosfilt
    n = int(SR * d); t = np.linspace(0, 1, n)
    nz = np.random.default_rng(5).normal(0, 1, (n, 2))
    lo = sosfilt(butter(2, 900, 'low', fs=SR, output='sos'), nz, axis=0)
    hi = sosfilt(butter(2, 2500, 'high', fs=SR, output='sos'), nz, axis=0)
    mix = (t if rise else 1 - t)[:, None]
    env = (np.sin(np.pi * t) ** 2 if not rise else t ** 2.2 * (1 - np.clip((t - 0.92) / 0.08, 0, 1)))[:, None]
    x = (lo * (1 - mix) + hi * mix) * env
    return (x / (np.abs(x).max() + 1e-9) * gain).astype(np.float32)

_sfx = {}
def sfx_clip(path, reverse=False):
    if (path, reverse) not in _sfx:
        a = load_audio(path)
        _sfx[(path, reverse)] = a[::-1].copy() if reverse else a
    return _sfx[(path, reverse)]

def sfx_peak(a):
    env = np.sqrt(np.convolve((a ** 2).mean(1), np.ones(480) / 480, 'same'))
    return float(np.argmax(env)) / SR

def place(buf, clip, t):
    i = int(round(t * SR))
    if i >= len(buf): return
    if i < 0: clip = clip[-i:]; i = 0
    n = min(len(clip), len(buf) - i)
    buf[i:i + n] += clip[:n]

def render_audio(ed, out_wav, base):
    from scipy.ndimage import uniform_filter1d
    import wave
    e = ed.e
    n = int(math.ceil(ed.total * SR)) + SR
    dia = np.zeros((n, 2), np.float32)
    speech = np.zeros(n, np.float32)
    target = db(e.get('dialogue_rms_db', -20))
    if e.get('audio_passthrough'):          # an already-cut video: keep its own soundtrack as one continuous track
        src = next(i['src'] for i in ed.items if i['type'] == 'clip')
        a = load_audio(src, 0.0, ed.total) * db(e.get('audio_gain_db', 0))
        place(dia, a, 0.0)
        speech[:len(a)] = 0.0
    for it in ed.items:
        if e.get('audio_passthrough'): break
        if it['type'] != 'clip' or it.get('mute'): continue
        a = load_audio(it['src'], it['in'], it['out'] - it['in'])
        if not len(a): continue
        mono = a.mean(1); loud = np.abs(mono) > 0.01
        rms = np.sqrt(np.mean(mono[loud] ** 2)) if loud.any() else 0
        norm = clamp(target / rms, 0.25, 6.0) if (rms > 0 and e.get('normalize_dialogue', True)) else 1.0
        a *= norm * db(it.get('gain_db', 0))
        fd = int(SR * 0.012); ramp = np.linspace(0, 1, fd)[:, None]
        a[:fd] *= ramp; a[-fd:] *= ramp[::-1]
        place(dia, a, it['start'])
        i0 = int(it['start'] * SR); speech[i0:i0 + len(a)] = 1.0
    m = e.get('music')
    if not m:
        mus = np.zeros_like(dia)
    else:
        mus = music_track(ed, m, base, n, speech)
    end_i = int(ed.total * SR)
    fx = np.zeros_like(dia)
    if e.get('sfx', True) and any(i['type'] == 'title' for i in ed.items):
        for it in ed.items:
            if it.get('section') == 'hook' and it['start'] > 0.05:
                place(fx, sfx_whoosh(0.35, 0.12, rise=False), it['start'] - 0.17)
        place(fx, sfx_whoosh(1.4, 0.22, rise=True), ed.title_start - 1.4)
        place(fx, sfx_impact(0.42), ed.title_start)
        for it in ed.items:
            if it['type'] == 'outro': place(fx, sfx_whoosh(0.6, 0.14, rise=False), it['start'] - 0.2)
    # hand-placed sound effects: {"file", "t", "gain_db", "align": peak|start|end, "reverse"}
    for ev in e.get('sfx_events', []):
        clip = sfx_clip(os.path.join(base, ev['file']), ev.get('reverse', False))
        align = ev.get('align', 'peak')
        off = sfx_peak(clip) if align == 'peak' else len(clip) / SR if align == 'end' else 0.0
        place(fx, clip * db(ev.get('gain_db', -10)), ev['t'] - off)
    mix = dia + mus + fx
    peak = np.abs(mix).max()
    if peak > 0.98: mix = np.tanh(mix / peak * 1.2) / np.tanh(1.2) * 0.98
    pcm = (np.clip(mix[:end_i], -1, 1) * 32767).astype('<i2')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

def music_track(ed, m, base, n, speech):
    from scipy.ndimage import uniform_filter1d
    mus_all = load_audio(os.path.join(base, m['file']))
    off = m.get('drop', 0.0) - ed.title_start + m.get('nudge', 0.0)
    mus = mus_all[int(off * SR):] if off >= 0 else np.concatenate([np.zeros((int(-off * SR), 2), np.float32), mus_all])
    mus = mus[:n] if len(mus) >= n else np.concatenate([mus, np.zeros((n - len(mus), 2), np.float32)])
    lev = np.full(n, m.get('main_db', -21.0), np.float32)
    for it in ed.items:
        i0, i1 = int(it['start'] * SR), int(it['end'] * SR)
        if it['type'] == 'title': lev[i0:i1] = m.get('title_db', -3.0)
        elif it['type'] == 'outro': lev[i0:i1] = m.get('outro_db', -6.0)
        elif it.get('section') == 'hook': lev[i0:i1] = m.get('hook_db', -15.0)
    lev = lev - uniform_filter1d(speech, int(SR * 0.25)) * m.get('speech_duck_db', 2.0)
    gain = db(uniform_filter1d(lev, int(SR * 0.18)))
    end_i = int(ed.total * SR); fo = int(SR * m.get('fade_out', 2.0))
    gain[end_i - fo:end_i] *= np.linspace(1, 0, fo) ** 1.5
    gain[end_i:] = 0
    return mus * gain[:, None] * db(m.get('gain_db', 0))

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
