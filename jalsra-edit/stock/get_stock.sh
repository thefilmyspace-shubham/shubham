#!/bin/sh
# Stand-in podcast clips for style_test.json — Mixkit Stock Video Free License (https://mixkit.co/license/)
cd "$(dirname "$0")" && for id in 44031 44033 44036 2955 44028; do curl -sSL -o s$id.mp4 https://assets.mixkit.co/videos/$id/$id-1080.mp4; done
