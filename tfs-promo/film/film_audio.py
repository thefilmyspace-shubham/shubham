"""Audio for the TFS film: Mixkit 'Epical Drums 05' bed (drop at NOW SHOWING) + synth trailer SFX.
Output: film_mix.wav (48k stereo, -14 LUFS)."""
import os, subprocess, wave
import numpy as np
import film as F

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; N = int(F.END * SR)
rng = np.random.default_rng(11)
G = F.G

def load(path, ss=None, dur=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None: cmd += ['-ss', f'{ss:.4f}']
    if dur is not None: cmd += ['-t', f'{dur:.4f}']
    cmd += ['-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2).copy()
def sfx(name): return load(os.path.join(HERE, 'sfx', f'sfx_{name}.mp3'))
def db(x): return 10 ** (x / 20)
def place(bus, clip, t, gain_db=0.0):
    i = int(round(t * SR))
    if i >= len(bus) or len(clip) == 0: return
    if i < 0: clip = clip[-i:]; i = 0
    j = min(len(bus), i + len(clip)); bus[i:j] += clip[:j - i] * db(gain_db)
def st(x, w=0.0):
    s = np.stack([x, x], -1).astype(np.float32)
    if w: s[:, 1] = np.roll(s[:, 1], int(w * SR))
    return s
def env(n, tau): return np.exp(-np.arange(n) / (tau * SR))
def onepole(x, fc):
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = a[i] * acc + (1 - a[i]) * x[i]; y[i] = acc
    return y

# ---------------- synth palette ----------------
def braam(d=2.6, root=55.0):
    n = int(d * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f, g in [(root, 1.0), (root * 1.5, 0.7), (root * 2, 0.6), (root * 3, 0.25)]:
        for det in (-0.4, 0.0, 0.45):
            ph = 2 * np.pi * (f + det) * t
            x += g * (2 * ((ph / (2 * np.pi)) % 1) - 1)          # saw
    fc = 180 + 2600 * np.exp(-t / 0.35) + 400 * np.exp(-t / 1.2)
    y = onepole(onepole(x, fc), fc)
    y = np.tanh(y * 0.9) * np.minimum(1, t / 0.012) * np.exp(-t / 1.1)
    return st(y / (np.abs(y).max() + 1e-9) * 0.9, 0.004)
def boom(d=1.8):
    n = int(d * SR); t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t / 0.08)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.55)
    click = rng.standard_normal(n) * np.exp(-t / 0.006) * 0.35
    return st(np.tanh((x + click) * 1.4) * 0.9)
def riser(d=1.6):
    n = int(d * SR); t = np.arange(n) / SR; u = t / d
    y = onepole(rng.standard_normal(n), 300 * (30 ** u))
    y /= np.abs(y).max() + 1e-9
    tone = np.sin(2 * np.pi * np.cumsum(90 * (5 ** u)) / SR) * 0.25
    x = (y * 0.8 + tone) * u ** 2.4
    x[-int(0.008 * SR):] *= np.linspace(1, 0, int(0.008 * SR))
    return st(x * 0.75, 0.003)
def revcym(d=1.2):
    n = int(d * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); x = x - onepole(x, 4500)
    x *= (t / d) ** 3
    x[-int(0.006 * SR):] *= np.linspace(1, 0, int(0.006 * SR))
    return st(x * 0.5, 0.002)
def beep(f=1000, d=0.12):
    n = int(d * SR); t = np.arange(n) / SR
    return st(np.sin(2 * np.pi * f * t) * np.minimum(1, t / 0.004) * np.minimum(1, (d - t) / 0.01) * 0.35)
def tick(f=2600, d=0.02, a=0.5):
    n = int(d * SR); t = np.arange(n) / SR
    return st((np.sin(2 * np.pi * f * t) * 0.6 + rng.standard_normal(n) * 0.4) * np.exp(-t / 0.003) * a)
def clap():
    n = int(0.35 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n) * np.exp(-t / 0.012)
    knock = np.sin(2 * np.pi * 820 * t) * np.exp(-t / 0.05) + 0.6 * np.sin(2 * np.pi * 210 * t) * np.exp(-t / 0.07)
    return st(np.tanh((nz * 0.9 + knock * 0.8) * 1.5) * 0.8)
def whir(d):
    n = int(d * SR); t = np.arange(n) / SR
    x = onepole(rng.standard_normal(n), 1400) * (0.6 + 0.4 * np.abs(np.sin(2 * np.pi * 12 * t)))
    x += 0.15 * np.sin(2 * np.pi * 48 * t)
    return st(x / (np.abs(x).max() + 1e-9) * 0.3)
def thunk():
    n = int(0.4 * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t / 0.05) + 45) / SR) * np.exp(-t / 0.12)
    x += rng.standard_normal(n) * np.exp(-t / 0.004) * 0.5
    return st(np.tanh(x * 1.5) * 0.8)
def chime():
    n = int(1.6 * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t / dd) * g for f, dd, g in [(1568, 0.6, 0.5), (2093, 0.45, 0.35), (3136, 0.3, 0.2), (784, 0.9, 0.3)])
    return st(x * np.minimum(1, t / 0.003) * 0.4, 0.006)
def typing(d):
    n = int(d * SR); x = np.zeros(n); tt = 0.0
    while tt < d - 0.03:
        i = int(tt * SR); m = int(0.014 * SR)
        x[i:i + m] += np.diff(rng.standard_normal(m + 1)) * env(m, 0.002) * rng.uniform(0.5, 1) * 0.6 \
            + np.sin(2 * np.pi * rng.uniform(150, 230) * np.arange(m) / SR) * env(m, 0.004) * 0.5
        tt += rng.uniform(0.045, 0.085)
    return st(x * 0.6)

def main():
    music = np.zeros((N, 2), np.float32)
    mus = load(os.path.join(HERE, 'music', 'm680.mp3'), F.M0, F.END - F.V0 + 0.5)
    place(music, mus, F.V0)
    # music drop under COMING SOON -> NOW SHOWING (G80..G84), groove continues underneath
    t = np.arange(N) / SR
    g = np.ones(N)
    a0, a1 = G(80), G(84)
    g[(t >= a0) & (t < a1)] = 0.0
    r = (t >= a0 - 0.03) & (t < a0); g[r] = 1 - (t[r] - (a0 - 0.03)) / 0.03
    r = (t >= a1) & (t < a1 + 0.012); g[r] = (t[r] - a1) / 0.012
    r = t < F.V0 + 0.01; g[r] = 0
    music *= (g * db(-2.0))[:, None].astype(np.float32)

    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: place(fx, clip, tt, gd)
    W2, W1, W3, I2, I3, I4, SH = sfx('whoosh2'), sfx('whoosh1'), sfx('whoosh3'), sfx('impact2'), sfx('impact3'), sfx('impact4'), sfx('shutter1')
    # cold open
    pl(whir(G(12) + 0.1), 0.0, -21)
    pl(st(np.sin(2 * np.pi * 55 * np.arange(int(G(12) * SR)) / SR) * np.minimum(1, np.arange(int(G(12) * SR)) / (2 * SR)) * 0.25), 0.0, -19)
    for k in (6, 8, 10): pl(beep(1000, 0.11), G(k), -8)
    for k in np.arange(6, 12, 0.5): pl(tick(1700, 0.015, 0.4), G(k) + 0.2, -18)
    pl(revcym(1.4), G(12) - 1.4, -8)
    # music entry
    pl(braam(2.8), G(12), -4); pl(boom(2.0), G(12), -3)
    pl(W1[:int(1.8 * SR)], G(12.4), -16)
    # extras / lead
    pl(I2, G(21), -6); pl(boom(1.2), G(21), -9)
    pl(thunk(), G(24.3), -4); pl(thunk(), G(24.3) + 0.12, -12)
    pl(W2, G(25), -14)
    pl(chime(), G(28), -10)
    # slate
    pl(W2, G(32) - 0.15, -10)
    pl(W2, G(32.3), -18)
    pl(clap(), G(34), -2); pl(boom(0.9), G(34), -12)
    # written by
    pl(W2, G(36) - 0.2, -12)
    for (s_, fk, k0, k1) in F.SCRIPT:
        d = G(k1) - G(k0); pl(typing(d), G(k0), -13)
        pl(tick(3200, 0.03, 0.6), G(k1) + 0.02, -18)
    pl(tick(900, 0.06, 0.5), G(41.6), -16)
    pl(I4, G(42), -14)
    # directed by
    pl(W2, G(44) - 0.15, -10)
    pl(beep(2400, 0.05), G(46) - 0.02, -16); pl(beep(2400, 0.05), G(46) + 0.07, -16)
    pl(SH, G(51.4), -14); pl(SH, G(52), -12)
    # shot by: f-stop clicks + shutter
    for i in range(1, len(F.FSTOPS)): pl(tick(2100, 0.025, 0.6), G(52.5) + i * F._T / 2, -16)
    pl(SH, G(57), -6)
    # edited for
    pl(W2, G(60) - 0.15, -10)
    pl(I2, G(61), -8)
    for (_, _, _, _, kb) in F.CLIPS: pl(tick(700, 0.05, 0.6), G(kb) + 0.12, -14)
    for kb in (62, 63, 64, 65, 66, 67): pl(tick(3000, 0.02, 0.7), G(kb), -16)
    # starring
    pl(W3[:int(2.0 * SR)], G(68) - 0.3, -16)
    pl(boom(1.5), G(68), -10); pl(chime(), G(68.2), -14)
    pl(chime(), G(77.6), -16)
    for i in range(20): pl(tick(1800 + 60 * i, 0.03, 0.7), G(F.STAR_K0 + i * F.STAR_DK), -15)
    pl(I4, G(77.2), -10); pl(boom(1.0), G(77.2), -14)
    # now showing (music drop) — one click per flap step, generated from the board timing
    pl(W2, G(80) - 0.18, -10)
    for (row_from, row_to, k0, row) in [('', 'COMING SOON', 80.2, 0), ('COMING SOON', 'NOW SHOWING', 82, 1), ('', 'ON YOUR FEED', 84, 3)]:
        a_ = row_from.center(F.NCELL); b_ = row_to.center(F.NCELL)
        for i in range(F.NCELL):
            if a_[i] == b_[i]: continue
            n_ = len(F.flap_seq(a_[i], b_[i], i, row)) - 1
            for j in range(n_):
                pl(tick(rng.uniform(2200, 3600), 0.012, 0.8), G(k0) + i * 0.035 + (j + 0.5) * 0.075, -17)
    pl(riser(G(84) - G(82.4)), G(82.4), -7)
    pl(I3, G(84), -2); pl(boom(2.0), G(84), -5); pl(braam(2.2, 49.0), G(84), -10)
    # blockbuster
    pl(W3[:int(2.5 * SR)], G(88), -14)
    pl(braam(2.6, 55.0), G(90), -6); pl(I3, G(90), -6); pl(boom(1.8), G(90), -7)
    # film strip run: sprocket clatter decelerating
    tt = G(94)
    while tt < G(96):
        x0 = F.strip_offset(tt); x1 = F.strip_offset(tt + 1 / 240)
        v = abs(x1 - x0) * 240
        if v < 40: break
        pl(tick(rng.uniform(1100, 1500), 0.012, 0.6), tt, -15)
        tt += max(0.018, 52.0 / v)
    pl(W1[:int(2.0 * SR)], G(94), -14)
    # logo hit
    pl(I3, G(96), 0); pl(boom(2.6), G(96), -2); pl(braam(3.2, 41.2), G(96), -7)
    pl(chime(), G(96) + 1.4, -12)

    mix = music + fx
    mix *= np.clip((F.END - t) / 0.5, 0, 1)[:, None] ** 0.6
    mix = np.tanh(mix * 1.05) / 1.05
    raw = os.path.join(HERE, 'film_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89:level=false', '-ar', '48000', '-c:a', 'pcm_s16le',
                    os.path.join(HERE, 'film_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
