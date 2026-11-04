# Fit the chosen VO (Magnific / ElevenLabs v4, voice "Gavin", audio/vo_final.mp3, 32.9 s) into the 32 s reel:
# speed it up 8 % (pitch kept), cut it into its phrases at the quiet points between them and lay them out with small
# pauses, plus room for the lights & music jingle after "...loud music" and for the zoom after "...watch it race".
# Line 6 is replaced (client: the car comes in one colour only) by audio/vo_line5_cool_style.mp3, same voice,
# "Cool style, bold looks... built to race!", gain-matched to the line it replaces.
# -> audio/vo_timed.wav (48 kHz mono) + audio/vo_timing.json (phrases with word times on the reel clock)
import os, json, subprocess, numpy as np, soundfile as sf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'audio', *p)
SR, TEMPO, DUR, START = 48000, 1.08, 32.0, 0.10
FIRST = ['On', 'Say', 'Give', 'Press', '4', 'Cool', 'A', '36', 'Distributors', 'Fun']     # first word of each phrase
GAP = [0.0, 0.22, 0.22, 0.42, 0.50, 0.26, 0.30, 0.22, 0.22, 0.28]                          # pause before each phrase

src = subprocess.run(['ffmpeg', '-v', 'error', '-i', A('vo_final.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x0 = np.frombuffer(src, np.float32)
words = [(s, e, w.strip()) for s, e, w in json.load(open(A('vo_words_src.json')))]
idx, fi = [], 0
for i, (s, e, w) in enumerate(words):
    if fi < len(FIRST) and w == FIRST[fi]: idx.append(i); fi += 1
assert fi == len(FIRST), fi
# quiet points between phrases, on the source clock (10 ms energy)
h = SR // 100; env = 20 * np.log10(np.sqrt(np.convolve(x0 ** 2, np.ones(h) / h, 'same')[::h]) + 1e-7)
THR = np.percentile(env[env > -80], 90) - 30                     # quiet = 30 dB under the speech level
def quiet(a, b):
    """longest run under THR between a and b (s); falls back to the single quietest point"""
    i0, i1 = int(a * 100), int(b * 100); q = env[i0:i1] < THR; best, cur, st = (0, 0, 0), 0, 0
    for i, v in enumerate(q):
        if v:
            if cur == 0: st = i
            cur += 1
            if cur > best[0]: best = (cur, st, i)
        else: cur = 0
    if best[0] == 0: m = i0 + int(np.argmin(env[i0:i1])); return m / 100, m / 100
    return (i0 + best[1]) / 100, (i0 + best[2]) / 100
bounds = [0.0]
for k in range(1, len(idx)):
    a = words[idx[k] - 1][0] + 0.15; b = words[idx[k]][0] + 0.05
    lo, hi = quiet(a, b); bounds += [lo + 0.03, hi - 0.03]
bounds.append(len(x0) / SR - 0.05)
spans = [(bounds[2 * k], bounds[2 * k + 1]) for k in range(len(idx))]

def stretched(name):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', A(name), '-af', f'rubberband=tempo={TEMPO}:pitchq=quality:transients=smooth',
                          '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)
x = stretched('vo_final.mp3')
REPL = 5                                                          # phrase index replaced by the new line
x5 = stretched('vo_line5_cool_style.mp3'); w5 = [(s, e, w.strip()) for s, e, w in json.load(open(A('vo_line5_words.json')))]
def speech_rms(v): v = v[np.abs(v) > 0.01]; return np.sqrt((v ** 2).mean())
out = np.zeros(int(DUR * SR), np.float32); t = START; info = []; fade = int(0.008 * SR)
for k, (s0, s1) in enumerate(spans):
    t += GAP[k]
    a, b = int(s0 / TEMPO * SR), int(s1 / TEMPO * SR)
    seg = x[a:b].copy()
    if k == REPL:
        ref = seg; s0 = max(0.0, w5[0][0] - 0.06); s1 = w5[-1][1] + 0.18
        seg = x5[int(s0 / TEMPO * SR):int(s1 / TEMPO * SR)].copy(); seg *= speech_rms(ref) / speech_rms(seg)
    seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    i = int(t * SR); out[i:i + len(seg)] += seg[:len(out) - i]
    w_end = idx[k + 1] if k + 1 < len(idx) else len(words)
    src_w = w5 if k == REPL else words[idx[k]:w_end]
    ws = [[round(t + max(0.0, ws_ - s0) / TEMPO, 3), w] for ws_, we, w in src_w]
    info.append({'start': round(t, 3), 'end': round(t + len(seg) / SR, 3), 'words': ws})
    t += len(seg) / SR
sf.write(A('vo_timed.wav'), out, SR, subtype='FLOAT')
json.dump(info, open(A('vo_timing.json'), 'w'), indent=1)
for p in info: print('%6.2f-%6.2f  %s' % (p['start'], p['end'], ' '.join(w for _, w in p['words'])))
