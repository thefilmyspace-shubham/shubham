# Funhoods — Fighter Jets (6 in 1 pack), B2B Reel (9:16, 2160x3840, 60 fps, 30 s)

Master: `exports/Funhoods_Fighter_Jets_Reel_4K60.mp4` · share copy: `exports/Funhoods_Fighter_Jets_Reel_1080p.mp4`
VO script: `SCRIPT.md` · caption: `CAPTION.md`

The reel uses the same format as the Dino Car reel:
- White-backdrop motion graphics, cut to the voice-over.
- How the toy works is animated: pull back, let go.
- Logo top-left.
- Audience is distributors & wholesalers only: bulk orders only, pan India delivery, no phone number.

No "metal" or "die-cast" claim is made: the client confirmed the jets are not metal.
The product shots get a light colour grade: +6 % contrast, +12 % saturation and a little clarity, with whites kept white.

| Time | VO | Scene |
|---|---|---|
| 0.0–3.6 | Ready for take-off? Meet the Funhoods Fighter Jet Squad! | The fire jet swoops in with a contrail and speed lines · READY FOR TAKE-OFF? → MEET THE FIGHTER JET SQUAD! |
| 3.6–7.2 | Six jets, six bold designs, all in one pack! | The six designs take off into a 3 × 2 grid · 6 JETS · 6 BOLD DESIGNS · ALL IN 1 PACK |
| 7.2–9.4 | Pull it back... and let it fly! | How it works: a glove pulls the jet back (pull-back clicks), lets go, and the jet zooms off (whoosh, trail, dust) · PULL IT BACK · LET IT FLY! · PULL-BACK & GO ACTION |
| 9.4–13.3 | A fire jet, a camo jet and four more colourful flyers. | SAME BASE, DIFFERENT DESIGNS · FIRE JET · CAMO JET · + 4 MORE COLOURFUL FLYERS |
| 13.3–18.0 | BIS certified, non-toxic and BPA free, proudly Made in India. | BIS CERTIFIED – IS 9873 · SAFE & NON-TOXIC · BPA FREE · MADE IN INDIA |
| 18.0–20.9 | Bright, eye-catching packs that fly off the shelves! | The blister packs land on a shelf, then fly up off it · BRIGHT, EYE-CATCHING PACKS · FLY OFF THE SHELVES! |
| 20.9–24.0 | 144 per carton, delivered anywhere in India. | 144 PCS PER CARTON (cartons stack) · a Funhoods truck drives in · PAN INDIA DELIVERY |
| 24.0–27.1 | Distributors and wholesalers, book your bulk stock now! | FOR DISTRIBUTORS & WHOLESALERS · the squad flies in V formation · BULK ORDERS ONLY · BOOK NOW! |
| 27.1–30.0 | Funhoods, childhood full of fun. | End card: logo, jets, FIGHTER JETS • 6 IN 1 PACK • AGES 3+, BULK ORDERS ONLY, 144 PCS / CARTON, PAN INDIA DELIVERY |

## Sources
- **Product images:** the client's "360° Product View" and "What's in the box" infographics (Drive, 1529x2048).
  - Each view was cropped, upscaled 4x with Real-ESRGAN and cut out with BiRefNet, keeping the largest part (`assets/src`).
  - `tools/prep_pack.py` masks the blister card as a rounded rectangle and inpaints the infographic's callout line.
  - `tools/prep_assets.py` applies the colour grade.
- **VO:** Magnific (ElevenLabs v4), voice "Callum Nathaniel Sinclair" (`audio/vo_final.mp3`, the client picked sample 2).
  - It runs 29.3 s, so it is only offset by 0.15 s (`tools/vo_timing.py`).
  - ElevenLabs itself had too few credits left this month.
- **SFX:** generated separately from the VO with Magnific (ElevenLabs SFX): jet whoosh ×2, pull-back clicks. Synthesized whooshes, pops and chimes are added on top.
- **Music:** **"Fun Times" — Ahjay Stelino (Mixkit Stock Music Free License)**, 145 BPM, ducked under the VO.
  It is a different track from the earlier reels (Punked Up Fun, Playground Fun, Cupcakes).

## Render
```sh
python3 tools/prep_pack.py && python3 tools/prep_assets.py   # graded assets
python3 tools/vo_timing.py                                    # audio/vo_timed.wav + vo_timing.json
sh music/get_music.sh && python3 audio.py                     # mix.wav (-14 LUFS)
python3 render.py --start 0 --end 7.5 --out c0.mp4            # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af aresample=192000,alimiter=limit=0.84:level=false:attack=2:release=60,aresample=48000 -c:a aac -b:a 256k Funhoods_Fighter_Jets_Reel_4K60.mp4
```
Fonts come from `../funhoods-target-blaster/fonts` (Lilita One, Luckiest Guy, Inter ExtraBold).
