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
