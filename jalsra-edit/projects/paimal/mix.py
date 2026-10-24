#!/usr/bin/env python3
"""Audio for the Paimal reel, in timeline time: cut dialogue, music bed (beat-aligned jump so the groove runs to the last
line, final hit right after "जय भारत"), and SFX on every B-roll move (whoosh in, paper landing, highlighter, marker).

  python3 projects/paimal/mix.py  -> projects/paimal/audio/mix.wav
"""
import json, os, subprocess, sys, wave
import numpy as np
D = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(D, '../..'))
sys.path.insert(0, ROOT)
from docu import Timeline, Broll, Font, path

SR = 48000
BEAT = 60 / 99.384; BEAT0 = 0.12; BAR = 4 * BEAT


def load(f, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path(f), '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def db(x): return 10 ** (x / 20)


def place(buf, clip, t):
    i = int(round(t * SR))
    if i < 0: clip, i = clip[-i:], 0
    n = min(len(clip), len(buf) - i)
    if n > 0: buf[i:i + n] += clip[:n]


def peak_time(clip):
    e = np.convolve(np.abs(clip), np.ones(480) / 480, 'same'); return int(np.argmax(e)) / SR


def sub_boom(dur=1.4, seed=7):
    """original cinematic impact: pitch-dropping sub sine + short filtered noise transient"""
    t = np.arange(int(dur * SR)) / SR
    f = 34 + 46 * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 3.2) * (1 - np.exp(-t * 400))
    r = np.random.default_rng(seed); n = r.normal(0, 1, len(t)) * np.exp(-t * 38)
    n = np.convolve(n, np.ones(24) / 24, 'same')
    y = 0.9 * body + 0.35 * n
    return (y / np.abs(y).max() * 0.9).astype(np.float32)


def main():
    e = json.load(open(os.path.join(D, 'edl.json')))
    tl = Timeline(e['segments'])
    fonts = {'label': Font('fonts/Khand-SemiBold.ttf', 44)}
    brolls = [Broll(b, tl, fonts) for b in e['brolls']]
    end_black = e.get('tail', 2.6)
    total = tl.dur + end_black
    N = int(total * SR) + SR

    # ---- dialogue along the cut list (5 ms fades at every join; joins sit in pauses)
    dia_src = load(e['dialogue'])
    dia = np.zeros(N, np.float32); f = int(0.005 * SR)
    for s in tl.segs:
        seg = dia_src[int(s['src0'] * SR):int(s['src1'] * SR)].copy()
        seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        place(dia, seg, s['t0'])
    # gentle broadcast chain: high-pass, compression
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-af',
                        'highpass=f=75,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=140:makeup=3dB,'
                        'alimiter=limit=0.89:level=false', '-f', 'f32le', '-'], input=dia.tobytes(), capture_output=True, check=True)
    dia = np.frombuffer(p.stdout, np.float32).copy()[:N]
    dia = np.pad(dia, (0, N - len(dia)))

    # ---- music
    mus = load(e['music']['file'])
    last_word_src = 167.45
    t_last = tl.tl(last_word_src)          # end of "जय भारत"
    hit_at = t_last + 0.12
    m0 = 0.6                                 # drop (music 33.6 s) lands with B-roll 4a
    jump = 9 * BAR                           # whole bars keep the beat phase
    tj_target = brolls[8].t0                 # hide the jump under the tax B-roll whoosh
    k = round((tj_target + m0 - BEAT0) / BEAT); tj = BEAT0 + k * BEAT - m0
    bed = np.zeros(N, np.float32)
    a = mus[int(m0 * SR):int((tj + m0) * SR)]
    b = mus[int((tj + m0 + jump) * SR):]
    xf = int(0.03 * SR)
    a = a.copy(); a[-xf:] *= np.linspace(1, 0, xf)
    b = b.copy(); b[:xf] *= np.linspace(0, 1, xf)
    place(bed, a, 0.0); place(bed, b, tj - xf / SR)
    cut = int(hit_at * SR); fo = int(0.06 * SR)
    bed[cut:cut + fo] *= np.linspace(1, 0, fo); bed[cut + fo:] = 0
    tail = mus[int(171.45 * SR):]  # final hit + decay
    tail = tail * np.linspace(1, 1, len(tail)); place(bed, tail, hit_at - (peak_time(tail[:SR]) - 0.0))
    # ducking: music sits under the voice, lifts a little when nobody speaks
    env = np.convolve(np.abs(dia), np.ones(2400) / 2400, 'same')
    speaking = (env > db(-42)).astype(np.float32)
    k_att = np.ones(int(0.6 * SR)) / int(0.6 * SR)  # only real gaps lift the music, not the tail of a word
    speaking = np.clip(np.convolve(speaking, k_att, 'same') * 2.0, 0, 1)
    gain_db = -23.5 + 3.5 * (1 - speaking)
    drop_t = 33.6 - m0  # the intro is ~12 dB quieter in the track itself; lift it but keep the build into the drop
    tt = np.arange(N) / SR
    gain_db += 7.0 * np.clip((drop_t + 0.4 - tt) / 0.8, 0, 1)
    for b_ in brolls:  # a touch more energy under B-roll
        i0, i1 = int(b_.t0 * SR), int(b_.t1 * SR); gain_db[i0:i1] += 1.5
    gain_db[int(hit_at * SR):] = -13.0
    bed *= db(gain_db).astype(np.float32)

    # ---- SFX
    sfx = np.zeros(N, np.float32)
    def clip(name, rev=False, rate=1.0):
        c = load('sfx/' + name)
        if rate != 1.0:
            idx = np.arange(0, len(c) - 1, rate); c = np.interp(idx, np.arange(len(c)), c).astype(np.float32)
        return c[::-1].copy() if rev else c
    whooshes = [clip(n) for n in ('whoosh_1.mp3', 'whoosh_2.mp3', 'whoosh_3.mp3')]
    paper = clip('paper_slide_1.mp3'); hl = clip('highlighter_1.mp3')
    marker = clip('marker_1.mp3') if os.path.exists(path('sfx/marker_1.mp3')) else clip('highlighter_1.mp3', rate=1.25)
    boom = sub_boom()
    for i, b_ in enumerate(brolls):
        w = whooshes[i % 3]; place(sfx, w * db(-13), b_.t0 + 0.04 - peak_time(w))
        wr = whooshes[(i + 1) % 3][::-1].copy(); place(sfx, wr * db(-28), b_.t1 + 0.08 - peak_time(wr))  # soft, after the cut
        for pc in b_.pieces:
            place(sfx, paper * db(-10), b_.t0 + pc.t_in - 0.06)
            seen = set()
            for h in pc.hls:
                if any(abs(h['t'] - s) < 0.6 for s in seen): continue
                seen.add(h['t']); place(sfx, hl * db(-12), b_.t0 + h['t'] - 0.02)
            for c in pc.circles:
                place(sfx, marker * db(-11), b_.t0 + c['t'] - 0.02)
        # camera whips
        for kk in b_.cam[1:]:
            if kk[0] > 0.3:
                place(sfx, whooshes[(i + 2) % 3] * db(-24), b_.t0 + kk[0] + kk[4] * 0.5 - peak_time(whooshes[(i + 2) % 3]))
    for s_ in e.get('sfx_emphasis', []):
        t = tl.tl(s_); place(sfx, boom * db(-9), t)

    for nm, st in (('dia', dia), ('bed', bed), ('sfx', sfx)):  # stems for level checks
        with wave.open(os.path.join(D, 'audio', f'stem_{nm}.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((np.clip(st[:int(total * SR)], -1, 1) * 32767).astype('<i2').tobytes())
    mix = dia * db(0) + bed + sfx
    mix[int((tl.dur + end_black) * SR):] = 0
    mix = mix[:int((tl.dur + end_black) * SR)]
    out = os.path.join(D, 'audio', 'mix_pre.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix / max(1.0, np.abs(mix).max() / 0.95), -1, 1) * 32767).astype('<i2').tobytes())
    fin = os.path.join(D, 'audio', 'mix.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-ar', str(SR), '-ac', '2', fin], check=True)
    print(f'wrote {fin}: {len(mix) / SR:.2f}s, music jump at {tj:.2f}s, final hit at {hit_at:.2f}s')


if __name__ == '__main__':
    main()
