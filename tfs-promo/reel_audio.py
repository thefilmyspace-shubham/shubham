"""Audio for the vertical reel: music hits at 1.833s (like the reference), subtle SFX, no VO."""
import os, subprocess, wave
import numpy as np
import audio as A
from reel import T1, T2, T3, T4, T5, T6, T7, T8, END, CUTS, SERV

HERE = os.path.dirname(os.path.abspath(__file__))
SR = A.SR; N = int(END * SR)

def main():
    OFF = 13.867  # music time = video time + OFF  (drop lands on T1)
    mus = A.load(os.path.join(HERE, 'music', 'm132.mp3'), OFF + T1, OFF + END)
    music = np.zeros((N, 2), np.float32); A.place(music, mus, T1)
    t = np.arange(N) / SR
    env = np.clip((END - t) / 1.6, 0, 1) ** 1.5
    nf = int(0.008 * SR); i1 = int(T1 * SR); music[i1:i1 + nf] *= np.linspace(0, 1, nf)[:, None]
    music *= env[:, None] * A.db(-3)

    fx = np.zeros((N, 2), np.float32)
    for i in range(len('Hi there.')): A.place(fx, A.s_tick(2600, 0.02), 0.35 + i * 0.075, -20)
    for i in range(7): A.place(fx, A.s_pop(500, 1100, 0.05), T1 + 0.06 + i * 0.05, -22)
    W2 = A.sfx('whoosh2')
    for tt in (T2, T3, T4, T6): A.place(fx, W2, tt - 0.12, -18)
    for i in range(2): A.place(fx, A.s_tick(2600, 0.02), T4 + 0.05 + i * 0.06, -20)
    for i in range(13): A.place(fx, A.s_tick(2600, 0.02), T4 + 0.33 + i * 0.04, -22)
    for i in range(27): A.place(fx, A.s_tick(2600, 0.02), T4 + 1.35 + i * 0.035, -22)
    dt = (T6 - T5) / len(SERV)
    for i in range(len(SERV)): A.place(fx, A.s_tick(1700, 0.03), T5 + i * dt, -16)
    A.place(fx, A.sfx('impact2'), T8 + 0.15, -2)

    mix = music + fx
    mix = np.tanh(mix * 1.05) / 1.05
    raw = os.path.join(HERE, 'reel_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9', '-ar', '48000',
                    os.path.join(HERE, 'reel_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
