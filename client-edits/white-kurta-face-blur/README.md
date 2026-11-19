# White kurta face blur (sangeet drummer clip)

Source: Google Drive "Document from Shubh" (iPhone HDR/Dolby Vision HEVC, 1080x1920, 72.4s).

Output: `white_kurta_face_blur_edit.mp4` — 1080x1920 H.264, original audio (no music).

## What was done
1. HDR (HLG) -> SDR tonemap (zscale + hable), auto-rotated to vertical.
2. `track.py` — YOLO11m-pose + BoT-SORT person tracking on every frame.
3. `heads2.py` — picks the bearded man in the white kurta across track IDs
   (A: dancing 0–31s, B: 31s–end incl. singing at the mic), fills detection gaps with
   CSRT tracking / manual keyframes, smooths the head path.
   Between ~28–42s a second bearded man in a white/cream kurta is near him; both are blurred there to be safe.
4. `blur.py` — feathered elliptical pixelate + gaussian blur over the head on every frame.
5. Finish (ffmpeg): vidstab stabilization (smoothing 20, optzoom), mild unsharp, contrast/saturation/warmth grade,
   S-curve, 0.3s fade-in / 0.6s fade-out. Audio untouched apart from the fades (already ~-14.5 LUFS).
