# The pouch is clear plastic. In the client's photos it was shot on a dark surface, so the cut-out showed that dark
# background through the bag and the pouch read as black. Here the bag area is made see-through:
# - kept opaque: the header card and the toy inside (saturated colours + the small enclosed parts like the eyes and hub)
# - the rest of the bag becomes a clear film: the dark background is removed, the plastic's own glare is kept as soft white
#   highlights, plus a faint film tint and a thin edge so the bag's shape still reads.
# In place on assets/pack_front.png, pack_front2.png, pack_back.png (run after tools/prep_assets.py).
import os
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)

def clear(name):
    im = Image.open(A(name)).convert('RGBA'); v = np.asarray(im).astype(np.float32)
    a = v[..., 3] / 255; rgb = v[..., :3]
    hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    S, V = hsv[..., 1], hsv[..., 2]
    H = hsv[..., 0]; blue = (H > 85) & (H < 135)
    blue_ok = ((S > 130) & (V > 95)) | ((S > 55) & (V > 150))                # light-blue scooter, also in shade / under glare;
    solid = np.where(blue, blue_ok, (S > 95) & (V > 115)) & (a > 0.5)        # the navy backdrop is S < 110, V < 120
    solid = cv2.morphologyEx(solid.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((21, 21), np.uint8)) > 0   # bridge glare streaks
    holes = ndi.binary_fill_holes(solid) & ~solid                           # eyes, wheel hub, lashes ...
    lab, n = ndi.label(holes); sizes = ndi.sum(holes, lab, range(1, n + 1))
    small = np.isin(lab, 1 + np.where(sizes < 0.015 * solid.size)[0])
    solid = (solid | small)
    lab, n = ndi.label(solid); sizes = ndi.sum(solid, lab, range(1, n + 1))  # drop specks
    solid = np.isin(lab, 1 + np.where(sizes > 0.002 * solid.size)[0])
    soft = cv2.GaussianBlur(solid.astype(np.float32), (0, 0), 1.5)
    # clear film: brightness above the dark backdrop = plastic glare -> white highlight with that much opacity
    bgv = np.percentile(V[(a > 0.5) & ~solid], 25) if ((a > 0.5) & ~solid).any() else 40
    glare = np.clip((V - bgv - 12) / (235 - bgv), 0, 1) ** 1.3 * np.clip(1 - S / 140, 0, 1)
    inside = (a > 0.5).astype(np.uint8)
    edge = np.clip(1 - cv2.distanceTransform(inside, cv2.DIST_L2, 5) / 14, 0, 1) * (a > 0.05)
    film_a = np.clip(0.10 + 0.80 * glare + 0.45 * edge, 0, 1)
    film_rgb = np.ones_like(rgb) * np.array([226, 232, 240], np.float32)
    film_rgb = film_rgb * (1 - glare[..., None]) + 255 * glare[..., None]
    film_rgb = film_rgb * (1 - 0.35 * edge[..., None]) + np.array([150, 160, 172], np.float32) * 0.35 * edge[..., None]
    out_rgb = rgb * soft[..., None] + film_rgb * (1 - soft[..., None])
    out_a = a * (soft + (1 - soft) * film_a)
    out = np.concatenate([np.clip(out_rgb, 0, 255), np.clip(out_a * 255, 0, 255)[..., None]], -1).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(A(name)); print(name, 'clear film', round(float((~solid & (a > 0.5)).mean()), 3))

for n in ('pack_front.png', 'pack_front2.png', 'pack_back.png'): clear(n)
