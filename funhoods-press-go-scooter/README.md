# Funhoods — Press & Go Scooter (PL-001), B2B Reel (9:16, 2160x3840, 60 fps, 32 s)

Master: `exports/Funhoods_Press_Go_Scooter_Reel_4K60.mp4` · share copy: `exports/Funhoods_Press_Go_Scooter_Reel_1080p.mp4`
Script: `SCRIPT.md` · Caption: `CAPTION.md`
360° sheets: `exports/Press_Go_Scooter_360_Product_View.png`, `exports/Press_Go_Scooter_Packaging_View.png`

This reel is cut like the Dino Car reel: white-backdrop motion graphics cut to the VO, logo top-left, and an animated
"how it works" scene.

- **Audience:** distributors & wholesalers only, bulk orders only, pan India delivery. No phone number, no MRP.
- **Footage:** none. The client's raw clips were used only to see how the toy works and to take its real sounds.

**How it works (scene 2):** the toy is rigged from the client's photos (`tools/prep_assets.py`, `tools/rig_back.py`):
- the scooter + body;
- the head in 4 poses, all sharing the neck point: front, profile, mirrored profile, back.

Pressing and turning are two separate demos (client's note: they must not mix). The VO's line 2 is re-ordered for this
in `tools/vo_retime.py`, cut at its natural pauses: "Just press the head... and off it goes!" then "Watch it turn!".
1. **Press & go:** a finger presses the head (down, up), presses again and holds; the head only sinks over the neck,
   with the real gear whirr. It lets go, and the scooter rolls forward across the frame with the real wheel whirr.
2. **Head turn** (its own close-up shot): no finger, no press. The head turns a full 360° on its own:
   front → left → back → right → front, each quarter a quick cross-fade between neighbouring poses.

The client's photos have no view of the back of the head. That pose is made from the front head's silhouette: plain yellow, shaded like the plastic.

**Product facts** (all from the client's material):
- **Catalogue** (FUNHOODS_02.pdf, p. 11): Press & Go Scooter (2 models) · PL-001 · 240 pcs per carton.
- **Pack label:** Press the Head · 360° · 3 Years+ · Made in India · non-toxic · IS 9873 (Part-1) · BIS CM/L 8200185112.
- **Photos:** a mouse and a duck rider.
- **Client infographic** (6 Nov): "Friction Powered Toy", the mouse in **4 colours** (blue, red, sky blue, orange), and the **new transparent packaging**.

| Time | VO | Scene |
|---|---|---|
| 0–3.2 | *(horn: beep beep)* Meet the Funhoods Press and Go Scooter! | The orange mouse scooter (sharp shot from the client's infographic) drops in and honks (horn SFX, honk rings, BEEP BEEP!) · MEET THE · PRESS & GO · SCOOTER |
| 3.2–6.3 | Just press the head... and off it goes! | **Press & go** on its own: a finger presses the head (down, up), presses again and holds (real press whirr) · PRESS THE HEAD · PRESS DOWN. It lets go, and the scooter rolls forward across the frame (it faces left) with arrows on the ground and the real wheel whirr · OFF IT GOES! · LET GO: IT ROLLS FORWARD |
| 6.3–7.8 | Watch it turn! | **Head turn** in its own shot: close-up, no finger, no press. The head turns a full 360° on its own (front → left → back → right → front), ring of arrows round the neck · WATCH IT TURN! · HEAD TURNS 360° |
| 7.8–11.5 | Two cute riders, a little mouse and a happy duck! | Mouse (blue) and duck (blue) slide in, each hops on its word · 2 CUTE RIDERS · MOUSE · DUCK |
| 11.5–14.3 | Bright blue, red and orange scooters. | The 4 colours from the client's infographic pop in one by one (sky blue between red and orange): BLUE · RED · SKY BLUE · ORANGE · BRIGHT 4 COLOURS |
| 14.3–17.8 | BIS certified, Made in India and non-toxic. | Red mouse + blue duck, badge rows: BIS CERTIFIED (IS 9873 Part-1), MADE IN INDIA, NON-TOXIC, 3+ YEARS |
| 17.8–20.9 | In a see-through pouch that shows off every rider. | The new transparent pouch (client infographic) drops onto a peg and swings; a ring shows the rider through the clear bag · SEE-THROUGH POUCH · SHOWS EVERY RIDER! |
| 20.9–24.1 | Two hundred forty pieces per carton, pan India delivery. | 240 PCS PER CARTON (cartons stack) · Funhoods truck · PAN INDIA DELIVERY |
| 24.1–27.8 | Distributors and wholesalers, fill your shelves with Press and Go! | A peg board slides up and fills with 6 of the new pouches · BULK ORDERS ONLY · FILL YOUR SHELVES! |
| 27.8–32 | Funhoods, Childhood Full of Fun! | End card: logo, orange mouse with blue and red beside it (infographic), PRESS & GO SCOOTER • PL-001 • 3+ YEARS, 240 PCS / CARTON, PAN INDIA DELIVERY |

## Sources
- **Product:** BiRefNet cut-outs of the client's phone photos (Drive, 5 Nov), colour graded by `tools/prep_assets.py`
  (levels, +6 % contrast, +12 % saturation, clarity). The MRP and the phone number on the pack label are painted out.
- **New pack + 4 colours:** from the client's infographic (`assets/src_infographic/`, 1199x1312), cropped, upscaled 4x
  (Real-ESRGAN) and cut out with BiRefNet. The clear bag is rebuilt as a film by `tools/new_pack.py`: outline, tint, edge,
  and the plastic's own glare and creases from the photo. (`tools/clear_pouch.py` made the old pouch photos see-through.
  It is kept for the packaging sheet's back label.)
- **VO:** Magnific (ElevenLabs v4), voice "Gavin" (client pick, sample 1), re-timed by `tools/vo_retime.py` (+8 % tempo, pitch kept).
  It never speaks a sound effect.
- **Toy sounds:** the scooter's REAL sounds, cut from the client's raw clip and denoised by `tools/og_sound.py`:
  - `og_press_1..4`: the gear whirr when the head is pressed
  - `og_go`: the wheels running free
- **Horn:** `audio/sfx_horn_beep_1.mp3` (generated SFX), its first two beeps.
  Synthesized whooshes, pops, thocks and chimes are used for the graphics.
- **Music:** **"Kidding Around" — Ahjay Stelino (Mixkit Stock Music Free License)**, ducked under the VO, dipped under the press sounds.
  It is a different track from the earlier reels.

## Render
```sh
python3 tools/prep_assets.py && python3 tools/clear_pouch.py && python3 tools/new_pack.py && python3 tools/rig_back.py && python3 tools/sheets.py
python3 tools/og_sound.py <dir with 130920.mp4>              # audio/og_*.wav (real toy sounds)
python3 tools/vo_retime.py                                    # audio/vo_timed.wav + vo_timing.json
sh music/get_music.sh && python3 audio.py                     # mix.wav (-14 LUFS)
python3 render.py --start 0 --end 8 --out c0.mp4              # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af aresample=192000,alimiter=limit=0.8:level=false:attack=2:release=60,aresample=48000 -c:a aac -b:a 256k Funhoods_Press_Go_Scooter_Reel_4K60.mp4
```
