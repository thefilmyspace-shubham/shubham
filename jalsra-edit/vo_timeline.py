#!/usr/bin/env python3
"""Cut a full voice-over take into script lines and lay them on the script's timestamps.

  python3 vo_timeline.py take.mp3 take.words.json out_prefix --tempo 1.12 --starts 10,16,22,27,30,38 --total 45

Lines are found from the word list (first words of each line given with --firsts); long silences inside a line are
shortened, an optional pitch-preserving tempo is applied, and each line starts at its script time (or a little earlier
when the previous gap allows) so it ends before the next line's slot.
"""
import argparse, json, subprocess, wave
import numpy as np
SR = 48000

def load(f):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def env(y, win=0.01):
    n = int(SR * win); return np.sqrt(np.convolve(y ** 2, np.ones(n) / n, 'same'))

def tighten(y, max_pause, keep):
    """shorten silent runs longer than max_pause to `keep` seconds"""
    e = env(y); q = e < 0.008; out = []; i = 0; n = len(y)
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]: j += 1
            run = j - i
            out.append(y[i:j] if run <= max_pause * SR else np.concatenate([y[i:i + int(keep * SR / 2)], y[j - int(keep * SR / 2):j]]))
            i = j
        else:
            j = i
            while j < n and not q[j]: j += 1
            out.append(y[i:j]); i = j
    return np.concatenate(out)

def tempo(y, f):
    if abs(f - 1) < 1e-3: return y
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af', f'atempo={f}',
                        '-f', 'f32le', '-'], input=y.tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, np.float32).copy()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('take'); ap.add_argument('words'); ap.add_argument('out')
    ap.add_argument('--firsts', default='This,The,A,And,Today,,This')
    ap.add_argument('--starts', default='10,16,22,27,30,38'); ap.add_argument('--total', type=float, default=45)
    ap.add_argument('--tempo', type=float, default=1.0); ap.add_argument('--max-pause', type=float, default=0.38)
    a = ap.parse_args()
    y = load(a.take); e = env(y)
    words = json.load(open(a.words))
    firsts = [w.strip(',') for w in a.firsts.split(',') if w.strip(',')]
    # line start word indices, in order
    idx, k = [], 0
    for fw in firsts:
        while k < len(words) and words[k][0].strip('.,!?…') != fw: k += 1
        idx.append(k); k += 1
    starts = [float(s) for s in a.starts.split(',')]
    lines = []
    for n, i0 in enumerate(idx):
        t0 = words[i0][1]; t1 = words[idx[n + 1]][1] if n + 1 < len(idx) else len(y) / SR
        s0, s1 = int(max(0, t0 - 0.06) * SR), int(t1 * SR)
        seg_e = e[s0:s1]; voiced = np.where(seg_e > 0.01)[0]
        end = s0 + (voiced[-1] if len(voiced) else len(seg_e)) + int(0.12 * SR)
        seg = y[s0:min(end, s1)]
        keep = 0.5 if '…' in ' '.join(w[0] for w in words[i0:(idx[n + 1] if n + 1 < len(idx) else len(words))]) or n == 3 else 0.3
        seg = tempo(tighten(seg, a.max_pause, keep), a.tempo)
        f = int(0.008 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        lines.append(seg)
    out = np.zeros(int(a.total * SR) + SR, np.float32); prev_end = 0.0; report = []
    for n, seg in enumerate(lines):
        d = len(seg) / SR
        nxt = starts[n + 1] if n + 1 < len(starts) else a.total
        st = max(prev_end + 0.3, min(starts[n], nxt - d - 0.15))
        i = int(st * SR); out[i:i + len(seg)] += seg
        prev_end = st + d
        report.append((n + 1, starts[n], round(st, 2), round(prev_end, 2), round(d, 2)))
    end = max(a.total, prev_end + 0.5); out = out[:int(end * SR)]
    pk = np.abs(out).max(); out = out / pk * 10 ** (-1.5 / 20) if pk > 0 else out
    pcm = (out * 32767).astype('<i2')
    with wave.open(a.out + '.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.out + '.wav', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
                    '-ar', '48000', '-c:a', 'libmp3lame', '-b:a', '320k', a.out + '.mp3'], check=True)
    for r in report: print('line %d  script %4.1fs -> placed %5.2f-%5.2f  (%.2fs)' % r)

if __name__ == '__main__':
    main()
