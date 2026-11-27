# Funhoods HELICOPTER (launcher with flying propellers) -- the client's edited 4K60 video (Drive, 2160x3840 HEVC, 38.8 s)
# with on-screen captions only (client: "isme text add krdo"). The footage, its own "PLEASE ROTATE YOUR PHONE" screens and
# the music are left as they are.
# The video changes orientation (client: "video kab horizontal hai kab vertical dekh lena"):
#   0.00-1.63   vertical    -- propellers in the sky, hands launching
#   1.63-3.70   black "PLEASE ROTATE YOUR PHONE" screen (turns to landscape) -- no text
#   3.70-29.23  HORIZONTAL  -- the unboxing is shot sideways: upright = the frame turned 90 deg counter-clockwise
#   29.23-31.18 black "PLEASE ROTATE YOUR PHONE" screen (back to portrait) -- no text
#   31.18-36.07 vertical    -- outdoors, the propellers fly; 36.07 fade to white, then the logo card (untouched)
# Vertical captions sit top-centre (as in the other reels); horizontal ones are drawn on a landscape canvas, top-left
# (clear of Instagram's side buttons, which end up on the landscape's top-right), then turned 90 deg clockwise into the
# portrait frame, so they read upright when the phone is turned with the video.
# usage: python3 tools/overlay.py <src>                    -> exports/Funhoods_Helicopter_4K60.mp4
#        python3 tools/overlay.py <src> --still <t> <png>  (one frame, captions fully in)
import os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONTS = os.path.join(ROOT, '..', 'funhoods-target-blaster', 'fonts')
F_HEAD = os.path.join(FONTS, 'LilitaOne-Regular.ttf')
RED, DRED, YEL, WHITE = (210, 24, 31), (120, 6, 14), (255, 212, 0), (255, 255, 255)
W, H, FPS = 2160, 3840, 60
V_TOP = 350                       # vertical: top of the first pill (below Instagram's top bar)
L_LEFT, L_TOP = 300, 90           # horizontal: top-left of the first pill on the 3840x2160 landscape canvas

# (start, end, orientation, [(text, size, bg, fg), ...]) -- pills stacked top-down; times read from the footage
CAPTIONS = [
    (0.15, 1.55, 'v', [('LAUNCH IT HIGH!', 120, YEL, DRED)]),                                    # propellers in the sky
    (3.90, 8.90, 'h', [('NEW LAUNCH', 64, RED, WHITE), ('FUNHOODS HELICOPTER', 120, YEL, DRED)]),  # wrapped display box
    (9.10, 14.30, 'h', [('6 PCS PER DISPLAY BOX', 96, RED, WHITE)]),                              # 3 x 2 packs inside
    (14.50, 20.00, 'h', [('EACH IN ITS OWN BOX', 96, RED, WHITE)]),                               # packs opened
    (20.15, 26.60, 'h', [('FOR 3 YEARS+', 96, RED, WHITE)]),                                      # "3 YEARS+" on the pack
    (27.00, 29.10, 'h', [('4 CUTE DESIGNS', 110, YEL, DRED)]),                                    # the line-up
    (31.40, 34.00, 'v', [('WATCH IT FLY!', 124, YEL, DRED)]),                                     # launched outdoors
    (34.15, 36.00, 'v', [('FOR DISTRIBUTORS', 96, RED, WHITE), ('& WHOLESALERS', 96, RED, WHITE)]),
]

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
    """[(png, start, end, x, y, slide)] in portrait pixels; x, y = top-left of the PNG when fully in;
    slide = (dx, dy) direction the card comes in from (60 px, 'up' in its own reading orientation)"""
    out = []; tmp = os.path.join(ROOT, 'build'); os.makedirs(tmp, exist_ok=True)
    for i, (a, b, ori, pills) in enumerate(CAPTIONS):
        y = V_TOP if ori == 'v' else L_TOP
        for k, (txt, size, bg, fg) in enumerate(pills):
            im = pill(txt, size, bg, fg); t0 = a + 0.12 * k
            if ori == 'v':                                   # centred, top of the portrait frame
                p = os.path.join(tmp, 'cap%02d_%d.png' % (i, k)); im.save(p)
                out.append((p, t0, b, int(W / 2 - im.width / 2), y - 70, (0, 1)))
            else:                                            # landscape (x', y') -> portrait (W-1-y', x'); PNG turned clockwise
                lx, ly = L_LEFT - 70, y - 70; rot = im.rotate(-90, expand=True)
                p = os.path.join(tmp, 'cap%02d_%d.png' % (i, k)); rot.save(p)
                out.append((p, t0, b, W - ly - im.height, lx, (-1, 0)))
            y += im.height - 140 + 22
    return out

def build(src, outp):
    cs = cards(); args = ['ffmpeg', '-v', 'error', '-y', '-i', src]
    for p, *_ in cs: args += ['-loop', '1', '-framerate', str(FPS), '-t', '39', '-i', p]
    fl = []; last = '0:v'
    for k, (p, a, b, x, y, (sx, sy)) in enumerate(cs):
        fl.append('[%d:v]format=rgba,fade=t=in:st=%.2f:d=0.22:alpha=1,fade=t=out:st=%.2f:d=0.2:alpha=1[c%d]' % (k + 1, a, b - 0.2, k))
        m = '60*max(0\\,1-(t-%.2f)/0.25)' % a
        xe = '%d%s' % (x, ('+' if sx > 0 else '-') + m if sx else '')
        ye = '%d%s' % (y, ('+' if sy > 0 else '-') + m if sy else '')
        fl.append("[%s][c%d]overlay=x='%s':y='%s':shortest=1:enable='between(t\\,%.2f\\,%.2f)'[v%d]" % (last, k, xe, ye, a, b, k))
        last = 'v%d' % k
    args += ['-filter_complex', ';'.join(fl), '-map', '[%s]' % last, '-map', '0:a', '-c:a', 'copy',
             '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '5.2',
             '-threads', '8', '-movflags', '+faststart', outp]
    subprocess.run(args, check=True)

def still(src, t, outp):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '%.3f' % t, '-i', src, '-frames:v', '1', outp], check=True)
    fr = Image.open(outp).convert('RGBA')
    for p, a, b, x, y, _ in cards():
        if a <= t <= b: fr.alpha_composite(Image.open(p), (x, y))
    fr.convert('RGB').save(outp)

if __name__ == '__main__':
    src = sys.argv[1]
    if len(sys.argv) > 3 and sys.argv[2] == '--still': still(src, float(sys.argv[3]), sys.argv[4])
    else:
        os.makedirs(os.path.join(ROOT, 'exports'), exist_ok=True)
        build(src, os.path.join(ROOT, 'exports', 'Funhoods_Helicopter_4K60.mp4'))
