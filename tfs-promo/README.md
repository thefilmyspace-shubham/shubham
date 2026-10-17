# TFS Promo (60s, 16:9)

The Filmy Space ka agency promo — animation + Instagram feed clips, ElevenLabs VO (Yatin voice), Mixkit music.

## Render
```sh
pip install skia-python numpy        # Linux pe libegl1 bhi chahiye
sh music/get_music.sh                # music download
python3 audio.py                     # -> mix.wav (VO + music ducking + SFX)
python3 render.py --out video.mp4    # -> 1920x1080 30fps (--w 3840 --fps 60 for 4K60)
ffmpeg -i video.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k TFS_Promo.mp4
```
Stills check: `python3 render.py --stills 2.6,16.2,30.0`

## Feed clips
Abhi saare clip slots placeholder hain. Real clips `clips/` mein daal ke `clips/map.txt` mein slot se map karo.
Slots: `reel_1..13`, `restaurant_1..5`, `gym_1..5`, `coaching_1..5`, `events_1..6`, `retail_1`, `tile_0..19`, `burst_a_0..2`, `burst_b_0..2`.

## Audio
- `audio/vo_take2.mp3` — VO used (take 1 bhi rakha hai). Word timings: `audio/vo_take2.mp3.words.json`
- `audio/sfx_*.mp3` — ElevenLabs sound effects; baaki chhote SFX `audio.py` mein synthesize hote hain.

## Vertical intro reel (9:16, 19.35s)
Foretell Studio reel ki timing par based, original logo (`logo.png`).
```sh
# feed reels ../feed/r1.mp4 ... r7.mp4 mein chahiye (yt-dlp se):
# r1 DYhHkWiNnU3, r2 DWf6R8FSMBN, r3 DWqxMcTk2cN, r4 DSIaYukEsCu, r5 DeRomZBAts6, r6 DdoZOkxgXbj, r7 DdYVVHMRR0b
python3 reel_audio.py && python3 reel.py --out reel.mp4
ffmpeg -i reel.mp4 -i reel_mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k TFS_Intro_Reel.mp4
```

## Brand reel (9:16, 43s, 4K60) — `exports/TFS_Brand_Reel_4K60.mp4`
Hyper Visuals reel ke structure par kinetic typography + feed clips. VO: ElevenLabs "Everett" (`brand_reel/TFS_brand_reel_VO.mp3`).
Music: Mixkit "Remember Me" (https://assets.mixkit.co/music/739/739.mp3 → `music/m739.mp3`).
```sh
python3 brand_audio.py   # brand_mix.wav  (brand_audio.py expects the VO at ../tfs2/; copy from brand_reel/)
python3 brand_reel.py --scale 2 --fps 60 --out brand_4k.mp4   # split with --start/--end to render in parallel
```

## Brand reel v2 (9:16, 35.44s, 4K60) — `exports/TFS_Brand_Reel_v2_4K60.mp4`
Reference (Hyper Visuals) ke music par re-timed: har VO sentence reference ki line ki jagah par (`SEG` in brand2.py),
camera drift + beat punches, whip/zoom/defocus motion-blur transitions, 10 reels se unique shots.
Music bed = reference audio se Demucs (htdemucs, two-stems) se nikala gaya `no_vocals.wav`.
```sh
python3 brand2_audio.py && python3 brand2.py --scale 2 --fps 60 --start 0 --end 9 --out p0.mp4   # ...chunks, then concat
```

## Brand reel v3 (9:16, 35.44s, 4K60) — `exports/TFS_Brand_Reel_v3_4K60.mp4`
v2 ki timing/music + 3D assets (Microsoft Fluent 3D emoji — MIT; NASA earth texture via three.js), ambientCG Paper001 (CC0),
DeepLabV3 person cut-outs (`assets3d/cut_*.png`), warm footage grade + caption-safe crops, bigger framing, words 0.06s before VO.
Note: brand3.py expects the paper texture at assets3d/paper/Paper001_2K-JPG_Color.jpg (copied here to assets3d/).

## Motion-graphic film "Every brand deserves a blockbuster" (9:16, 41.7s, 4K60) — `exports/TFS_Blockbuster_MG_4K60.mp4`
Own concept: TFS ka promo ek movie trailer ki tarah. Pure motion graphics, koi client footage nahi, aur zero paid credits.
Scenes: green rating card ("approved for all brands") → film-leader countdown 3-2-1 → "In a world of endless scrolling" (grey 'extras' feed)
→ spotlight "The lead." → clapperboard → WRITTEN BY (screenplay typing) → DIRECTED BY (viewfinder focus pull) → SHOT BY (lens + iris)
→ EDITED FOR (NLE timeline, "the first 3 seconds") → STARRING (17 clients + "& 20+ brands") → split-flap "NOW SHOWING / ON YOUR FEED"
(music drop) → letterbox opens: "Every brand deserves a BLOCKBUSTER." → film strip stops on the T/F/S logo blocks (original logo).
Music: Mixkit "Epical Drums 05" (https://assets.mixkit.co/music/680/680.mp3, Mixkit license); every cut is on the fitted beat grid (`beats680.json`).
SFX: synthesised in `film_audio.py` (braam, boom, riser, beeps, clap, typing, flap clicks) + earlier ElevenLabs whoosh/impact files.
Fonts: Cinzel, Courier Prime, Inter Tight (Google Fonts, OFL), Anton, Bebas Neue.
```sh
cd film && sh get_music.sh
python3 film_audio.py                                   # film_mix.wav (-14 LUFS)
python3 film.py --scale 2 --fps 60 --start 0 --end 10.433333 --out c0.mp4   # 4 chunks in parallel, then concat
python3 film.py --scale 0.5 --stills 10.5,22,29         # quick style frames
```
