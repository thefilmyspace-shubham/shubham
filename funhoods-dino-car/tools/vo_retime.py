# Re-time the client's ElevenLabs VO: speed it up 4.7 % (pitch kept), then lay the phrases out with room
# for the roar (after "The Dino Monster Truck!") and the zoom (after "just push and go.").
# -> audio/vo_timed.wav (48 kHz mono) + audio/vo_timing.json (phrase starts/ends, word times on the reel clock)
import os, json, subprocess, numpy as np, soundfile as sf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'audio', *p)
SR, TEMPO = 48000, 1.047
# (src start, src end, gap before) -- src times in the original file, cut in its silences
PH = [(0.00, 1.68, 0.25),   # The Dino Monster Truck!
      (1.92, 4.45, 0.75),   # No batteries needed, just push and go.      (roar in the gap)
      (4.78, 8.83, 0.80),   # It flips 360 degree and its dino mouth opens wide.   (zoom in the gap)
      (9.35, 10.43, 0.30),  # Four fun colours.
      (10.68, 12.60, 0.12), # Blue, pink, green and yellow.
      (13.05, 16.96, 0.30), # BIS approved, made of virgin polymer, safe for little hands.
      (17.37, 20.50, 0.30), # 12 per display box, it sells itself on the counter.
      (20.91, 24.34, 0.28), # 192 pieces per carton with pan India delivery.
      (24.75, 27.73, 0.28), # Distributors and wholesalers, place your bulk order today.
      (28.22, 30.45, 0.35)] # Funhoods, childhood full of fun.
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', A('vo_elevenlabs.mp3'), '-af', f'rubberband=tempo={TEMPO}:pitchq=quality:transients=smooth',
                      '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
words = json.load(open(A('vo_words_src.json')))
out = np.zeros(int(30.0 * SR), np.float32); t = 0.0; info = []
fade = int(0.008 * SR)
for i, (s0, s1, gap) in enumerate(PH):
    t += gap
    a, b = int(s0 / TEMPO * SR), int(s1 / TEMPO * SR)
    seg = x[a:b].copy(); seg[:fade] *= np.linspace(0, 1, fade); seg[-fade:] *= np.linspace(1, 0, fade)
    k = int(t * SR); out[k:k + len(seg)] += seg
    ws = [(round(t + (w0 - s0) / TEMPO, 3), w.strip()) for w0, w1, w in words if s0 - 0.15 <= w0 < s1 - 0.05]
    info.append({'start': round(t, 3), 'end': round(t + len(seg) / SR, 3), 'words': ws})
    t += len(seg) / SR
sf.write(A('vo_timed.wav'), out, SR, subtype='FLOAT')
json.dump(info, open(A('vo_timing.json'), 'w'), indent=1)
for p in info: print('%6.2f-%6.2f  %s' % (p['start'], p['end'], ' '.join(w for _, w in p['words'])))
