"""Cut the original reel audio down to the short script and write the lip-sync envelope.
   python3 build_audio.py /path/to/reel.mp4"""
import json, os, subprocess, sys, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
src = sys.argv[1]
segs = json.load(open(f'{HERE}/timeline.json'))['segs']
FADE = 0.03
parts, labels = [], []
for i, (a, b) in enumerate(segs):
    d = b - a
    parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d={FADE},afade=t=out:st={d-FADE}:d={FADE}[s{i}]")
    labels.append(f"[s{i}]")
total = sum(b - a for a, b in segs)
fc = ';'.join(parts) + ';' + ''.join(labels) + f"concat=n={len(segs)}:v=0:a=1,apad=pad_dur=1.2,afade=t=out:st={total-0.6}:d=1.6[o]"
out = f'{HERE}/build/audio.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', fc, '-map', '[o]', '-ar', '48000', out], check=True)
# speech-band envelope, 60 samples per second
tmp = f'{HERE}/build/_sp.wav'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out, '-ac', '1', '-ar', '16000', '-af', 'highpass=f=300,lowpass=f=3400', tmp], check=True)
w = wave.open(tmp); y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
hop = 16000 // 60; win = hop * 3
e = np.array([np.sqrt(np.mean(y[max(0, i - win // 2):i + win // 2] ** 2) + 1e-9) for i in range(0, len(y), hop)])
db = 20 * np.log10(e)
env = np.clip((db + 26) / 14, 0, 1)
json.dump({'total': total + 1.2, 'env': [round(float(v), 2) for v in env]}, open(f'{HERE}/build/env.json', 'w'))
os.remove(tmp)
print('duration', total + 1.2)
