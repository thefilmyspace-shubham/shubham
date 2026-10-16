# Music edit + synthesized SFX -> mix.wav (48 kHz stereo)
import numpy as np, wave, subprocess, sys
sys.path.insert(0, '.')
import timeline as T
SR = 48000
def load_mp3(p):
    raw = subprocess.run(['ffmpeg','-v','error','-i',p,'-f','s16le','-ac','2','-ar',str(SR),'-'],capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1,2)/32768
m = load_mp3('music/m12.mp3')
N = int(T.DUR*SR)
out = np.zeros((N,2), np.float32)
def S(t): return int(round(t*SR))
# music: pieces from T.MUSIC joined on beats with 12 ms equal-power crossfades
xf = S(0.012)
mus = np.zeros((N + 4*xf, 2), np.float32)
r = np.linspace(0, 1, 2*xf)[:, None]
for k, (vb, mt) in enumerate(T.MUSIC):
    v0 = S(T.b(vb)); v1 = S(T.b(T.MUSIC[k+1][0])) if k+1 < len(T.MUSIC) else N
    a = max(0, v0 - xf); e = min(N, v1 + xf)
    piece = m[S(mt) - (v0 - a): S(mt) - (v0 - a) + (e - a)].copy()
    if k > 0: piece[:2*xf] *= np.sin(r*np.pi/2)
    if k+1 < len(T.MUSIC): piece[-2*xf:] *= np.cos(r*np.pi/2)
    mus[a:a+len(piece)] += piece
mus = mus[:N]
mus[:S(0.02)] *= np.linspace(0, 1, S(0.02))[:, None]
fo0, fo1 = S(T.DUR-1.3), N
mus[fo0:fo1] *= (np.cos(np.linspace(0, np.pi/2, fo1-fo0))**2)[:, None]
out += mus*1.08

rng = np.random.default_rng(7)
def place(sig, t, gain=1.0, pan=0.0):
    i = S(t); sig = np.asarray(sig, np.float32)
    if sig.ndim == 1: sig = np.stack([sig*(1-max(pan,0)), sig*(1+min(pan,0))],1)
    e = min(N, i+len(sig)); 
    if i < 0: sig = sig[-i:]; i = 0
    out[i:e] += sig[:e-i]*gain
def lp(x, a):   # one-pole lowpass, a may be array
    y = np.empty_like(x); s = 0.0; a = np.broadcast_to(a, x.shape)
    for k in range(len(x)): s += a[k]*(x[k]-s); y[k] = s
    return y
def whoosh(d=0.42, peak=0.62, bright=0.35):
    n = S(d); t = np.linspace(0,1,n)
    env = np.where(t<peak, (t/peak)**2, ((1-t)/(1-peak))**1.5)
    a = 0.02 + bright*np.where(t<peak, t/peak, (1-t)/(1-peak))
    x = rng.standard_normal(n).astype(np.float32)
    y = lp(x, a) - lp(x, a*0.15)
    y = y/np.abs(y).max()*env
    l = y; r = np.roll(y, S(0.004))
    return np.stack([l, r], 1)
def impact(d=1.2, f0=62, f1=32):
    n = S(d); t = np.arange(n)/SR
    f = f1 + (f0-f1)*np.exp(-t*5); ph = 2*np.pi*np.cumsum(f)/SR
    sub = np.sin(ph)*np.exp(-t*3.2)
    nz = lp(rng.standard_normal(n).astype(np.float32), 0.08)*np.exp(-t*14)*3
    clk = rng.standard_normal(n)*np.exp(-t*300)*0.5
    y = sub + nz + clk; return y/np.abs(y).max()
def thwip(d=0.16):
    n = S(d); t = np.arange(n)/SR
    f = 260 + 1300*np.exp(-t*38); ph = 2*np.pi*np.cumsum(f)/SR
    tone = np.sin(ph)*np.exp(-t*30)
    nz = rng.standard_normal(n); nz = (nz - lp(nz.astype(np.float32), 0.25))*np.exp(-t*60)
    pop = np.sin(2*np.pi*110*t)*np.exp(-t*45)
    y = tone*0.8 + nz*0.6 + pop*0.9; return y/np.abs(y).max()
def click(d=0.12, gap=0.055):
    n = S(d); y = np.zeros(n)
    for k, g in ((0, 1.0), (S(gap), 0.7)):
        m_ = S(0.006); b_ = rng.standard_normal(m_)*np.exp(-np.arange(m_)/SR*900)
        b_ = np.diff(np.concatenate([[0], b_])); y[k:k+m_] += b_*g
        tt = np.arange(S(0.03))/SR; y[k:k+len(tt)] += np.sin(2*np.pi*1900*tt)*np.exp(-tt*220)*0.35*g
    return y/np.abs(y).max()
def thock(d=0.12):
    n = S(d); t = np.arange(n)/SR
    f = 120 + 140*np.exp(-t*60); y = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*40)
    y += lp(rng.standard_normal(n).astype(np.float32), 0.3)*np.exp(-t*90)*2
    return y/np.abs(y).max()
def blip(d=0.09, f0=650, f1=1150):
    n = S(d); t = np.arange(n)/SR; f = f0 + (f1-f0)*(t/d)
    return np.sin(2*np.pi*np.cumsum(f)/SR)*np.sin(np.pi*t/d)**2
def riser(d):
    n = S(d); t = np.linspace(0,1,n)
    x = rng.standard_normal(n).astype(np.float32); a = 0.01 + 0.5*t**2
    y = lp(x, a) - lp(x, a*0.2); y = y/np.abs(y).max()*t**2.5
    return np.stack([y, np.roll(y, S(0.006))],1)

def chime(notes, step=0.075, d=0.55):
    """toy music-box: short bell tones (fundamental + bright partials)"""
    n = S(step*len(notes) + d); y = np.zeros(n)
    for i, f in enumerate(notes):
        t = np.arange(S(d))/SR; k = S(i*step)
        tone = (np.sin(2*np.pi*f*t) + 0.45*np.sin(2*np.pi*2.76*f*t)*np.exp(-t*9) + 0.2*np.sin(2*np.pi*5.4*f*t)*np.exp(-t*16))
        y[k:k+len(t)] += tone*np.exp(-t*6.5)*(1 - np.exp(-t*900))
    return y/np.abs(y).max()
def press(d=0.07):
    n = S(d); t = np.arange(n)/SR
    y = np.sin(2*np.pi*(1500 + 900*np.exp(-t*80))*t)*np.exp(-t*90)
    y += rng.standard_normal(n)*np.exp(-t*400)*0.4
    return y/np.abs(y).max()
b = T.b
for t, k in T.CUTS:
    if k == 'chev':   place(whoosh(0.50, 0.7, 0.4), t-0.35, 0.30)
    elif k == 'zoom': place(whoosh(0.34, 0.7, 0.25), t-0.24, 0.17)
place(impact(1.4), 0.0, 0.40)
place(chime([1047, 1319, 1568, 2093]), b(4.1), 0.16)          # product reveal sparkle
place(riser(T.DROP-b(28)), b(28), 0.15)
place(impact(1.6), T.DROP, 0.55)
place(chime([784, 988, 1175, 1568, 1976], 0.06), T.DROP + 0.05, 0.14)
place(impact(1.2, 70, 36), b(52), 0.38)
place(impact(1.8, 58, 30), T.END_HIT, 0.55)
place(chime([1319, 1568, 2093, 2637], 0.07), b(8) + 0.45, 0.13)                 # notes pour out of the box
place(whoosh(0.5, 0.6, 0.35), T.PICK_RISE[0] - 0.05, 0.20)                        # stick rises out of the box
place(chime([1047, 1568, 2093], 0.08), T.PICK_RISE[0] + T.PICK_RISE[1] * 0.6, 0.15)
for x, y, tl in T.STACK:                                                         # boxes land on the stack
    place(thock(0.16), tl, 0.45); place(impact(0.5, 90, 50), tl, 0.12)
# step 2: three button presses, each answered by a toy chime
for i, t in enumerate(T.TAPS):
    place(press(), t, 0.30)
    place(chime([[1047, 1319, 1568], [1175, 1480, 1760], [1319, 1568, 2093]][i], 0.07), t + 0.05, 0.17)
# step 3: music-box run while the sounds "play"
place(chime([1568, 1319, 1047, 1319, 1568, 2093, 1568, 1319], 0.11, 0.6), b(28.3), 0.13)
for t in [b(4.5), b(12), b(16), b(24.5), b(28.5), b(36.5), b(38.5), b(40.5), b(46), b(47.5), b(49), b(53), b(54), b(58), b(59), b(60.5)]:
    place(blip(), t, 0.10)
peak = np.abs(out).max()
ax = np.abs(out); knee = 0.80
out = np.sign(out) * np.where(ax < knee, ax, knee + 0.17*np.tanh((ax - knee)/0.17))
pcm = (np.clip(out, -1, 1)*32767).astype(np.int16)
w = wave.open('mix.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('mix.wav', len(out)/SR, 's  peak', peak)
