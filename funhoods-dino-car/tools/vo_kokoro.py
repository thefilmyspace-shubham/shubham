import sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
D = sys.argv[1]; voice = sys.argv[2]; speed = float(sys.argv[3]); out = sys.argv[4]
k = Kokoro(f'{D}/kokoro-v1.0.onnx', f'{D}/voices-v1.0.bin')
LINES = [
 ("Funhoods presents... the Dino Monster Truck!", 0.12), ("Rawr!", 0.35),
 ("No batteries needed! Just push and go... zoom!", 0.35),
 ("It flips three sixty, climbs like a champ, and its dino mouth opens wide!", 0.3),
 ("Four fun colours! Blue, pink, green and yellow!", 0.3),
 ("B.I.S. approved, made of virgin polymer. Safe for little hands.", 0.3),
 ("Twelve per display box. It sells itself on the counter!", 0.3),
 ("One ninety-two pieces per carton, with pan India delivery.", 0.3),
 ("Distributors and wholesalers, place your bulk order today!", 0.35),
 ("Funhoods! Childhood Full of Fun!", 0.0)]
parts = []; sr = 24000
for txt, gap in LINES:
    a, sr = k.create(txt, voice=voice, speed=speed, lang='en-us')
    parts += [a, np.zeros(int(gap*0.8*sr), np.float32)]
y = np.concatenate(parts); sf.write(out, y, sr)
print(voice, round(len(y)/sr, 2), 's')
