# Funhoods — ride-on assembly guide (English text on the client's video)

Source: the client's assembly video (Google Drive, 2160x3840 HEVC, 60 fps, 43.6 s). It is not stored in the repo.
`tools/overlay.py` adds English step cards on top. The footage is not re-cut, and the original sound is kept.

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
python3 tools/overlay.py <source.mp4>                      # 4K60 H.264 + original audio
python3 tools/overlay.py <source.mp4> --still 9.0 out.png  # preview one frame
```
