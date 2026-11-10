# Fit the chosen VO (Magnific / ElevenLabs v4, voice "Gavin", sample 1, audio/vo_final.mp3, 36.7 s) into the reel:
# speed it up 8 % (pitch kept), cut it into its 9 lines at the quiet points between them and lay them out with pauses
# sized for the story -- the shutter before line 1, the kids walking past after it, the dino roar after line 4.
# -> audio/vo_timed.wav (48 kHz mono) + audio/vo_timing.json (phrases with word times on the reel clock)
import os, json, subprocess, numpy as np, soundfile as sf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'audio', *p)
SR, TEMPO, DUR = 48000, 1.08, 37.5
FIRST = ['Morning', 'Then', '12', 'One', 'Kids', 'Four', '192', 'Distributors', 'Fun']     # first word of each line
GAP = [0.55, 0.60, 0.35, 0.30, 0.60, 0.30, 0.30, 0.30, 0.35]                               # pause before each line
src = subprocess.run(['ffmpeg', '-v', 'error', '-i', A('vo_final.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x0 = np.frombuffer(src, np.float32)
words = [(s, e, w.strip()) for s, e, w in json.load(open(A('vo_words_src.json')))]
idx, fi = [], 0
for i, (s, e, w) in enumerate(words):
    if fi < len(FIRST) and w == FIRST[fi]: idx.append(i); fi += 1
assert fi == len(FIRST), fi
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
    pw, cw = words[idx[k] - 1], words[idx[k]]                     # look for the pause up to 0.4 s past the previous word's end
    lo, hi = quiet(pw[0] + 0.15, max(cw[0] + 0.05, pw[1] + 0.40)); bounds += [lo + 0.03, hi - 0.03]   # (whisper can run "turn" into "and")
bounds.append(len(x0) / SR - 0.05)
spans = [(bounds[2 * k], bounds[2 * k + 1]) for k in range(len(idx))]
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', A('vo_final.mp3'), '-af', f'rubberband=tempo={TEMPO}:pitchq=quality:transients=smooth',
                      '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
out = np.zeros(int(DUR * SR), np.float32); t = 0.0; info = []; fade = int(0.008 * SR)
for k, (s0, s1) in enumerate(spans):
    t += GAP[k]
    seg = x[int(s0 / TEMPO * SR):int(s1 / TEMPO * SR)].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    i = int(t * SR); out[i:i + len(seg)] += seg[:len(out) - i]
    w_end = idx[k + 1] if k + 1 < len(idx) else len(words)
    ws = [[round(t + max(0.0, ws_ - s0) / TEMPO, 3), w] for ws_, we, w in words[idx[k]:w_end]]
    info.append({'start': round(t, 3), 'end': round(t + len(seg) / SR, 3), 'words': ws})
    t += len(seg) / SR
sf.write(A('vo_timed.wav'), out, SR, subtype='FLOAT')
json.dump(info, open(A('vo_timing.json'), 'w'), indent=1)
for p in info: print('%6.2f-%6.2f  %s' % (p['start'], p['end'], ' '.join(w for _, w in p['words'])))
