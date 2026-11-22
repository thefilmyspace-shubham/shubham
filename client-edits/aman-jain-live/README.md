# Aman Jain Live: event reel (9:16, 23.9 s, 4K 30 fps)

Reference: IG reel DSkT940kqyS (a "sufi night" college event montage). Footage: 10 iPhone clips from Aman's Drive folder (garden acoustic night).

**Brief from Shubham (2026-11-22):** make the same kind of edit, in a slow pace. Don't write "sufi night"; write **Aman Jain live** in the reference's font.

## What the reference does, and what we kept
- A cinematic event montage: musicians, fairy lights and bokeh, then crowd reactions, then the stage, ending on the performer.
- A dark, warm, cinematic grade with glow and a vignette.
- One small brush-script title held in the centre for the whole reel. We wrote "aman jain live" in **Marck Script**, the closest free match to the reference's script. Its width is about 33% of the frame, the same as the reference.
- Not carried over: the reference's subtitle line ("A night of ghazals…") and the editor's handle.

## Slow pace
- The 60 fps clips play at 0.5× (real slow motion). The 30 fps clips play at 0.6–0.75× with frame blending.
- 11 shots of 2.5–3.4 s each, joined by 0.6 s cross-dissolves (the reference cuts about every 1.3 s).
- A slow 5% push-in on every shot. No shake or beat pulses.

## Shots
lantern tree → Aman close → crowd from behind → audience faces → stage wide → keyboard player → crowd vibing → Aman (second moment) → garden pan → wide with dancing → string-light wide (fade out). No source moment is used twice.

## Audio
- `Aman_Jain_Live_4K.mp4` has a bed made from the live audio of IMG_0287, IMG_0102 and IMG_0289, crossfaded and normalised to −14 LUFS. These are probably different parts of the set, so if Aman has a studio or clean recording of the song, swap it in.
- `Aman_Jain_Live_4K_no_music.mp4` is silent, for adding the song from Instagram's music library.

## Rebuild
```sh
sh audio.sh SRC_DIR mix.wav 23.9
python3 edit.py --src SRC_DIR --work WORK_DIR --out Aman_Jain_Live_4K.mp4 --w 2160 --audio mix.wav
python3 edit.py --src SRC_DIR --work WORK_DIR --out preview.mp4 --w 1080   # quick preview
```

## v2: original colours, stabilised, Aman's song (`Aman_Jain_Live_v2_4K.mp4`, 24.6 s)
Feedback on v1: *"color grading mt bdlo, clips ko stable rkho, mai song deta hu"* (don't change the colour grading, keep the clips stable, I'll send the song).
- **Colours:** the clips' original colours are kept. There's no grade, glow, vignette or grain. `--grade` brings back the v1 look.
- **Stabilisation:**
  - The v1 slow push-in is removed.
  - Every shot is stabilised with a vid.stab two-pass (smoothing 60, optzoom only as much as needed to hide the borders).
- **Audio:**
  - The song Shubham sent (`ReelAudio-88386.mp3`, 25.1 s) plays from 0 s.
  - It's cut at 24.6 s with a 0.7 s fade, where the track ends on its own.
  - To fit it, the last shot was extended to 4.1 s.
```sh
ffmpeg -i ReelAudio-88386.mp3 -af "atrim=0:24.6,afade=t=out:st=23.9:d=0.7" -ar 48000 -ac 2 song_cut.wav
python3 edit.py --src SRC_DIR --work WORK_DIR --out Aman_Jain_Live_v2_4K.mp4 --w 2160 --audio song_cut.wav
```

## v3: slow zoom in/out, jittery clip replaced (`Aman_Jain_Live_v3_4K.mp4`, 24.6 s)
Feedback on v2: "use slow zoom in zoom out effect and replace the clip jittering".
- **Jitter found by measurement.** The opener (IMG_0102, a 720p handheld lantern-tree pan) still moved about 2 px/frame after stabilising, with high variance. Every other shot was at about 0.1.
- **Opener replaced** with IMG_0289 at 0 s (string lights + stage, tripod-steady).
- **Ending changed** to IMG_0287 from 8.15 s (stage wide), so IMG_0289 isn't used twice.
- **Zoom:**
  - Even shots zoom in from 1.00 to 1.08; odd shots zoom out from 1.08 to 1.00.
  - The zoom is linear.
  - It uses the `perspective` filter with sub-pixel corners, so it doesn't step the way an integer `scale`/`zoompan` zoom does.
