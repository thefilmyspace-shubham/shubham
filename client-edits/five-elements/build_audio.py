"""Lay the AI voice lines (vo/waiter_raw.mp3, vo/guest_raw.mp3) on the timeline and write the lip-sync envelope.
   timeline.json 'voice' rows: [file, clip_in, clip_out, place_at].   python3 build_audio.py"""
import json, os, subprocess, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); SR = 48000
tl = json.load(open(f'{HERE}/timeline.json')); total = tl['total']
os.makedirs(f'{HERE}/build', exist_ok=True)
def load(f):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f'{HERE}/vo/{f}_raw.mp3', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768
src = {f: load(f) for f in {v[0] for v in tl['voice']}}
mix = np.zeros(int(total * SR))
for f, a, b, at in tl['voice']:
    c = src[f][int(max(0, a - 0.04) * SR):int((b + 0.10) * SR)].copy()
    c *= 0.5 / (np.sqrt(np.mean(c[np.abs(c) > 0.01] ** 2)) * 4.0)          # level each line to the same loudness
    n = int(0.03 * SR); c[:n] *= np.linspace(0, 1, n); c[-2 * n:] *= np.linspace(1, 0, 2 * n)
    i = int((at - 0.04) * SR); mix[i:i + len(c)] += c[:len(mix) - i]
mix = np.tanh(mix * 1.6) / 1.6 * 1.5
voice = mix.copy()
if tl.get('music'):                                                      # music bed, ducked under the voices
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f"{HERE}/music/{tl['music']}.mp3", '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    m = np.frombuffer(raw, dtype=np.int16).astype(np.float64)[:len(mix)] / 32768
    m *= 0.125 / np.sqrt(np.mean(m ** 2))
    k = SR // 4; act = np.convolve((np.abs(voice) > 0.02).astype(float), np.ones(k) / k, 'same')
    act = np.convolve(np.clip(act * 6, 0, 1), np.ones(k) / k, 'same')    # 0 = no speech, 1 = speech
    g = 0.85 - 0.60 * act
    t = np.arange(len(m)) / SR; g *= np.clip(t / 0.4, 0, 1) * np.clip((total - t) / 1.5, 0, 1)
    mix = mix + m * g
w = wave.open(f'{HERE}/build/audio.wav', 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
hop = SR // 60; win = hop * 3
e = np.array([np.sqrt(np.mean(voice[max(0, i - win // 2):i + win // 2] ** 2) + 1e-9) for i in range(0, len(voice), hop)])
env = np.clip((20 * np.log10(e) + 34) / 16, 0, 1)
json.dump({'total': total, 'env': [round(float(v), 2) for v in env]}, open(f'{HERE}/build/env.json', 'w'))
print('duration', total)
