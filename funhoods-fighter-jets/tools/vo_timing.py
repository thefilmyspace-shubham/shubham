# The chosen VO (Magnific / ElevenLabs v4, voice "Callum Nathaniel Sinclair", audio/vo_final.mp3) fits the 30 s reel as is:
# it is only offset by 0.15 s. Writes audio/vo_timed.wav (48 kHz mono) and audio/vo_timing.json (phrases + word times on
# the reel clock), from the word timestamps in audio/vo_words_src.json (faster-whisper small.en).
import os, json, subprocess, numpy as np, soundfile as sf
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'audio', *p)
SR, OFF, DUR = 48000, 0.15, 30.0
FIRST = ['Ready', 'Six', 'Pull', 'A', 'BIS', 'Bright,', '144', 'Distributors', 'FunHoods,']   # first word of each phrase
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', A('vo_final.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
out = np.zeros(int(DUR * SR), np.float32); k = int(OFF * SR); out[k:k + len(x)] = x[:len(out) - k]
sf.write(A('vo_timed.wav'), out, SR, subtype='FLOAT')
words = [(round(s + OFF, 3), round(e + OFF, 3), w.strip()) for s, e, w in json.load(open(A('vo_words_src.json')))]
phrases, fi = [], 0
for s, e, w in words:
    if fi < len(FIRST) and w == FIRST[fi]:
        phrases.append({'start': s, 'end': e, 'words': []}); fi += 1
    phrases[-1]['words'].append([s, w]); phrases[-1]['end'] = e
assert fi == len(FIRST), fi
json.dump(phrases, open(A('vo_timing.json'), 'w'), indent=1)
for p in phrases: print('%6.2f-%6.2f  %s' % (p['start'], p['end'], ' '.join(w for _, w in p['words'])))
