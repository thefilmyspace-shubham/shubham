# Jalsara: "Project B" teaser (9:16, 15s, 4K60)

Cut from `JALSARA 17.10 (interview)`, which Shubham shared on Drive. Export: `Jalsara_ProjectB_Teaser_4K60.mp4`.

**Structure**
- **0–2.7 s:** hook. "Project B abhi toh main reveal nahi karunga" with a glitch "PROJECT B" title.
- **2.7–4.5 s:** "SINCE 1990" montage on the beat. Two B&W intro shots, then the father, then the two-shot, under the "1990 mein…" line.
- **Bites:**
  - "toh woh sab Project B laane wala hai"
  - "aur Ratlam walon ko bahut hi maza aayega"
  - "pura naya experience rahega unke liye"
  - "ki Jalsara mein naya kya hone wala hai?"
- **12.45 s:** end card on the music hit. PROJECT B, JALSARA, "Ratlam · Reveal this month", STAY TUNED.

**Edit notes**
- The interview's burned-in subtitles are hidden under a frosted caption card that carries new kinetic Hinglish captions (key words in amber).
- The last bite cuts to a reaction shot before the source's own "till then" title appears; the audio continues underneath.

**Sound**
- Voice is the Demucs vocal stem, so the interview's own music doesn't clash.
- Music is Mixkit "Epical Drums 01" (https://assets.mixkit.co/music/676/676.mp3, Mixkit license), ducked about 11 dB under speech.
- SFX: synth hits (from `tfs-promo/film/film_audio.py`) plus whoosh, impact and shutter files.

**How to rebuild** (needs `tfs-promo/film` alongside, the source at `../jalsara_dl/jalsara.mp4`, and the Demucs stem at `sep/htdemucs/a/vocals.wav`):
```sh
python3 teaser.py --base                        # base.mp4: graded, concatenated shots
python3 teaser_audio.py                         # teaser_mix.wav
python3 teaser.py --scale 2 --start 0 --end 3.75 --out t0.mp4   # 4 chunks, then concat + mux
```

## v2 — dreamy, text-led (`Jalsara_ProjectB_Teaser_v2_4K60.mp4`)
Shubham's feedback on v1:
- music → Daydream
- no text on faces
- better text animation
- fix the jitter
- 3:4 rounded frame with side margins

What changed:
- **Frame:** the interview sits in a rounded 3:4 window (960×1280 design px, 60 px side margins). The crop stops above the burned-in subtitles, so no patch is needed.
- **Background:** warm terracotta background with line arches (the venue's niche motif) drawing in, plus drifting light orbs and grain.
- **Text placement:**
  - Headlines sit above the window: Project B → since 1990 → ten years in the making → for Ratlam → a whole new experience → what's next?
  - Speech captions sit inside the window bottom, over a soft shadow, away from faces.
- **Fonts:** Playfair Display + Allura script (gold) + Inter Tight. Every letter fades up from a blur.
- **Jitter:** no beat pulses or shake. Only a slow push per shot, with a soft light-bloom across cuts.
- **Audio:** voice + soft SFX only, with **no music bed**. Add "Daydream" (Günter Kallmann Choir) from Instagram's music library when posting. It's licensed there, and a baked-in copy may get muted.
```sh
python3 teaser2.py --base && python3 teaser2_audio.py
python3 teaser2.py --scale 2 --start 0 --end 3.75 --out t0.mp4   # 4 chunks, concat, mux teaser2_mix.wav
```

## v3 — opening line only, then a visual edit (`Jalsara_ProjectB_Teaser_v3_4K60.mp4`)
Feedback on v2: everything after the opening line felt chopped together. So v3 changes the structure:
- **0–2.7 s:** only "Project B abhi toh main reveal nahi karunga" is spoken.
- **2.7–12.45 s:** a silent visual edit of 10 clean shots, under these headlines:
  - three B&W flashes + father → since 1990
  - both together → ten years in the making
  - son → father → for Ratlam
  - son → both → a whole new experience
  - son → what's next?
- **12.45 s:** end card.

Music: add "Daydream" (Günter Kallmann Choir) on Instagram, with the start point set where the lyrics come in after the intro.
```sh
python3 teaser3.py --base && python3 teaser3_audio.py
python3 teaser3.py --scale 2 --start 0 --end 3.75 --out t0.mp4   # 4 chunks, concat, mux teaser3_mix.wav
```
