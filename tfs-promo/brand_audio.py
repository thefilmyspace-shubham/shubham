"""Audio for the TFS brand reel: ElevenLabs VO + Mixkit 'Remember Me' + SFX."""
import os, subprocess, wave
import numpy as np
import audio as A
from brand_reel import B, END, VO_OFF, V

HERE = os.path.dirname(os.path.abspath(__file__))
SR = A.SR; N = int(END * SR)

def main():
    MOFF = 4.5  # music time = video time + MOFF (track's full beat lands on "The answer")
    mus = A.load(os.path.join(HERE, 'music', 'm739.mp3'), MOFF, MOFF + END)
    music = np.zeros((N, 2), np.float32); A.place(music, mus, 0.0)
    vo_src = A.load(os.path.join(os.path.dirname(HERE), 'tfs2', 'TFS_brand_reel_VO.mp3'))
    vo = np.zeros((N, 2), np.float32); A.place(vo, vo_src, VO_OFF)
    vo *= A.db(-2) / (np.abs(vo).max() + 1e-9)
    t = np.arange(N) / SR
    g = np.where(t < 39.9, A.db(-15), A.db(-7))
    ramp = (t >= 39.9) & (t < 40.3); g[ramp] = A.db(-15) + (A.db(-7) - A.db(-15)) * (t[ramp] - 39.9) / 0.4
    g *= np.clip((END - t) / 1.8, 0, 1) ** 1.5
    g *= np.clip(t / 0.4, 0, 1)
    music *= g[:, None]

    fx = np.zeros((N, 2), np.float32)
    W2, I2, I3, I4, SH = A.sfx('whoosh2'), A.sfx('impact2'), A.sfx('impact3'), A.sfx('impact4'), A.sfx('shutter1')
    pl = lambda clip, tt, gd: A.place(fx, clip, tt, gd)
    pl(W2, 0.0, -16); pl(W2, V(1.06) - 0.1, -12)
    for b in B[1:16]: pl(W2, b - 0.12, -18)
    pl(A.s_thump(), V(2.64), -6); pl(A.s_tick(1800, 0.03), V(3.58), -16)
    for tt in (3.95, 4.10): pl(A.s_pop(), tt, -16)
    pl(W2, V(4.92), -16)
    for tt in (6.6, 6.75, 6.9): pl(A.s_pop(500, 1000, 0.06), tt, -20)
    pl(I2, V(7.0), -6)
    pl(W2, V(8.66) - 0.1, -12)
    pl(A.s_pop(), V(10.02), -10); pl(A.s_pop(), V(12.08), -10)
    pl(A.sfx('scroll1'), V(13.4), +6); pl(A.sfx('scroll2'), V(14.9), +6)
    pl(I3, V(15.72) - 0.05, -4)
    pl(A.s_pop(), V(18.24), -12); pl(A.s_tick(2200, 0.03), V(18.24) + 0.6, -12)
    for k in range(6): pl(A.s_tick(1500 + 100 * k, 0.03), B[9] + k * 0.05, -18)
    pl(W2, V(19.24) - 0.1, -12); pl(W2, V(19.56) - 0.1, -12)
    pl(W2, V(20.54) - 0.1, -12); pl(I4, V(22.61), +2)
    pl(A.s_pop(400, 800, 0.08), B[11], -12)
    for wd, tw in [('Every', 23.59), ('brand', 23.82), ('needs', 24.12), ('a', 24.38), ('creative', 24.52), ('partner', 24.82), ('that', 25.24),
                   ('knows', 25.48), ('exactly', 25.72), ('how', 26.44), ('to', 26.72), ('make', 26.82), ('it', 26.98), ('seen.', 27.12)]:
        pl(A.s_typing(0.04 + 0.05 * len(wd) / 2), V(tw), -16)
    pl(A.s_thump(), V(28.90), -4)
    for tt in (B[13], V(30.0) - 0.05, V(30.5) - 0.05, V(31.35) - 0.05):
        pass
    for tt in (V(30.0) - 0.05, V(30.5) - 0.05, V(31.35) - 0.05):
        pl(SH, tt, -8); pl(A.s_thump(), tt, -8)
    for tt in (B[14], V(32.76 + 0.48) - 0.03, V(33.54 + 0.5) - 0.03, V(34.20 + 0.46) - 0.03):
        pl(W2, tt - 0.08, -10); pl(A.s_thump(), tt, -10)
    for tw in (35.51, 35.80, 36.10): pl(A.s_pop(), V(tw), -14)
    pl(A.sfx('whoosh3')[:int(2.0 * SR)], B[16] - 1.1, -8)
    pl(I3, B[16] + 0.15, -1); pl(A.s_thump(), B[16] + 0.15, -4)

    mix = music + vo + fx * A.db(-2)
    mix = np.tanh(mix * 1.05) / 1.05
    raw = os.path.join(HERE, 'brand_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9', '-ar', '48000',
                    os.path.join(HERE, 'brand_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
