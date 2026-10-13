"""Audio for brand reel v2: reference music bed (separated) + VO placed per sentence + light SFX."""
import os, subprocess, wave
import numpy as np
import audio as A
from brand2 import SEG, END, B, T, find, WORDS

HERE = os.path.dirname(os.path.abspath(__file__))
SR = A.SR; N = int(END * SR)
MUSIC = os.path.join(os.path.dirname(HERE), 'ref2', 'sep', 'htdemucs', 'ref_audio', 'no_vocals.wav')
VO = os.path.join(os.path.dirname(HERE), 'tfs2', 'TFS_brand_reel_VO.mp3')

def seg_audio(a, b, tempo):
    af = f'atempo={tempo}' if abs(tempo - 1) > 1e-3 else 'anull'
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(a), '-t', str(b - a), '-i', VO, '-af', af, '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-']
    x = np.frombuffer(subprocess.run(cmd, capture_output=True).stdout, np.float32).reshape(-1, 2).copy()
    nf = int(0.01 * SR)
    if len(x) > 2 * nf: x[:nf] *= np.linspace(0, 1, nf)[:, None]; x[-nf:] *= np.linspace(1, 0, nf)[:, None]
    return x

def main():
    music = np.zeros((N, 2), np.float32); A.place(music, A.load(MUSIC), 0.0)
    vo = np.zeros((N, 2), np.float32)
    for a, b, v, tp in SEG:
        A.place(vo, seg_audio(a, b, tp), v)
    vo *= A.db(-2) / (np.abs(vo).max() + 1e-9)
    music *= A.db(-3)

    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: A.place(fx, clip, tt, gd)
    pl(A.s_pop(400, 900, 0.08), find('trust'), -14); pl(A.s_pop(400, 900, 0.08), find('followers.'), -14)
    pl(A.s_pop(500, 1100, 0.06), find('posts.'), -16)
    pl(A.s_tick(2200, 0.03), find('plan,') + 0.55, -14)
    for a, b, w_ in WORDS:
        if 23.4 <= a <= 27.5:
            for k in range(len(w_)): pl(A.s_tick(2600 + 200 * (k % 3), 0.015), T(a) + k * 0.035, -24)
    for tk in (B[14], find('creates', 29.0) - 0.06, find('delivers', 29.0) - 0.06):
        pl(A.sfx('shutter1'), tk, -12)
    for key in ('the', 'filmy', 'space'): pl(A.s_pop(), find(key, 34.5), -18)
    pl(A.sfx('impact3'), B[16], -6)

    mix = music + vo + fx
    t = np.arange(N) / SR
    mix *= np.clip((END - t) / 0.6, 0, 1)[:, None] ** 0.5
    mix = np.tanh(mix * 1.05) / 1.05
    raw = os.path.join(HERE, 'b2_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.0:LRA=9', '-ar', '48000',
                    os.path.join(HERE, 'b2_mix.wav')], check=True)
    print('ok')

if __name__ == '__main__':
    main()
