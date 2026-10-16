#!/bin/sh
# usage: ingest_clip.sh <name k1..k4> <video file>  -> clips/<name>/%05d.png + fps.txt (1080x1920)
set -e
d="$(dirname "$0")/../clips/$1"; mkdir -p "$d"; rm -f "$d"/*.png
fps=$(ffprobe -v error -select_streams v -show_entries stream=r_frame_rate -of csv=p=0 "$2" | awk -F/ '{printf "%.4f", $1/($2?$2:1)}')
ffmpeg -v error -y -i "$2" -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" -start_number 0 "$d/%05d.png"
echo "$fps" > "$d/fps.txt"; echo "$1: $(ls "$d" | grep -c png) frames @ $fps fps"
