# Jalsra interview edit (≤ 1:15)

Hook montage (cold-open style) → title reveal on the music drop → interview → outro.
Text style = the two reference reels (Instagram DXanI5ECvq-, DXeU5dDkeXe), rebuilt frame by frame in `kinetic.py`.
Reference board: https://claude.ai/artifact/6qZ75nUhgXPWBZSQHJUqYQ

## Text style (kinetic.py), measured from the references at 30 fps
- **Type:** Helvetica-Neue-style mixed weights in one stack: thin/light (or light italic) connector words, medium or
  bold (italic) key words. Tight negative tracking, tight leading (baseline gap ≈ 0.85× the next line's size),
  stepped indents. Font: **Aileron** (CC0, a free Helvetica-style family with matching weights). For real Helvetica Neue, put the licensed
  files in `fonts/` and map them in the EDL: `"fonts": {"bold": "fonts/HelveticaNeue-Bold.ttf", "thin": ...}`.
- **Entry:** each word comes in on its spoken time, rising from 1.35 em below with ease-out-expo over 0.33 s
  (the offset halves every frame). It is visible from the first frame and has real motion blur (10 sub-frame samples, centred 360° shutter),
  which reproduces the reference's echo streaks.
- **Exit:** words leave upward half a frame apart, ease-in-cubic over 0.1 s (gone in 3 frames), with the same blur.
- **Key-word fills** sampled from the reels: `cyan`, `blue`, `azure`, `navy`, `chrome` (gradient + slow sheen), plain `white`.
- **Behind the speaker:** `"layer": "behind"` puts a word behind the person (Robust Video Matting person matte, computed per frame).
- **Caps:** `{"style": "caps"}`: one centred upper-case word at a time, medium weight with a soft shadow and quick blur fades.

## Setup
```sh
pip install skia-python numpy scipy onnxruntime faster-whisper   # Linux pe libegl1 bhi chahiye
# RVM matte model downloads itself on first use into models/ (GPL-3.0, not committed)
```

## Workflow
1. Put the footage in `footage/`. Share the Drive folder as "Anyone with the link", then download each file by its ID:
   `curl -L -o footage/NAME "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"`.
2. Run `python3 transcribe.py footage/*.MP4 --roman` to get a `.txt` per file (segments with timestamps) and a `.words.json` (word times).
3. Pick 5–6 hook lines (1.5–2.5 s each) and the main story from the transcript, then write `edl.json`.
   Text blocks go in each clip's `"text"`, with word `t` in source time (see `style_test.json`).
4. Check stills: `python3 edit.py edl.json --stills 2,9,20 --stills-dir stills`
5. Render: `python3 edit.py edl.json --out Jalsra_Interview.mp4`

## Text block format
```json
{"anchor": [0.185, 0.536], "end": 14.2, "lines": [
  {"words": [{"w": "Look", "t": 12.30, "weight": "medium", "size": 210}]},
  {"dx": 88,  "gap": 0.83, "words": [{"w": "at", "t": 12.45, "weight": "thin", "size": 120}, {"w": "your", "t": 12.52, "weight": "thin", "size": 120}]},
  {"dx": 125, "gap": 0.92, "words": [{"w": "standards", "t": 12.60, "weight": "bold", "size": 142, "fill": "cyan", "layer": "behind"}]}]}
```
Weights: `thin light regular medium semibold bold heavy`, plus `_i` for italic. Sizes are px at 1080 wide.
`anchor` is the first line's left baseline (or its centre with `"align": "center"`). `end` triggers the exit.

## Style test (stand-in footage, sample text)
```sh
sh stock/get_stock.sh && python3 edit.py style_test.json --out out_style_test.mp4
```

## Licences
- Music: `music/trap_hamza.mp3` is Mixkit "Trap Hamza", under the Mixkit Stock Music Free License (commercial use, no attribution). See `music/LICENSE.txt`.
- Font: Aileron by Dot Colon, CC0 (`fonts/Aileron-LICENSE.txt`).
- Person matte: Robust Video Matting (GPL-3.0). The model is downloaded at runtime and not redistributed here.
- Stand-in clips (style test only): Mixkit Stock Video Free License.
