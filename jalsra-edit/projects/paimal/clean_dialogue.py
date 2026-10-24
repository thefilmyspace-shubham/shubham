#!/usr/bin/env python3
"""Dialogue repair for the Paimal speech.

0-85.9 s was recorded on a clean (gated, mono) mic; from 85.9 s the file falls back to the camera mic: ~17 dB quieter,
distant and hissy. This script denoises the camera part (or takes an already-isolated version), matches its tone to the
clean part with a long-term-spectrum EQ, matches its level, and writes one source-time dialogue track.

  python3 clean_dialogue.py [--isolated audio/part2_isolated.wav]   -> audio/dialogue_clean.wav (48 kHz mono)
"""
import argparse, os, subprocess, wave
import numpy as np
from scipy.signal import fftconvolve, firwin2

D = os.path.dirname(os.path.abspath(__file__))
SR = 48000
SPLIT = 85.90


def load(f, ss=None):
    cmd = ['ffmpeg', '-v', 'error'] + (['-ss', str(ss)] if ss else []) + ['-i', f, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).copy()


def frames_db(y, hop=480):
    n = len(y) // hop
    return 20 * np.log10(np.sqrt((y[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)


def voiced(y, top_db=18):
    """samples of the loudest (speech) frames only"""
    hop = 480; db = frames_db(y, hop); thr = np.percentile(db, 95) - top_db
    idx = np.where(db > thr)[0]
    return np.concatenate([y[i * hop:(i + 1) * hop] for i in idx])


def ltas(y, n=4096):
    win = np.hanning(n); hop = n // 2; acc = np.zeros(n // 2 + 1)
    k = 0
    for i in range(0, len(y) - n, hop):
        acc += np.abs(np.fft.rfft(y[i:i + n] * win)) ** 2; k += 1
    return 10 * np.log10(acc / max(k, 1) + 1e-12)


def smooth_oct(f, v, frac=3):
    out = np.empty_like(v)
    for i, fc in enumerate(f):
        if fc <= 0: out[i] = v[i]; continue
        lo, hi = fc * 2 ** (-0.5 / frac), fc * 2 ** (0.5 / frac)
        m = (f >= lo) & (f <= hi); out[i] = v[m].mean()
    return out


def match_eq(src, ref, max_db=12):
    f = np.fft.rfftfreq(4096, 1 / SR)
    diff = smooth_oct(f, ltas(voiced(ref)) - ltas(voiced(src)))
    band = (f >= 90) & (f <= 9000)
    diff -= np.median(diff[band])  # tone only; level is matched separately
    diff = np.clip(diff, -max_db, max_db)
    diff[f < 70] = np.minimum(diff[f < 70], 0); diff[f > 12000] = np.minimum(diff[f > 12000], diff[np.searchsorted(f, 12000)])
    gain = 10 ** (diff / 20)
    taps = firwin2(2047, f / (SR / 2), gain)
    return fftconvolve(src, taps, mode='same'), diff, f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--isolated', default=None)
    ap.add_argument('--rnn', default='../../models/rnnoise/cb.rnnn', help='RNNoise model for ffmpeg arnndn ("" = noisereduce)')
    a = ap.parse_args()
    full = load(os.path.join(D, '../../footage/paimal_audio.wav'))
    p1, p2raw = full[:int(SPLIT * SR)], full[int(SPLIT * SR):]
    if a.isolated:
        p2 = load(os.path.join(D, a.isolated))[:len(p2raw)]
    elif a.rnn:
        src = os.path.join(D, 'audio', 'part2_cam_raw.wav')
        if not os.path.exists(src):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(SPLIT), '-i', os.path.join(D, '../../footage/paimal_audio.wav'),
                            '-ac', '1', '-ar', str(SR), src], check=True)
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-af', f'highpass=f=80,arnndn=m={os.path.join(D, a.rnn)}:mix=1',
                              '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
        p2 = np.frombuffer(raw, np.float32).copy()[:len(p2raw)]
    else:
        import noisereduce as nr
        db = frames_db(p2raw); hop = 480
        quiet = np.where(db < np.percentile(db, 12))[0]
        noise = np.concatenate([p2raw[i * hop:(i + 1) * hop] for i in quiet])
        p2 = nr.reduce_noise(y=p2raw, sr=SR, y_noise=noise, stationary=True, prop_decrease=0.9, n_fft=2048)
        p2 = nr.reduce_noise(y=p2, sr=SR, stationary=False, prop_decrease=0.5, n_fft=2048)
    p2, diff, f = match_eq(p2, p1)
    for fc in (100, 200, 400, 800, 1600, 3200, 6400, 10000):
        print(f'  EQ {fc:5d} Hz {diff[np.searchsorted(f, fc)]:+5.1f} dB')
    g = np.sqrt((voiced(p1) ** 2).mean() / ((voiced(p2) ** 2).mean() + 1e-12))
    print(f'  level match {20 * np.log10(g):+.1f} dB')
    p2 = p2 * g
    # expander on the repaired part: pull residual noise down between words (part 1 is gated to silence)
    hop = 480; db = frames_db(p2, hop); thr = np.percentile(db, 95) - 30
    gate = np.clip((db - thr) / 10, 0, 1) ** 1.5
    gate = np.maximum(0.12, np.convolve(gate, np.ones(9) / 9, 'same'))
    env = np.repeat(gate, hop)[:len(p2)]; env = np.pad(env, (0, len(p2) - len(env)), constant_values=env[-1])
    p2 = p2 * env
    xf = int(0.02 * SR)
    p1[-xf:] *= np.linspace(1, 0, xf); p2[:xf] *= np.linspace(0, 1, xf)
    y = np.concatenate([p1, p2])
    pk = np.abs(y).max(); y = y / pk * 0.89 if pk > 0.89 else y
    out = os.path.join(D, 'audio', 'dialogue_clean.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype('<i2').tobytes())
    print('wrote', out, f'{len(y) / SR:.2f}s')


if __name__ == '__main__':
    main()
