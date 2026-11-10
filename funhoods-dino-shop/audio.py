# VO + music + sound design for the Dino Car "shop story" -> mix.wav (48 kHz stereo, about -14 LUFS)
#   VO:    audio/vo_timed.wav (Magnific / ElevenLabs v4, voice "Gavin", sample 1, re-timed by tools/vo_retime.py).
#          The VO never speaks a sound effect.
#   story: the quiet morning has no music -- street ambience, birds, the shop shutter (audio/sfx_shutter.mp3, generated);
#          the music starts when the Funhoods truck arrives.
#   toy:   the Dino Car's REAL friction sound (audio/og_friction.mp3, from the Dino Car reel) for the push and the roll,
#          and the Dino Car reel's roar (audio/sfx_roar.mp3) on the wide chomp
#   kids:  audio/sfx_kids_cheer.mp3 (generated)
#   SFX:   synthesized engine, thocks, stamp, register bell, clock ticks, whooshes, pops and chimes
#   music: music/m10.mp3 ("Playful", Ahjay Stelino, Mixkit free license; sh music/get_music.sh) -- 130 BPM, a new track
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

# ---- voice-over + music (starts with the truck, ducked under the voice)
vo = load('audio/vo_timed.wav', 1)[:N]; vo = np.pad(vo, (0, N - len(vo)))
h = S(0.03); env = np.sqrt(np.convolve(vo ** 2, np.ones(h) / h, 'same'))
env = np.clip(env / (np.percentile(env[env > 1e-4], 70) + 1e-9), 0, 1)
sm = np.empty_like(env); s = 0.0; att, rel = 1 - np.exp(-1 / (0.03 * SR)), 1 - np.exp(-1 / (0.30 * SR))
for i in range(N):                                      # envelope follower: fast attack, slow release
    s += (att if env[i] > s else rel) * (env[i] - s); sm[i] = s
duck = 1.0 - 0.70 * np.clip(sm * 1.6, 0, 1)
M0 = T.S_ARRIVE - 0.15                                  # a bar of the music lands as the truck pulls in
m = load('music/m10.mp3')[S(T.MUSIC_IN):S(T.MUSIC_IN) + N - S(M0)]
mus = np.zeros((N, 2), np.float32); mus[S(M0):S(M0) + len(m)] = m
mus *= (duck * 0.42)[:, None]
dip = np.ones(N, np.float32); a_, b_ = S(T.PUSH0 - 0.1), S(T.CHOMPS[-1][0] + 0.9); r_ = S(0.2)   # room for the toy's own sounds
dip[a_:b_] = 0.7; dip[a_ - r_:a_] = np.linspace(1, 0.7, r_); dip[b_:b_ + r_] = np.linspace(0.7, 1, r_)
mus *= dip[:, None]
mus[S(M0):S(M0) + S(0.06)] *= np.linspace(0, 1, S(0.06))[:, None]
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

def chirp(f0=3200, f1=4400, d=0.07):
    t = np.arange(S(d)) / SR; f = f0 + (f1 - f0) * (t / d) ** 0.5
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / d) ** 1.5
def engine(d, f=46):
    t = np.arange(S(d)) / SR
    y = np.sin(2 * np.pi * f * t) * 0.6 + np.sin(2 * np.pi * f * 2.02 * t) * 0.3 + lp(rng.standard_normal(len(t)).astype(np.float32), 0.02) * 4
    y *= 1 + 0.25 * np.sin(2 * np.pi * 11 * t)
    return y / np.abs(y).max()
def tick(d=0.03):
    n = S(d); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2400 * t) * 0.5 + rng.standard_normal(n) * 0.5) * np.exp(-t * 260)
def register():
    """cash-register bell: a short ka-chunk then a bright ding"""
    y = np.zeros(S(1.0)); k = thock(0.08); y[:len(k)] += k * 0.6
    t = np.arange(S(0.9)) / SR; i0 = S(0.09)
    for f in (2093, 2637, 3136): y[i0:i0 + len(t)] += np.sin(2 * np.pi * f * t) * np.exp(-t * 5) * 0.4
    return y / np.abs(y).max()
def ambience(d):
    """quiet street morning: soft filtered noise"""
    n = S(d); y = lp(rng.standard_normal(n).astype(np.float32), 0.015) * 6
    return np.stack([y, np.roll(y, S(0.011))], 1) / (np.abs(y).max() + 1e-9)

# ---- placements
for t, k in T.CUTS:
    if k == 'chev': place(whoosh(0.50, 0.7, 0.4), t - 0.35, 0.26)
    elif k == 'zoom': place(whoosh(0.34, 0.7, 0.25), t - 0.24, 0.14)
    elif k == 'flash': place(whoosh(0.4, 0.7, 0.3), t - 0.28, 0.14)
def onset(x, thr=0.25):
    a = np.abs(x if x.ndim == 1 else x.mean(1)); return int(np.argmax(a > thr * a.max())) / SR
# 0 quiet morning: street ambience + birds, the shutter rolls up; nobody stops (no music yet)
amb = ambience(T.S_COUNTER + 0.3); amb[:S(0.3)] *= np.linspace(0, 1, S(0.3))[:, None]; amb[-S(0.5):] *= np.linspace(1, 0, S(0.5))[:, None]
place(amb, 0.0, 0.05)
for i, tb in enumerate([0.4, 0.55, 1.9, 2.05, 2.2, 3.6, 4.6, 4.75]): place(chirp(3000 + 300 * (i % 3), 4200 + 200 * (i % 2)), tb, 0.05, pan=(-0.4 if i % 2 else 0.4))
sh = load('audio/sfx_shutter.mp3'); place(fade(norm(sh, 0.9), 0.003, 0.15), T.SHUTTER[0] - 0.05, 0.42)
# 1 the Funhoods truck pulls up (engine, no horn), a carton hops to the shop door
place(fade(np.stack([engine(T.TRUCK_STOP - T.S_ARRIVE + 0.9)] * 2, 1), 0.4, 0.5), T.S_ARRIVE - 0.2, 0.10)
place(whoosh(0.6, 0.5, 0.3), T.S_ARRIVE - 0.1, 0.12); place(thock(0.12), T.TRUCK_STOP, 0.18)
place(whoosh(0.3, 0.7, 0.4), T.CARTON_LAND - 0.42, 0.10); place(thock(0.16), T.CARTON_LAND, 0.42); place(impact(0.6, 90, 50), T.CARTON_LAND, 0.14)
place(chime([1047, 1319, 1568, 2093], 0.06), T.CARTON_LAND + 0.05, 0.12)
# 2 the display box lands on the counter; the lamp becomes a spotlight
place(whoosh(0.36, 0.8, 0.3), T.BOX_LAND - 0.34, 0.14); place(thock(0.16), T.BOX_LAND, 0.45); place(impact(0.6, 90, 50), T.BOX_LAND, 0.14)
place(chime([784, 1175, 1568, 2349], 0.05, 0.8), T.SPOT, 0.12)
# 3 push & go on the counter: the real friction ratchet while pushing, the flywheel whirr as it rolls, flip, land, chomps
fric = load('audio/og_friction.mp3')
def og(x, s0, s1, fi=0.01, fo=0.12): return fade(norm(x[S(s0):S(s1)], 0.9), fi, fo)
place(pop_snd(), T.PUSH0 - 0.04, 0.16)
place(og(fric, 0.5, 0.5 + T.RELEASE - T.PUSH0 + 0.15, 0.01, 0.08), T.PUSH0, 0.55)
place(og(fric, 1.3, 1.3 + T.LAUNCH - T.RELEASE + 0.2, 0.005, 0.3), T.RELEASE, 0.55)
place(whoosh(0.5, 0.4, 0.5), T.LAUNCH - 0.05, 0.18); place(whoosh(0.5, 0.6, 0.4), T.LAUNCH + 0.25, 0.12)
place(thock(0.16), T.LAND, 0.45); place(impact(0.7, 80, 40), T.LAND, 0.2)
cheer = load('audio/sfx_kids_cheer.mp3'); cheer = fade(norm(cheer, 0.9), 0.01, 0.4)
place(cheer, T.LAND + 0.02 - onset(cheer, 0.4), 0.30)
for t0, amp, hold in T.CHOMPS: place(thock(0.08), t0 + 0.16 + hold + 0.10, 0.22)
roar = load('audio/sfx_roar.mp3'); place(fade(norm(roar, 0.9), 0.003, 0.2), T.CHOMPS[-1][0] + 0.02, 0.40)
# 4 kids crowd in, the dinos hop out, the clock runs to evening, SOLD OUT, reorder
place(cheer[:S(2.2)], T.S_RUSH + 0.15, 0.22)
for i, tg in enumerate(T.GRABS): place(pop_snd(), tg, 0.13, pan=(-0.3, 0, 0.3)[i % 3]); place(blip(0.07, 700 + 40 * i, 1200 + 40 * i), tg + 0.02, 0.04)
for k in range(8): place(tick(), T.EVENING + 0.125 * k, 0.10)
place(impact(0.9, 70, 36), T.SOLD, 0.38); place(thock(0.18), T.SOLD, 0.5)
place(register(), T.REORDER - 0.02, 0.22)
# 5-8 facts, carton, route, end
for t in T.FACT_POPS[:1] + [T.FACT_POPS[0] + 0.12 * i for i in range(1, 4)]: place(pop_snd(), t, 0.16)
for t in T.FACT_POPS[1:]: place(pop_snd(), t - 0.04, 0.18); place(blip(), t - 0.02, 0.06)
for x, y, tl in T.STACK: place(thock(0.16), tl, 0.45); place(impact(0.5, 90, 50), tl, 0.12)
place(whoosh(0.6, 0.6, 0.35), T.TRUCK, 0.20)
place(fade(np.stack([engine(1.8, 52)] * 2, 1), 0.3, 0.5), T.ROUTE_LIT[0] - 0.7, 0.07)
for i, t in enumerate(T.ROUTE_LIT): place(chime([1319 + 200 * i, 1568 + 200 * i, 2093 + 200 * i], 0.05, 0.4), t, 0.10); place(whoosh(0.3, 0.5, 0.3), t - 0.15, 0.06)
place(impact(1.8, 58, 30), T.S_END, 0.42); place(chime([1319, 1568, 2093, 2637], 0.07), T.w(8, 0) - 0.1, 0.12)
for t in (T.w(2, 5), T.w(3, 1), T.w(5, 0), T.w(6, 0), T.w(6, 2), T.w(7, 0), T.w(7, 2)): place(blip(), t - 0.05, 0.06)

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
