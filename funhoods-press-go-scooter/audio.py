# VO + music bed (ducked under the voice) + SFX -> mix.wav (48 kHz stereo, about -14 LUFS)
#   VO:    audio/vo_timed.wav (chosen take "Gavin", Magnific / ElevenLabs v4, re-timed by tools/vo_retime.py).
#          The VO never speaks a sound effect: the horn and the toy's sounds are separate tracks below.
#   toy:   the scooter's REAL sounds from the client's raw clip (tools/og_sound.py): audio/og_press_1..3.wav (the head
#          pressed down -- flywheel gear whirr) and og_go.wav (wheels running free as it shoots off)
#   horn:  audio/sfx_horn_beep_1.mp3 (generated SFX, Magnific), first two beeps only
#   SFX:   synthesized whooshes, pops, thocks and chimes for the graphics
#   music: music/m9.mp3 ("Kidding Around", Ahjay Stelino, Mixkit free license; sh music/get_music.sh)
import numpy as np, wave, subprocess, sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T
SR = 48000
ROOT = os.path.dirname(os.path.abspath(__file__))
def load(p, ch=2):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(ROOT, p), '-f', 'f32le', '-ac', str(ch), '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).copy()
    return x.reshape(-1, ch) if ch > 1 else x
N = int(T.DUR * SR)
def S(t): return int(round(t * SR))
out = np.zeros((N, 2), np.float32)
def place(sig, t, gain=1.0, pan=0.0):
    i = S(t); sig = np.asarray(sig, np.float32)
    if sig.ndim == 1: sig = np.stack([sig * (1 - max(pan, 0)), sig * (1 + min(pan, 0))], 1)
    if i < 0: sig = sig[-i:]; i = 0
    e = min(N, i + len(sig)); out[i:e] += sig[:e - i] * gain
def norm(x, peak=1.0): return x / (np.abs(x).max() + 1e-9) * peak
def fade(x, fi=0.005, fo=0.05):
    x = x.copy(); a, b = S(fi), S(fo)
    if a: x[:a] *= np.linspace(0, 1, a)[:, None] if x.ndim > 1 else np.linspace(0, 1, a)
    if b: x[-b:] *= np.linspace(1, 0, b)[:, None] if x.ndim > 1 else np.linspace(1, 0, b)
    return x

# ---- voice-over + ducked music
vo = load('audio/vo_timed.wav', 1)[:N]; vo = np.pad(vo, (0, N - len(vo)))
h = S(0.03); env = np.sqrt(np.convolve(vo ** 2, np.ones(h) / h, 'same'))
env = np.clip(env / (np.percentile(env[env > 1e-4], 70) + 1e-9), 0, 1)
sm = np.empty_like(env); s = 0.0; att, rel = 1 - np.exp(-1 / (0.03 * SR)), 1 - np.exp(-1 / (0.30 * SR))
for i in range(N):                                      # envelope follower: fast attack, slow release
    s += (att if env[i] > s else rel) * (env[i] - s); sm[i] = s
duck = 1.0 - 0.70 * np.clip(sm * 1.6, 0, 1)
m = load('music/m9.mp3')[S(T.MUSIC_IN):S(T.MUSIC_IN) + N]
mus = m * duck[:, None] * 0.42
dip = np.ones(N, np.float32); a_, b_ = S(T.PRESSES[0] - 0.15), S(T.RELEASE + 0.7); r_ = S(0.2)   # make room for the toy's own sounds
dip[a_:b_] = 0.6; dip[a_ - r_:a_] = np.linspace(1, 0.6, r_); dip[b_:b_ + r_] = np.linspace(0.6, 1, r_)
mus *= dip[:, None]
mus[:S(0.03)] *= np.linspace(0, 1, S(0.03))[:, None]
fo0 = S(T.DUR - 1.4); mus[fo0:] *= (np.cos(np.linspace(0, np.pi / 2, N - fo0)) ** 2)[:, None]
out += mus
out += np.stack([vo, vo], 1) * 1.0

# ---- synthesized SFX (same toolkit as the Target Blaster / Musical Stick reels)
rng = np.random.default_rng(7)
def lp(x, a):
    y = np.empty_like(x); s = 0.0; a = np.broadcast_to(a, x.shape)
    for k in range(len(x)): s += a[k] * (x[k] - s); y[k] = s
    return y
def whoosh(d=0.42, peak=0.62, bright=0.35):
    n = S(d); t = np.linspace(0, 1, n)
    env = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.5)
    a = 0.02 + bright * np.where(t < peak, t / peak, (1 - t) / (1 - peak))
    x = rng.standard_normal(n).astype(np.float32)
    y = lp(x, a) - lp(x, a * 0.15); y = y / np.abs(y).max() * env
    return np.stack([y, np.roll(y, S(0.004))], 1)
def impact(d=1.2, f0=62, f1=32):
    n = S(d); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 5); ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * 3.2) + lp(rng.standard_normal(n).astype(np.float32), 0.08) * np.exp(-t * 14) * 3 + rng.standard_normal(n) * np.exp(-t * 300) * 0.5
    return y / np.abs(y).max()
def thock(d=0.14):
    n = S(d); t = np.arange(n) / SR
    f = 120 + 140 * np.exp(-t * 60); y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 40)
    y += lp(rng.standard_normal(n).astype(np.float32), 0.3) * np.exp(-t * 90) * 2
    return y / np.abs(y).max()
def blip(d=0.09, f0=650, f1=1150):
    n = S(d); t = np.arange(n) / SR; f = f0 + (f1 - f0) * (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 2
def pop_snd(d=0.07):
    n = S(d); t = np.arange(n) / SR; f = 300 + 900 * np.exp(-t * 70)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 55)
def chime(notes, step=0.075, d=0.55):
    n = S(step * len(notes) + d); y = np.zeros(n)
    for i, f in enumerate(notes):
        t = np.arange(S(d)) / SR; k = S(i * step)
        tone = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 9) + 0.2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-t * 16)
        y[k:k + len(t)] += tone * np.exp(-t * 6.5) * (1 - np.exp(-t * 900))
    return y / np.abs(y).max()
def press(d=0.07):
    n = S(d); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * (1500 + 900 * np.exp(-t * 80)) * t) * np.exp(-t * 90) + rng.standard_normal(n) * np.exp(-t * 400) * 0.4
    return y / np.abs(y).max()
def beep(f=880, d=0.11):
    t = np.arange(S(d)) / SR
    return (np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6) * np.sin(np.pi * t / d) ** 0.5

# ---- placements
for t, k in T.CUTS:
    if k == 'chev': place(whoosh(0.50, 0.7, 0.4), t - 0.35, 0.26)
    elif k == 'zoom': place(whoosh(0.34, 0.7, 0.25), t - 0.24, 0.14)
def onset(x, thr=0.25):
    """first sample above thr x peak (s)"""
    a = np.abs(x if x.ndim == 1 else x.mean(1)); return int(np.argmax(a > thr * a.max())) / SR
# 0 the duck scooter drops in, lands, honks twice (horn SFX: its first two beeps only)
place(whoosh(0.34, 0.8, 0.35), T.LAND0 - 0.30, 0.16); place(thock(0.16), T.LAND0, 0.40); place(impact(0.6, 90, 50), T.LAND0, 0.14)
horn = load('audio/sfx_horn_beep_1.mp3')[:S(0.44)]
place(fade(norm(horn, 0.9), 0.003, 0.03), T.HORN, 0.50)
place(impact(1.0, 70, 36), T.w(0, 3) - 0.06, 0.30); place(pop_snd(), T.w(0, 3) - 0.06, 0.18)
place(chime([1047, 1319, 1568, 2093]), T.w(0, 6) - 0.04, 0.12)
# 1 two presses (real press whirr), the head turns 360 on its own, a final press + hold, lets go -> real "go" whirr
place(whoosh(0.4, 0.6, 0.3), T.PRESSES[0] - 0.42, 0.12)
for k, tp in enumerate(T.PRESSES + [T.GO_PRESS]):                    # the presses: the real press whirr each time
    x = load('audio/og_press_%d.wav' % (k + 1), 1); x = fade(norm(x, 0.9), 0.003, 0.03)
    place(x, tp - onset(x), 0.62, pan=0.1)
# the head turning 360 on its own (no press): a soft swirl across the turn + a light tick at each quarter
place(whoosh(T.TURN1 - T.TURN0 + 0.1, 0.5, 0.3), T.TURN0 - 0.05, 0.10)
uu = np.linspace(0, 1, 2001); ee = np.where(uu < .5, 4 * uu ** 3, 1 - (-2 * uu + 2) ** 3 / 2)
for q in (0.125, 0.375, 0.625, 0.875):
    place(blip(0.05, 520, 700), T.TURN0 + (T.TURN1 - T.TURN0) * uu[np.argmin(np.abs(ee - q))], 0.06)
go = load('audio/og_go.wav', 1); go = fade(norm(go, 0.9), 0.004, 0.12)
place(go, T.RELEASE + 0.02 - onset(go, 0.35), 0.72)
place(whoosh(0.5, 0.35, 0.5), T.RELEASE + 0.08, 0.16); place(impact(0.8, 80, 40), T.RELEASE + 0.02, 0.18)
# 2 riders slide in, each hops on its word
place(whoosh(0.6, 0.5, 0.35), T.S_RIDERS + 0.15, 0.14)
for t in (T.MOUSE, T.DUCK): place(pop_snd(), t, 0.22); place(chime([1319, 1568, 2093], 0.05, 0.4), t + 0.06, 0.10)
# 3 one pop per colour, a hop on "scooters"
for t in T.COL_POPS: place(pop_snd(), t, 0.22); place(blip(0.08, 700, 1300), t + 0.02, 0.07)
place(chime([1047, 1319, 1568], 0.05, 0.4), T.w(3, 5), 0.10)
# 4 badges
for t in T.SAFE_POPS: place(pop_snd(), t - 0.04, 0.18); place(blip(), t - 0.02, 0.06)
# 5 the pouch drops onto the peg (light clack), sparkle when the rider shows through
place(whoosh(0.36, 0.8, 0.3), T.S_POUCH + 0.04, 0.16); place(thock(0.10), T.S_POUCH + 0.38, 0.30); place(press(), T.S_POUCH + 0.38, 0.10)
place(chime([1319, 1568, 2093, 2637], 0.06), T.SHOWS, 0.12)
# 6 cartons land, truck delivers
for x, y, tl in T.STACK: place(thock(0.16), tl, 0.45); place(impact(0.5, 90, 50), tl, 0.12)
place(whoosh(0.6, 0.6, 0.35), T.TRUCK, 0.20)
place(beep(880), T.TRUCK + 0.66, 0.08); place(beep(880), T.TRUCK + 0.82, 0.08)
# 7 the peg board slides up, pouches pop on, FILL YOUR SHELVES!
place(whoosh(0.5, 0.6, 0.3), T.S_BULK + 0.2, 0.14)
for i, t in enumerate(T.FILL): place(pop_snd(), t, 0.16); place(press(), t, 0.05)
place(impact(1.0, 70, 36), T.w(7, 3) - 0.06, 0.34); place(chime([784, 988, 1175, 1568, 1976], 0.06), T.w(7, 3), 0.12)
# 8 end card
place(impact(1.8, 58, 30), T.S_END, 0.42); place(chime([1319, 1568, 2093, 2637], 0.07), T.w(8, 0) - 0.1, 0.12)
for t in (T.w(1, 4), T.w(2, 0), T.w(3, 1), T.w(5, 2), T.w(6, 0), T.w(6, 2), T.w(7, 0), T.w(7, 2)): place(blip(), t - 0.05, 0.07)

# ---- loudness: integrated to about -14 LUFS, then a soft-knee limiter (ffmpeg alimiter at mux catches true peaks)
def lufs(x):
    p = subprocess.run(['ffmpeg', '-v', 'info', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'ebur128', '-f', 'null', '-'],
                       input=x.astype(np.float32).tobytes(), capture_output=True).stderr.decode()
    return float(p.rsplit('I:', 1)[1].split('LUFS')[0])
for _ in range(2):
    g = 10 ** ((-14.0 - lufs(out)) / 20); out *= g
    ax = np.abs(out); knee = 0.80
    out = np.sign(out) * np.where(ax < knee, ax, knee + 0.17 * np.tanh((ax - knee) / 0.17))
pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16)
w = wave.open(os.path.join(ROOT, 'mix.wav'), 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('mix.wav', len(out) / SR, 's  LUFS %.1f  peak %.3f' % (lufs(out), np.abs(out).max()))
