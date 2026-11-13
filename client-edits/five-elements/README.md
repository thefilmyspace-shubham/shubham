# The Five Elements — animated "Sushi" reel

Animated remake of the client reel (IG DezE1gUAeGm, 63 s) cut down to 33 s. Everything is drawn in code (SVG) and rendered with headless Chromium; the voices are the original reel audio, cut to the short script.

    python3 build_audio.py /path/to/reel.mp4      # short audio + lip-sync envelope -> build/
    node render.js --stills 1,8,18                # preview stills -> build/stills
    for p in 0 1 2 3; do node render.js --scale 2 --fps 60 --part $p --parts 4 & done; wait
    ffmpeg -framerate 60 -i build/frames/f%06d.jpg -i build/audio.wav -c:v libx264 -crf 17 -pix_fmt yuv420p -c:a aac -shortest export/FiveElements_Sushi_Animated_4K60.mp4

- `timeline.json`: which parts of the original audio are kept.
- `anim.html`: scenes, characters, captions and shot list (`SHOTS`, `SPEAK`, `CAPS` use original-reel timestamps).

## Short script (33 s)
Waiter: Hello sir! How are you? — Guest: I'm good, sir. Aap batao — Waiter: Main bhi badhiya hu sir. Kya lenge sir aaj? — Guest: Wahi regular laga do.
Waiter: Sir main aapko alag-alag outfits mein dekha hai. — Guest: Actually sir mujhe nayi-nayi cheezein explore karna pasand hai.
Waiter: Agar sir aapko explore karna itna pasand hai… to phir order mein aaj kuch naya try kare. Actually chhodiye sir, aap ye try kijiye.
**Sushi** — Waiter: Haan sir. Fresh mouth-watering sushi, authentic sauce ke saath. — Guest: Hmm… kya hai ye…
Waiter 2: Sir… aaj kuch naya try kiya kya? — Guest: Hmm.. — Logo.

Dropped from the original: "ek cheez pooch sakta hoon aapse? / Haan, boliye", "Jab bhi aate ho aap, sab alag-alag outfit rehte hai sir", "Haan actually aap sahi…", and the long eating montage.
