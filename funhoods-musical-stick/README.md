# Funhoods — Cartoon Fun Story Musical Stick, B2B Reel (9:16, 2160x3840, 60 fps, 30 s)

`exports/Funhoods_Musical_Stick_Reel_4K60.mp4` (master) · `exports/Funhoods_Musical_Stick_Reel_1080p.mp4` (share copy)

Same format as the Target Blaster reel (v5): same music edit on the 130 BPM grid, same motion-graphics system,
Funhoods logo top-left, distributors & wholesalers only (no "retailers"), bulk orders only, pan India delivery.
Product facts used: display box of **12 pcs**, ages 3+, story mode, music & songs, animal sounds, 10-button panel.
Carton quantity is not on any material yet, so the reel says "12 PCS PER DISPLAY BOX" and nothing about cartons.

| Time | Scene | Text |
|---|---|---|
| 0.0–1.8 | Funhoods logo | NEW LAUNCH · For Distributors & Wholesalers |
| 1.8–3.7 | Stick pops up, music notes | INTRODUCING · CARTOON FUN STORY · MUSICAL STICK · PACK OF 12 PCS • AGES 3+ |
| 3.7–5.5 | AI b-roll 1 (box push-in) | STORIES, MUSIC & FUN / IN EVERY PRESS! |
| 5.5–9.2 | Key features | 01 button panel lights up: STORIES, SONGS & ANIMAL SOUNDS · 02 AI b-roll 3 (stick): CUTE, LIGHTWEIGHT & EASY TO HOLD |
| 9.2–14.8 | How it works | 1 PICK A PAL (AI b-roll 2) · 2 PRESS A BUTTON (tap rings + chimes) · 3 LISTEN & LEARN (stories / songs / animal sounds) |
| 14.8–16.6 | Drop, AI b-roll 4 | PRESS & PLAY! |
| 16.6–20.3 | AI b-roll 2 | Why stock it: ready-to-display box · 12 pcs in every box · educational & fun |
| 20.3–24.0 | Display box graphic | BULK ORDERS ONLY · 12 PCS PER DISPLAY BOX · PAN INDIA DELIVERY · Distributors / Wholesalers |
| 24.0–25.8 | AI b-roll 1 | STOCK UP NOW! |
| 25.8–30.0 | End card | BULK ORDERS ONLY · 12 PCS / BOX · PAN INDIA DELIVERY · DM US FOR TRADE PRICING |

## Sources
- Product cut-outs: `assets/box_open.png` (BiRefNet cut-out of a 4K frame of the client's reference video — used only as a
  still, never as footage), `assets/stick.png` (catalogue front view, Real-ESRGAN x4; right paw restored by mirroring
  the left one because the catalogue had Chase covering it), `assets/panel.png` (catalogue button panel, rebuilt
  without the callout lines), `assets/logo_rgba.png` (logo, Real-ESRGAN x4 then 2x).
- The client's phone videos are reference only — none of their footage is in the edit.
- AI b-roll: Magnific Space "Funhoods Musical Stick B-roll" — 4 x Kling 2.5 (9:16, 1080p, 5 s) from the start
  frames in `sf/` (built by `tools/startframes.py`). Run it in the Magnific app (unlimited applies there, not via the API).
  Until the clips exist, `render.py` uses the start frames with a matching camera move.

## Render
```sh
sh music/get_music.sh && python3 audio.py               # mix.wav
# after the Kling clips are generated: tools/ingest_clip.sh k1 scene1.mp4  (k1 box push-in, k2 box arc, k3 stick, k4 sticks glide)
python3 render.py --start 0 --end 7.5 --out c0.mp4      # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af alimiter=limit=0.891:level=false -c:a aac -b:a 256k Funhoods_Musical_Stick_Reel_4K60.mp4
```
