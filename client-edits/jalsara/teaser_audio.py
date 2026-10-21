"""Teaser audio: Mixkit 'Epical Drums 01' (ducked under speech) + interview vocals (Demucs stem) + synth hits."""
import os, subprocess, wave, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'film'))
import film_audio as FA
import teaser as T

SR = FA.SR; N = int(T.END * SR)
VOC = os.path.join(HERE, 'sep', 'htdemucs', 'a', 'vocals.wav')
MUS = os.path.join(os.path.dirname(HERE), 'film', 'music', 'm676.mp3')

def bite(a, b):
    x = FA.load(VOC, a, b - a)
    nf = int(0.012 * SR)
    if len(x) > 2 * nf: x[:nf] *= np.linspace(0, 1, nf)[:, None]; x[-nf:] *= np.linspace(1, 0, nf)[:, None]
    return x

def main():
    t = np.arange(N) / SR
    vo = np.zeros((N, 2), np.float32); spans = []
    starts = {s[5]: s[0] for s in T.SEGS}
    for nm, a, b in [('b1', T.B1[1], T.B1[2])] + [(n, a, b) for n, a, b, _ in T.TAIL]:
        FA.place(vo, bite(a, b), starts[nm]); spans.append((starts[nm], starts[nm] + b - a))
    a, b = T.VO_1990; FA.place(vo, bite(a, b), T.VO_AT); spans.append((T.VO_AT, T.VO_AT + b - a))
    vo *= FA.db(-1.5) / (np.abs(vo).max() + 1e-9)
    # music + ducking
    music = np.zeros((N, 2), np.float32); FA.place(music, FA.load(MUS, T.M0, T.END + 0.5), 0.0)
    duck = np.ones(N)
    for s0, s1 in spans:
        m = (t >= s0 - 0.05) & (t < s1 + 0.05); duck[m] = FA.db(-11)
    k = int(0.06 * SR); duck = np.convolve(duck, np.ones(k) / k, 'same')
    music *= (duck * FA.db(-2))[:, None].astype(np.float32)
    # end card: music to full, small fade at the very end
    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: FA.place(fx, clip, tt, gd)
    W2, W1, I3, I4, SH = FA.sfx('whoosh2'), FA.sfx('whoosh1'), FA.sfx('impact3'), FA.sfx('impact4'), FA.sfx('shutter1')
    def glitch(d=0.25):
        n = int(d * SR); x = FA.rng.standard_normal(n) * (np.sin(2 * np.pi * 37 * np.arange(n) / SR) > 0)
        x = x * np.exp(-np.arange(n) / (0.1 * SR)); return FA.st(x * 0.35)
    pl(I3, 0.08, -4); pl(FA.boom(1.4), 0.08, -6); pl(glitch(), 0.08, -14)
    for c in T.CUTS:
        if c >= T.E - 0.1: continue
        nm = [s[5] for s in T.SEGS if abs(s[0] - c) < 1e-6][0]
        if nm.startswith('m'): pl(SH, c - 0.02, -14); pl(FA.tick(1500, 0.03, 0.7), c, -16)
        elif nm == 'b5x': pass
        else: pl(W2, c - 0.12, -11)
    pl(I4, T.SEGS[1][0], -10)
    pl(FA.riser(1.5), T.E - 1.5, -9)
    pl(I3, T.E, -1); pl(FA.boom(2.2), T.E, -3); pl(FA.braam(2.4, 49.0), T.E, -9); pl(glitch(0.35), T.E, -12)
    pl(FA.tick(2600, 0.03, 0.7), T.E + 0.35, -14); pl(FA.tick(2200, 0.03, 0.7), T.E + 0.7, -15)
    pl(FA.chime(), T.E + 1.05, -14)
    mix = music + vo + fx * FA.db(-1)
    mix *= np.clip((T.END - t) / 0.5, 0, 1)[:, None] ** 0.6
    mix = np.tanh(mix * 1.05) / 1.05
    raw = os.path.join(HERE, 'teaser_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-13:TP=-1.5:LRA=9,alimiter=limit=0.89:level=false',
                    '-ar', '48000', '-c:a', 'pcm_s16le', os.path.join(HERE, 'teaser_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
