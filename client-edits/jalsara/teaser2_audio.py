"""Teaser v2 audio: interview vocals + soft dreamy SFX, NO music bed (Daydream to be added on Instagram or from Shubham's file)."""
import os, subprocess, wave, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'film'))
import film_audio as FA
import teaser as T
import teaser2 as T2
from teaser_audio import bite

SR = FA.SR; N = int(T.END * SR)
def swell(d=1.2):
    n = int(d * SR); t = np.arange(n) / SR
    x = FA.onepole(FA.rng.standard_normal(n), 900 + 2500 * (t / d)) * np.sin(np.pi * t / d) ** 2
    return FA.st(x / (np.abs(x).max() + 1e-9) * 0.35, 0.004)

def main():
    t = np.arange(N) / SR
    vo = np.zeros((N, 2), np.float32)
    starts = {s[5]: s[0] for s in T.SEGS}
    for nm, a, b in [('b1', T.B1[1], T.B1[2])] + [(n, a, b) for n, a, b, _ in T.TAIL]:
        FA.place(vo, bite(a, b), starts[nm])
    a, b = T.VO_1990; FA.place(vo, bite(a, b), T.VO_AT)
    vo *= FA.db(-1.5) / (np.abs(vo).max() + 1e-9)
    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: FA.place(fx, clip, tt, gd)
    for (a_, b_, runs) in T2.HEADS: pl(FA.chime(), a_, -22)
    for c in T.CUTS:
        if c < T.E - 0.1 and [s[5] for s in T.SEGS if abs(s[0] - c) < 1e-6][0] != 'b5x': pl(swell(0.5), c - 0.25, -20)
    pl(swell(1.4), T.E - 0.7, -14); pl(FA.chime(), T.E + 0.55, -12); pl(FA.chime(), T.E + 1.5, -16)
    mix = vo + fx
    mix *= np.clip((T.END - t) / 0.5, 0, 1)[:, None] ** 0.6
    raw = os.path.join(HERE, 'teaser2_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9,alimiter=limit=0.89:level=false',
                    '-ar', '48000', '-c:a', 'pcm_s16le', os.path.join(HERE, 'teaser2_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
