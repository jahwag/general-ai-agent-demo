#!/usr/bin/env bash
set -euo pipefail

before=${1:-artifacts/freshworks-before.mp4}
terminal=${2:-artifacts/terminal.mp4}
after=${3:-artifacts/freshworks-after.mp4}
output=${4:-artifacts/freshworks-agent-demo.mp4}

for input in "$before" "$terminal" "$after"; do
  if [[ ! -s $input ]]; then
    echo "missing recording input: $input" >&2
    exit 2
  fi
done

ffmpeg -hide_banner -loglevel error -y \
  -i "$before" \
  -i "$terminal" \
  -i "$after" \
  -filter_complex \
  "[0:v]scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v0];\
   [1:v]scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v1];\
   [2:v]scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v2];\
   [v0][v1][v2]concat=n=3:v=1:a=0[outv]" \
  -map "[outv]" \
  -c:v libx264 \
  -preset medium \
  -crf 20 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$output"

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate \
  -of json \
  "$output"
