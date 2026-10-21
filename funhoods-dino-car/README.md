# Funhoods — Dino Car (MT-03), B2B Reel (9:16, 2160x3840, 60 fps, 30 s)

Master: `exports/Funhoods_Dino_Car_Reel_4K60.mp4` · share copy: `exports/Funhoods_Dino_Car_Reel_1080p.mp4`
Caption: `CAPTION.md` · VO script: `SCRIPT.md`

The reel uses the same motion-graphics system as the Musical Stick reel. It has the **white backdrop** of that reel's white version: white sunburst, red type, and yellow lines with a red outline.
The cut follows the client's **ElevenLabs voice-over** instead of a beat grid.
Every shot is animated, including how the toy works. None of the client's phone footage is used as footage. One frame of it is used as a still: the cut-out of the real display box.
Logo is top-left. Audience is distributors & wholesalers only, no retailers. Bulk orders only, pan India delivery, **no phone number**.
On-screen packaging wording is spelled exactly as on the box: "DINOSAUR 4WD OFF-ROAD ROLLOVER VEHICLE", "360 DEGREE TUMBLING STUNT CAR", "NEW DESIGN", "3+ AGES", "AVAILABLE IN 4 COLORS", "CLIMB - MULTIPLE VENUES", "INERTIAL POWER", "360 DEGREE FLIP, COOL STUNTS, MORE ADDICTIVE", "DINOSAUR MOUTH CAN BE OPENED UP AND DOWN", "SPECIFICATIONS COLOURS AND CONTENTS MAY VARY FROM ILLUSTRATIONS".

| Time | VO | Scene |
|---|---|---|
| 0.0–2.6 | The Dino Monster Truck! + roar | Truck drops in · NEW DESIGN · DINO MONSTER TRUCK · RAWR! (roar arcs, shake) · DINOSAUR 4WD OFF-ROAD ROLLOVER VEHICLE |
| 2.6–5.8 | No batteries needed, just push and go. + zoom | NO BATTERIES NEEDED! (battery "no" icon) → a glove pushes the truck (rims spin, real ratchet sound) → lets go → ZOOM! (speed lines, trail, dust) · PUSH & GO · INERTIAL POWER |
| 5.8–7.8 | It flips 360 degree and | Truck climbs a ramp and does a 360° flip in the air with spinning arrows, then lands · 360° TUMBLING STUNT CAR · CLIMB - MULTIPLE VENUES · 360 DEGREE FLIP, COOL STUNTS, MORE ADDICTIVE |
| 7.8–9.8 | its dino mouth opens wide. | Close-up: as on the real toy, only the head moves. It hinges at its back-top and chomps open and shut twice, then opens wide on "wide" (upper teeth over the fixed lower jaw, a clack on each close) · DINOSAUR MOUTH CAN BE OPENED UP AND DOWN |
| 9.8–13.1 | Four fun colours. Blue, pink, green and yellow. | AVAILABLE IN 4 COLORS · each colour pops in on its word |
| 13.1–17.2 | BIS approved, made of virgin polymer, safe for little hands. | BIS APPROVED · VIRGIN POLYMER · SAFE FOR LITTLE HANDS · 3+ AGES |
| 17.2–20.4 | 12 per display box, it sells itself on the counter. | 12 PCS DISPLAY BOX: the real display box (cut-out) drops in and lands on a shop counter that slides in · COUNTER-READY DISPLAY |
| 20.4–24.0 | 192 pieces per carton with pan India delivery. | 192 PCS PER CARTON: three cartons drop and stack (logo printed straight on the board); a yellow Funhoods truck drives in · PAN INDIA DELIVERY |
| 24.0–27.2 | Distributors and wholesalers, place your bulk order today. | FOR DISTRIBUTORS & WHOLESALERS · 4 trucks line up · BULK ORDERS ONLY · ORDER TODAY! |
| 27.2–30.0 | Funhoods, childhood full of fun. | End card: logo (with "Childhood Full of Fun"), trucks, DINO CAR • MT-03 • 3+ AGES, BULK ORDERS ONLY, 192 PCS / CARTON, PAN INDIA DELIVERY, packaging disclaimer |

## Sources
- Product: BiRefNet cut-outs of the client's "360° product mockup" image (`assets/src`), upscaled with Real-ESRGAN x4 —
  side view, front view, and the 4 colour variants. `tools/prep_assets.py` splits the side view into the body (tail and spikes),
  the head, the chassis + lower jaw, and a wheel rim, so the rims can spin and the head can chomp on its hinge
  (`assets/geom.json`: seam, head rear edge, head pivot, hubs). The real video showed that the head moves on its own.
- Display box: `assets/box_real.png`, cut out by `tools/prep_box.py` from the frame at 5.62 s of the client's reference video
  (`assets/src/box_frame_5.62.png`). A blue car in the foreground covered the lip's left end, so that strip is patched and inpainted.
- Cartons, truck, glove, icons: drawn in `render.py`. The Funhoods logo is placed straight on the carton and the truck, with no white sticker behind it.
- Audio:
  - VO: client's ElevenLabs file `audio/vo_elevenlabs.mp3`, re-timed by `tools/vo_retime.py`.
  - Roar and zoom: ElevenLabs sound effects (`audio/sfx_*_elevenlabs.mp3`, 50 credits each).
  - Friction motor: the client's real "sound file", cleaned (`audio/Dino_Car_friction_sound_clean.mp3`). The ratchet plays while the glove pushes, and the flywheel whirr plays as the truck rolls away and drives into the stunt.
  - Synthesized whooshes, pops and chimes.
  - Music: **"Cupcakes" — Michael Ramir C. (Mixkit Stock Music Free License)**, 138 BPM, ducked under the VO.
    It is a different track and artist from the two earlier reels.
- AI b-roll: none. Through the API, Magnific's Kling 2.5 costs 325 credits per clip because unlimited mode does not apply there. The brief was unlimited only, so everything is motion graphics.

## Render
```sh
python3 tools/prep_assets.py                            # once: car parts + geom.json
python3 tools/prep_box.py <rembg models dir>            # once: assets/box_real.png
python3 tools/vo_retime.py                              # audio/vo_timed.wav + vo_timing.json
sh music/get_music.sh && python3 audio.py               # mix.wav (-14 LUFS)
python3 render.py --start 0 --end 7.5 --out c0.mp4      # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af aresample=192000,alimiter=limit=0.84:level=false:attack=2:release=60,aresample=48000 -c:a aac -b:a 256k Funhoods_Dino_Car_Reel_4K60.mp4
```
Fonts come from `../funhoods-target-blaster/fonts` (Lilita One, Luckiest Guy, Inter ExtraBold).
