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
