# English assembly text for the client's ride-on assembly video (Drive, 2160x3840 HEVC 60 fps, 43.6 s, "src").
# Each step gets a card at the top of the frame: a red "STEP n" chip + a white rounded card with the instruction and
# progress dots. The cards fade and slide in on the step's own shot (step times were read from the footage).
# The video is not re-cut; the original sound is kept. -> exports/*_4K60.mp4 + *_1080p.mp4
# usage: python3 tools/overlay.py <src video>            (or: --still <t> <out.png> to preview one frame)
import os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_HEAD, F_BODY = os.path.join(FONTS, 'LilitaOne-Regular.ttf'), os.path.join(FONTS, 'Inter-ExtraBold.ttf')
RED, DRED, INK, YEL = (210, 24, 31), (120, 6, 14), (34, 28, 30), (255, 212, 0)
W, H = 2160, 3840
STEPS = [  # (start, end, text) -- seconds on the video clock
    (0.30, 6.05, 'Put the batteries in the battery box and close the cover'),
    (6.35, 11.75, 'Place the seat on top and press it down firmly'),
    (11.95, 14.75, 'Fit the black cap on the front tube'),
    (14.95, 19.10, 'Slide the front wheel axle through the front tube'),
    (19.30, 23.15, 'Fit the black ring on top of the steering tube'),
    (23.45, 26.45, 'Insert the handlebar into the steering tube'),
    (26.65, 30.40, 'Press the centre cap onto the handlebar'),
]
TITLE = (0.0, 1.9)                    # "HOW TO ASSEMBLE" before step 1 settles
READY = (31.95, 37.45)                # top view of the finished ride-on
DONE = (37.75, 41.75)

def font(p, s): return ImageFont.truetype(p, s)

def wrap(d, s, fo, w):
    out, cur = [], ''
    for wd in s.split():
        tr = (cur + ' ' + wd).strip()
        if d.textlength(tr, font=fo) <= w: cur = tr
        else: out.append(cur); cur = wd
    return out + [cur]

def shadowed(im, blur=26, dy=18, a=90):
    pad = 70; out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (40, 10, 10, 255)); sh.putalpha(im.getchannel('A').point(lambda v: v * a // 255))
    lay = Image.new('RGBA', out.size, (0, 0, 0, 0)); lay.alpha_composite(sh, (pad, pad + dy))
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur))); out.alpha_composite(im, (pad, pad)); return out

def step_card(n, text):
    cw = 1720; fo = font(F_BODY, 84); d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    lines = wrap(d0, text, fo, cw - 140); lh = 104
    ch = 70 + len(lines) * lh + 90
    im = Image.new('RGBA', (cw, ch + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 70, cw, 70 + ch), 54, fill=(255, 255, 255, 240))
    chip_f = font(F_HEAD, 76); label = 'STEP %d' % n; tw = d.textlength(label, font=chip_f)
    d.rounded_rectangle((60, 0, 60 + tw + 90, 128), 64, fill=RED + (255,))
    d.text((60 + 45, 64), label, font=chip_f, fill=(255, 255, 255), anchor='lm')
    for k, ln in enumerate(lines): d.text((cw / 2, 70 + 62 + k * lh + lh / 2), ln, font=fo, fill=INK, anchor='mm')
    for k in range(len(STEPS)):                                   # progress dots
        x = cw / 2 + (k - (len(STEPS) - 1) / 2) * 46; y = 70 + ch - 44
        r = 13 if k + 1 == n else 9
        d.ellipse((x - r, y - r, x + r, y + r), fill=(RED if k + 1 <= n else (214, 214, 218)) + (255,))
    return shadowed(im)

def pill(text, size=96, bg=RED, fg=(255, 255, 255), padx=80, pady=40, path=F_HEAD):
    fo = font(path, size); d0 = ImageDraw.Draw(Image.new('RGB', (10, 10))); tw = d0.textlength(text, font=fo)
    im = Image.new('RGBA', (int(tw + 2 * padx), int(size * 1.15 + 2 * pady)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width, im.height), im.height // 2, fill=bg + (255,))
    d.text((im.width / 2, im.height / 2), text, font=fo, fill=fg, anchor='mm')
    return shadowed(im)

def cards():
    """(png path, start, end, centre x, top y)"""
    out = []; tmp = os.path.join(ROOT, 'build'); os.makedirs(tmp, exist_ok=True)
    def save(im, name): p = os.path.join(tmp, name); im.save(p); return p, im
    p, im = save(pill('HOW TO ASSEMBLE', 104), 'title.png'); out.append((p, TITLE[0], TITLE[1], W / 2, 430))
    for i, (a, b, txt) in enumerate(STEPS):
        p, im = save(step_card(i + 1, txt), 'step%d.png' % (i + 1)); out.append((p, max(a, TITLE[1] + 0.05) if i == 0 else a, b, W / 2, 430))   # below Instagram's top bar
    p, im = save(pill('READY TO RIDE!', 132, YEL, DRED), 'ready.png'); out.append((p, READY[0], READY[1], W / 2, 430))
    p, im = save(pill('EASY TO ASSEMBLE AT HOME', 84), 'done.png'); out.append((p, DONE[0], DONE[1], W / 2, 430))
    return out

def build(src, outp):
    cs = cards(); args = ['ffmpeg', '-v', 'error', '-y', '-i', src]
    for p, a, b, cx, ty in cs: args += ['-loop', '1', '-framerate', '60', '-t', '44', '-i', p]
    fl = []; last = '0:v'
    for k, (p, a, b, cx, ty) in enumerate(cs):
        w_ = Image.open(p).width
        fl.append('[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.22:alpha=1,fade=t=out:st=%.2f:d=0.2:alpha=1[c%d]' % (k + 1, a, b - 0.2, k))
        y = '%d+60*max(0\\,1-(t-%.2f)/0.25)' % (ty - 70, a)
        fl.append("[%s][c%d]overlay=x=%d:y='%s':enable='between(t\\,%.2f\\,%.2f)'[v%d]" % (last, k, int(cx - w_ / 2), y, a, b, k))
        last = 'v%d' % k
    args += ['-filter_complex', ';'.join(fl), '-map', '[%s]' % last, '-map', '0:a', '-c:a', 'copy',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '5.2',
             '-threads', '4', '-movflags', '+faststart', outp]
    subprocess.run(args, check=True)

def still(src, t, outp):
    """preview one frame: the source frame + whichever card is on screen (fully in)"""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', src, '-frames:v', '1', outp], check=True)
    fr = Image.open(outp).convert('RGBA')
    for p, a, b, cx, ty in cards():
        if a <= t <= b:
            im = Image.open(p); fr.alpha_composite(im, (int(cx - im.width / 2), int(ty - 70)))
    fr.convert('RGB').save(outp)

if __name__ == '__main__':
    src = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == '--still':
        still(src, float(sys.argv[3]), sys.argv[4])
    else:
        build(src, os.path.join(ROOT, 'exports', 'Funhoods_RideOn_Assembly_Guide_4K60.mp4'))
