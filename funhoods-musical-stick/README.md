# Funhoods — Cartoon Fun Story Musical Stick, B2B Reel (9:16, 2160x3840, 60 fps, 30 s)

Red backdrop: `exports/Funhoods_Musical_Stick_Reel_4K60.mp4` (master) · `exports/Funhoods_Musical_Stick_Reel_1080p.mp4` (share copy)
White backdrop: `exports/Funhoods_Musical_Stick_Reel_White_4K60.mp4` · `exports/Funhoods_Musical_Stick_Reel_White_1080p.mp4`
(`BG=white python3 render.py ...` — product scenes on white, red type, yellow lines with a red outline; intro and end card unchanged)
Caption: `CAPTION.md`

Same format as the Target Blaster reel (v5) — same 130 BPM cut grid and motion-graphics system — but its own music:
**"Playground Fun" — Ahjay Stelino (Mixkit, free license, no attribution required)**, 130 BPM; bars 16-18 → 35-39 (breakdown) →
40-44 (return on PRESS & PLAY!) → 87-90 (end card).
Funhoods logo top-left, distributors & wholesalers only (no "retailers"), bulk orders only, pan India delivery.
Product facts used: **12 PCS / PACKAGING** (display box of 12), ages 3+, story mode, music & songs, animal sounds, 10-button panel.
Client wording: "12 PCS / PACKAGING" (used in the intro chip, why-stock-it list, bulk scene and end card).

| Time | Scene | Text |
|---|---|---|
| 0.0–1.8 | Funhoods logo | NEW LAUNCH · For Distributors & Wholesalers |
| 1.8–3.7 | Stick pops up, music notes | INTRODUCING · CARTOON FUN STORY · MUSICAL STICK · 12 PCS / PACKAGING • AGES 3+ |
| 3.7–5.5 | Display box bounces in, notes pour out | STORIES, MUSIC & FUN / IN EVERY PRESS! |
| 5.5–9.2 | Key features | 01 button panel lights up: STORIES, SONGS & ANIMAL SOUNDS · 02 AI b-roll 3 (stick): CUTE, LIGHTWEIGHT & EASY TO HOLD |
| 9.2–14.8 | How it works | 1 PICK A PAL (a stick rises out of the box) · 2 PRESS A BUTTON (tap rings + chimes) · 3 LISTEN & LEARN (stories / songs / animal sounds) |
| 14.8–16.6 | Drop: box punches in | PRESS & PLAY! |
| 16.6–20.3 | Box sways on brand red | Why stock it: ready-to-display box · 12 pcs / packaging · educational & fun |
| 20.3–24.0 | Display box graphic | BULK ORDERS ONLY · 12 PCS / PACKAGING · PAN INDIA DELIVERY · Distributors / Wholesalers |
| 24.0–25.8 | Three display boxes drop in and stack | STOCK UP NOW! |
| 25.8–30.0 | End card | BULK ORDERS ONLY · 12 PCS / PACKAGING · PAN INDIA DELIVERY · DM US FOR TRADE PRICING |

## Sources
- Product cut-outs: `assets/box_open.png` (BiRefNet cut-out of a 4K frame of the client's reference video — used only as a
  still, never as footage), `assets/stick.png` (catalogue front view, Real-ESRGAN x4; right paw restored by mirroring
  the left one because the catalogue had Chase covering it), `assets/panel.png` (catalogue button panel, rebuilt
  without the callout lines), `assets/logo_rgba.png` (logo, Real-ESRGAN x4 then 2x).
- The client's phone videos are reference only — none of their footage is in the edit.
- v2 (client): the box on a blurred photo background didn't work — every box shot is now a motion graphic on the
  brand red background (`scene_box_hero`, `scene_pick`, `scene_box_drop`, `scene_why`, `scene_stack`).
- AI b-roll: only feature 02 (5.5–9.2 s, stick) still has a Kling slot — Magnific Space "Funhoods Musical Stick
  B-roll", Scene 3 (Kling 2.5, 9:16, 1080p, 5 s). Run it in the Magnific app (unlimited applies there, not via the API).
  Until that clip exists, `render.py` uses its start frame (`sf/sf2_stick.png`) with a matching camera move.

## Render
```sh
sh music/get_music.sh && python3 audio.py               # mix.wav
# after the Kling stick clip (Space Scene 3) is generated: tools/ingest_clip.sh k3 scene3.mp4
python3 render.py --start 0 --end 7.5 --out c0.mp4      # ... 4 chunks in parallel, then concat
ffmpeg -f concat -i list.txt -c copy video.mp4
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -af alimiter=limit=0.891:level=false -c:a aac -b:a 256k Funhoods_Musical_Stick_Reel_4K60.mp4
```
