#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo 'usage: assemble-live-demo.sh OUTPUT.mp4 INPUT1 INPUT2 [INPUT...]' >&2
  exit 2
fi

output=$1
shift
inputs=("$@")
ffmpeg_inputs=()
filter=''
labels=''

for index in "${!inputs[@]}"; do
  input=${inputs[$index]}
  if [[ ! -s $input ]]; then
    echo "missing recording input: $input" >&2
    exit 2
  fi
  ffmpeg_inputs+=(-i "$input")
  filter+="[$index:v]scale=1440:900:force_original_aspect_ratio=decrease,pad=1440:900:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1[v$index];"
  labels+="[v$index]"
done

filter+="${labels}concat=n=${#inputs[@]}:v=1:a=0[outv]"

ffmpeg -hide_banner -loglevel error -y \
  "${ffmpeg_inputs[@]}" \
  -filter_complex "$filter" \
  -map '[outv]' \
  -c:v libx264 \
  -preset medium \
  -crf 20 \
  -pix_fmt yuv420p \
  -movflags +faststart \
  "$output"

ffprobe -v error \
  -show_entries format=duration,size \
  -show_entries stream=codec_name,width,height,pix_fmt \
  -of json \
  "$output"
