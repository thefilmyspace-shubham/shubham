"""Teaser v3 audio: only the opening line + soft SFX. Daydream is added on Instagram (start at the first lyric)."""
import os, subprocess, wave, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'film'))
import film_audio as FA
import teaser3 as T3
import teaser2 as T2
from teaser_audio import bite
from teaser2_audio import swell

SR = FA.SR; N = int(T3.T.END * SR)
def main():
    t = np.arange(N) / SR
    vo = np.zeros((N, 2), np.float32)
    FA.place(vo, bite(*T3.HOOK), 0.0)
    vo *= FA.db(-1.5) / (np.abs(vo).max() + 1e-9)
    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: FA.place(fx, clip, tt, gd)
    for (a_, b_, runs) in T2.HEADS: pl(FA.chime(), a_, -22)
    for c in T3.CUTS:
        if c < T3.E - 0.1: pl(swell(0.5), c - 0.25, -22)
    pl(swell(1.4), T3.E - 0.7, -15); pl(FA.chime(), T3.E + 0.55, -13); pl(FA.chime(), T3.E + 1.5, -17)
    mix = vo + fx
    mix *= np.clip((T3.T.END - t) / 0.5, 0, 1)[:, None] ** 0.6
    raw = os.path.join(HERE, 'teaser3_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.89:level=false',
                    '-ar', '48000', '-c:a', 'pcm_s16le', os.path.join(HERE, 'teaser3_mix.wav')], check=True)
    print('ok')
if __name__ == '__main__':
    main()
