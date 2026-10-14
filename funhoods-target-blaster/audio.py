# Music edit + synthesized SFX -> mix.wav (48 kHz stereo)
import numpy as np, wave, subprocess, sys
sys.path.insert(0, '.')
import timeline as T
SR = 48000
def load_mp3(p):
    raw = subprocess.run(['ffmpeg','-v','error','-i',p,'-f','s16le','-ac','2','-ar',str(SR),'-'],capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32).reshape(-1,2)/32768
m = load_mp3('music/m47.mp3')
N = int(T.DUR*SR)
out = np.zeros((N,2), np.float32)
def S(t): return int(round(t*SR))
# music: part 1 [MUSIC_IN, MUSIC_IN+JUMP_V), part 2 from MUSIC_JUMP_TO; 12 ms equal-power crossfade at the jump
xf = S(0.012)
p1 = m[S(T.MUSIC_IN):S(T.MUSIC_IN+T.JUMP_V)+xf]
p2 = m[S(T.MUSIC_JUMP_TO)-xf:S(T.MUSIC_JUMP_TO)+N]
j = S(T.JUMP_V)
mus = np.zeros((N+xf*2,2),np.float32)
mus[:len(p1)] += p1
r = np.linspace(0,1,2*xf)[:,None]
fade_out = np.ones((len(p1),1),np.float32); fade_out[-2*xf:] = np.cos(r*np.pi/2)
mus[:len(p1)] *= fade_out
p2 = p2.copy(); p2[:2*xf] *= np.sin(r*np.pi/2)
mus[j-xf:j-xf+len(p2)] += p2[:len(mus)-(j-xf)]
mus = mus[:N]
mus[:S(0.02)] *= np.linspace(0,1,S(0.02))[:,None]
fo0, fo1 = S(T.DUR-1.6), N
mus[fo0:fo1] *= (np.cos(np.linspace(0,np.pi/2,fo1-fo0))**2)[:,None]
out += mus*0.86
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
b = T.b
# transitions
for t, k in T.CUTS:
    if k in ('chev','whip'): place(whoosh(0.44, 0.7, 0.4), t-0.31, 0.32)
    elif k == 'zoom':        place(whoosh(0.30, 0.7, 0.25), t-0.21, 0.18)
place(impact(1.4), 0.0, 0.40)            # logo slam
place(riser(T.DROP-b(36)), b(36), 0.16)  # build into the drop
place(impact(1.6), T.DROP, 0.55)         # drop
place(impact(1.2, 70, 36), b(68), 0.38)  # STOCK UP
place(impact(1.8, 58, 30), T.END_HIT, 0.55)
# mechanism SFX (synced to the footage)
place(click(), 11.30, 0.38)
place(thock(), 14.33, 0.35); place(thock(), 16.08, 0.35)
place(thwip(), 18.53, 0.60); place(thwip(), b(43), 0.55)
# UI pops for text
for t in [b(16), b(18), b(20), b(22), b(44), b(48), b(52), b(56), b(61), b(62), b(63), b(69), b(70), b(74), b(76)]:
    place(blip(), t, 0.10)
peak = np.abs(out).max(); out *= min(1.0, 0.97/peak)
pcm = (np.clip(out, -1, 1)*32767).astype(np.int16)
w = wave.open('mix.wav','wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('mix.wav', len(out)/SR, 's  peak', peak)
