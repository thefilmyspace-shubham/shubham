# VO + music bed (ducked under the voice) + SFX -> mix.wav (48 kHz stereo, about -14 LUFS)
#   VO:    audio/vo_timed.wav (client's ElevenLabs voice-over, re-timed by tools/vo_retime.py)
#   SFX:   audio/sfx_roar_elevenlabs.mp3, audio/sfx_zoom_elevenlabs.mp3 (ElevenLabs sound effects),
#          audio/Dino_Car_friction_sound_clean.mp3 (the toy's real friction motor, cleaned) + synthesized whooshes/pops
#   music: music/m1057.mp3 ("Cupcakes", Mixkit free license; sh music/get_music.sh)
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
m = load('music/m1057.mp3')[S(T.MUSIC_IN):S(T.MUSIC_IN) + N]
mus = m * duck[:, None] * 1.2
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
def beep(f=880, d=0.11):
    t = np.arange(S(d)) / SR
    return (np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6) * np.sin(np.pi * t / d) ** 0.5
def spin(d=0.7):                                   # flip whoosh: whoosh with a fast tremolo
    w = whoosh(d, 0.5, 0.45); t = np.arange(len(w)) / SR
    return w * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))[:, None]

# ---- placements
for t, k in T.CUTS:
    if k == 'chev': place(whoosh(0.50, 0.7, 0.4), t - 0.35, 0.26)
    elif k == 'zoom': place(whoosh(0.34, 0.7, 0.25), t - 0.24, 0.14)
place(whoosh(0.32, 0.8, 0.3), 0.0, 0.20); place(impact(1.3), 0.32, 0.42); place(thock(), 0.32, 0.30)    # truck lands
place(chime([1047, 1319, 1568, 2093]), T.w(0, 1) - 0.04, 0.12)                                         # DINO
roar = load('audio/sfx_roar_elevenlabs.mp3'); place(fade(norm(roar, 0.9), 0.002, 0.08), T.ROAR, 0.62)
place(impact(0.8, 80, 40), T.ROAR, 0.22)
# push & go: the toy's real friction motor -- ratchet while the glove pushes, flywheel whirr as it rolls away
fr = load('audio/Dino_Car_friction_sound_clean.mp3')
place(fade(norm(fr[S(0.48):S(2.95)], 0.9), 0.01, 0.6), T.PUSH0, 0.62)
place(pop_snd(), T.HAND_IN + 0.26, 0.25)                                                               # glove touches down
zoom = load('audio/sfx_zoom_elevenlabs.mp3'); place(fade(norm(zoom, 0.9), 0.002, 0.1), T.RELEASE - 0.02, 0.55)
place(whoosh(0.5, 0.35, 0.5), T.RELEASE + 0.05, 0.18)
place(blip(0.09, 500, 900), T.w(1, 1), 0.10)                                                           # battery icon
# stunt: rolls in on the friction motor, climbs, flips, lands
place(fade(norm(fr[S(3.86):S(5.40)], 0.9), 0.02, 0.4), T.S_STUNT, 0.40)
place(whoosh(0.4, 0.6, 0.35), T.LAUNCH - 0.25, 0.16)
place(spin(T.LAND - T.LAUNCH), T.LAUNCH, 0.24)
place(thock(0.16), T.LAND, 0.45); place(impact(0.7, 85, 45), T.LAND, 0.22)
place(chime([784, 988, 1175, 1568], 0.06), T.w(2, 2), 0.11)                                             # 360°
# mouth opens: a little growl + creak
place(fade(norm(roar, 0.9), 0.002, 0.15)[:S(0.55)], T.JAW_OPEN + 0.05, 0.20)
place(thock(0.1), T.JAW_OPEN, 0.18); place(blip(0.12, 300, 700), T.JAW_WIDE, 0.10)
# colours / safety rows
for i, t in enumerate(T.COL_POPS): place(chime([[1047, 1319], [1175, 1480], [1319, 1568], [1568, 2093]][i], 0.06, 0.45), t, 0.12); place(pop_snd(), t, 0.18)
for t in T.SAFE_POPS: place(blip(), t, 0.10); place(pop_snd(), t, 0.14)
# display box: lands, fills with 12 trucks, counter slides in
place(whoosh(0.36, 0.8, 0.3), T.BOX_LAND - 0.34, 0.16); place(thock(0.16), T.BOX_LAND, 0.45); place(impact(0.6, 90, 50), T.BOX_LAND, 0.16)
for i, t in enumerate(T.FILL): place(pop_snd(0.06), t + 0.12, 0.13, pan=[-0.3, -0.1, 0.1, 0.3][i % 4])
place(whoosh(0.45, 0.5, 0.3), T.COUNTER - 0.05, 0.16); place(chime([1319, 1568, 2093, 2637], 0.07), T.COUNTER + 0.25, 0.12)
# cartons land, truck delivers
for x, y, tl in T.STACK: place(thock(0.16), tl, 0.45); place(impact(0.5, 90, 50), tl, 0.12)
place(whoosh(0.6, 0.6, 0.35), T.TRUCK, 0.20)
place(beep(880), T.TRUCK + 0.66, 0.10); place(beep(880), T.TRUCK + 0.82, 0.10)
# bulk / order today / end card
for i in range(4): place(pop_snd(), T.S_BULK + 0.34 + i * 0.12, 0.14)
place(impact(1.0, 70, 36), T.w(8, 7) - 0.10, 0.38); place(chime([784, 988, 1175, 1568, 1976], 0.06), T.w(8, 7) - 0.05, 0.12)
place(impact(1.8, 58, 30), T.S_END, 0.42); place(chime([1319, 1568, 2093, 2637], 0.07), T.w(9, 0) - 0.1, 0.12)
for t in (T.w(0, 2), T.w(2, 3), T.w(6, 2), T.w(7, 1), T.w(7, 6), T.w(8, 0), T.w(8, 2), T.w(8, 5)): place(blip(), t, 0.08)

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
