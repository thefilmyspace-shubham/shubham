# Jalsara: Diwali reel (9:16, 4K60, ~52 s)

Export: `Jalsara_Diwali_4K60.mp4`. The presenter speaks the Diwali script on camera; B-roll covers the lines about the venue and the menu.

**Footage** (shared on Drive, 8 Nov 2026):
- Folder 1 (`1UrVysT0OPz21QmKrT2CkyhyVpvWY9QYq`): originals of the interiors, the food and the two selfie A-rolls.
- Folder 2 (`1fKWNnXoNNzuWIv_B0N65Vy3593prWrQg`): the full-body A-rolls in 4K (IMG_1130, 1136, 1143, 1151). Everything else in it is a 568×320 Google Photos copy.
- **IMG_1124** ("Hello dosto") exists only as that 320p copy. Shubham said to use it anyway, so it is on screen for only 1.9 s (walk-in) and the rest of the line plays over a 4K B-roll.

**Script → clip** (lines found by transcribing each clip with a local Whisper model)

| # | Line | A-roll | B-roll over the voice |
|---|---|---|---|
| 1 | Hello dosto… shubhkaamnaayein | IMG_1124 (320p) | IMG_1043 arch + lamp |
| 2 | Iss Diwali… extra special | IMG_1130 | IMG_1052 set tables |
| 3 | Ek zaroori baat… Padwa ho ya Bhai Dooj | IMG_1151 | IMG_1111 tables + food |
| 4 | Project B ke final touches… brand new interiors | IMG_1136 (night exterior, voice only) | IMG_1042, 1044, 1041, 1040 interiors |
| 5 | Ek aur exciting surprise… new menu pre-launch | 4FE2E755 Copy (selfie) | IMG_1106 platter, IMG_1083 chaat |
| 6 | first few logon mein… introductory price | IMG_1177 (selfie) | IMG_1064 palak |
| 7 | Toh der kis baat ki… Happy Diwali | IMG_1143 (Jalsara arch) | — |

**Look:** the approved Project B teaser v2/v3 system.
- Footage sits in a rounded 3:4 window on a warm terracotta background with line arches.
- Text appears letter by letter with a dreamy blur. Headlines sit above the window, never on faces.
- No beat pulses, shake or jitter. Each shot gets one slow push, and every cut has a soft light-bloom.

**Diwali layer:**
- two strings of twinkling fairy lights at the top
- slow golden sparks
- an end card: JALSARA · Hotel · Restaurant · Banquet → Happy Diwali → from the Jalsara family → open all festive days · Ratlam

**Headlines (one per spoken beat):**
Hello dosto → Happy Deepawali → celebrate with family → make it extra special → open all festive days → Padwa to Bhai Dooj → Project B · final touches → brand new interiors → a brighter Diwali → an exciting surprise → new menu pre-launch → be among the first few → special intro price → make memories → we're waiting for you.

**Captions:** there are no word-by-word captions. The local transcription was not reliable enough in Hinglish to time every word, so the headlines carry the message for sound-off viewers. If word captions are wanted, use CapCut auto-captions on the export and keep them inside the window bottom.

**Sound:**
- The presenter's own voice from each take, level-matched, lightly denoised, EQ'd and compressed. Loudness is about -14 LUFS.
- Soft swells at each new setup, and chimes on the end card.
- **No music bed.** Add a festive track on Instagram at about 10–15% volume so it sits under the voice.

**Rebuild** (sources in `$JALSARA_DIWALI_SRC`, default `../../../jalsara_diwali` with `src/` and `src2/`; needs `tfs-promo/film`):
```sh
python3 diwali.py --base            # base.mp4: all shots cropped to the window, graded, concatenated
python3 diwali_audio.py             # diwali_mix.wav
python3 diwali.py --scale 2 --start 0 --end 13.2 --out c0.mp4   # 4 chunks (13.2 / 26.4 / 39.6 / end) in parallel
# concat the chunks + mux diwali_mix.wav
```
