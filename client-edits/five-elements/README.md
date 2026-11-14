# The Five Elements — animated "Sushi" reel

Animated remake of the client reel (IG DezE1gUAeGm). Everything is drawn in code (SVG) and rendered with headless Chromium.

- **v2 (current, 31.5 s):** new short script, AI voices. Guest = ElevenLabs "Abhishek - Conversational Hinglish" (eleven_v4); waiter = Magnific voiceover "Deepak Singh" (eleven_v4). Raw takes are in `vo/`. No music bed (add on Instagram).
- **v1 (33 s):** original reel voices cut down — rejected ("script adhi kat di"). See git history.

    python3 build_audio.py                        # places vo/ lines per timeline.json -> build/audio.wav + lip-sync envelope
    node render.js --stills 3,9,20                # preview stills -> build/stills
    for p in 0 1 2 3; do node render.js --scale 2 --fps 60 --part $p --parts 4 & done; wait
    ffmpeg -framerate 60 -i build/frames/f%06d.jpg -i build/audio.wav -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -shortest export/out.mp4

- `timeline.json`: where each voice line sits (`[file, clip_in, clip_out, place_at]`).
- `anim.html`: scenes, characters, captions and shot list (`SHOTS`, `SPEAK`, `CAPS`, in output seconds).

## Script v2 (approved by Shubham, punchline scene removed at his request)
Waiter: Hello sir! Aaj kya lenge? — Guest: Wahi… regular laga do.
Waiter: Sir, ek baat bolun? Aap har baar naye outfit mein aate ho… par order hamesha wahi regular!
Guest: (hanste hue) Haan yaar… mujhe nayi cheezein explore karna pasand hai.
Waiter: To phir aaj khaane mein bhi kuch naya try kijiye!
**Sushi** — Waiter: Fresh sushi, authentic sauce ke saath.
Guest: (khaate hue) Mmm… kya cheez hai ye! — Logo.
