# Funhoods V.O.

Style matched to the narrator of the Bonkers Corner reel (deep, measured Indian-English brand-film narrator), by voice
choice and delivery only; nothing from that reel's audio is used or cloned.

- `Funhoods_VO_A_Aakash_timed.mp3`: recommended. ElevenLabs "Aakash Aryan – Formal & Cinematic Ads" (multilingual v2), lines
  on the script timestamps (10 / 16 / 22 / 27 / 30 / 38 s), 45 s, −16 LUFS. "SKUs" re-generated and spliced for clarity.
- `Funhoods_VO_B_Pavan_timed.mp3`: punchier alternative, "Pavan M – Deep, Warm & Polished" (v4).
- `*_raw.mp3` / `funhoods_vo_aakash_fixed.wav`: full takes; `*.words.json`: word timings.
- Re-time: `python3 ../vo_timeline.py take.wav take.words.json OUT --tempo 1.12 --starts 10,16,22,27,30,38 --total 45`
