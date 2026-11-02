# Funhoods — PVC Racing Car (PVC-3301), B2B Reel (9:16, 2160x3840, 60 fps, 32 s)

Master: `exports/Funhoods_PVC_Racing_Car_Reel_4K60.mp4` · share copy: `exports/Funhoods_PVC_Racing_Car_Reel_1080p.mp4`
Script + storyboard: `SCRIPT.md`, `exports/Racing_Inertia_Car_Storyboard.png`
360° sheets: `exports/Racing_Inertia_Car_360_Product_View.png`, `exports/Racing_Inertia_Car_360_Packaging_View.png`
Caption: `CAPTION.md`

This reel uses the same format as the Dino Car and Fighter Jets reels: white-backdrop motion graphics cut to the VO, logo top-left.
Audience is distributors & wholesalers only: bulk orders only, pan India delivery, no phone number.
How the toy works is animated: push and let go, press the roof for lights and music. The client's phone videos were reference only.

Product facts:
- **Catalogue** (FUNHOODS_02.pdf, p. 25): PVC Racing Car · PVC-3301 · outer carton 36 pcs · inertia car.
- **Box:** friction / hand push / inertia / sturdy, four-wheel drive, loud music and bright light, 3+ ages. The car comes in **one colour only** (client), so the box's "multiple models / colors" is not claimed.
- **Claims left out:**
  - "no batteries": the lights and music run on 3 × Ag13 cells.
  - BIS / Made in India: not on this product; the box says Made in China.

| Time | VO | Scene |
|---|---|---|
| 0–3.2 | On your marks... get set... VROOM! | Start lights red → red → green, the car shoots in with speed lines and dust |
| 3.2–5.8 | Say hello to the Funhoods Racing Car! | 360° turntable (photo views) · RACING CAR · PVC RACING CAR • PVC-3301 |
| 5.8–9.4 | Give it a push... let go... and watch it race! | A glove pushes the car (rims spin, friction whirr), lets go, and the car races off · FRICTION · HAND PUSH · INERTIA |
| 9.4–12.7 | Press the roof... bright lights and loud music! | Front view: a finger presses the roof, the headlights glow with rays, music notes burst out · BRIGHT LIGHT · LOUD MUSIC |
| 12.7–16.3 | Four-wheel drive, a sturdy body and chunky tyres. | Side view rolling, wheel rings, callouts STURDY BODY · CHUNKY TYRES |
| 16.2–19.6 | Cool style, bold looks... built to race! | The orange car (one colour only) in 3/4 view swings round to face the camera · COOL STYLE · BOLD LOOKS · BUILT TO RACE! |
| 19.6–22.7 | A bold window box that grabs every eye in the store. | The window box (front) pops in, then lands on a shop counter · EYE-CATCHING WINDOW BOX |
| 22.7–25.6 | Thirty-six pieces per carton, shipped anywhere in India. | 36 PCS PER CARTON (cartons stack) · Funhoods truck · PAN INDIA DELIVERY |
| 25.6–29.1 | Distributors and wholesalers, stock up for the season! | Boxes line up · BULK ORDERS ONLY · STOCK UP NOW! |
| 29.1–32 | Funhoods, Childhood Full of Fun! | End card: logo, car + box, PVC RACING CAR • PVC-3301 • AGES 3+, 36 PCS / CARTON, PAN INDIA DELIVERY, box disclaimer |

## Sources
- **Product:** BiRefNet cut-outs of the client's 17 phone photos (Drive, 1 Nov), colour graded by `tools/prep_assets.py`
  (levels, +6 % contrast, +12 % saturation, clarity). The box panels are perspective-flattened.
- **VO:** Magnific (ElevenLabs v4), voice "Gavin" (client pick, sample 2), re-timed by `tools/vo_retime.py` (+8 % tempo, pitch kept).
  Line 6 was regenerated in the same voice (`audio/vo_line5_cool_style.mp3`) and spliced in.
- **SFX:** generated separately from the VO on Magnific (ElevenLabs SFX), plus synthesized beeps, whooshes, pops and chimes:
  - engine rev / VROOM
  - zoom
  - friction push
  - lights & music jingle
- **Music:** **"Jumping Around" — Ahjay Stelino (Mixkit Stock Music Free License)**, 110 BPM, ducked under the VO.
  It is a different track from the earlier reels.

## Render
```sh
python3 tools/prep_assets.py && python3 tools/sheets.py && python3 tools/storyboard.py
python3 tools/vo_retime.py                                    # audio/vo_timed.wav + vo_timing.json
sh music/get_music.sh && python3 audio.py                     # mix.wav (-14 LUFS)
python3 render.py --start 0 --end 8 --out c0.mp4              # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af aresample=192000,alimiter=limit=0.76:level=false:attack=2:release=60,aresample=48000 -c:a aac -b:a 256k Funhoods_PVC_Racing_Car_Reel_4K60.mp4
```
