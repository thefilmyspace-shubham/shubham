#!/bin/sh
# Live-audio bed: IMG_0287 -> IMG_0102 -> IMG_0289, crossfaded, normalised, faded out.
# usage: sh audio.sh SRC_DIR OUT.wav LENGTH_SECONDS
SRC=$1; OUT=$2; LEN=$3
ffmpeg -v error -y -i "$SRC/IMG_0287.MOV" -i "$SRC/IMG_0102.MP4" -i "$SRC/IMG_0289.MOV" -filter_complex \
"[0:a]aresample=48000,highpass=f=70[a0];[1:a]aresample=48000,highpass=f=70[a1];[2:a]aresample=48000,highpass=f=70[a2];\
[a0][a1]acrossfade=d=1.5:c1=tri:c2=tri[m1];[m1][a2]acrossfade=d=1.5:c1=tri:c2=tri,\
loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.6,afade=t=out:st=$(python3 -c "print($LEN-2.2)"):d=2.2,atrim=0:$LEN" \
-ac 2 -ar 48000 "$OUT"
