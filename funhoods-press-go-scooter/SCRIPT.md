# Funhoods — Press & Go Scooter (PL-001) · VO script v3 (approved: sample 1, Gavin)

Reel: about 30 s · 9:16 · white-background motion graphics (same system as the earlier Funhoods reels) · B2B
(distributors & wholesalers only) · no phone number.

Product facts:
- **FUNHOODS_02.pdf, p. 11:** Press & Go Scooter (2 Model) · PL-001 · outer carton 240 pieces · size 4–5 inch.
  The card's icons are PRESS ACTION · GOES FORWARD · DURABLE & SAFE · KIDS FAVOURITE. The pack is a clear pouch with a "Funhoods PRESS & GO" header card.
- **October catalogue:** PL-001 is listed as BIS Approved · Virgin Polymer.
- **Left out:** "no batteries" (not printed on the card or the label).

## VO v3 (English, cute and cheerful, about 70 words, about 28 s)

**Rule: the VO never speaks a sound effect.** "Beep beep", "zoom", "vroom", "rawr", "whoosh" and the like are
sound effects in the mix, never words in the voice-over.

```
[cheerful] Meet the Funhoods Press and Go Scooter!
Just press the head... watch it turn... and off it goes!
Two cute riders, a little mouse and a happy duck!
Bright blue, red and orange scooters.
BIS certified, Made in India and non-toxic.
In a see-through pouch that shows off every rider.
Two hundred forty pieces per carton, pan India delivery.
Distributors and wholesalers, fill your shelves with Press and Go!
[excited] Funhoods... Childhood Full of Fun!
```

SFX (in the mix, not in the VO):
- toy scooter horn "beep beep": opening
- the scooter's real gear whirr on each press (`audio/og_press_*.wav`)
- the real wheel whirr and a whoosh when it goes (`audio/og_go*.wav`)

### v2 facts (client photos + raw clips, Drive 5 Nov)
- **Models:** two riders, a **mouse** and a **duck**. Photos show the mouse on blue and red scooters, and the duck on blue and orange scooters.
- **Pack back label:** "Press the Head" · Usage age 3 Years+ · Item code PL-001 · Made in India · 100% safe for children, non-toxic ·
  IS 9873 (Part-1), BIS CM/L 8200185112. The MRP and the customer-care number are on the label but are NOT used.
- **How it works** (raw clips, reference only): press the head down a few times. The neck slides into the body, the gear whirrs, and **the head turns on each press** (the label prints "360°" over the head). Let go, and the scooter shoots forward.
  Real sounds: `audio/og_*.wav` (`tools/og_sound.py`).

How-it-works animation in the edit (Dino Car style, `render.py` scene_press):
- A finger presses the head down **4 times**. Each time the neck sinks in, the real gear whirr plays, and the head makes a
  quarter turn: front → left → back → right → front (the full 360° on the label).
- The finger holds the last press, then lets go. The scooter shoots forward with speed lines and the real wheel whirr.

## VO samples v3 (`audio/`, Magnific / ElevenLabs v4)
- `VO_sample_1_Gavin.mp3` (playful, 31.6 s) and `VO_sample_2_Callum.mp3` (warm, 29.1 s): v3 script, no spoken SFX.
- `sfx_horn_beep_1/2.mp3`: the "beep beep" horn as a sound effect.
- The v2 samples (they spoke "beep beep" and "zoom") are kept in `audio/old_v2/`.
