# Editable CapCut (desktop) project for the ride-on assembly guide, built with pyJianYingDraft (the open draft format
# shared by CapCut / JianYing). Tracks:
#   video  : assembly_base_4K60.mp4 -- the client's footage, brightened (same eq as overlay.py), no text, original sound
#   overlay: funhoods_logo.png      -- watermark top-left, 60 % opacity (hidden on the closing logo card)
#   text   : HOW TO ASSEMBLE / STEP n chips / step instructions / READY TO RIDE! / EASY TO ASSEMBLE AT HOME,
#            as native CapCut text layers (editable wording, size, colour, position)
# Media paths point to C:/Users/Public/Funhoods_Assembly/ (extract the media there on Windows), otherwise relink in CapCut.
# usage: python3 tools/capcut_project.py <out dir>   (expects <out dir>/media/assembly_base_4K60.mp4 + funhoods_logo.png)
import os, sys, json, shutil
import pyJianYingDraft as draft
from pyJianYingDraft import trange, TrackType, TrackSpec, ClipSettings, TextStyle, TextBackground
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from overlay import STEPS, TITLE, READY, DONE, WM

OUT = os.path.abspath(sys.argv[1]); MEDIA = os.path.join(OUT, 'media')
NAME = 'Funhoods_RideOn_Assembly'
WIN_MEDIA = 'C:/Users/Public/Funhoods_Assembly'          # where the media is expected on Windows
W, H, FPS, DUR = 2160, 3840, 60, 43.56

def s(t): return '%.3fs' % t
def tr(a, b): return trange(s(a), s(b - a))

folder = draft.DraftFolder(OUT)
sc = folder.create_draft(NAME, W, H, fps=FPS, allow_replace=True)
sc.append_track(TrackSpec(TrackType.video, 'footage'))
sc.append_track(TrackSpec(TrackType.video, 'watermark'))                   # appended later = drawn above the footage
for name in ('title', 'step chip', 'step text'): sc.append_track(TrackSpec(TrackType.text, name))

base = draft.VideoMaterial(os.path.join(MEDIA, 'assembly_base_4K60.mp4')); DUR = base.duration / 1e6   # the real clip length
sc.add_segment(draft.VideoSegment(base, tr(0, DUR)), 'footage')
logo = draft.VideoMaterial(os.path.join(MEDIA, 'funhoods_logo.png'))       # a still image is a video material too
wm_scale = WM['width'] / W                                                 # the logo is fitted to the canvas width
sc.add_segment(draft.VideoSegment(logo, tr(0, WM['end']), clip_settings=ClipSettings(
    alpha=WM['alpha'], scale_x=wm_scale, scale_y=wm_scale,
    transform_x=WM['cx'] / (W / 2) - 1, transform_y=1 - WM['cy'] / (H / 2))), 'watermark')

RED, INK, YEL, DRED = '#D2181F', (0.13, 0.11, 0.12), '#FFD400', (0.47, 0.02, 0.05)
def y_of(px): return 1 - px / (H / 2)                                     # pixel row -> CapCut y (half-canvas units, up = +)
def pill(text, a, b, y, bg, fg, size):
    sc.add_segment(draft.TextSegment(text, tr(a, b), style=TextStyle(size=size, bold=True, color=fg, align=1),
                   background=TextBackground(color=bg, alpha=1.0, round_radius=1.0, height=0.25, width=0.25),
                   clip_settings=ClipSettings(transform_y=y_of(y))), 'title')
pill('HOW TO ASSEMBLE', TITLE[0], TITLE[1], 560, RED, (1, 1, 1), 11)
for i, (a, b, text) in enumerate(STEPS):
    a = max(a, TITLE[1] + 0.05) if i == 0 else a
    sc.add_segment(draft.TextSegment('STEP %d' % (i + 1), tr(a, b), style=TextStyle(size=8, bold=True, color=(1, 1, 1), align=1),
                   background=TextBackground(color=RED, alpha=1.0, round_radius=1.0, height=0.3, width=0.3),
                   clip_settings=ClipSettings(transform_x=-0.62, transform_y=y_of(520))), 'step chip')
    sc.add_segment(draft.TextSegment(text, tr(a, b), style=TextStyle(size=9, bold=True, color=INK, align=1, auto_wrapping=True, max_line_width=0.78),
                   background=TextBackground(color='#FFFFFF', alpha=0.94, round_radius=0.5, height=0.32, width=0.18),
                   clip_settings=ClipSettings(transform_y=y_of(660))), 'step text')
pill('READY TO RIDE!', READY[0], READY[1], 560, YEL, DRED, 13)
pill('EASY TO ASSEMBLE AT HOME', DONE[0], DONE[1], 560, RED, (1, 1, 1), 10)
sc.save()

# point the media at the Windows folder the client will extract them to, keep the same file names
dpath = os.path.join(OUT, NAME); cj = os.path.join(dpath, 'draft_content.json')
txt = open(cj, encoding='utf-8').read().replace(MEDIA.replace('\\', '/'), WIN_MEDIA)
open(cj, 'w', encoding='utf-8').write(txt)
shutil.copy(cj, os.path.join(dpath, 'draft_info.json'))                    # the macOS app reads draft_info.json
print('draft:', dpath)
