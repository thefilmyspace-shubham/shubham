#!/usr/bin/env python3
"""Aman Jain Live: slow cinematic event reel (style of the IG 'sufi night' reference).

Usage:
  python3 edit.py --src DIR --work DIR --out FILE [--w 2160] [--fps 30] [--mute]

Pipeline: each shot is trimmed, slowed, graded and given a slow push-in -> soft
cross-dissolves -> centred "aman jain live" title (Marck Script) -> grain -> live audio bed.
"""
import argparse, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))

# (clip, src_start, speed, out_dur)  speed < 1 = slow motion
SHOTS = [
    ("IMG_0102.MP4", 7.10, 0.60, 2.8),   # lantern tree, opener
    ("IMG_0103.MOV", 0.40, 0.75, 2.8),   # Aman, guitar, close
    ("IMG_0257.MOV", 0.05, 0.50, 2.6),   # audience from behind, bulbs
    ("IMG_0283.MOV", 0.30, 0.50, 2.6),   # audience faces
    ("IMG_0286.MOV", 0.00, 0.50, 2.5),   # stage wide
    ("IMG_0287.MOV", 4.40, 0.50, 2.6),   # keyboard player
    ("IMG_0288.MOV", 0.20, 0.50, 2.6),   # crowd vibing
    ("IMG_0103.MOV", 3.80, 0.75, 2.8),   # Aman, second moment
    ("IMG_0258.MOV", 2.20, 0.50, 2.6),   # garden pan wide
    ("IMG_0260.MOV", 0.30, 0.50, 2.6),   # wide, dancing
    ("IMG_0289.MOV", 3.90, 0.50, 3.4),   # back wide, string lights (end)
]
XF = 0.6  # dissolve length

GRADE = (
    "huesaturation=hue=-8:saturation=-0.55:intensity=-0.02:colors=g+y:strength=1,"
    "eq=brightness=-0.05:contrast=1.08:saturation=0.9:gamma=0.92,"
    "colorbalance=rs=0.0:gs=0.0:bs=0.03:rm=0.04:gm=0.02:bm=-0.07:rh=0.05:gh=0.025:bh=-0.08,"
    "curves=master='0/0.02 0.25/0.18 0.6/0.58 1/0.94'"
)


def run(cmd):
    print(" ".join(cmd)[:300], file=sys.stderr)
    subprocess.run(cmd, check=True)


def render_shot(i, shot, a):
    clip, ss, speed, dur = shot
    W, H, fps = a.w, a.w * 16 // 9, a.fps
    src_len = dur * speed + 0.1
    out = os.path.join(a.work, f"s{i:02d}.mov")
    if os.path.exists(out) and not a.force:
        return out
    blur = max(2, W // 160)
    vf = (
        f"setpts=(PTS-STARTPTS)/{speed},"
        f"framerate=fps={fps}:interp_start=0:interp_end=255:scene=100,"
        f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},"
        f"{GRADE},"
        # slow push-in (about 5% over the shot), centre crop
        f"scale=w='trunc({W}*(1+0.05*t/{dur})/2)*2':h=-2:eval=frame:flags=bicubic,crop={W}:{H},"
        # soft glow: blurred copy screened at low opacity
        f"split[a][b];[b]gblur=sigma={blur}[g];[a][g]blend=all_mode=screen:all_opacity=0.22,"
        f"vignette=angle=PI/4.2:mode=forward,format=yuv420p10le"
    )
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(ss), "-t", f"{src_len:.3f}", "-i",
         os.path.join(a.src, clip), "-filter_complex", vf, "-t", f"{dur:.3f}", "-an",
         "-r", str(fps), "-c:v", "prores_ks", "-profile:v", "1", out])
    return out


def title_png(a):
    W, H = a.w, a.w * 16 // 9
    path = os.path.join(a.work, "title.png")
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype(os.path.join(HERE, "fonts", "MarckScript-Regular.ttf"), int(W * 0.062))
    text = "aman jain live"
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), text, font=font, stroke_width=max(1, W // 900))
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x, y = (W - tw) // 2 - bb[0], int(H * 0.485) - bb[1]
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((x, y + W // 400), text, font=font, fill=(0, 0, 0, 150),
                            stroke_width=max(1, W // 900), stroke_fill=(0, 0, 0, 150))
    sh = sh.filter(ImageFilter.GaussianBlur(W // 200))
    im = Image.alpha_composite(im, sh)
    ImageDraw.Draw(im).text((x, y), text, font=font, fill=(255, 250, 242, 245),
                            stroke_width=max(1, W // 900), stroke_fill=(255, 250, 242, 245))
    im.save(path)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--w", type=int, default=2160)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--audio", default="")  # pre-mixed wav; empty = silent
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    os.makedirs(a.work, exist_ok=True)

    files = [render_shot(i, s, a) for i, s in enumerate(SHOTS)]
    total = sum(s[3] for s in SHOTS) - XF * (len(SHOTS) - 1)
    title = title_png(a)

    inputs, fc = [], []
    for f in files:
        inputs += ["-i", f]
    prev, off = "[0:v]", 0.0
    for i in range(1, len(files)):
        off += SHOTS[i - 1][3] - XF
        lab = f"[x{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{lab}")
        prev = lab
    n = len(files)
    inputs += ["-loop", "1", "-framerate", str(a.fps), "-i", title]
    fc.append(f"[{n}:v]format=rgba,fade=t=in:st=0.5:d=1.4:alpha=1,"
              f"fade=t=out:st={total - 1.6:.2f}:d=1.2:alpha=1[t]")
    fc.append(f"{prev}[t]overlay=0:0:shortest=1,noise=alls=7:allf=t,"
              f"fade=t=in:st=0:d=0.8,fade=t=out:st={total - 1.0:.2f}:d=1.0,format=yuv420p[v]")
    cmd = ["ffmpeg", "-v", "error", "-y"] + inputs
    maps = ["-map", "[v]"]
    if a.audio:
        cmd += ["-i", a.audio]
        maps += ["-map", f"{n + 1}:a", "-c:a", "aac", "-b:a", "256k"]
    cmd += ["-filter_complex", ";".join(fc)] + maps + [
        "-t", f"{total:.3f}", "-r", str(a.fps), "-c:v", "libx264", "-preset", "slow",
        "-crf", "16" if a.w >= 2000 else "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    run(cmd)
    print(f"done {a.out} ({total:.2f}s)")


if __name__ == "__main__":
    main()
