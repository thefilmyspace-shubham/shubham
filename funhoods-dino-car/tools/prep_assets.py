# Split the side-view cut-out into the parts the animation moves:
#   car_shell.png  -- dino head/body shell (lifts on its rear pivot = "mouth opens")
#   car_base.png   -- chassis, lower jaw and tyres
#   rim.png        -- one wheel rim disc (spins), cut from the rear wheel
# Sources (assets/src) are BiRefNet cut-outs of the client's 360° product mockup, Real-ESRGAN x4.
import os, json
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)

side = Image.open(A('src', 'side.png')).convert('RGBA')
w, h = side.size
# seam between the shell and the chassis / lower jaw, traced on the cut-out (left -> right)
SEAM = [(0, 840), (420, 842), (460, 875), (1060, 905), (1110, 895), (1170, 848), (1260, 802),
        (1430, 790), (1560, 772), (1700, 722), (1780, 690), (w, 680)]
m = Image.new('L', (w, h), 0)
ImageDraw.Draw(m).polygon([(0, 0), (w, 0)] + SEAM[::-1], fill=255)
a = np.asarray(side.getchannel('A')).astype(np.float32)
mk = np.asarray(m).astype(np.float32) / 255
shell, base = side.copy(), side.copy()
shell.putalpha(Image.fromarray((a * mk).astype(np.uint8)))
base.putalpha(Image.fromarray((a * (1 - mk)).astype(np.uint8)))
shell.save(A('car_shell.png')); base.save(A('car_base.png'))

HUBS = [(430, 1488), (1517, 1489)]; R = 232
x, y = HUBS[0]
rim = side.crop((x - R, y - R, x + R, y + R))
d = Image.new('L', (R * 8, R * 8), 0); ImageDraw.Draw(d).ellipse((0, 0, R * 8 - 1, R * 8 - 1), fill=255)
rim.putalpha(Image.fromarray((np.asarray(rim.getchannel('A')).astype(np.float32) *
                              np.asarray(d.resize((2 * R, 2 * R), Image.LANCZOS)).astype(np.float32) / 255).astype(np.uint8)))
rim.save(A('rim.png'))

for k in ('front', 'c_blue', 'c_pink', 'c_green', 'c_yellow'):
    Image.open(A('src', k + '.png')).save(A(k + '.png'))
json.dump({'size': [w, h], 'seam': SEAM, 'pivot': [380, 850], 'hubs': HUBS, 'rim_r': R}, open(A('geom.json'), 'w'), indent=1)
print('ok', w, h)
