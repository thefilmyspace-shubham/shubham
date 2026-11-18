# Funhoods FIDGET BALL (Avengers series spinner) -- the client's 4K60 product video (Drive, 2160x3840 H.264, 45.5 s, one take
# with a few cuts) with on-screen captions, the Funhoods watermark and very light effects:
#   - captions: Funhoods pills at the top (below Instagram's top bar), each fades and rises in on its own shot;
#   - watermark: logo top-left at 85 % opacity (as in the assembly guides), hidden for the closing logo card;
#   - two slow push-ins (5 % and 6 %, eased) that end on a cut: the 12-pack reveal and the 4-design line-up;
#   - a light colour pop (+4 % contrast, +8 % saturation) on the footage, not on the client's logo card.
# The footage is not re-cut and the original music is kept.
# usage: python3 tools/overlay.py <src>                    -> exports/Funhoods_Fidget_Ball_4K60.mp4
#        python3 tools/overlay.py <src> --still <t> <png>  (one frame, captions fully in)
import os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
LOGO = os.path.join(ROOT, '..', 'funhoods-dino-car', 'assets', 'logo_rgba.png')
RED, DRED, YEL, WHITE = (210, 24, 31), (120, 6, 14), (255, 212, 0), (255, 255, 255)
W, H, FPS = 2160, 3840, 60
TOP = 350                                   # top of the first pill: under the watermark, above the balls at the top of frame

# (start, end, [(text, size, bg, fg), ...]) -- pills stacked top-down; times read from the footage
CAPTIONS = [
    (0.85, 2.80, [('FIDGET BALL', 150, YEL, DRED), ('AVENGERS SERIES SPINNER', 76, RED, WHITE)]),   # closed display box
    (2.95, 6.20, [('SPIN PLAY  •  STRESS RELIEF  •  FOCUS BOOST', 66, RED, WHITE)]),                # the box front says so
    (6.40, 8.70, [('12 PCS PER DISPLAY BOX', 88, RED, WHITE)]),                                     # 3 x 4 packs inside
    (8.90, 11.65, [('EACH BALL IN ITS OWN BOX', 88, RED, WHITE)]),                                  # window packs taken out
    (11.95, 19.60, [('TWIST & SPIN IN YOUR HAND', 88, RED, WHITE)]),                                # spider + super designs
    (19.90, 28.20, [('FUN FIDGET PLAY, ANYTIME', 88, RED, WHITE)]),                                 # star + black designs
    (30.20, 31.75, [('4 DESIGNS', 130, YEL, DRED)]),                                                # the 2 x 2 line-up (cut at 30.12)
    (33.10, 39.40, [('SPINS LIKE A TOP!', 116, YEL, DRED)]),                                        # balls spinning on the table
    (39.70, 42.70, [('288 PCS PER OUTER CARTON', 96, YEL, DRED), ('FOR DISTRIBUTORS & WHOLESALERS', 66, RED, WHITE)]),
]
WM = dict(width=360, cx=300, cy=250, alpha=0.85, start=0.30, end=42.75)   # 42.8-42.95 fade to white, then the logo card
ZOOMS = [(379, 483, 0.05, 104), (1807, 1919, 0.06, 95)]    # (first frame, cut frame, zoom, frames to reach it) -- eased push-ins
GRADE_END = 42.9                                            # colour pop stops as the clip fades to the logo card

def shadowed(im, blur=26, dy=18, a=90):
    pad = 70; out = Image.new('RGBA', (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (40, 10, 10, 255)); sh.putalpha(im.getchannel('A').point(lambda v: v * a // 255))
    lay = Image.new('RGBA', out.size, (0, 0, 0, 0)); lay.alpha_composite(sh, (pad, pad + dy))
    out.alpha_composite(lay.filter(ImageFilter.GaussianBlur(blur))); out.alpha_composite(im, (pad, pad)); return out

def pill(text, size, bg, fg, padx=70, pady=34, maxw=1700):
    fo = ImageFont.truetype(F_HEAD, size); d0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    while d0.textlength(text, font=fo) + 2 * padx > maxw: size -= 2; fo = ImageFont.truetype(F_HEAD, size)
    tw = d0.textlength(text, font=fo)
    im = Image.new('RGBA', (int(tw + 2 * padx), int(size * 1.15 + 2 * pady)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width, im.height), im.height // 2, fill=bg + (255,))
    d.text((im.width / 2, im.height / 2), text, font=fo, fill=fg, anchor='mm')
    return shadowed(im)

def cards():
    """[(png, start, end, x, y)] -- y is the top of the pill (the PNG has a 70 px shadow margin)"""
    out = []; tmp = os.path.join(ROOT, 'build'); os.makedirs(tmp, exist_ok=True)
    for i, (a, b, pills) in enumerate(CAPTIONS):
        y = TOP
        for k, (txt, size, bg, fg) in enumerate(pills):
            im = pill(txt, size, bg, fg); p = os.path.join(tmp, 'cap%02d_%d.png' % (i, k)); im.save(p)
            out.append((p, a + 0.12 * k, b, int(W / 2 - im.width / 2), y))     # a stacked pill follows 0.12 s later
            y += im.height - 140 + 22
    return out

def watermark():
    lg = Image.open(LOGO).convert('RGBA'); lg = lg.crop(lg.getchannel('A').getbbox())
    lg = lg.resize((WM['width'], int(lg.height * WM['width'] / lg.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda v: int(v * WM['alpha'])))
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    p = os.path.join(ROOT, 'build', 'watermark.png'); lg.save(p); return p, lg

def zoom_expr(z, n):
    e = '(1+%.3f*(0.5-0.5*cos(PI*min(1\\,(in-1)/%d))))' % (z, n)          # 'in' = frame number inside the segment
    pts = [('W/2-W/2/%s', 'H/2-H/2/%s'), ('W/2+W/2/%s', 'H/2-H/2/%s'), ('W/2-W/2/%s', 'H/2+H/2/%s'), ('W/2+W/2/%s', 'H/2+H/2/%s')]
    return 'perspective=' + ':'.join("x%d='%s':y%d='%s'" % (k, x % e, k, y % e) for k, (x, y) in enumerate(pts)) + \
           ':interpolation=cubic:sense=source:eval=frame'

def base_graph():
    """colour pop, then split at the zoom windows: the push-in segments get a smooth sub-pixel zoom, the rest passes through"""
    cuts = [0]; segs = []
    for f0, f1, z, n in ZOOMS: cuts += [f0, f1]
    fl = ["[0:v]eq=contrast=1.04:saturation=1.08:enable='lt(t\\,%.2f)',split=%d%s" % (GRADE_END, len(cuts), ''.join('[p%d]' % i for i in range(len(cuts))))]
    for i, f0 in enumerate(cuts):
        f1 = cuts[i + 1] if i + 1 < len(cuts) else None
        tr = 'trim=start_frame=%d' % f0 + (':end_frame=%d' % f1 if f1 else '') + ',setpts=PTS-STARTPTS'
        zm = [zoom_expr(z, n) for a, b, z, n in ZOOMS if a == f0]
        fl.append('[p%d]%s%s[q%d]' % (i, tr, (',' + zm[0]) if zm else '', i))
    fl.append(''.join('[q%d]' % i for i in range(len(cuts))) + 'concat=n=%d:v=1:a=0[base]' % len(cuts))
    return fl

def build(src, outp):
    cs = cards(); wp, wm = watermark(); args = ['ffmpeg', '-v', 'error', '-y', '-i', src]
    for p, *_ in cs: args += ['-loop', '1', '-framerate', str(FPS), '-t', '46', '-i', p]
    args += ['-loop', '1', '-framerate', str(FPS), '-t', '46', '-i', wp]; nw = len(cs) + 1
    fl = base_graph()
    fl.append('[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.4:alpha=1,fade=t=out:st=%.2f:d=0.2:alpha=1[wm]' % (nw, WM['start'], WM['end'] - 0.2))
    fl.append("[base][wm]overlay=x=%d:y=%d:shortest=1:enable='lte(t\\,%.2f)'[b0]" % (WM['cx'] - wm.width // 2, WM['cy'] - wm.height // 2, WM['end']))
    last = 'b0'
    for k, (p, a, b, x, y) in enumerate(cs):
        fl.append('[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.22:alpha=1,fade=t=out:st=%.2f:d=0.2:alpha=1[c%d]' % (k + 1, a, b - 0.2, k))
        ye = '%d+60*max(0\\,1-(t-%.2f)/0.25)' % (y - 70, a)
        fl.append("[%s][c%d]overlay=x=%d:y='%s':shortest=1:enable='between(t\\,%.2f\\,%.2f)'[v%d]" % (last, k, x, ye, a, b, k))
        last = 'v%d' % k
    args += ['-filter_complex', ';'.join(fl), '-map', '[%s]' % last, '-map', '0:a', '-c:a', 'copy',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '5.2',
             '-threads', '8', '-movflags', '+faststart', outp]
    subprocess.run(args, check=True)

def still(src, t, outp):
    """one frame with the colour pop, the watermark and the caption(s) on screen (zoom not applied)"""
    vf = 'eq=contrast=1.04:saturation=1.08' if t < GRADE_END else 'null'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % t, '-i', src, '-frames:v', '1', '-vf', vf, outp], check=True)
    fr = Image.open(outp).convert('RGBA')
    if WM['start'] <= t <= WM['end']:
        wp, wm = watermark(); fr.alpha_composite(wm, (WM['cx'] - wm.width // 2, WM['cy'] - wm.height // 2))
    for p, a, b, x, y in cards():
        if a <= t <= b: fr.alpha_composite(Image.open(p), (x, y - 70))
    fr.convert('RGB').save(outp)

if __name__ == '__main__':
    src = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == '--still': still(src, float(sys.argv[3]), sys.argv[4])
    else:
        os.makedirs(os.path.join(ROOT, 'exports'), exist_ok=True)
        build(src, os.path.join(ROOT, 'exports', 'Funhoods_Fidget_Ball_4K60.mp4'))
