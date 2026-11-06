# The scooter's real sounds, from the client's raw clip 20261105_130920.mp4 (Drive, 5 Nov): the head is pressed down
# again and again while the toy is held in the hand -- each press spins the flywheel (a short gear whirr), and at
# 8.00-8.55 s and 9.60-10.20 s the wheels run free (the "go" whirr). Reference only: no footage of it is used.
# Each cut is denoised (noisereduce, stationary, profile = the quiet room tone at 0.10-1.00 s), band-limited,
# compressed and loudness-normalised. Writes audio/og_press_1..4.wav, audio/og_go.wav, og_go_2.wav (48 kHz mono).
# usage: python3 tools/og_sound.py <dir with 130920.mp4>
import os, sys, subprocess
import numpy as np, soundfile as sf, noisereduce as nr
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SRC = sys.argv[1]; SR = 48000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(SRC, '130920.mp4'), '-vn', '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).copy()
noise = x[int(0.10 * SR):int(1.00 * SR)]
CUTS = {'og_press_1': (1.12, 1.50), 'og_press_2': (1.72, 1.98), 'og_press_3': (2.12, 2.40), 'og_press_4': (2.48, 2.80),
        'og_go': (7.95, 8.60), 'og_go_2': (9.58, 10.25)}
for name, (s0, s1) in CUTS.items():
    seg = nr.reduce_noise(y=x[int(s0 * SR):int(s1 * SR)], sr=SR, y_noise=noise, stationary=True, prop_decrease=0.9)
    f = int(0.008 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
    tmp = os.path.join(ROOT, 'audio', name + '_nr.wav'); sf.write(tmp, seg.astype(np.float32), SR)
    out = os.path.join(ROOT, 'audio', name + '.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', 'highpass=f=150,lowpass=f=15000,equalizer=f=3000:t=q:w=1:g=2,'
                    'acompressor=threshold=-24dB:ratio=3:attack=3:release=80,loudnorm=I=-18:TP=-2:LRA=9', '-ar', str(SR), '-ac', '1', out], check=True)
    os.remove(tmp); print(out, round(len(seg) / SR, 2), 's')
