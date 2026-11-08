"""Jalsara Diwali reel audio: the presenter's own voice from each A-roll line, level-matched and cleaned,
plus a few soft SFX (swells at line changes, chimes on the end card). No music bed: add a festive track on Instagram
at a low volume (about 10-15%) under the voice.
  python3 diwali_audio.py      -> diwali_mix.wav (48 kHz, about -14 LUFS)
"""
import os, subprocess, sys, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diwali as D
sys.path.insert(0, os.path.join(D.REPO, 'tfs-promo', 'film'))
import film_audio as FA

SR = FA.SR; N = int(D.END * SR)
def load(path, ss, dur):
    pcm = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{ss:.3f}', '-t', f'{dur:.3f}', '-i', path, '-ac', '1', '-ar', str(SR),
                          '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(pcm, np.float32).copy()
def swell(d=1.2):
    n = int(d * SR); t = np.arange(n) / SR
    x = FA.onepole(FA.rng.standard_normal(n), 900 + 2500 * (t / d)) * np.sin(np.pi * t / d) ** 2
    return FA.st(x / (np.abs(x).max() + 1e-9) * 0.35, 0.004)

def main():
    vo = np.zeros(N, np.float32)
    for key, f, a, b, _ in D.AROLL:
        x = load(os.path.join(D.SRC, f), a, b - a)
        fr = int(0.02 * SR)                                   # 20 ms in/out so every join is click-free
        x[:fr] *= np.linspace(0, 1, fr); x[-fr:] *= np.linspace(1, 0, fr)
        e = np.sqrt(np.convolve(x ** 2, np.ones(SR // 20) / (SR // 20), 'same'))
        voiced = e[e > np.percentile(e, 60)]                  # match the speaking level of every take
        x *= 0.1 / (np.sqrt(np.mean(voiced ** 2)) + 1e-9)
        i0 = int(D.LINES[key][0] * SR); vo[i0:i0 + len(x)] += x[:N - i0]
    raw_vo = os.path.join(HERE, 'vo_raw.wav')
    with wave.open(raw_vo, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(vo * 0.5, -1, 1) * 32767).astype('<i2').tobytes())
    clean = os.path.join(HERE, 'vo_clean.wav')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw_vo, '-af',
                    'highpass=f=85,afftdn=nf=-28,equalizer=f=250:t=q:w=1.2:g=-2,equalizer=f=3500:t=q:w=1.5:g=2,'
                    'acompressor=threshold=-22dB:ratio=3:attack=6:release=140:makeup=2',
                    '-ar', str(SR), '-ac', '1', clean], check=True)
    with wave.open(clean) as w:
        v = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32767
    v = np.pad(v, (0, max(0, N - len(v))))[:N]
    mix = np.stack([v, v], 1) * FA.db(-1.0) / (np.abs(v).max() + 1e-9)
    fx = np.zeros((N, 2), np.float32)
    pl = lambda clip, tt, gd: FA.place(fx, clip, tt, gd)
    pl(FA.chime(), 0.0, -24)
    for key, *_ in D.AROLL[1:]:
        pl(swell(0.6), D.LINES[key][0] - 0.3, -24)            # soft air at each new setup
    pl(swell(1.4), D.E - 0.7, -16); pl(FA.chime(), D.E + 0.5, -15); pl(FA.chime(), D.E + 1.5, -19)
    mix = mix + fx
    t = np.arange(N) / SR
    mix *= np.clip((D.END - t) / 0.5, 0, 1)[:, None] ** 0.6
    raw = os.path.join(HERE, 'diwali_mix_raw.wav')
    with wave.open(raw, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.89:level=false',
                    '-ar', '48000', '-c:a', 'pcm_s16le', os.path.join(HERE, 'diwali_mix.wav')], check=True)
    for p in (raw_vo, clean, raw): os.remove(p)
    print('ok')

if __name__ == '__main__':
    main()
