# Jalsra interview edit (≤ 1:15)

Hook montage (Raj Shamani / DOAC cold-open style) → title reveal on the music drop → interview with smooth
word-by-word text (minimal style: bold key word + serif italic words) → outro. Reference board:
https://claude.ai/artifact/6qZ75nUhgXPWBZSQHJUqYQ

## Setup
```sh
pip install skia-python numpy scipy faster-whisper   # Linux pe libegl1 bhi chahiye
```

## Workflow
1. Footage `footage/` mein (Drive folder "Anyone with the link" share karke, file IDs se
   `curl -L -o footage/NAME "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"`).
2. `python3 transcribe.py footage/*.MP4 --roman` → har file ka `.txt` (segments + timestamps) aur `.words.json` (word times).
3. Transcript se hook lines (5–6, 1.5–2.5 s each) aur main story arc chuno → `edl.json` likho
   (format: `style_test.json` dekho; caption word times source-time mein hote hain).
4. Stills check: `python3 edit.py edl.json --stills 2,9,20 --stills-dir stills`
5. Render: `python3 edit.py edl.json --out Jalsra_Interview.mp4`
   (chunks: `--start 0 --end 30 --no-audio --out p0.mp4` …, phir concat + audio mux).

## EDL notes
- `timeline`: `clip` (src/in/out, `section` hook|main, `captions`, `crop_x`, `zoom`, `punch`, `focus`), `title`, `outro`.
- Hook clips get a flash + zoom punch on the cut; the title gets a white flash + impact on the drop.
- `music.drop` = drop time inside the track; it is aligned to the title's start automatically.
- Levels (dB): `hook_db`, `title_db`, `main_db`, `outro_db`; dialogue is normalised per clip to `dialogue_rms_db` (−20),
  final mix loudnorm −14 LUFS / −1.5 dBTP.
- Devanagari words switch to Noto Sans Devanagari automatically.

## Style test (stand-in footage)
```sh
sh stock/get_stock.sh && python3 edit.py style_test.json --out out_style_test.mp4
```

## Licences
- Music: `music/trap_hamza.mp3` — Mixkit "Trap Hamza", Mixkit Stock Music Free License (commercial use, no attribution). See `music/LICENSE.txt`.
- Fonts: Inter, Instrument Serif, Noto Sans Devanagari — SIL Open Font License.
- Stand-in clips (style test only): Mixkit Stock Video Free License.
