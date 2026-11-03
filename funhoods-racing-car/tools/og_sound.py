# The toy's real sounds, from the client's two "working" phone clips in Drive (1 Nov):
#   20261101_120849.mp4 -- a hand pushes the car back and forth: friction / flywheel whirr (0.42-2.95 s), button clicks (3.28-3.70 s)
#   20261101_120922.mp4 -- the car's own built-in music that plays with the lights (5.70-14.90 s)
# Each cut is denoised (noisereduce, stationary, noise profile = the silent room tone at 15.40-16.30 s of 120922),
# band-limited, lightly compressed and loudness-normalised. Writes audio/og_*.wav (48 kHz mono).
# usage: python3 tools/og_sound.py <dir with 120849.mp4 and 120922.mp4>
import os, sys, subprocess
import numpy as np, soundfile as sf, noisereduce as nr
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = sys.argv[1]; SR = 48000
def load(name):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(SRC, name), '-vn', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()
a, b = load('120849.mp4'), load('120922.mp4')
noise = b[int(15.40 * SR):int(16.30 * SR)]
CUTS = {'og_friction_push': (a, 0.42, 2.95, 'highpass=f=70,lowpass=f=15000,equalizer=f=3000:t=q:w=1:g=2'),
        'og_button_click': (a, 3.28, 3.70, 'highpass=f=120,lowpass=f=15000'),
        'og_music': (b, 5.70, 14.90, 'highpass=f=150,lowpass=f=12000,equalizer=f=250:t=q:w=1:g=-3,equalizer=f=2500:t=q:w=1:g=2')}
for name, (x, s0, s1, eq) in CUTS.items():
    seg = x[int(s0 * SR):int(s1 * SR)]
    seg = nr.reduce_noise(y=seg, sr=SR, y_noise=noise, stationary=True, prop_decrease=0.9)
    f = int(0.01 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    tmp = os.path.join(ROOT, 'audio', name + '_nr.wav'); sf.write(tmp, seg.astype(np.float32), SR)
    out = os.path.join(ROOT, 'audio', name + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', eq + ',acompressor=threshold=-24dB:ratio=3:attack=5:release=120,loudnorm=I=-18:TP=-2:LRA=9',
                    '-ar', str(SR), '-ac', '1', out], check=True)
    os.remove(tmp); print(out, round(len(seg) / SR, 2), 's')
