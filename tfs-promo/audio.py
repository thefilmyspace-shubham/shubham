"""Build the 60s audio mix: music (ducked) + VO segments + SFX. Output: mix.wav (48k stereo)."""
import subprocess, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000; DUR = 60.0; N = int(SR * DUR)
rng = np.random.default_rng(3)

def load(path, ss=None, to=None):
    cmd = ['ffmpeg', '-v', 'error']
    if ss is not None: cmd += ['-ss', str(ss)]
    if to is not None: cmd += ['-t', str(to - (ss or 0))]
    cmd += ['-i', path, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    a = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32)
    return a.reshape(-1, 2).copy()

def db(x): return 10 ** (x / 20)
def place(bus, clip, t, gain_db=0.0, fade_out=0.0):
    i = int(t * SR)
    if i >= len(bus) or len(clip) == 0: return
    c = clip * db(gain_db)
    if fade_out > 0:
        nf = min(len(c), int(fade_out * SR)); c = c.copy(); c[-nf:] *= np.linspace(1, 0, nf)[:, None]
    j = min(len(bus), i + len(c)); bus[i:j] += c[:j - i]

def mono2(x): return np.stack([x, x], -1).astype(np.float32)
def env_exp(n, tau): return np.exp(-np.arange(n) / (tau * SR))

# ---------------- synth sfx ----------------
def s_tick(f=1800, d=0.04):
    n = int(d * SR); t = np.arange(n) / SR
    return mono2(np.sin(2 * np.pi * f * t) * env_exp(n, 0.008) * 0.6)
def s_pop(f0=380, f1=950, d=0.09):
    n = int(d * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(np.linspace(f0, f1, n)) / SR
    return mono2(np.sin(ph) * env_exp(n, 0.025) * np.minimum(1, t / 0.003) * 0.7)
def s_ding():
    n = int(0.45 * SR); t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t) + 0.25 * np.sin(2 * np.pi * 2637 * t)) * env_exp(n, 0.09)
    return mono2(x * np.minimum(1, t / 0.004) * 0.35)
def s_error():
    n = int(0.32 * SR); t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * 146 * k * t) / k for k in range(1, 9))
    gate = ((t < 0.12) | ((t > 0.16) & (t < 0.30))).astype(float)
    return mono2(np.tanh(x * 1.5) * gate * env_exp(n, 0.25) * 0.35)
def s_notif():
    a = np.zeros(int(0.32 * SR))
    for st, f, d in [(0.0, 988, 0.09), (0.1, 1480, 0.18)]:
        n = int(d * SR); t = np.arange(n) / SR
        a[int(st * SR):int(st * SR) + n] += np.sin(2 * np.pi * f * t) * env_exp(n, d / 2.5) * np.minimum(1, t / 0.003)
    return mono2(a * 0.4)
def s_riser(d=1.85):
    n = int(d * SR); t = np.arange(n) / SR; u = t / d
    noise = rng.standard_normal(n)
    # time-varying one-pole lowpass
    fc = 200 * (40 ** u); a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc = a[i] * acc + (1 - a[i]) * noise[i]; y[i] = acc
    y = y / (np.abs(y).max() + 1e-9)
    ph = 2 * np.pi * np.cumsum(110 * (6 ** u)) / SR
    tone = np.sin(ph) * 0.35 + np.sin(2 * ph) * 0.15
    x = (y * 0.8 + tone) * (u ** 2.2)
    x[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    st = mono2(x * 0.7); st[:, 1] = np.roll(st[:, 1], 120)
    return st
def s_typing(d=1.7):
    n = int(d * SR); x = np.zeros(n); t = 0.0
    while t < d - 0.03:
        i = int(t * SR); m = int(0.012 * SR)
        click = np.diff(rng.standard_normal(m + 1)) * env_exp(m, 0.0025) * rng.uniform(0.4, 1.0)
        th = np.sin(2 * np.pi * rng.uniform(140, 220) * np.arange(m) / SR) * env_exp(m, 0.004) * 0.6
        x[i:i + m] += click * 0.5 + th
        t += rng.uniform(0.055, 0.12)
    return mono2(x * 0.5)
def s_thump():
    n = int(0.18 * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(np.linspace(120, 45, n)) / SR
    return mono2(np.sin(ph) * env_exp(n, 0.05) * 0.9)

def sfx(name): return load(os.path.join(HERE, 'audio', f'sfx_{name}.mp3'))

def build():
    music = load(os.path.join(HERE, 'music', 'm132.mp3'), 0, DUR)
    music = np.pad(music, ((0, max(0, N - len(music))), (0, 0)))[:N]
    vo_src = load(os.path.join(HERE, 'audio', 'vo_take2.mp3'))
    vo = np.zeros((N, 2), np.float32)
    # (vo_start, vo_end, video_time)
    segs = [(0.00, 5.52, 2.00), (5.52, 11.05, 8.12), (11.40, 14.62, 16.40), (14.95, 21.95, 20.15),
            (22.25, 26.30, 28.85), (26.30, 30.36, 32.90), (30.50, 36.27, 39.50), (36.27, 41.25, 52.00 - 0.03)]
    for a, b, tv in segs:
        clipv = vo_src[int(a * SR):int(b * SR)].copy()
        nf = int(0.012 * SR); clipv[:nf] *= np.linspace(0, 1, nf)[:, None]; clipv[-nf:] *= np.linspace(1, 0, nf)[:, None]
        place(vo, clipv, tv)
    # normalize VO to peak -3 dB
    vo *= db(-3) / (np.abs(vo).max() + 1e-9)

    fx = np.zeros((N, 2), np.float32)
    W1, W2, W3 = sfx('whoosh1')[:int(2.2 * SR)], sfx('whoosh2'), sfx('whoosh3')[:int(2.0 * SR)]
    I2, I3, I4 = sfx('impact2'), sfx('impact3'), sfx('impact4')
    # hook
    place(fx, sfx('scroll1'), 0.10, +16); place(fx, sfx('scroll4'), 1.0, +14)
    place(fx, s_tick(2200), 2.0, -4); place(fx, s_thump(), 2.0, -6)
    place(fx, s_pop(), 3.0, -8)
    place(fx, W3, 7.55 - 1.1, -8, fade_out=0.6)
    # problem
    place(fx, s_ding(), 8.40, -10); place(fx, s_ding(), 10.12, -10)
    place(fx, s_error(), 11.55, -8)
    place(fx, sfx('scroll2'), 12.92, +14)
    place(fx, s_riser(), 13.80, -6)
    # slam
    place(fx, I3, 15.66, 0); place(fx, s_thump(), 15.68, -2)
    place(fx, W1, 19.80 - 1.2, -8, fade_out=0.5)
    # process
    place(fx, s_typing(1.8), 20.40, -10)
    place(fx, sfx('shutter1'), 22.42, -4)
    for j in range(7): place(fx, s_tick(1400 + 90 * j, 0.03), 23.52 + 0.04 + j * 0.07 + 0.26, -14)
    for i in range(13): place(fx, s_pop(600, 1200, 0.05), 24.70 + i * 0.13, -18)
    place(fx, s_notif(), 26.38, -8)
    place(fx, W2, 27.02, -8)
    # proof
    for t in (27.33, 27.70, 28.08): place(fx, s_thump(), t + 0.2, -12)
    for t in (28.92, 29.90, 30.72, 32.10): place(fx, W2, t - 0.15, -12)
    for i in range(20):
        ti = 33.0 + 1.4 * (1 - (1 - i / 20) ** (1 / 3)) if i else 33.0
        place(fx, s_tick(2400, 0.025), ti, -16)
    place(fx, W3, 37.10 - 1.1, -10, fade_out=0.6)
    # services
    for t in (39.65, 40.68, 42.38, 43.04): place(fx, s_pop(300, 700, 0.1), t, -8)
    place(fx, W2, 43.90, -10)
    place(fx, I4, 44.82, +4)
    place(fx, W1, 45.25 - 1.2, -9, fade_out=0.5)
    place(fx, W3, 50.15 - 1.1, -10, fade_out=0.6)
    # end logo
    b70, b71, b72 = [16.43 + k * 60 / 123 for k in (70, 71, 72)]
    place(fx, I2, b70, +6); place(fx, I4, b71, +5); place(fx, I3, b72, 0); place(fx, s_thump(), b72, -2)

    # ---- music ducking from VO envelope
    e = np.abs(vo).max(1)
    win = int(0.05 * SR); k = np.ones(win) / win
    env = np.convolve(e, k, 'same')
    act = (env > 0.02).astype(np.float32)
    # smooth attack/release
    sm = np.zeros_like(act); a_up, a_dn = np.exp(-1 / (0.04 * SR)), np.exp(-1 / (0.35 * SR)); acc = 0.0
    for i in range(0, N, 32):
        target = act[i]
        coef = a_up if target > acc else a_dn
        acc = target + (acc - target) * coef ** 32
        sm[i:i + 32] = acc
    mgain = db(-4) * (1 - sm * (1 - db(-9)))[:, None]
    # intro lower until drop, fade out at end
    t = np.arange(N) / SR
    shape = np.where(t < 15.6, db(-3), 1.0) * np.clip((DUR - t) / 3.0, 0, 1) ** 1.5
    # brief dip before the slam for impact
    shape *= np.where((t > 15.35) & (t < 15.66), db(-10), 1.0)
    mus = music * mgain * shape[:, None]
    mix = mus + vo * db(0) + fx * db(-2)
    mix = np.tanh(mix * 1.1) / 1.1  # soft clip safety
    out = os.path.join(HERE, 'mix_raw.wav')
    pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
    import wave
    with wave.open(out, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', out, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9', '-ar', '48000',
                    os.path.join(HERE, 'mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    build()
