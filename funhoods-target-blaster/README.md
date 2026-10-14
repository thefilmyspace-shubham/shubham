# Funhoods — Target Blaster B2B Reel (9:16, 1080x1920, 30 fps, 39 s)

`exports/Funhoods_Target_Blaster_B2B_Reel_1080x1920.mp4` (master, 44 MB) · `..._share.mp4` (22 MB, WhatsApp/upload ke liye)

Retailers / distributors / wholesalers ke liye product reel: AI videos ke clean parts + catalogue close-ups + motion graphics.
Music: **"Punked Up Fun" — Ahjay Stelino (Mixkit)**, Mixkit Stock Music Free License (commercial use OK, no attribution required).
Fonts: Lilita One (OFL), Luckiest Guy (Apache 2.0), Inter (OFL).

## Structure (130 BPM, har cut beat par)
| Time | Scene | Text |
|---|---|---|
| 0.0–1.8 | Funhoods logo | NEW LAUNCH · For Retailers • Distributors • Wholesalers |
| 1.8–3.7 | Real pack (catalogue) | INTRODUCING TARGET BLASTER · FOAM DART BLASTER • AGES 3+ |
| 3.7–7.4 | Hero + out-of-pack | BUILT TO FLY OFF YOUR SHELVES! · READY TO PLAY |
| 7.4–11.1 | Key features | Twin-barrel nozzle · Police badge design · Textured easy grip · Soft foam darts |
| 11.1–18.5 | How it works | 1 PULL BACK · 2 LOAD DARTS · 3 AIM... |
| 18.5–20.3 | Music drop | FIRE! (2 darts, synced SFX) |
| 20.3–27.7 | Why retailers stock it | Eye-catching retail pack · Complete play set · Police theme kids love · Great for gifting & impulse buys |
| 27.7–31.4 | Partner | NOW TAKING BULK ORDERS · Retailers / Distributors / Wholesalers |
| 31.4–33.2 | — | STOCK UP NOW! |
| 33.2–39.0 | End card | Funhoods logo · BULK & WHOLESALE ENQUIRIES OPEN · DM US FOR TRADE PRICING |

## Footage edit log (product match vs catalogue)
Mechanism real video se verify kiya: hook pull → rod bahar (cocking) → front twin nozzle mein darts (suction tip bahar) → trigger.
AI clips mein jahan product badla, woh hata diya:
- **AI-A (…72324 = …72325, same file):** 10.8–12.0s & 13.0–13.9s (badge blank, do hooks), 8.3–8.6s (instant flip), 15.2–17s (body shape change), 22.1–22.48s (hook pull par badge smeared),
  17.5–20s (dart peeche se load), pack shots 0–6s (pack par brand "Fruneels" garbled).
- **AI-B (…72327):** 12.0–17.0s (body stretch / upside-down morph), 5.0–5.6s (badge glitch), pack shots + 6.1–8.6s (background pack text garbled), 23.5s+.
- **AI-C (…72326):** 13.0–15.4s (POLICE badge gayab), 16.2–16.9s (hook loop ban gaya), 18.4–18.8s (dart ulta), pack 0–4.8s ("Romget", age "1D").
- Pack shots sirf catalogue ki real packaging se (upscaled), AI pack nahi.

Used ranges: `shots.py` + `timeline.py`.

## Render
Inputs `src/` mein: `ai_a.mov ai_b.mov ai_c.mp4 catalog.webp logo.png`; model `models/realesr-general-x4v3.pth`
(https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth).
```sh
pip install torch numpy pillow --index-url https://download.pytorch.org/whl/cpu
for s in a b c; do mkdir -p dec/${s^^}; ffmpeg -i src/ai_$s.* -start_number 0 dec/${s^^}/%05d.png; done
python3 tools/prep_assets.py crops && OUTW=0 python3 tools/sr.py models/realesr-general-x4v3.pth cat_in cat_sr && python3 tools/prep_assets.py cutouts
# used footage frames -> sr_in/<idx>_<A|B|C><frame>.png, phir 480p -> 1080p Real-ESRGAN (72% SR + 28% lanczos blend in render.py)
python3 tools/sr.py models/realesr-general-x4v3.pth sr_in sr_out
python3 audio.py                                   # mix.wav (music edit + SFX)
python3 render.py --out video.mp4                  # --start/--end se chunks parallel; --stills 5,18.6 for checks
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k Funhoods_Target_Blaster_B2B_Reel_1080x1920.mp4
```
CTA abhi generic hai ("DM US FOR TRADE PRICING") — phone/website/WhatsApp number mile to `scene_end()` mein add kar do.
