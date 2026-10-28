# Product assets for the Fighter Jets reel, with a light colour grade.
# Sources: the client's "360° Product View" and "What's in the box" infographics (Drive, 1529x2048), each view cropped,
# Real-ESRGAN x4, BiRefNet cut-out keeping the largest part (assets/src/*.png).
# Grade (slight, as asked): +6 % contrast, +12 % saturation, a touch of clarity (unsharp mask), whites kept white.
# usage: python3 tools/prep_assets.py
import os
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
A = lambda *p: os.path.join(ROOT, 'assets', *p)

def grade(im):
    a = im.getchannel('A'); rgb = im.convert('RGB')
    rgb = ImageEnhance.Contrast(rgb).enhance(1.06)
    rgb = ImageEnhance.Color(rgb).enhance(1.12)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=3, percent=45, threshold=2))
    out = rgb.convert('RGBA'); out.putalpha(a); return out

NAMES = {'q34': 'jet_q34', 'side': 'jet_side', 'top': 'jet_top', 'front': 'jet_front', 'back': 'jet_back', 'bottom': 'jet_bottom',
         'd1': 'd1', 'd2': 'd2', 'd3': 'd3', 'd4': 'd4', 'd5': 'd5', 'd6': 'd6', 'pack': 'pack'}
for k, n in NAMES.items():
    src = A('src', k + '.png')
    if not os.path.exists(src): print('missing', src); continue
    im = Image.open(src).convert('RGBA')
    grade(im).save(A(n + '.png')); print(n, im.size)
