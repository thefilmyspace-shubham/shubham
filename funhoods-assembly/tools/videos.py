# Per-video settings for the assembly guides. Pick the video with the env var ASM_VIDEO (default 1):
#   ASM_VIDEO=2 python3 tools/overlay.py <source of video 2>
# Every time in a video's entry is on the SOURCE clock (as read from the client's file); `trim` seconds are cut from
# the start (video 2: the black & white "REWIND" intro), and V holds the same times on the OUTPUT clock.
import os

VIDEOS = {
    '1': dict(  # Drive 1ElAoa-XPilOL4Y5zXSruIckf8zlooPp3 -- 2160x3840 HEVC 60 fps, 43.56 s
        out='Funhoods_RideOn_Assembly_Guide', draft='Funhoods_RideOn_Assembly', base='assembly_base_4K60.mp4',
        zip='Funhoods_Assembly_CapCut', win='C:/Users/Public/Funhoods_Assembly', build='build', gains='grade_gains.json',
        trim=0.0,
        shots=[0.0, 6.2, 23.3, 31.783, 37.583, 41.9, 43.56],      # cuts (scene detection); the last shot is the logo card
        title=(0.0, 1.9),
        steps=[(0.30, 6.05, 'Put the batteries in the battery box and close the cover'),
               (6.35, 11.75, 'Place the seat on top and press it down firmly'),
               (11.95, 14.75, 'Fit the black cap on the front tube'),
               (14.95, 19.10, 'Slide the front wheel axle through the front tube'),
               (19.30, 23.15, 'Fit the black ring on top of the steering tube'),
               (23.45, 26.45, 'Insert the handlebar into the steering tube'),
               (26.65, 30.40, 'Press the centre cap onto the handlebar')],
        ready=(31.95, 37.45), done=(37.75, 41.75), wm_end=41.7),
    '2': dict(  # Drive 1JCjxbxnSHlrNb-F_YP3OtfL65mi0Lmnw -- 2160x3840 H.264 60 fps, 38.67 s (red / cream ride-on, teal seat)
        out='Funhoods_RideOn_Assembly_Guide_2', draft='Funhoods_RideOn_Assembly_2', base='assembly2_base_4K60.mp4',
        zip='Funhoods_Assembly_2_CapCut', win='C:/Users/Public/Funhoods_Assembly_2', build='build/v2', gains='grade_gains_v2.json',
        trim=3.15,      # 0-2.93 s is the B&W rewind, 2.93-3.13 s its glitch transition: the guide starts on the clean parts layout
        shots=[3.15, 3.95, 5.15, 6.2, 9.917, 11.7, 15.267, 22.717, 22.983, 23.717, 28.5, 29.683, 33.45, 34.4, 35.7,
               36.483, 38.667],                                   # 36.32-36.48 fade to white, then the logo card (left as is)
        title=(3.15, 4.10),                                       # over the parts layout
        steps=[(4.15, 6.10, 'Put the batteries in and close the cover'),
               (6.35, 9.85, 'Turn the frame over and place the seat on top'),
               (9.97, 15.20, 'Press the cap into the seat and tighten it with the black tool'),
               (15.35, 18.30, 'Fit the orange ring on top of the front tube'),
               (18.50, 22.65, 'Join the two handlebar halves together'),
               (22.77, 24.95, 'Slide the front wheel stem into the front tube'),
               (25.05, 27.15, 'Fit the handlebar on top and press it down'),
               (27.25, 29.60, 'Press the centre cap onto the handlebar')],
        ready=(29.75, 33.40), done=(33.50, 36.28), wm_end=36.32),
}

KEY = os.environ.get('ASM_VIDEO', '1')
_v = VIDEOS[KEY]; T0 = _v['trim']
def _o(t): return round(t - T0, 3)
V = dict(_v, shots=[_o(t) for t in _v['shots']], title=tuple(map(_o, _v['title'])),
         steps=[(_o(a), _o(b), s) for a, b, s in _v['steps']], ready=tuple(map(_o, _v['ready'])),
         done=tuple(map(_o, _v['done'])), wm_end=_o(_v['wm_end']))
