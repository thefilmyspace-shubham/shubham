# Funhoods — ride-on assembly guide (English text on the client's video)

Source: the client's assembly video (Google Drive, 2160x3840 HEVC, 60 fps, 43.6 s). It is not stored in the repo.
`tools/overlay.py` adds English step cards on top, and the approved colour grade (`tools/grade.py`):
- **White balance per shot:** the cloth is measured in each shot and made neutral, which removes the warm/orange cast. The top-view shot was the warmest.
- **Even exposure:** every shot is brought to the same cloth level, so the cuts don't jump.
- **A brightening curve:** the cloth goes from ~150 to ~200. The client found ~220 too bright. Nothing clips.
- **Saturation:** +6 %, so the yellow body pops while the hands stay natural.

It also adds a Funhoods logo watermark top-left (85 % opacity, logo only; 60 % looked faded), as in the animated reels; the watermark is hidden on the closing logo card. The footage is not re-cut, and the original sound is kept.

Master: `exports/Funhoods_RideOn_Assembly_Guide_4K60.mp4` · share copy: `exports/Funhoods_RideOn_Assembly_Guide_1080p.mp4`

## Text on screen
Each card is a red "STEP n" chip on a white rounded card, with progress dots, set below Instagram's top bar. The cards fade and slide in on their own shot.

| Time (s) | Text |
|---|---|
| 0–1.9 | HOW TO ASSEMBLE |
| 1.95–6.05 | STEP 1 · Put the batteries in the battery box and close the cover |
| 6.35–11.75 | STEP 2 · Place the seat on top and press it down firmly |
| 11.95–14.75 | STEP 3 · Fit the black cap on the front tube |
| 14.95–19.10 | STEP 4 · Slide the front wheel axle through the front tube |
| 19.30–23.15 | STEP 5 · Fit the black ring on top of the steering tube |
| 23.45–26.45 | STEP 6 · Insert the handlebar into the steering tube |
| 26.65–30.40 | STEP 7 · Press the centre cap onto the handlebar |
| 31.95–37.45 | READY TO RIDE! |
| 37.75–41.75 | EASY TO ASSEMBLE AT HOME |
| 41.9–43.6 | (the client's Funhoods logo card, untouched) |

The step times and wording were read from the footage frame by frame (the cells going into the battery box, the cap, axle,
ring, handlebar and centre cap). No product name, battery size or feature claims were added.

## Render
```sh
python3 tools/grade.py <source.mp4> --stills <dir> 9,26,34  # before | v2 | graded comparisons
python3 tools/overlay.py <source.mp4>                      # graded 4K60 H.264 with text + watermark + original audio
python3 tools/overlay.py <source.mp4> --still 9.0 out.png  # preview one frame
```

## Editable CapCut project
`exports/Funhoods_Assembly_CapCut.zip` is built by `tools/capcut_project.py`, using pyJianYingDraft (the open draft format CapCut and JianYing share). It contains:
- **CapCut project:** tracks *footage* (colour-graded clip, no text, original sound) and *watermark* (logo 85 %, top-left), plus the text tracks *title*, *step chip* and *step text* as native, editable CapCut text.
- **Media:** `2_Media`. The draft looks for it in `C:/Users/Public/Funhoods_Assembly/`; on other paths, CapCut asks to relink.
- **Backup kit:** the PNG cards, the watermark and `assembly_steps.srt`, in case a CapCut version refuses third-party drafts.
- **`HOW_TO_OPEN.txt`:** step-by-step instructions for Windows and Mac.

The text layers use CapCut's default font. Positions and sizes are set in the draft, but they could not be checked inside CapCut here.
