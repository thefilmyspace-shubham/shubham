# Funhoods — FIDGET BALL (Avengers Series Spinner): captions + watermark on the client's video

Source: the client's product video (Google Drive, 2160x3840 H.264, 60 fps, 45.5 s; one take with a few cuts, music only, no voice). It is not stored in the repo.
`tools/overlay.py` adds:
- **Captions:** Funhoods pills at the top, below Instagram's top bar and the watermark. Each fades and rises in on its own shot.
- **Watermark:** the Funhoods logo top-left at 85 % opacity, same as the assembly guides. It fades in after the opening fade from black and is hidden on the closing logo card.
- **Very light effects:**
  - **Two slow push-ins**, both ending on a cut:
    - 5 % on the 12-pack reveal;
    - 6 % on the 4-design line-up, ending on the white flash.
  - **A light colour pop** of +4 % contrast and +8 % saturation, not applied to the logo card.

The footage is not re-cut, and the original music is kept.

Master: `exports/Funhoods_Fidget_Ball_4K60.mp4` · share copy: `exports/Funhoods_Fidget_Ball_1080p.mp4` · post caption: `CAPTION.md`

| Time (s) | Caption | On screen |
|---|---|---|
| 0.85–2.8 | FIDGET BALL / AVENGERS SERIES SPINNER | closed display box |
| 2.95–6.2 | SPIN PLAY • STRESS RELIEF • FOCUS BOOST | box front (these three are printed on it) |
| 6.4–8.7 | 12 PCS PER DISPLAY BOX | open box: 3 x 4 packs |
| 8.9–11.65 | EACH BALL IN ITS OWN BOX | the window packs taken out |
| 11.95–19.6 | TWIST & SPIN IN YOUR HAND | first two balls twisted and spun |
| 19.9–28.2 | FUN FIDGET PLAY, ANYTIME | next two balls |
| 30.2–31.75 | 4 DESIGNS | the 2 x 2 line-up |
| 33.1–39.4 | SPINS LIKE A TOP! | balls spinning on the table |
| 39.7–42.7 | 288 PCS PER OUTER CARTON / FOR DISTRIBUTORS & WHOLESALERS | spinning close-up |
| 42.8–45.5 | (fade to white + the client's Funhoods logo card, untouched) | |

**Facts used:**
- **From the client:** "Avengers series spinner" and 288 pcs per outer carton.
- **From the footage:**
  - the name FIDGET BALL as printed on the pack;
  - SPIN PLAY / STRESS RELIEF / FOCUS BOOST, printed on the display box;
  - 12 packs counted in the display box;
  - 4 designs.

No phone number and no price are shown.

```sh
python3 tools/overlay.py <source.mp4>                      # 4K60 H.264 with captions + watermark + effects, original audio
python3 tools/overlay.py <source.mp4> --still 7.2 out.png  # preview one frame (no zoom)
```

## Thumbnail / reel cover
There are two 9:16 versions:
- `exports/Funhoods_Fidget_Ball_Thumbnail_4K.png` / `.jpg` (2160x3840);
- `exports/Funhoods_Fidget_Ball_Thumbnail_1080x1920.jpg`.

All of them are made by `tools/thumbnail.py`, in the format of the earlier Funhoods reels. The script reuses the Press & Go reel's drawing helpers, so the look matches. The cover has:
- v2 (client: "still dull"): a bright Funhoods red sunburst background, as in the Musical Stick opener;
- a yellow NEW LAUNCH chip;
- the yellow FIDGET BALL title and a white AVENGERS SERIES SPINNER subtitle;
- the 4 balls on an orange + yellow burst, with punchier colour, a white sticker outline, spin arcs and sparkles;
- the chips 4 DESIGNS • 288 PCS / CARTON and FOR DISTRIBUTORS & WHOLESALERS.

There is no logo sticker (client: no watermark on the cover).

**Ball images:** from the video's last clean line-up frame (31.75 s), each upscaled 4x with Real-ESRGAN and cut out with rembg (`assets/ball_*.png`). The white ball's lower edge, lost against the white cloth, is filled in.
