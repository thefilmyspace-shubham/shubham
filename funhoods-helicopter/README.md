# Funhoods — helicopter (flying propellers): text on the client's video

The source is the client's edited video (Google Drive, 2160x3840 HEVC, 60 fps, 38.8 s, music only). It is not stored in the repo.
`tools/overlay.py` adds on-screen captions only, as the client asked ("isme text add krdo"). The footage, the editor's own
"PLEASE ROTATE YOUR PHONE" screens and the music are not changed. There is no watermark.

Master: `exports/Funhoods_Helicopter_4K60.mp4` · share copy: `exports/Funhoods_Helicopter_1080p.mp4`

## Orientation
The client warned: "video kab horizontal hai kab vertical dekh lena".

| Time (s) | Part | Orientation |
|---|---|---|
| 0–1.63 | propellers in the sky, hands launching | vertical |
| 1.63–3.70 | black PLEASE ROTATE YOUR PHONE (turns to landscape) | no text |
| 3.70–29.23 | the unboxing, shot sideways | **horizontal**: upright is the frame turned 90° counter-clockwise |
| 29.23–31.18 | black PLEASE ROTATE YOUR PHONE (back to portrait) | no text |
| 31.18–36.07 | outdoors, the propellers fly | vertical |
| 36.07–38.85 | fade to white + the client's Funhoods logo card | untouched |

- **Vertical captions:** top-centre, as in the other reels.
- **Horizontal captions:** drawn on a landscape canvas at the top-left, then turned 90° clockwise into the frame, so they read upright when the phone is turned. The top-left also keeps them clear of Instagram's side buttons.

## Captions

| Time (s) | Caption | View |
|---|---|---|
| 0.15–1.55 | LAUNCH IT HIGH! | vertical |
| 3.9–8.9 | FUNHOODS HELICOPTER | horizontal |
| 9.1–14.3 | 12 PCS PER DISPLAY BOX | horizontal |
| 14.5–20.0 | EACH IN ITS OWN BOX | horizontal |
| 20.15–26.6 | FOR 3 YEARS+ | horizontal |
| 27.0–29.1 | 4 CUTE DESIGNS | horizontal |
| 31.4–34.0 | WATCH IT FLY! | vertical |
| 34.15–36.0 | FOR DISTRIBUTORS / & WHOLESALERS | vertical |

**Facts used:**
- **From the client:** 12 pcs per display box (only one layer of 6 is visible in the footage). Also from the client: no NEW LAUNCH.
- **From the footage:**
  - the name "helicopter" on the packs;
  - "3 YEARS+" printed on the packs;
  - 4 designs in the line-up.

The pieces per carton are not known, so they are not shown. There is no phone number and no price.

```sh
python3 tools/overlay.py <source.mp4>                       # 4K60 H.264 with captions, original audio
python3 tools/overlay.py <source.mp4> --still 16.0 out.png  # preview one frame
```
